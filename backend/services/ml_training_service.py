"""
ML Training Service — trains per-field confidence models from correction feedback.
"""

import joblib
import os
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score

from django.conf import settings
import structlog

logger = structlog.get_logger()


def _min_corrections_threshold():
    """Minimum number of corrections required before training a field model."""
    return getattr(settings, "ML_MIN_CORRECTIONS", 5)


def _extract_field_value(result_json, field_name):
    """
    ExtractionResult.result_json can store either
    {field_name: "value"} or {field_name: {"value": "...", "confidence": 0.9, ...}}
    Return the string value or "".
    """
    if not isinstance(result_json, dict):
        return ""
    entry = result_json.get(field_name)
    if entry is None:
        return ""
    if isinstance(entry, dict):
        return str(entry.get("value", "") or "")
    return str(entry)


def _extract_field_confidence(confidence_json, field_name, result_json=None):
    """
    ExtractionResult.confidence_json can store either
    {field_name: 0.9} or nested inside result_json as {field_name: {confidence: 0.9}}.
    Returns a float in [0, 1] or 0.5 if unknown.
    """
    if isinstance(confidence_json, dict):
        val = confidence_json.get(field_name)
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, dict) and "confidence" in val:
            return float(val["confidence"])
    if isinstance(result_json, dict):
        entry = result_json.get(field_name)
        if isinstance(entry, dict) and "confidence" in entry:
            try:
                return float(entry["confidence"])
            except (TypeError, ValueError):
                pass
    return 0.5


class MLTrainingService:
    """Trains and serves per-field ML models to improve OCR confidence scores."""

    def get_model_path(self, template_id, field_name):
        """Return (and create) the directory for a field model."""
        path = Path(settings.STORAGE_PATH) / "models" / str(template_id) / field_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train_field_model(self, template_id, field_name):
        """
        Train a GradientBoosting model for a specific template + field.

        Training data comes from ExtractionCorrection records.  The model
        learns to predict whether an extracted value is correct and produces
        a calibrated probability used to adjust OCR confidence.
        """
        from corrections.models import ExtractionCorrection, MLModel
        from extractions.models import ExtractionResult

        # Gather corrections for this template + field
        corrections = ExtractionCorrection.objects.filter(
            template_id=template_id,
            field_name=field_name,
        ).select_related("extraction_result")

        min_corrections = _min_corrections_threshold()
        if corrections.count() < min_corrections:
            return {
                "status": "insufficient_data",
                "samples": corrections.count(),
                "message": f"Need at least {min_corrections} corrections, have {corrections.count()}",
            }

        # Build training data
        texts = []
        numerical_features = []
        labels = []

        for corr in corrections:
            # Text feature: original value + context
            context = corr.original_value or ""
            texts.append(context)

            # Numerical features
            conf = corr.original_confidence if corr.original_confidence is not None else 0.5
            has_correction = 1 if corr.corrected_value and corr.corrected_value != corr.original_value else 0
            numerical_features.append([conf, has_correction])

            # Label: 1 if the original value was correct (no meaningful correction), 0 otherwise
            if corr.corrected_value and corr.corrected_value != corr.original_value:
                labels.append(0)  # original was wrong
            else:
                labels.append(1)  # original was correct

        # Also include extraction results without corrections as positive examples
        extraction_results = ExtractionResult.objects.filter(
            template_id=template_id,
        ).exclude(
            corrections__field_name=field_name,
        )[:200]

        for er in extraction_results:
            value = _extract_field_value(er.result_json, field_name)
            if value:
                texts.append(value)
                conf = _extract_field_confidence(er.confidence_json, field_name, er.result_json)
                numerical_features.append([conf, 0])
                labels.append(1)  # no correction means it was correct

        labels = np.array(labels)
        numerical_features = np.array(numerical_features)

        # Need both classes
        if len(set(labels)) < 2:
            return {
                "status": "insufficient_variety",
                "samples": len(labels),
                "message": "Need both correct and incorrect examples to train",
            }

        # TF-IDF on text
        vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(texts).toarray()

        # Combine features
        X = np.hstack([tfidf_matrix, numerical_features])

        # Train with calibration
        base_clf = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )

        # Cross-validation
        n_splits = min(5, max(2, int(len(labels) / 10)))
        try:
            cv_scores = cross_val_score(base_clf, X, labels, cv=n_splits, scoring="accuracy")
            accuracy = float(cv_scores.mean())
        except Exception:
            accuracy = None

        # Fit calibrated model on all data
        calibrated_clf = CalibratedClassifierCV(base_clf, cv=min(3, n_splits))
        calibrated_clf.fit(X, labels)

        # Save artefacts
        model_path = self.get_model_path(template_id, field_name)
        joblib.dump(calibrated_clf, model_path / "model.pkl")
        joblib.dump(vectorizer, model_path / "vectorizer.pkl")

        # Update or create MLModel record
        existing = MLModel.objects.filter(
            template_id=template_id,
            field_name=field_name,
            is_active=True,
        ).order_by("-version").first()

        new_version = (existing.version + 1) if existing else 1

        if existing:
            existing.is_active = False
            existing.save(update_fields=["is_active"])

        MLModel.objects.create(
            template_id=template_id,
            field_name=field_name,
            model_path=str(model_path),
            version=new_version,
            training_samples=len(labels),
            accuracy_score=accuracy,
            is_active=True,
        )

        # Mark corrections as processed
        corrections.filter(is_processed=False).update(is_processed=True)

        logger.info(
            "ml_model_trained",
            template_id=template_id,
            field_name=field_name,
            version=new_version,
            accuracy=accuracy,
            samples=len(labels),
        )

        return {
            "status": "trained",
            "accuracy": accuracy,
            "samples": len(labels),
            "version": new_version,
        }

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_confidence(self, template_id, field_name, extracted_value, ocr_confidence, context_text=""):
        """
        Use a trained model to produce a calibrated confidence score.

        Blends ML prediction with raw OCR confidence:
            final = 0.4 * ocr_confidence + 0.6 * ml_confidence
        """
        model_path = self.get_model_path(template_id, field_name)
        model_file = model_path / "model.pkl"
        vectorizer_file = model_path / "vectorizer.pkl"

        if not model_file.exists() or not vectorizer_file.exists():
            return ocr_confidence

        try:
            clf = joblib.load(model_file)
            vectorizer = joblib.load(vectorizer_file)

            text = str(extracted_value or "") + " " + str(context_text or "")
            tfidf = vectorizer.transform([text]).toarray()

            conf = ocr_confidence if ocr_confidence is not None else 0.5
            numerical = np.array([[conf, 0]])
            X = np.hstack([tfidf, numerical])

            proba = clf.predict_proba(X)
            # Probability of "correct" class (label=1)
            ml_confidence = float(proba[0][1]) if proba.shape[1] > 1 else float(proba[0][0])

            final = 0.4 * conf + 0.6 * ml_confidence
            return round(min(max(final, 0.0), 1.0), 4)

        except Exception as exc:
            logger.warning("ml_predict_error", error=str(exc), template_id=template_id, field_name=field_name)
            return ocr_confidence

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def check_training_ready(self, template_id, field_name):
        """Return True if there are enough unprocessed corrections to train this field."""
        from corrections.models import ExtractionCorrection

        count = ExtractionCorrection.objects.filter(
            template_id=template_id,
            field_name=field_name,
            is_processed=False,
        ).count()
        return count >= _min_corrections_threshold()

    def get_model_info(self, template_id, field_name):
        """Return info dict about the active model, or None."""
        from corrections.models import MLModel

        model = MLModel.objects.filter(
            template_id=template_id,
            field_name=field_name,
            is_active=True,
        ).order_by("-version").first()

        if model is None:
            return None

        return {
            "id": model.id,
            "template_id": model.template_id,
            "field_name": model.field_name,
            "version": model.version,
            "training_samples": model.training_samples,
            "accuracy_score": model.accuracy_score,
            "is_active": model.is_active,
            "created_at": model.created_at.isoformat() if model.created_at else None,
        }


ml_training_service = MLTrainingService()

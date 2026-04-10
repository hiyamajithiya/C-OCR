"""
Learning service for improving extraction accuracy from user corrections.

This service:
1. Processes user corrections to learn patterns
2. Updates abbreviation mappings
3. Tracks template accuracy metrics
4. Suggests improvements to extraction rules
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from django.db.models import Count, Q

from corrections.models import ExtractionCorrection, FieldAbbreviation, TemplateAccuracy
from extractions.models import ExtractionResult
from templates_app.models import Template


class LearningService:
    """Service for learning from user corrections and improving extraction."""

    def __init__(self):
        # Common word patterns for abbreviation detection
        self.word_patterns = {
            "cap": ["capital", "capacity"],
            "acc": ["account", "accumulated", "accrued"],
            "bal": ["balance"],
            "op": ["opening", "operation"],
            "cl": ["closing", "close"],
            "usl": ["unsecured loans", "unsecured loan"],
            "curr": ["current"],
            "liab": ["liabilities", "liability"],
            "asset": ["assets", "asset"],
            "dep": ["depreciation", "deposit"],
            "int": ["interest"],
            "amt": ["amount"],
            "tot": ["total"],
            "sub": ["sub-total", "subtotal"],
            "inv": ["inventory", "investment", "invoice"],
            "rec": ["receivable", "received"],
            "pay": ["payable", "payment"],
            "exp": ["expense", "expenses"],
            "inc": ["income"],
            "rev": ["revenue"],
            "sal": ["salary", "sales"],
            "pur": ["purchase", "purchases"],
            "stk": ["stock"],
            "wip": ["work in progress"],
            "fin": ["finished", "finance"],
            "raw": ["raw material", "raw materials"],
            "adv": ["advance", "advances"],
            "pre": ["prepaid"],
            "prov": ["provision", "provisions"],
            "res": ["reserve", "reserves"],
            "ret": ["retained"],
            "earn": ["earnings"],
            "div": ["dividend", "dividends"],
            "tax": ["tax", "taxes"],
            "gst": ["gst", "goods and services tax"],
            "cgst": ["cgst", "central gst"],
            "sgst": ["sgst", "state gst"],
            "igst": ["igst", "integrated gst"],
            "tds": ["tds", "tax deducted at source"],
            "dr": ["debit", "dr"],
            "cr": ["credit", "cr"],
            "fy": ["financial year"],
            "yr": ["year"],
            "mth": ["month"],
            "qtr": ["quarter"],
        }

    def process_corrections(self, tenant_id: int) -> Dict[str, Any]:
        """
        Process all unprocessed corrections and learn from them.

        Args:
            tenant_id: Tenant ID to process corrections for

        Returns:
            Summary of learning process results
        """
        # Get unprocessed corrections
        unprocessed = list(
            ExtractionCorrection.objects.filter(
                tenant_id=tenant_id,
                is_processed=False,
            )
        )

        if not unprocessed:
            return {
                "status": "success",
                "message": "No unprocessed corrections found",
                "processed_count": 0,
                "abbreviations_learned": 0,
                "accuracy_updated": False,
            }

        # Track learning results
        abbreviations_learned = []
        field_patterns = defaultdict(list)

        for correction in unprocessed:
            # Try to learn abbreviation patterns
            learned = self._learn_abbreviation_pattern(
                tenant_id,
                correction.field_name,
                correction.original_value,
                correction.corrected_value,
            )
            if learned:
                abbreviations_learned.extend(learned)

            # Track field-level patterns
            field_patterns[correction.field_name].append(
                {
                    "original": correction.original_value,
                    "corrected": correction.corrected_value,
                    "method": correction.extraction_method,
                }
            )

            # Mark as processed
            correction.is_processed = True
            correction.learned_pattern = {
                "abbreviations_found": (
                    [a["abbreviation"] for a in learned] if learned else []
                ),
                "processed_at": datetime.utcnow().isoformat(),
            }
            correction.save()

        # Update template accuracy metrics
        self._update_template_accuracy(tenant_id)

        return {
            "status": "success",
            "message": f"Processed {len(unprocessed)} corrections",
            "processed_count": len(unprocessed),
            "abbreviations_learned": len(abbreviations_learned),
            "new_abbreviations": abbreviations_learned,
            "field_patterns": {k: len(v) for k, v in field_patterns.items()},
            "accuracy_updated": True,
        }

    def _learn_abbreviation_pattern(
        self,
        tenant_id: int,
        field_name: str,
        original_value: Optional[str],
        corrected_value: str,
    ) -> List[Dict[str, str]]:
        """
        Try to learn abbreviation patterns from a correction.

        Args:
            tenant_id: Tenant ID
            field_name: Name of the field
            original_value: Original extracted value
            corrected_value: User-corrected value

        Returns:
            List of learned abbreviation mappings
        """
        learned = []

        # Extract potential abbreviations from field name
        field_name_lower = field_name.lower()

        # Find abbreviation-like patterns (2-4 letter segments)
        abbr_pattern = r"\b([a-z]{2,4})\b"
        potential_abbrs = re.findall(abbr_pattern, field_name_lower)

        for abbr in potential_abbrs:
            # Check if this abbreviation already exists
            existing = FieldAbbreviation.objects.filter(
                abbreviation=abbr,
            ).filter(
                Q(tenant_id=tenant_id) | Q(tenant_id__isnull=True)
            ).first()

            if existing:
                # Update usage count
                existing.usage_count += 1
                existing.save()
                continue

            # Try to find what this abbreviation might mean
            expanded = self._guess_abbreviation_expansion(
                abbr, field_name, corrected_value
            )

            if expanded:
                # Create new abbreviation mapping
                new_abbr = FieldAbbreviation(
                    tenant_id=tenant_id,
                    abbreviation=abbr,
                    expanded_form=expanded,
                    source="learned",
                )
                new_abbr.save()
                learned.append(
                    {
                        "abbreviation": abbr,
                        "expanded_form": expanded,
                        "source": "learned",
                    }
                )

        return learned

    def _guess_abbreviation_expansion(
        self, abbr: str, field_name: str, corrected_value: str
    ) -> Optional[str]:
        """
        Guess the expanded form of an abbreviation.

        Args:
            abbr: The abbreviation to expand
            field_name: The field name containing the abbreviation
            corrected_value: The user-provided correct value

        Returns:
            The guessed expansion, or None if unable to determine
        """
        abbr_lower = abbr.lower()

        # Check against known patterns
        if abbr_lower in self.word_patterns:
            return self.word_patterns[abbr_lower][0]

        # Try to find pattern in corrected value
        # If corrected value starts with similar letters, it might be the expansion
        corrected_lower = corrected_value.lower() if corrected_value else ""
        words = corrected_lower.split()

        for word in words:
            if word.startswith(abbr_lower[:2]) and len(word) > len(abbr_lower):
                return word

        return None

    def _update_template_accuracy(self, tenant_id: int):
        """
        Update template accuracy metrics based on corrections.

        Args:
            tenant_id: Tenant ID
        """
        # Get all templates for tenant
        templates = Template.objects.filter(tenant_id=tenant_id)

        period_start = datetime.utcnow() - timedelta(days=30)
        period_end = datetime.utcnow()

        for template in templates:
            # Count extractions
            total_extractions = ExtractionResult.objects.filter(
                template_id=template.id,
                created_at__gte=period_start,
            ).count()

            # Count corrections
            total_corrections = ExtractionCorrection.objects.filter(
                template_id=template.id,
                created_at__gte=period_start,
            ).count()

            # Calculate accuracy
            accuracy_rate = None
            if total_extractions > 0:
                # Rough estimate: each correction represents one field error
                # Assuming avg 5 fields per extraction
                estimated_total_fields = total_extractions * 5
                accuracy_rate = max(
                    0, 100 - (total_corrections / estimated_total_fields * 100)
                )

            # Get field-level metrics
            field_corrections = (
                ExtractionCorrection.objects.filter(
                    template_id=template.id,
                    created_at__gte=period_start,
                )
                .values("field_name")
                .annotate(count=Count("id"))
            )

            field_metrics = {
                fc["field_name"]: {"corrections": fc["count"]}
                for fc in field_corrections
            }

            # Check if accuracy record exists for this period
            period_start_normalized = period_start.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            existing_accuracy = TemplateAccuracy.objects.filter(
                template_id=template.id,
                period_start=period_start_normalized,
            ).first()

            if existing_accuracy:
                # Update existing record
                existing_accuracy.total_extractions = total_extractions
                existing_accuracy.total_corrections = total_corrections
                existing_accuracy.accuracy_rate = accuracy_rate
                existing_accuracy.field_metrics_json = field_metrics
                existing_accuracy.updated_at = datetime.utcnow()
                existing_accuracy.save()
            else:
                # Create new record
                TemplateAccuracy.objects.create(
                    tenant_id=tenant_id,
                    template_id=template.id,
                    period_start=period_start_normalized,
                    period_end=period_end.replace(
                        hour=23, minute=59, second=59, microsecond=999999
                    ),
                    total_extractions=total_extractions,
                    total_corrections=total_corrections,
                    accuracy_rate=accuracy_rate,
                    field_metrics_json=field_metrics,
                )

    def get_abbreviations_for_extraction(
        self, tenant_id: int, doc_category: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get all active abbreviations for use in extraction.

        Args:
            tenant_id: Tenant ID
            doc_category: Optional document category filter

        Returns:
            Dictionary mapping abbreviations to expanded forms
        """
        query = FieldAbbreviation.objects.filter(
            is_active=True,
        ).filter(
            Q(tenant_id=tenant_id) | Q(tenant_id__isnull=True)
        )

        if doc_category:
            query = query.filter(
                Q(doc_category=doc_category) | Q(doc_category__isnull=True)
            )

        abbreviations = query.all()

        # Build dictionary, preferring tenant-specific over global
        result = {}
        for abbr in abbreviations:
            if abbr.abbreviation not in result or abbr.tenant_id == tenant_id:
                result[abbr.abbreviation] = abbr.expanded_form

        return result

    def suggest_field_improvements(
        self, tenant_id: int, template_id: int
    ) -> List[Dict[str, Any]]:
        """
        Suggest improvements for template fields based on correction patterns.

        Args:
            tenant_id: Tenant ID
            template_id: Template ID

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Get correction patterns for this template
        corrections = list(
            ExtractionCorrection.objects.filter(
                template_id=template_id,
                tenant_id=tenant_id,
            )
        )

        # Analyze patterns by field
        field_patterns = defaultdict(list)
        for correction in corrections:
            field_patterns[correction.field_name].append(
                {
                    "original": correction.original_value,
                    "corrected": correction.corrected_value,
                    "method": correction.extraction_method,
                }
            )

        for field_name, patterns in field_patterns.items():
            if len(patterns) >= 3:
                # Check for consistent extraction method failures
                method_failures = defaultdict(int)
                for p in patterns:
                    if p["method"]:
                        method_failures[p["method"]] += 1

                for method, count in method_failures.items():
                    if count >= 2:
                        suggestions.append(
                            {
                                "field_name": field_name,
                                "suggestion_type": "method_failure",
                                "message": f"Field '{field_name}' has {count} corrections when extracted via '{method}'. Consider adjusting coordinates or search terms.",
                                "correction_count": count,
                            }
                        )

                # Check for numeric vs text issues
                numeric_corrections = sum(
                    1
                    for p in patterns
                    if p["corrected"] and re.search(r"\d", p["corrected"])
                )
                if numeric_corrections > len(patterns) / 2:
                    suggestions.append(
                        {
                            "field_name": field_name,
                            "suggestion_type": "numeric_field",
                            "message": f"Field '{field_name}' often corrected to numeric values. Ensure field type is set to 'number'.",
                            "correction_count": numeric_corrections,
                        }
                    )

        return suggestions


# Singleton instance
learning_service = LearningService()

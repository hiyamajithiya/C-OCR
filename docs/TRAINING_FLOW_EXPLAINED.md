# C-OCR Learning Flow (Non-Technical Guide)

## Why this document exists
This explains, in simple language, how your system is supposed to work from upload to learning, what "Learned" means, where the model is saved, what is currently going wrong, and what to change so results actually improve.

---

## 1) End-to-end flow (simple version)

### Step 1: Upload a document
- You upload PDF/image.
- System stores the file and runs OCR (text reading).

### Step 2: OCR output is saved
- OCR text is saved as structured JSON per page.
- This is the raw material used for extraction.

### Step 3: Apply template
- You choose a template.
- System tries to fill fields (Name, DOB, etc.) from OCR text.
- It saves an extraction result.

### Step 4: You correct wrong/missing fields
- In Extraction Results page, you edit values and click Save Corrections.
- These corrections are stored in Correction History.

### Step 5: Learn
- You click Learn.
- System processes saved corrections.
- Status changes from Awaiting Learn to Learned.

### Step 6: Model training (only when conditions are met)
- If there is enough correction data per template + field, ML training runs.
- New model version is saved.

---

## 2) What "Awaiting Learn" and "Learned" mean

- Awaiting Learn:
  - Correction is saved, but not yet processed by learning pipeline.
- Learned:
  - Correction has been processed by learning pipeline.
  - Important: this does NOT always mean a new ML model was trained.

So, Learned = "processed for learning", not necessarily "model improved".

---

## 3) How model training works in this project

Training is per **template + field**.

Example:
- Template A + field Name
- Template A + field DOB
- Template B + field Name

Each pair is treated separately.

Current training rule:
- Need at least 20 corrections for that template+field group.
- If not enough data, model training is skipped.

---

## 4) Where learned/trained data is stored

### A) Corrections and learning status (database)
- Table: extraction_corrections
- Key columns:
  - corrected_value
  - is_processed
  - learned_pattern

### B) Trained model metadata (database)
- Table: ml_models
- Stores:
  - template_id
  - field_name
  - version
  - training_samples
  - accuracy_score
  - is_active

### C) Trained model files (disk)
- Base path uses STORAGE_PATH from settings.
- Current configured STORAGE_PATH: ./storage
- Expected model files:
  - storage/models/<template_id>/<field_name>/model.pkl
  - storage/models/<template_id>/<field_name>/vectorizer.pkl

---

## 5) What is currently going wrong (your current state)

From live checks:
- MLModel count is 0 (no trained model versions).
- Active models are empty.
- Corrections exist, but all are grouped under template_id = null.
- Field counts are 6 each (DOB/Name/Gender/Aadhar number), not 20.

What this means:
1. Training group filter (template + field) cannot pick these corrections because template_id is missing.
2. Even by count, each field is still below threshold.
3. No model files are produced.
4. Re-uploading same file will likely keep giving similar extraction output.

---

## 6) Very important: model usage during extraction

There is a training service that can create models and has a predict_confidence method.

But model improvement only helps if extraction pipeline actually calls that model during inference.

So there are two separate requirements:
1. Training must create models.
2. Extraction flow must use trained model outputs.

If (2) is missing, you can train forever and still see no practical improvement.

---

## 7) What to improve (recommended roadmap)

### Priority A: Link corrections to template and template_version
When saving corrections, derive and store template_id/template_version_id from extraction_result.

Result:
- Corrections become trainable for correct template+field groups.

### Priority B: Adjust minimum training threshold for real usage
Current threshold = 20 per field is strict for early stage.
Consider temporary threshold of 5-10 for pilot/testing.

### Priority C: Avoid inflated repeated corrections from same document
If user corrects same field many times on same doc, optionally deduplicate or weight less.

### Priority D: Ensure inference uses trained model
After model exists, call model prediction in extraction flow and blend confidence/output.

### Priority E: Improve UI transparency
Show separate statuses:
- Saved
- Processed for learning
- Model trained
- Model applied in extraction

---

## 8) Practical answer to your main question

"If I upload same dataset again, will I get better result?"
- Not reliably yet, because model training is currently not producing active models in your live data.
- And even if models were trained, inference path must apply them.

So at this moment: repeated upload alone does not guarantee better extraction.

---

## 9) Non-technical checklist (quick)

Before expecting improvement, confirm all below are true:
- Corrections show linked template in DB.
- Learn has been run after saving corrections.
- MLModel table has active rows.
- model.pkl and vectorizer.pkl exist under storage/models.
- New extraction flow uses model output.

If any one of these is missing, quality improvement may not appear.

---

## 10) Current project snapshot (today)

- Learned status is visible in UI.
- Corrections are being saved.
- Training artifacts are not yet visible (no MLModel rows found).
- This is why improvements are not showing consistently on re-upload.

---

If you want, next step can be a focused implementation document with exact backend/frontend code changes to make this fully working in production behavior.

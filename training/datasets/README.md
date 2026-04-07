# Datasets

This folder documents external datasets used to **train/validate** custom models and to demonstrate that SPEAKEZ AI does not rely only on pretrained components.

## Quick Start: Build Real Training Data

### 0) Bootstrap with 5000+ samples per class (fast)
If you need larger data quickly for experimentation, run:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python ..\training\scripts\generate_and_train_large_datasets.py
```

This generates and trains:
- `training/datasets/confidence/confidence_synthetic_15000.csv` (5000 x 3 classes)
- `training/datasets/voice/voice_features_10000.csv` (5000 x 2 classes)
- `training/datasets/emotion/emotion_synthetic_20000.csv` (5000 x 4 classes)
- `backend/models/confidence_model.joblib`
- `training/models/voice_modulation_model.joblib`
- `training/models/emotion_baseline_model.joblib`

Note: these are synthetic bootstrap datasets. For production quality, replace/augment with real recordings.

### 1) Confidence dataset from recorded sessions
Generate a CSV from your completed local sessions:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python ..\training\scripts\export_confidence_dataset.py
```

Output:
- `training/student_samples/derived_confidence_samples.csv`

Then manually fill `label_confidence` with:
- `poor`
- `average`
- `good`

Use this CSV as your real confidence training set.

### 2) Voice modulation dataset from audio clips
1. Add clips under `training/datasets/voice/clips/`
2. Fill metadata in `training/datasets/voice/metadata_template.csv`
3. Build features:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python ..\training\scripts\build_voice_features.py
```

Output:
- `training/datasets/voice/voice_features.csv`

## Emotion Detection

### FER2013
- Download via Kaggle or other authorized source.
- Expected structure:
  - `training/datasets/fer2013/fer2013.csv`

The training notebook maps FER classes into SPEAKEZ classes:
- happy
- neutral
- nervous
- stressed

## Student Samples (Confidence Model)

Collect 10–20 student recordings and label them:
- `good|average|poor`

Store tabular labels in:
- `training/student_samples/template.csv` (copy and fill)
- or `training/student_samples/derived_confidence_samples.csv` (auto-exported from app sessions)

## Licensing
You must comply with each dataset’s license/terms.


# Datasets

This folder documents external datasets used to **train/validate** custom models and to demonstrate that SPEAKEZ AI does not rely only on pretrained components.

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

## Licensing
You must comply with each dataset’s license/terms.


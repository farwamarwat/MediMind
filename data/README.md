# Datasets

## dataset.csv (not committed)

Training data comes from the **Disease Symptom Prediction** dataset:
<https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset>

Download `dataset.csv` from Kaggle and place it in this directory, then run:

```bash
python scripts/train_model.py
```

The file is not committed because it is redistributed under Kaggle terms;
`scripts/train_model.py` reports a clear error if it is missing.

### Known limitation

This dataset is synthetically generated: each disease maps to a fixed symptom
set with little overlap or noise, so classifiers reach near-perfect accuracy on
it. Those scores measure separability of the dataset, **not** real-world
diagnostic performance. See the model evaluation section of the main README.

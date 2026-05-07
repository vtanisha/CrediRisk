"""Train an XGBoost classifier on the same feature set as the neural network."""
import json
import logging
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score

logger = logging.getLogger(__name__)


def train_xgboost():
    try:
        import xgboost as xgb
    except ImportError:
        logger.error("xgboost not installed. Run: pip install xgboost")
        return

    csv_path = "Bank Data Sources/application_data.csv"
    if not os.path.exists(csv_path):
        logger.error("Dataset missing: %s", csv_path)
        return

    logger.info("Loading data for XGBoost training...")
    df = pd.read_csv(csv_path, nrows=50_000)

    features = ['AMT_INCOME_TOTAL', 'AMT_CREDIT', 'DAYS_BIRTH', 'EXT_SOURCE_2']
    df['EXT_SOURCE_2'] = df['EXT_SOURCE_2'].fillna(df['EXT_SOURCE_2'].mean())
    df['DAYS_BIRTH'] = df['DAYS_BIRTH'] / -365.0
    df = df.dropna(subset=features)

    X = df[features].values
    y = df['TARGET'].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)
    auc = roc_auc_score(y_test, y_pred_proba)
    acc = accuracy_score(y_test, y_pred)
    logger.info("XGBoost — AUC: %.4f  Accuracy: %.4f", auc, acc)

    os.makedirs("models", exist_ok=True)
    model.save_model("models/xgb_model.json")

    metrics_data = {
        "auc": float(auc),
        "accuracy": float(acc),
        "n_features": len(features),
        "features": features,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "feature_importance": {f: float(v) for f, v in zip(features, model.feature_importances_)},
    }
    with open("models/xgb_metrics.json", "w") as fp:
        json.dump(metrics_data, fp, indent=2)

    logger.info("XGBoost model saved to models/xgb_model.json")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_xgboost()

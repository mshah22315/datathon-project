"""Train and serve the enrollment Gradient Boosting Regression model."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, MaxAbsScaler

TARGET = "enrolled"
FEATURE_IMPORTANCE_THRESHOLD = 0.001
MODEL_VERSION = 3
PROJECT_DIR = Path(__file__).resolve().parent
BINARY_CATEGORICAL_COLUMNS = [
    "app_completed",
    "admitted",
    "deposit_paid",
    "first_generation",
    "legacy",
    "stealth",
    "grad_expct",
    "ed_plan_asst",
    "wrtng_asst",
    "read_asst",
    "study_skll_asst",
    "math_asst",
    "rotc_interest",
    "veteran",
    "stem_major",
    "urm",
]


def load_dataset(dataset_path: str | Path) -> pd.DataFrame:
    """Load a CSV or Excel dataset based on its file extension."""
    dataset_path = Path(dataset_path)
    if dataset_path.suffix.lower() == ".csv":
        return pd.read_csv(dataset_path)
    return pd.read_excel(dataset_path, sheet_name="data")


def prepare_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """Apply the notebook's feature typing before training or serving."""
    data = data.copy()
    missing_columns = [
        column
        for column in BINARY_CATEGORICAL_COLUMNS
        if column not in data.columns
    ]
    if missing_columns:
        raise ValueError(
            "Dataset is missing categorical columns: "
            f"{sorted(missing_columns)}"
        )
    data[BINARY_CATEGORICAL_COLUMNS] = data[BINARY_CATEGORICAL_COLUMNS].astype(
        "category"
    )
    return data


def train_model(dataset_path: str | Path, artifact_path: str | Path) -> dict:
    """
    Train the notebook's model and persist its preprocessing metadata.

    Args:
        dataset_path: Path to the dataset file.
        artifact_path: Path to save the model artifact.
    
    Returns:
        A dictionary containing the trained model and its metadata.
    """
    data = prepare_dataset(load_dataset(dataset_path))
    if TARGET not in data.columns:
        raise ValueError(f"Dataset must contain a '{TARGET}' column.")

    X = data.drop(columns=[TARGET])
    y = data[TARGET]

    numeric_columns = [
        'hs_gpa', 'act_cmpst', 'act_engl', 'act_math',
        'sat_comb', 'sat_vrbl', 'sat_math', 'hs_math', 'hs_sci',
        'hs_engl', 'hs_ss', 'hs_flang', 'hs_rank', 'campus_visit_tot',
        'coll_algbr_cr', 'coll_geom_cr', 'coll_trig_cr', 'coll_calc_cr',
        'coll_math', 'coll_sci', 'miles_from_campus', 'age', 'app_days_before_start'
    ]

    categorical_columns = X.select_dtypes(include=["object", "category"]).columns.tolist()
    if not categorical_columns:
        raise ValueError("The dataset contains no categorical model features.")

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median"))
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "encoder",
            OneHotEncoder(
                sparse_output=False,
                drop="first",
                handle_unknown="ignore",
            ),
        ),
    ])
    preprocessor = ColumnTransformer([
        ("numeric", numeric_pipeline, numeric_columns),
        ("categorical", categorical_pipeline, categorical_columns),
    ])

    X_processed = preprocessor.fit_transform(X)
    feature_names = preprocessor.get_feature_names_out()

    # Train the model
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_processed, y)

    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": rf.feature_importances_,
    }).sort_values("importance", ascending=False)

    selected_features = importance_df.loc[
        importance_df["importance"] > FEATURE_IMPORTANCE_THRESHOLD,
        "feature",
    ].tolist()
    if not selected_features:
        raise ValueError("Feature selection retained no model features.")

    selected_indices = [
        list(feature_names).index(feature) for feature in selected_features
    ]

    X_filtered = X_processed[:, selected_indices]

    scaler = MaxAbsScaler()
    X_filtered_norm = scaler.fit_transform(X_filtered)

    model = GradientBoostingRegressor(n_estimators=100, random_state=42)
    model.fit(X_filtered_norm, y)

    artifact = {
        "model_version": MODEL_VERSION,
        "target": TARGET,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "preprocessor": preprocessor,
        "processed_feature_names": feature_names.tolist(),
        "selected_features": selected_features,
        "feature_importance_threshold": FEATURE_IMPORTANCE_THRESHOLD,
        "scaler": scaler,
        "model": model,
    }
    artifact_path = Path(artifact_path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    return artifact


def load_model(artifact_path: str | Path) -> dict:
    """
    Load a persisted model artifact.

    Args:
        artifact_path: Path to the model artifact.
    
    Returns:
        A dictionary containing the loaded model and its metadata.
    """
    artifact = joblib.load(artifact_path)
    required_keys = {
        "preprocessor",
        "numeric_columns",
        "categorical_columns",
        "processed_feature_names",
        "selected_features",
        "scaler",
        "model",
    }
    missing_keys = required_keys.difference(artifact)
    if missing_keys:
        raise ValueError(f"Model artifact is missing: {sorted(missing_keys)}")
    return artifact


def predict_probability(artifact: Mapping, student: Mapping[str, object]) -> float:
    """
    Return the predicted enrollment probability for one student.

    Args:
        artifact: The trained model artifact.
        student: A dictionary containing the student's data.
    
    Returns:
        The predicted enrollment probability.
    """
    columns = artifact["numeric_columns"] + artifact["categorical_columns"]
    row = {
        column: (
            np.nan
            if student.get(column) in ("", None, "(missing)")
            else (
                int(student[column])
                if column in BINARY_CATEGORICAL_COLUMNS
                and str(student[column]) in {"0", "1"}
                else student[column]
            )
        )
        for column in columns
    }
    input_frame = pd.DataFrame([row], columns=columns)
    processed = artifact["preprocessor"].transform(input_frame)
    selected_indices = [
        artifact["processed_feature_names"].index(feature)
        for feature in artifact["selected_features"]
    ]
    selected = processed[:, selected_indices]
    selected_norm = artifact["scaler"].transform(selected)
    prediction = float(artifact["model"].predict(selected_norm)[0])
    return float(np.clip(prediction, 0.0, 1.0))


def predict_dataset(
    artifact: Mapping,
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Predict the enrollment probability for each row in the input dataset.

    Args:
        artifact: The trained model artifact.
        data: The input dataset.

    Returns:
        A DataFrame with the input features and the predicted enrollment probabilities.
    """
    target = artifact.get("target", TARGET)
    if target in data.columns:
        features = data.drop(columns=[target]).copy()
    else:
        features = data.copy()

    columns = artifact["numeric_columns"] + artifact["categorical_columns"]
    missing_columns = sorted(set(columns).difference(features.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing model features: {missing_columns}")

    input_frame = features[columns]
    processed = artifact["preprocessor"].transform(input_frame)
    selected_indices = [
        artifact["processed_feature_names"].index(feature)
        for feature in artifact["selected_features"]
    ]
    selected = processed[:, selected_indices]
    selected_norm = artifact["scaler"].transform(selected)
    predictions = np.clip(artifact["model"].predict(selected_norm), 0.0, 1.0)

    features["predicted_probability"] = predictions
    return features


def write_predictions(
    artifact: Mapping,
    dataset_path: str | Path,
    output_path: str | Path,
) -> pd.DataFrame:
    """
    Predict all rows in a dataset and write features and probabilities to CSV.

    Args:
        artifact: The trained model artifact.
        dataset_path: The path to the input dataset.
        output_path: The path to the output CSV file.

    Returns:
        A DataFrame with the input features and the predicted enrollment probabilities.
    """
    data = prepare_dataset(load_dataset(dataset_path))
    predictions = predict_dataset(artifact, data)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_path, index=False)
    return predictions


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=PROJECT_DIR / "data_asof_0501.csv")
    parser.add_argument("--output", default=PROJECT_DIR / "artifacts/gbr_model.joblib")
    parser.add_argument(
        "--predictions-output",
        default=PROJECT_DIR / "artifacts/gbr_predictions.csv",
        help="CSV path for input features and predicted enrollment probabilities.",
    )
    args = parser.parse_args()
    trained = train_model(args.data, args.output)
    print(f"Saved model with {len(trained['selected_features'])} selected features.")
    predictions = write_predictions(trained, args.data, args.predictions_output)
    print(f"Saved {len(predictions)} predictions to {args.predictions_output}.")
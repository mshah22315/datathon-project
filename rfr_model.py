"""Train and serve the enrollment Random Forest Regression model."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, MaxAbsScaler

TARGET = "enrolled"
FEATURE_IMPORTANCE_THRESHOLD = 0.001
MODEL_VERSION = 2
PROJECT_DIR = Path(__file__).resolve().parent


def load_dataset(dataset_path: str | Path) -> pd.DataFrame:
    """Load a CSV or Excel dataset based on its file extension."""
    dataset_path = Path(dataset_path)
    if dataset_path.suffix.lower() == ".csv":
        return pd.read_csv(dataset_path)
    return pd.read_excel(dataset_path, sheet_name="data")


def train_model(dataset_path: str | Path, artifact_path: str | Path) -> dict:
    """
    Train the notebook's model and persist its preprocessing metadata.

    Args:
        dataset_path: Path to the dataset file.
        artifact_path: Path to save the model artifact.
    
    Returns:
        A dictionary containing the trained model and its metadata.
    """
    data = load_dataset(dataset_path)
    if TARGET not in data.columns:
        raise ValueError(f"Dataset must contain a '{TARGET}' column.")

    # Convert all binary 0/1 columns except 'enrolled' to categorical type
    data['app_completed'] = data['app_completed'].astype('category')
    data['admitted'] = data['admitted'].astype('category')
    data['deposit_paid'] = data['deposit_paid'].astype('category')
    data['first_generation'] = data['first_generation'].astype('category')
    data['legacy'] = data['legacy'].astype('category')
    data['stealth'] = data['stealth'].astype('category')
    data['grad_expct'] = data['grad_expct'].astype('category')
    data['ed_plan_asst'] = data['ed_plan_asst'].astype('category')
    data['wrtng_asst'] = data['wrtng_asst'].astype('category')
    data['read_asst'] = data['read_asst'].astype('category')
    data['study_skll_asst'] = data['study_skll_asst'].astype('category')
    data['math_asst'] = data['math_asst'].astype('category')
    data['rotc_interest'] = data['rotc_interest'].astype('category')
    data['veteran'] = data['veteran'].astype('category')
    data['stem_major'] = data['stem_major'].astype('category')
    data['urm'] = data['urm'].astype('category')

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

    X_filtered_norm = MaxAbsScaler().fit_transform(X_filtered)

    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
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
            else student.get(column, np.nan)
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
    selected_norm = MaxAbsScaler().fit_transform(selected)
    prediction = float(artifact["model"].predict(selected_norm)[0])
    return float(np.clip(prediction, 0.0, 1.0))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=PROJECT_DIR / "data_asof_0501.csv")
    parser.add_argument("--output", default=PROJECT_DIR / "artifacts/rfr_model.joblib")
    args = parser.parse_args()
    trained = train_model(args.data, args.output)
    print(f"Saved model with {len(trained['selected_features'])} selected features.")
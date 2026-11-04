"""Streamlit demo for the enrollment probability model."""

from pathlib import Path

import pandas as pd
import streamlit as st

from gbr_model import load_model, predict_probability

ROOT = Path(__file__).parent
ARTIFACT_PATH = ROOT / "artifacts" / "gbr_model.joblib"
DATASET_PATH = ROOT / "datathon-dataset-2026.xlsx"


@st.cache_resource
def get_model() -> dict:
    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(
            f"Model artifact not found at {ARTIFACT_PATH}. "
            "Run `python gbr_model.py` first."
        )
    return load_model(ARTIFACT_PATH)


@st.cache_data
def get_categories() -> dict[str, list[str]]:
    data = pd.read_excel(DATASET_PATH, sheet_name="data")
    columns = data.drop(columns=["enrolled"]).select_dtypes(
        include=["object", "category"]
    ).columns
    return {
        column: (
            (["(missing)"] if data[column].isna().any() else [])
            + sorted(data[column].dropna().astype(str).unique())
        )
        for column in columns
    }


@st.cache_data
def get_numeric_defaults(columns: list[str]) -> dict[str, float]:
    data = pd.read_excel(DATASET_PATH, sheet_name="data")
    return {
        column: float(data[column].median())
        for column in columns
        if column in data.columns
    }


st.set_page_config(page_title="Enrollment Probability Demo", page_icon="🎓")
st.title("First-year enrollment probability")
st.write("Enter the student's academic, application, and demographic information.")

try:
    artifact = get_model()
    categories = get_categories()
    numeric_defaults = get_numeric_defaults(artifact["numeric_columns"])
except (FileNotFoundError, OSError, ValueError) as error:
    st.error(str(error))
    st.stop()

student = {}
with st.form("student_inputs"):
    for column in artifact["numeric_columns"]:
        label = column.replace("_", " ").title()
        student[column] = st.number_input(
            label,
            value=numeric_defaults.get(column, 0.0),
        )
    for column in artifact["categorical_columns"]:
        options = categories.get(column, ["(missing)"])
        student[column] = st.selectbox(column.replace("_", " ").title(), options)
    submitted = st.form_submit_button("Predict enrollment probability")

if submitted:
    probability = predict_probability(artifact, student)
    st.metric("Predicted probability", f"{probability:.1%}")
    st.progress(probability)
    st.caption(
        "This is a model estimate, not a guarantee. "
        "The regression output is clipped to the valid probability range."
    )

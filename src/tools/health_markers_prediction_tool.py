from pathlib import Path

try:
    from langchain_community.tools import tool
except ImportError:
    def tool(fn):
        return fn


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "health_markers_condition_classifier.joblib"

_MODEL_ARTIFACT = None


def _load_model_artifact():
    global _MODEL_ARTIFACT

    if _MODEL_ARTIFACT is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model artifact not found at {MODEL_PATH}. "
                "Run notebooks/health_markers_multiclass_training.ipynb first."
            )

        import joblib

        _MODEL_ARTIFACT = joblib.load(MODEL_PATH)

    return _MODEL_ARTIFACT


def _format_probability_table(classes, probabilities) -> str:
    rows = sorted(
        zip(classes, probabilities),
        key=lambda item: item[1],
        reverse=True,
    )

    try:
        import pandas as pd

        return pd.DataFrame(
            {
                "class": [label for label, _ in rows],
                "probability": [round(float(prob), 4) for _, prob in rows],
            }
        ).to_string(index=False)
    except ImportError:
        lines = ["class | probability", "----- | -----------"]
        lines.extend(f"{label} | {float(prob):.4f}" for label, prob in rows)
        return "\n".join(lines)


@tool
def predict_health_markers_condition(
    blood_glucose: float,
    hba1c: float,
    systolic_bp: float,
    diastolic_bp: float,
    ldl: float,
    hdl: float,
    triglycerides: float,
    haemoglobin: float,
    mcv: float,
    include_probabilities: bool = True,
) -> str:
    """
    Predict a condition class using the saved health markers multi-class model.

    Input columns:
    - blood_glucose, hba1c, systolic_bp, diastolic_bp, ldl, hdl,
      triglycerides, haemoglobin, mcv

    Output is model support for disease/syndrome classification. It is not a
    final diagnosis and must be interpreted with clinical caution.
    """
    print("\nCalling Tool: Health Markers Condition Prediction")
    print("INPUT TO HEALTH MARKERS CONDITION PREDICTION TOOL:")
    print(
        {
            "blood_glucose": blood_glucose,
            "hba1c": hba1c,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "ldl": ldl,
            "hdl": hdl,
            "triglycerides": triglycerides,
            "haemoglobin": haemoglobin,
            "mcv": mcv,
            "include_probabilities": include_probabilities,
        }
    )

    try:
        import pandas as pd

        artifact = _load_model_artifact()
        pipeline = artifact["pipeline"]
        feature_columns = artifact["feature_columns"]

        record = {
            "Blood_glucose": blood_glucose,
            "HbA1C": hba1c,
            "Systolic_BP": systolic_bp,
            "Diastolic_BP": diastolic_bp,
            "LDL": ldl,
            "HDL": hdl,
            "Triglycerides": triglycerides,
            "Haemoglobin": haemoglobin,
            "MCV": mcv,
        }

        input_df = pd.DataFrame([record])[feature_columns]
        predicted_class = pipeline.predict(input_df)[0]
        print("\nHealth Markers Condition Prediction TOOL RESULT:")
        print(f"Predicted condition class: {predicted_class}")

        output = f"""
Health markers multi-class model prediction:
- Predicted condition class: {predicted_class}
- Model artifact: {MODEL_PATH}

Important: This prediction is only machine-learning support for condition
classification. It is not a diagnosis and should be correlated with symptoms,
history, examination, reference ranges, and clinician judgment.
""".strip()

        if include_probabilities and hasattr(pipeline.named_steps["model"], "predict_proba"):
            probabilities = pipeline.predict_proba(input_df)[0]
            probability_table = _format_probability_table(pipeline.classes_, probabilities)
            output = f"{output}\n\nClass probabilities:\n{probability_table}"

        print("\nHealth Markers Condition Prediction TOOL OUTPUT:")
        print(output)
        print("\n" + "=" * 70)

        return output

    except Exception as exc:
        error_output = f"Error running health markers condition prediction: {exc}"
        print("\nHealth Markers Condition Prediction TOOL ERROR:")
        print(error_output)
        print("\n" + "=" * 70)
        return error_output

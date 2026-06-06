from pathlib import Path
from typing import Optional

try:
    from langchain_community.tools import tool
except ImportError:
    def tool(fn):
        return fn


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "vital_signs_risk_classifier.joblib"

_MODEL_ARTIFACT = None


def _load_model_artifact():
    global _MODEL_ARTIFACT

    if _MODEL_ARTIFACT is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model artifact not found at {MODEL_PATH}. "
                "Run notebooks/vital_signs_multiclass_training.ipynb first."
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
def predict_vital_signs_risk_category(
    heart_rate: float,
    respiratory_rate: float,
    body_temperature: float,
    oxygen_saturation: float,
    systolic_blood_pressure: float,
    diastolic_blood_pressure: float,
    age: float,
    gender: str,
    weight_kg: float,
    height_m: float,
    derived_hrv: float,
    derived_pulse_pressure: float,
    derived_bmi: float,
    derived_map: float,
    timestamp_hour: Optional[float] = None,
    timestamp_dayofweek: Optional[float] = None,
    timestamp_month: Optional[float] = None,
    include_probabilities: bool = True,
) -> str:
    """
    Predict risk category using the saved human vital signs multi-class model.

    Output is model support for the Vital Signs Monitoring Agent. It is not a
    diagnosis and must be interpreted with physiological and clinical caution.
    """
    print("\nCalling Tool: Vital Signs Risk Prediction")
    print("INPUT TO VITAL SIGNS RISK PREDICTION TOOL:")
    print(
        {
            "heart_rate": heart_rate,
            "respiratory_rate": respiratory_rate,
            "body_temperature": body_temperature,
            "oxygen_saturation": oxygen_saturation,
            "systolic_blood_pressure": systolic_blood_pressure,
            "diastolic_blood_pressure": diastolic_blood_pressure,
            "age": age,
            "gender": gender,
            "weight_kg": weight_kg,
            "height_m": height_m,
            "derived_hrv": derived_hrv,
            "derived_pulse_pressure": derived_pulse_pressure,
            "derived_bmi": derived_bmi,
            "derived_map": derived_map,
            "timestamp_hour": timestamp_hour,
            "timestamp_dayofweek": timestamp_dayofweek,
            "timestamp_month": timestamp_month,
            "include_probabilities": include_probabilities,
        }
    )

    try:
        import pandas as pd

        artifact = _load_model_artifact()
        pipeline = artifact["pipeline"]
        feature_columns = artifact["feature_columns"]

        record = {
            "Heart Rate": heart_rate,
            "Respiratory Rate": respiratory_rate,
            "Body Temperature": body_temperature,
            "Oxygen Saturation": oxygen_saturation,
            "Systolic Blood Pressure": systolic_blood_pressure,
            "Diastolic Blood Pressure": diastolic_blood_pressure,
            "Age": age,
            "Gender": gender,
            "Weight (kg)": weight_kg,
            "Height (m)": height_m,
            "Derived_HRV": derived_hrv,
            "Derived_Pulse_Pressure": derived_pulse_pressure,
            "Derived_BMI": derived_bmi,
            "Derived_MAP": derived_map,
            "timestamp_hour": timestamp_hour,
            "timestamp_dayofweek": timestamp_dayofweek,
            "timestamp_month": timestamp_month,
        }

        input_df = pd.DataFrame([record])
        missing_columns = [
            column
            for column in feature_columns
            if column not in input_df.columns
        ]
        if missing_columns:
            error_output = (
                "Error running vital signs risk prediction: "
                f"missing required columns {missing_columns}"
            )
            print("\nVital Signs Risk Prediction TOOL ERROR:")
            print(error_output)
            print("\n" + "=" * 70)
            return error_output

        input_df = input_df[feature_columns]
        predicted_class = pipeline.predict(input_df)[0]
        print("\nVital Signs Risk Prediction TOOL RESULT:")
        print(f"Predicted risk category: {predicted_class}")

        output = f"""
Vital signs multi-class model prediction:
- Predicted risk category: {predicted_class}
- Model artifact: {MODEL_PATH}

Important: This prediction is only machine-learning support for vital-sign
monitoring. It is not a diagnosis and should be correlated with symptoms,
clinical context, trends over time, and clinician judgment.
""".strip()

        if include_probabilities and hasattr(pipeline.named_steps["model"], "predict_proba"):
            probabilities = pipeline.predict_proba(input_df)[0]
            probability_table = _format_probability_table(pipeline.classes_, probabilities)
            output = f"{output}\n\nClass probabilities:\n{probability_table}"

        print("\nVital Signs Risk Prediction TOOL OUTPUT:")
        print(output)
        print("\n" + "=" * 70)

        return output

    except Exception as exc:
        error_output = f"Error running vital signs risk prediction: {exc}"
        print("\nVital Signs Risk Prediction TOOL ERROR:")
        print(error_output)
        print("\n" + "=" * 70)
        return error_output

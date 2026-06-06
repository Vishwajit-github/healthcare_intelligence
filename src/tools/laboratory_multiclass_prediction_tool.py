from pathlib import Path
from typing import Optional
import importlib
import sys

try:
    from langchain_community.tools import tool
except ImportError:
    def tool(fn):
        return fn


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "laboratory_disease_classifier.joblib"

_MODEL_ARTIFACT = None


def _register_sklearn_loss_aliases():
    """Support artifacts pickled with top-level _loss module references."""
    loss_package = importlib.import_module("sklearn._loss")
    loss_module = importlib.import_module("sklearn._loss.loss")
    link_module = importlib.import_module("sklearn._loss.link")

    if not hasattr(loss_package, "CyHalfMultinomialLoss"):
        loss_package.CyHalfMultinomialLoss = loss_module.CyHalfMultinomialLoss

    if not hasattr(loss_package, "__pyx_unpickle_CyHalfMultinomialLoss"):
        def __pyx_unpickle_CyHalfMultinomialLoss(cython_type, _checksum, state):
            instance = cython_type.__new__(cython_type)
            if state is not None and hasattr(instance, "__setstate__"):
                instance.__setstate__(state)
            return instance

        loss_package.__pyx_unpickle_CyHalfMultinomialLoss = __pyx_unpickle_CyHalfMultinomialLoss

    sys.modules.setdefault("_loss", loss_package)
    sys.modules.setdefault("_loss.loss", loss_module)
    sys.modules.setdefault("_loss.link", link_module)


def _load_model_artifact():
    global _MODEL_ARTIFACT

    if _MODEL_ARTIFACT is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model artifact not found at {MODEL_PATH}. "
                "Run notebooks/laboratory_multiclass_training.ipynb first."
            )

        import joblib

        _register_sklearn_loss_aliases()
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
def predict_laboratory_disease_class(
    gender: str,
    age: float,
    hemoglobin: float,
    rbc: float,
    wbc: float,
    ast: float,
    alt: float,
    spirometry: float,
    creatinine: float,
    glucose: float,
    lipase: float,
    troponin: float,
    cholestrol: Optional[float] = None,
    cholesterol: Optional[float] = None,
    include_probabilities: bool = True,
) -> str:
    """
    Predict a lab-pattern disease class using the saved laboratory multi-class model.
    
    Input Parameters:
    - gender (str): Patient gender (e.g., 'male', 'female')
    - age (float): Patient age in years
    - hemoglobin (float): Hemoglobin level (g/dL), indicator of anemia or oxygen-carrying capacity
    - rbc (float): Red blood cell count, related to anemia or blood disorders
    - wbc (float): White blood cell count, indicator of infection or inflammation
    - ast (float): Aspartate aminotransferase, liver enzyme marker
    - alt (float): Alanine aminotransferase, liver function indicator
    - spirometry (float): Lung function measurement (respiratory capacity index)
    - creatinine (float): Kidney function marker
    - glucose (float): Blood sugar level, diabetes/metabolic indicator
    - lipase (float): Pancreatic enzyme, indicator of pancreatic inflammation
    - troponin (float): Cardiac marker, indicates heart muscle injury
    - cholestrol (Optional[float]): Total cholesterol level (alternate spelling supported)
    - cholesterol (Optional[float]): Total cholesterol level (standard spelling)
    - include_probabilities (bool): If True, returns class probabilities along with prediction

    Returns:
    - str: Predicted disease class or label from trained laboratory model
    """

    print("\nCalling Tool: Laboratory Disease Class Prediction")
    print("INPUT TO LABORATORY DISEASE CLASS PREDICTION TOOL:")
    print(
        {
            "gender": gender,
            "age": age,
            "hemoglobin": hemoglobin,
            "rbc": rbc,
            "wbc": wbc,
            "ast": ast,
            "alt": alt,
            "cholestrol": cholestrol,
            "cholesterol": cholesterol,
            "spirometry": spirometry,
            "creatinine": creatinine,
            "glucose": glucose,
            "lipase": lipase,
            "troponin": troponin,
            "include_probabilities": include_probabilities,
        }
    )

    try:
        import pandas as pd

        artifact = _load_model_artifact()
        pipeline = artifact["pipeline"]
        feature_columns = artifact["feature_columns"]
        cholesterol_value = cholestrol if cholestrol is not None else cholesterol

        if cholesterol_value is None:
            error_output = (
                "Error running laboratory disease class prediction: missing cholesterol/cholestrol value. "
                "The trained dataset column is named 'Cholestrol'."
            )
            print("\nLaboratory Disease Class Prediction TOOL ERROR:")
            print(error_output)
            print("\n" + "=" * 70)
            return error_output

        record = {
            "Gender": gender,
            "Age": age,
            "Hemoglobin": hemoglobin,
            "RBC": rbc,
            "WBC": wbc,
            "AST (aspartate aminotransferase)": ast,
            "ALT (alanine aminotransferase)": alt,
            "Cholestrol": cholesterol_value,
            "Spirometry": spirometry,
            "Creatinine": creatinine,
            "Glucose": glucose,
            "Lipase": lipase,
            "Troponin": troponin,
        }

        input_df = pd.DataFrame([record])[feature_columns]
        predicted_class = pipeline.predict(input_df)[0]
        print("\nLaboratory Disease Class Prediction TOOL RESULT:")
        print(f"Predicted class: {predicted_class}")

        output = f"""
Laboratory multi-class model prediction:
- Predicted class: {predicted_class}
- Model artifact: {MODEL_PATH}

Important: This prediction is only machine-learning support for lab interpretation.
It is not a diagnosis and should be correlated with symptoms, history, physical
exam, reference ranges, and clinician judgment.
""".strip()

        if include_probabilities and hasattr(pipeline.named_steps["model"], "predict_proba"):
            probabilities = pipeline.predict_proba(input_df)[0]
            probability_table = _format_probability_table(pipeline.classes_, probabilities)
            output = f"{output}\n\nClass probabilities:\n{probability_table}"

        print("\nLaboratory Disease Class Prediction TOOL OUTPUT:")
        print(output)
        print("\n" + "=" * 70)

        return output

    except Exception as exc:
        error_output = f"Error running laboratory disease class prediction: {exc}"
        print("\nLaboratory Disease Class Prediction TOOL ERROR:")
        print(error_output)
        print("\n" + "=" * 70)
        return error_output

from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    DataInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd
import numpy as np


class ModelExplainer(Component):
    display_name = "Model Explainer"
    description = (
        "Explains a fitted sklearn-style model via built-in feature_importances_/coef_, "
        "permutation importance, or SHAP values (if installed)."
    )
    icon = "mdi-magnify-scan"
    name = "ModelExplainer"

    inputs = [
        DataInput(
            name="model_artifact",
            display_name="Model Artifact",
            info="Artifact produced by a trainer (Data with 'model' field) or a raw sklearn estimator.",
            required=True,
        ),
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            info="DataFrame of features used for explanation. Include the target only if you set target_column.",
            required=True,
        ),
        StrInput(
            name="target_column",
            display_name="Target Column",
            info="Optional target column to exclude from X and use for permutation importance.",
            required=False,
        ),
        DropdownInput(
            name="method",
            display_name="Method",
            options=["auto", "feature_importance", "permutation", "shap"],
            value="auto",
        ),
        IntInput(
            name="top_k",
            display_name="Top K",
            value=20,
        ),
        IntInput(
            name="n_repeats",
            display_name="Permutation Repeats",
            value=5,
        ),
    ]

    outputs = [
        Output(name="importances", display_name="Feature Importances", method="get_importances"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    def _unwrap_model(self):
        art = self.model_artifact
        if art is None:
            raise ValueError("model_artifact is required.")
        data = art.data if hasattr(art, "data") else art
        if isinstance(data, dict) and "model" in data:
            return data["model"]
        return data

    def _split(self):
        df = self.df.copy()
        if self.target_column and self.target_column in df.columns:
            y = df[self.target_column]
            X = df.drop(columns=[self.target_column])
        else:
            y = None
            X = df
        X = X.select_dtypes(include="number")
        if X.empty:
            raise ValueError("No numeric features available for explanation.")
        return X, y

    def _builtin(self, model, X):
        if hasattr(model, "feature_importances_"):
            values = np.asarray(model.feature_importances_, dtype=float)
            method = "feature_importances_"
        elif hasattr(model, "coef_"):
            coef = np.asarray(model.coef_)
            if coef.ndim > 1:
                coef = np.mean(np.abs(coef), axis=0)
            else:
                coef = np.abs(coef)
            values = coef.astype(float)
            method = "abs_coef"
        else:
            return None, None
        return values, method

    def _permutation(self, model, X, y):
        try:
            from sklearn.inspection import permutation_importance
        except ImportError as exc:
            raise ImportError("scikit-learn is required for permutation importance.") from exc
        if y is None:
            raise ValueError("target_column is required for permutation importance.")
        result = permutation_importance(model, X, y, n_repeats=int(self.n_repeats or 5), random_state=42)
        return np.asarray(result.importances_mean, dtype=float), "permutation"

    def _shap(self, model, X):
        try:
            import shap
        except ImportError as exc:
            raise ImportError("shap is required. Install with: pip install shap") from exc
        explainer = shap.Explainer(model, X)
        values = explainer(X).values
        if values.ndim > 2:
            values = np.mean(np.abs(values), axis=(0, 2))
        else:
            values = np.mean(np.abs(values), axis=0)
        return values.astype(float), "shap_mean_abs"

    def _run(self):
        model = self._unwrap_model()
        X, y = self._split()

        method = self.method or "auto"
        if method == "auto":
            values, used = self._builtin(model, X)
            if values is None:
                if y is not None:
                    values, used = self._permutation(model, X, y)
                else:
                    raise ValueError("Model has no feature_importances_/coef_ and no target_column for permutation.")
        elif method == "feature_importance":
            values, used = self._builtin(model, X)
            if values is None:
                raise ValueError("Model exposes neither feature_importances_ nor coef_.")
        elif method == "permutation":
            values, used = self._permutation(model, X, y)
        elif method == "shap":
            values, used = self._shap(model, X)
        else:
            raise ValueError(f"Unsupported method: {method}")

        importances = pd.DataFrame({"feature": X.columns.tolist(), "importance": values})
        importances = importances.sort_values("importance", ascending=False).reset_index(drop=True)
        top_k = int(self.top_k or 20)
        if top_k > 0:
            importances = importances.head(top_k)

        self._importances = importances
        self._report = {
            "method_used": used,
            "num_features": int(len(X.columns)),
            "top_k": top_k,
        }
        self.log(f"ModelExplainer: {self._report}")

    def get_importances(self) -> DataFrame:
        try:
            if not hasattr(self, "_importances"):
                self._run()
            return DataFrame(self._importances)
        except Exception as exc:
            self.log(f"ModelExplainer failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data
import numpy as np


class CrossValidator(Component):
    display_name = "Cross-Validator"
    description = (
        "Runs K-fold cross-validation (stratified for classification) on a scikit-learn "
        "style model and returns per-fold and aggregate scores."
    )
    icon = "mdi-checkbox-multiple-marked-outline"
    name = "CrossValidator"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="target_column",
            display_name="Target Column",
            required=True,
        ),
        DropdownInput(
            name="task",
            display_name="Task",
            options=["classification", "regression"],
            value="classification",
        ),
        DropdownInput(
            name="model_type",
            display_name="Model",
            options=[
                "LogisticRegression",
                "RandomForestClassifier",
                "GradientBoostingClassifier",
                "SVC",
                "LinearRegression",
                "Ridge",
                "RandomForestRegressor",
                "GradientBoostingRegressor",
            ],
            value="LogisticRegression",
        ),
        IntInput(name="folds", display_name="Folds", value=5),
        DropdownInput(
            name="scoring",
            display_name="Scoring",
            options=[
                "accuracy", "f1_macro", "f1_weighted", "roc_auc",
                "r2", "neg_root_mean_squared_error", "neg_mean_absolute_error",
            ],
            value="accuracy",
        ),
    ]

    outputs = [
        Output(name="cv_report", display_name="CV Report", method="get_report"),
    ]

    def _make_model(self, name):
        if name == "LogisticRegression":
            from sklearn.linear_model import LogisticRegression
            return LogisticRegression(max_iter=1000)
        if name == "RandomForestClassifier":
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(random_state=42)
        if name == "GradientBoostingClassifier":
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(random_state=42)
        if name == "SVC":
            from sklearn.svm import SVC
            return SVC(probability=True)
        if name == "LinearRegression":
            from sklearn.linear_model import LinearRegression
            return LinearRegression()
        if name == "Ridge":
            from sklearn.linear_model import Ridge
            return Ridge()
        if name == "RandomForestRegressor":
            from sklearn.ensemble import RandomForestRegressor
            return RandomForestRegressor(random_state=42)
        if name == "GradientBoostingRegressor":
            from sklearn.ensemble import GradientBoostingRegressor
            return GradientBoostingRegressor(random_state=42)
        raise ValueError(f"Unsupported model: {name}")

    def _run(self):
        try:
            from sklearn.model_selection import StratifiedKFold, KFold, cross_val_score
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.target_column or self.target_column not in self.df.columns:
            raise ValueError("Valid target_column is required.")

        df = self.df.copy()
        X = df.drop(columns=[self.target_column]).select_dtypes(include="number")
        y = df[self.target_column]
        if X.empty:
            raise ValueError("No numeric features available.")

        folds = int(self.folds or 5)
        if self.task == "classification":
            cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
        else:
            cv = KFold(n_splits=folds, shuffle=True, random_state=42)

        model = self._make_model(self.model_type)
        scores = cross_val_score(model, X, y, cv=cv, scoring=self.scoring)

        self._report = {
            "model_type": self.model_type,
            "task": self.task,
            "scoring": self.scoring,
            "folds": folds,
            "per_fold": [float(s) for s in scores.tolist()],
            "mean": float(np.mean(scores)),
            "std": float(np.std(scores)),
        }
        self.log(f"CrossValidator: {self._report}")

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            self.log(f"CrossValidator failed: {exc}")
            return Data(data={"error": str(exc)})

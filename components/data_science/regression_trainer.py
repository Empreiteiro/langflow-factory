from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    DropdownInput,
    FloatInput,
    Output,
    StrInput,
)
from lfx.schema import Data
import numpy as np


class RegressionTrainer(Component):
    display_name = "Regression Trainer"
    description = (
        "Trains a regression model (linear, regularized, tree-based, boosting) on a DataFrame "
        "with a numeric target and reports common error metrics on the hold-out set."
    )
    icon = "mdi-chart-line-variant"
    name = "RegressionTrainer"

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
        FloatInput(
            name="test_size",
            display_name="Test Size",
            value=0.2,
        ),
        DropdownInput(
            name="model_type",
            display_name="Model",
            options=[
                "LinearRegression",
                "Ridge",
                "Lasso",
                "ElasticNet",
                "RandomForestRegressor",
                "GradientBoostingRegressor",
                "ExtraTreesRegressor",
                "SVR",
                "KNeighborsRegressor",
                "XGBRegressor",
            ],
            value="RandomForestRegressor",
        ),
    ]

    outputs = [
        Output(name="model", display_name="Trained Model", method="get_model"),
        Output(name="report", display_name="Training Report", method="get_report"),
    ]

    def _make_model(self, name: str):
        if name == "LinearRegression":
            from sklearn.linear_model import LinearRegression
            return LinearRegression()
        if name == "Ridge":
            from sklearn.linear_model import Ridge
            return Ridge()
        if name == "Lasso":
            from sklearn.linear_model import Lasso
            return Lasso()
        if name == "ElasticNet":
            from sklearn.linear_model import ElasticNet
            return ElasticNet()
        if name == "RandomForestRegressor":
            from sklearn.ensemble import RandomForestRegressor
            return RandomForestRegressor(random_state=42)
        if name == "GradientBoostingRegressor":
            from sklearn.ensemble import GradientBoostingRegressor
            return GradientBoostingRegressor(random_state=42)
        if name == "ExtraTreesRegressor":
            from sklearn.ensemble import ExtraTreesRegressor
            return ExtraTreesRegressor(random_state=42)
        if name == "SVR":
            from sklearn.svm import SVR
            return SVR()
        if name == "KNeighborsRegressor":
            from sklearn.neighbors import KNeighborsRegressor
            return KNeighborsRegressor()
        if name == "XGBRegressor":
            try:
                from xgboost import XGBRegressor
            except ImportError as exc:
                raise ImportError("xgboost is required for XGBRegressor.") from exc
            return XGBRegressor(random_state=42)
        raise ValueError(f"Unsupported model: {name}")

    def _run(self):
        try:
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import (
                mean_squared_error, mean_absolute_error, r2_score,
            )
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.target_column or self.target_column not in self.df.columns:
            raise ValueError("Valid target_column is required.")
        if not (0.05 <= float(self.test_size) <= 0.95):
            raise ValueError("test_size must be between 0.05 and 0.95.")

        df = self.df.copy()
        X = df.drop(columns=[self.target_column]).select_dtypes(include="number")
        y = df[self.target_column]
        if X.empty:
            raise ValueError("No numeric features available for regression.")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=float(self.test_size), random_state=42
        )
        model = self._make_model(self.model_type)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        mse = float(mean_squared_error(y_test, preds))
        rmse = float(np.sqrt(mse))
        mae = float(mean_absolute_error(y_test, preds))
        r2 = float(r2_score(y_test, preds))

        self._model = model
        self._report = {
            "model_type": self.model_type,
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "features": X.columns.tolist(),
            "metrics": {"rmse": rmse, "mae": mae, "r2": r2, "mse": mse},
        }
        self.log(f"RegressionTrainer: {self._report['metrics']}")

    def get_model(self) -> Data:
        try:
            if not hasattr(self, "_model"):
                self._run()
            return Data(data={"model": self._model, "type": self.model_type, "report": self._report})
        except Exception as exc:
            self.log(f"RegressionTrainer failed: {exc}")
            return Data(data={"error": str(exc)})

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

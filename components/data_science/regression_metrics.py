from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    Output,
    StrInput,
)
from lfx.schema import Data
import numpy as np


class RegressionMetrics(Component):
    display_name = "Regression Metrics"
    description = (
        "Computes regression metrics (RMSE, MAE, MAPE, R2, explained variance, median AE) "
        "from y_true and y_pred columns."
    )
    icon = "mdi-ruler-square"
    name = "RegressionMetrics"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="y_true",
            display_name="y_true Column",
            required=True,
        ),
        StrInput(
            name="y_pred",
            display_name="y_pred Column",
            required=True,
        ),
    ]

    outputs = [
        Output(name="metrics", display_name="Metrics", method="get_metrics"),
    ]

    def _run(self):
        try:
            from sklearn.metrics import (
                mean_squared_error, mean_absolute_error, median_absolute_error,
                r2_score, explained_variance_score,
            )
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        for col in (self.y_true, self.y_pred):
            if not col or col not in self.df.columns:
                raise ValueError(f"Column '{col}' not found in DataFrame.")

        y_true = self.df[self.y_true].astype(float).values
        y_pred = self.df[self.y_pred].astype(float).values

        mse = float(mean_squared_error(y_true, y_pred))
        rmse = float(np.sqrt(mse))
        mae = float(mean_absolute_error(y_true, y_pred))
        medae = float(median_absolute_error(y_true, y_pred))
        r2 = float(r2_score(y_true, y_pred))
        evs = float(explained_variance_score(y_true, y_pred))

        with np.errstate(divide="ignore", invalid="ignore"):
            mask = y_true != 0
            mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100) if mask.any() else float("nan")

        self._metrics = {
            "rmse": rmse,
            "mse": mse,
            "mae": mae,
            "median_ae": medae,
            "mape_pct": mape,
            "r2": r2,
            "explained_variance": evs,
            "n": int(len(y_true)),
        }
        self.log(f"RegressionMetrics: rmse={rmse:.4f}, r2={r2:.4f}")

    def get_metrics(self) -> Data:
        try:
            if not hasattr(self, "_metrics"):
                self._run()
            return Data(data=self._metrics)
        except Exception as exc:
            self.log(f"RegressionMetrics failed: {exc}")
            return Data(data={"error": str(exc)})

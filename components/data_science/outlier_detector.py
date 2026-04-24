from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    FloatInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd
import numpy as np


class OutlierDetector(Component):
    display_name = "Outlier Detector"
    description = (
        "Detects outliers in numeric columns using IQR, z-score or Isolation Forest. "
        "Can flag them via a new column or remove the offending rows."
    )
    icon = "mdi-alert-decagram"
    name = "OutlierDetector"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            info="Input DataFrame.",
            required=True,
        ),
        StrInput(
            name="columns",
            display_name="Columns",
            info="Columns to inspect. Empty means all numeric columns.",
            is_list=True,
            required=False,
        ),
        DropdownInput(
            name="method",
            display_name="Method",
            options=["iqr", "zscore", "isolation_forest"],
            value="iqr",
        ),
        FloatInput(
            name="threshold",
            display_name="Threshold",
            info="IQR multiplier (default 1.5) or z-score cutoff (default 3.0). Ignored for isolation_forest.",
            value=1.5,
        ),
        FloatInput(
            name="contamination",
            display_name="Contamination",
            info="Expected outlier fraction for Isolation Forest (between 0 and 0.5).",
            value=0.05,
        ),
        DropdownInput(
            name="action",
            display_name="Action",
            options=["flag", "remove"],
            value="flag",
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result DataFrame", method="get_result"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    def _pick_columns(self, df: pd.DataFrame):
        raw = self.columns or []
        if isinstance(raw, str):
            raw = [raw]
        cols = [c for c in raw if isinstance(c, str) and c in df.columns]
        if not cols:
            cols = df.select_dtypes(include=[np.number]).columns.tolist()
        return cols

    def _iqr_mask(self, df: pd.DataFrame, cols, k: float):
        mask = pd.Series(False, index=df.index)
        for c in cols:
            q1, q3 = df[c].quantile(0.25), df[c].quantile(0.75)
            iqr = q3 - q1
            low, high = q1 - k * iqr, q3 + k * iqr
            mask = mask | (df[c] < low) | (df[c] > high)
        return mask

    def _zscore_mask(self, df: pd.DataFrame, cols, z: float):
        mask = pd.Series(False, index=df.index)
        for c in cols:
            series = df[c].astype(float)
            std = series.std(ddof=0)
            if std == 0 or pd.isna(std):
                continue
            scores = (series - series.mean()).abs() / std
            mask = mask | (scores > z)
        return mask

    def _iforest_mask(self, df: pd.DataFrame, cols, contamination: float):
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError as exc:
            raise ImportError("scikit-learn is required for Isolation Forest.") from exc
        X = df[cols].fillna(df[cols].mean(numeric_only=True))
        model = IsolationForest(contamination=contamination, random_state=42)
        preds = model.fit_predict(X)
        return pd.Series(preds == -1, index=df.index)

    def _run(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        df = self.df.copy()
        cols = self._pick_columns(df)
        if not cols:
            raise ValueError("No numeric columns found to inspect.")

        if self.method == "iqr":
            mask = self._iqr_mask(df, cols, float(self.threshold or 1.5))
        elif self.method == "zscore":
            mask = self._zscore_mask(df, cols, float(self.threshold or 3.0))
        elif self.method == "isolation_forest":
            mask = self._iforest_mask(df, cols, float(self.contamination or 0.05))
        else:
            raise ValueError(f"Unsupported method: {self.method}")

        total = int(mask.sum())
        if self.action == "remove":
            result = df.loc[~mask].reset_index(drop=True)
        else:
            result = df.copy()
            result["is_outlier"] = mask.values

        self._report = {
            "method": self.method,
            "columns": cols,
            "num_outliers": total,
            "ratio": float(total / max(len(df), 1)),
            "action": self.action,
            "rows_before": int(len(df)),
            "rows_after": int(len(result)),
        }
        self._result = result
        self.log(f"OutlierDetector: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"OutlierDetector failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

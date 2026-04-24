from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    FloatInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd
import numpy as np


class TargetEncoder(Component):
    display_name = "Target Encoder"
    description = (
        "Encodes categorical columns with smoothed target mean (or frequency). Supports "
        "K-fold out-of-fold encoding to reduce leakage."
    )
    icon = "mdi-target"
    name = "TargetEncoder"

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
        StrInput(
            name="categorical_columns",
            display_name="Categorical Columns",
            info="Columns to encode. Empty = all object/category columns.",
            is_list=True,
            required=False,
        ),
        DropdownInput(
            name="method",
            display_name="Method",
            options=["mean", "frequency"],
            value="mean",
        ),
        FloatInput(
            name="smoothing",
            display_name="Smoothing",
            info="Bayesian smoothing factor. 0 = plain mean, larger = shrink toward the global mean.",
            value=10.0,
        ),
        IntInput(
            name="cv_folds",
            display_name="CV Folds",
            info="Use K-fold out-of-fold encoding. 0 or 1 disables CV.",
            value=5,
        ),
        BoolInput(
            name="drop_original",
            display_name="Drop Original",
            value=False,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result DataFrame", method="get_result"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    def _smoothed_mean(self, series: pd.Series, y: pd.Series, global_mean: float, m: float):
        agg = y.groupby(series).agg(["mean", "count"])
        smoothed = (agg["count"] * agg["mean"] + m * global_mean) / (agg["count"] + m)
        return smoothed

    def _encode_mean_cv(self, df: pd.DataFrame, col: str, y: pd.Series, global_mean: float, m: float, folds: int):
        try:
            from sklearn.model_selection import KFold
        except ImportError as exc:
            raise ImportError("scikit-learn is required for CV target encoding.") from exc
        out = pd.Series(index=df.index, dtype=float)
        kf = KFold(n_splits=folds, shuffle=True, random_state=42)
        for train_idx, val_idx in kf.split(df):
            smoothed = self._smoothed_mean(
                df.iloc[train_idx][col], y.iloc[train_idx], global_mean, m
            )
            out.iloc[val_idx] = df.iloc[val_idx][col].map(smoothed).fillna(global_mean).values
        return out

    def _run(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.target_column or self.target_column not in self.df.columns:
            raise ValueError("Valid target_column is required.")
        df = self.df.copy()
        y = df[self.target_column]

        raw = self.categorical_columns or []
        if isinstance(raw, str):
            raw = [raw]
        cols = [c for c in raw if isinstance(c, str) and c in df.columns]
        if not cols:
            cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            cols = [c for c in cols if c != self.target_column]
        if not cols:
            raise ValueError("No categorical columns to encode.")

        global_mean = float(y.mean()) if pd.api.types.is_numeric_dtype(y) else float(y.value_counts(normalize=True).iloc[0])
        m = float(self.smoothing or 0.0)
        folds = int(self.cv_folds or 0)

        encoded_cols = []
        for c in cols:
            new_col = f"{c}_te"
            if self.method == "frequency":
                freq = df[c].value_counts(normalize=True)
                df[new_col] = df[c].map(freq).fillna(0.0)
            else:
                if folds and folds > 1:
                    df[new_col] = self._encode_mean_cv(df, c, y, global_mean, m, folds)
                else:
                    smoothed = self._smoothed_mean(df[c], y, global_mean, m)
                    df[new_col] = df[c].map(smoothed).fillna(global_mean)
            encoded_cols.append(new_col)

        if self.drop_original:
            df = df.drop(columns=cols)

        self._result = df
        self._report = {
            "method": self.method,
            "encoded_columns": cols,
            "new_columns": encoded_cols,
            "smoothing": m,
            "cv_folds": folds,
            "global_mean": global_mean,
        }
        self.log(f"TargetEncoder: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"TargetEncoder failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

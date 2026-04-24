from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    DropdownInput,
    FloatInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class CorrelationAnalyzer(Component):
    display_name = "Correlation Analyzer"
    description = (
        "Computes pairwise correlations (Pearson, Spearman or Kendall) between numeric "
        "columns and surfaces pairs above a threshold."
    )
    icon = "mdi-chart-bell-curve"
    name = "CorrelationAnalyzer"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="columns",
            display_name="Columns",
            info="Columns to include. Empty = all numeric columns.",
            is_list=True,
            required=False,
        ),
        DropdownInput(
            name="method",
            display_name="Method",
            options=["pearson", "spearman", "kendall"],
            value="pearson",
        ),
        FloatInput(
            name="threshold",
            display_name="Threshold",
            info="Absolute correlation to flag as 'high'.",
            value=0.7,
        ),
    ]

    outputs = [
        Output(name="matrix", display_name="Correlation Matrix", method="get_matrix"),
        Output(name="high", display_name="High Correlations", method="get_high"),
    ]

    def _run(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        df = self.df.copy()

        raw = self.columns or []
        if isinstance(raw, str):
            raw = [raw]
        cols = [c for c in raw if isinstance(c, str) and c in df.columns]
        if not cols:
            cols = df.select_dtypes(include="number").columns.tolist()
        if len(cols) < 2:
            raise ValueError("At least two numeric columns are required.")

        matrix = df[cols].corr(method=self.method or "pearson")

        pairs = []
        threshold = float(self.threshold or 0.0)
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                val = float(matrix.loc[a, b])
                if pd.notna(val) and abs(val) >= threshold:
                    pairs.append({"feature_a": a, "feature_b": b, "correlation": val})

        pairs.sort(key=lambda r: -abs(r["correlation"]))

        self._matrix = matrix.reset_index().rename(columns={"index": "feature"})
        self._high = pairs
        self._info = {"method": self.method, "threshold": threshold, "num_high_pairs": len(pairs)}
        self.log(f"CorrelationAnalyzer: {self._info}")

    def get_matrix(self) -> DataFrame:
        try:
            if not hasattr(self, "_matrix"):
                self._run()
            return DataFrame(self._matrix)
        except Exception as exc:
            self.log(f"CorrelationAnalyzer failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_high(self) -> Data:
        try:
            if not hasattr(self, "_high"):
                self._run()
            return Data(data={"pairs": self._high, **self._info})
        except Exception as exc:
            return Data(data={"error": str(exc)})

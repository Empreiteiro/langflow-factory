from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd
import math


class ClassImbalanceAnalyzer(Component):
    display_name = "Class Imbalance Analyzer"
    description = (
        "Analyzes class distribution for a categorical target: counts, proportions, "
        "imbalance ratio (max/min) and normalized Shannon entropy."
    )
    icon = "mdi-scale-unbalanced"
    name = "ClassImbalanceAnalyzer"

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
    ]

    outputs = [
        Output(name="distribution", display_name="Class Distribution", method="get_distribution"),
        Output(name="summary", display_name="Summary", method="get_summary"),
    ]

    def _run(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.target_column or self.target_column not in self.df.columns:
            raise ValueError("Valid target_column is required.")

        series = self.df[self.target_column]
        counts = series.value_counts(dropna=False)
        proportions = counts / counts.sum()

        rows = [
            {"class": c, "count": int(n), "proportion": float(p)}
            for (c, n), p in zip(counts.items(), proportions.values)
        ]

        max_c, min_c = int(counts.max()), int(counts.min())
        imbalance_ratio = float(max_c / min_c) if min_c > 0 else float("inf")

        n_classes = len(counts)
        if n_classes > 1:
            entropy = -sum(p * math.log2(p) for p in proportions if p > 0)
            max_entropy = math.log2(n_classes)
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        else:
            normalized_entropy = 0.0

        self._distribution = pd.DataFrame(rows)
        self._summary = {
            "target": self.target_column,
            "num_classes": n_classes,
            "total_samples": int(counts.sum()),
            "majority_class": counts.idxmax(),
            "minority_class": counts.idxmin(),
            "imbalance_ratio": imbalance_ratio,
            "normalized_entropy": float(normalized_entropy),
        }
        self.log(f"ClassImbalanceAnalyzer: {self._summary}")

    def get_distribution(self) -> DataFrame:
        try:
            if not hasattr(self, "_distribution"):
                self._run()
            return DataFrame(self._distribution)
        except Exception as exc:
            self.log(f"ClassImbalanceAnalyzer failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_summary(self) -> Data:
        try:
            if not hasattr(self, "_summary"):
                self._run()
            return Data(data=self._summary)
        except Exception as exc:
            return Data(data={"error": str(exc)})

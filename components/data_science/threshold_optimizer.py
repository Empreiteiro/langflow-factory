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
import numpy as np


class ThresholdOptimizer(Component):
    display_name = "Threshold Optimizer"
    description = (
        "Finds the optimal decision threshold for a binary classifier by sweeping predicted "
        "probabilities and maximizing F1, Youden's J, accuracy, or matching a target precision/recall."
    )
    icon = "mdi-arrow-split-horizontal"
    name = "ThresholdOptimizer"

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
            name="y_proba",
            display_name="y_proba Column",
            info="Predicted probability for the positive class.",
            required=True,
        ),
        DropdownInput(
            name="objective",
            display_name="Objective",
            options=["f1", "youden", "accuracy", "target_precision", "target_recall"],
            value="f1",
        ),
        FloatInput(
            name="target",
            display_name="Target",
            info="Desired precision or recall when objective is target_*.",
            value=0.9,
        ),
        FloatInput(name="step", display_name="Step", value=0.01),
    ]

    outputs = [
        Output(name="best", display_name="Best Threshold", method="get_best"),
        Output(name="sweep", display_name="Threshold Sweep", method="get_sweep"),
    ]

    def _run(self):
        try:
            from sklearn.metrics import (
                precision_score, recall_score, f1_score, accuracy_score,
            )
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        for col in (self.y_true, self.y_proba):
            if not col or col not in self.df.columns:
                raise ValueError(f"Column '{col}' not found in DataFrame.")

        y_true = self.df[self.y_true].astype(int).values
        y_proba = self.df[self.y_proba].astype(float).values

        step = max(float(self.step or 0.01), 1e-4)
        thresholds = np.arange(step, 1.0, step)

        rows = []
        for t in thresholds:
            y_pred = (y_proba >= t).astype(int)
            if y_pred.sum() == 0 or y_pred.sum() == len(y_pred):
                precision = 0.0
            else:
                precision = float(precision_score(y_true, y_pred, zero_division=0))
            recall = float(recall_score(y_true, y_pred, zero_division=0))
            f1 = float(f1_score(y_true, y_pred, zero_division=0))
            acc = float(accuracy_score(y_true, y_pred))
            youden = recall - (1 - precision) if precision + recall > 0 else 0.0
            rows.append({
                "threshold": float(t),
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "accuracy": acc,
                "youden_j": youden,
            })

        sweep = pd.DataFrame(rows)
        if sweep.empty:
            raise ValueError("Threshold sweep is empty.")

        objective = self.objective or "f1"
        if objective == "f1":
            best_idx = sweep["f1"].idxmax()
        elif objective == "youden":
            best_idx = sweep["youden_j"].idxmax()
        elif objective == "accuracy":
            best_idx = sweep["accuracy"].idxmax()
        elif objective == "target_precision":
            target = float(self.target or 0.9)
            candidates = sweep[sweep["precision"] >= target]
            best_idx = candidates["recall"].idxmax() if not candidates.empty else sweep["precision"].idxmax()
        elif objective == "target_recall":
            target = float(self.target or 0.9)
            candidates = sweep[sweep["recall"] >= target]
            best_idx = candidates["precision"].idxmax() if not candidates.empty else sweep["recall"].idxmax()
        else:
            raise ValueError(f"Unsupported objective: {objective}")

        best = sweep.loc[best_idx].to_dict()
        self._best = {"objective": objective, **{k: float(v) for k, v in best.items()}}
        self._sweep = sweep
        self.log(f"ThresholdOptimizer: {self._best}")

    def get_best(self) -> Data:
        try:
            if not hasattr(self, "_best"):
                self._run()
            return Data(data=self._best)
        except Exception as exc:
            self.log(f"ThresholdOptimizer failed: {exc}")
            return Data(data={"error": str(exc)})

    def get_sweep(self) -> DataFrame:
        try:
            if not hasattr(self, "_sweep"):
                self._run()
            return DataFrame(self._sweep)
        except Exception as exc:
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

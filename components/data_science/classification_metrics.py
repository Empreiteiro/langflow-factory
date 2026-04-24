from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd
import numpy as np


class ClassificationMetrics(Component):
    display_name = "Classification Metrics"
    description = (
        "Computes classification metrics (accuracy, precision/recall/F1, confusion matrix, "
        "ROC AUC and full classification report) from y_true and y_pred columns."
    )
    icon = "mdi-check-decagram"
    name = "ClassificationMetrics"

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
        StrInput(
            name="y_proba",
            display_name="y_proba Column",
            info="Optional column with predicted probability for the positive class (binary).",
            required=False,
        ),
        StrInput(
            name="average",
            display_name="Average",
            info="Averaging method for multi-class metrics: 'binary', 'macro', 'weighted', 'micro'.",
            value="weighted",
        ),
    ]

    outputs = [
        Output(name="metrics", display_name="Metrics", method="get_metrics"),
        Output(name="confusion", display_name="Confusion Matrix", method="get_confusion"),
    ]

    def _run(self):
        try:
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score, f1_score,
                confusion_matrix, classification_report, roc_auc_score,
            )
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        for col in (self.y_true, self.y_pred):
            if not col or col not in self.df.columns:
                raise ValueError(f"Column '{col}' not found in DataFrame.")

        y_true = self.df[self.y_true]
        y_pred = self.df[self.y_pred]
        avg = self.average or "weighted"

        metrics = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, average=avg, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, average=avg, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, average=avg, zero_division=0)),
            "average": avg,
            "support": int(len(y_true)),
        }

        if self.y_proba and self.y_proba in self.df.columns:
            try:
                proba = self.df[self.y_proba].astype(float)
                metrics["roc_auc"] = float(roc_auc_score(y_true, proba))
            except Exception as exc:
                self.log(f"ROC AUC failed: {exc}")
                metrics["roc_auc"] = None

        report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        metrics["report"] = report

        labels = sorted(pd.Series(y_true).unique().tolist())
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        cm_df = pd.DataFrame(cm, index=[f"true_{l}" for l in labels], columns=[f"pred_{l}" for l in labels])
        cm_df.insert(0, "class", cm_df.index)

        self._metrics = metrics
        self._confusion = cm_df.reset_index(drop=True)
        self.log(f"ClassificationMetrics: accuracy={metrics['accuracy']:.4f}, f1={metrics['f1']:.4f}")

    def get_metrics(self) -> Data:
        try:
            if not hasattr(self, "_metrics"):
                self._run()
            return Data(data=self._metrics)
        except Exception as exc:
            self.log(f"ClassificationMetrics failed: {exc}")
            return Data(data={"error": str(exc)})

    def get_confusion(self) -> DataFrame:
        try:
            if not hasattr(self, "_confusion"):
                self._run()
            return DataFrame(self._confusion)
        except Exception as exc:
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

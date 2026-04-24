from lfx.custom import Component
from lfx.io import (
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


class DataDriftDetector(Component):
    display_name = "Data Drift Detector"
    description = (
        "Compares a reference and a current DataFrame per-feature using the Kolmogorov-Smirnov "
        "test (numeric) or Population Stability Index."
    )
    icon = "mdi-compare-horizontal"
    name = "DataDriftDetector"

    inputs = [
        DataFrameInput(
            name="reference_df",
            display_name="Reference DataFrame",
            required=True,
        ),
        DataFrameInput(
            name="current_df",
            display_name="Current DataFrame",
            required=True,
        ),
        StrInput(
            name="features",
            display_name="Features",
            info="Columns to test. Empty = columns present in both DataFrames.",
            is_list=True,
            required=False,
        ),
        DropdownInput(
            name="method",
            display_name="Method",
            options=["ks", "psi"],
            value="ks",
        ),
        IntInput(
            name="psi_bins",
            display_name="PSI Bins",
            value=10,
        ),
        FloatInput(
            name="alpha",
            display_name="KS Alpha",
            info="Significance level for the KS test.",
            value=0.05,
        ),
    ]

    outputs = [
        Output(name="per_feature", display_name="Per-Feature Drift", method="get_per_feature"),
        Output(name="summary", display_name="Summary", method="get_summary"),
    ]

    def _psi(self, ref: np.ndarray, cur: np.ndarray, bins: int) -> float:
        edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
        if len(edges) < 2:
            return 0.0
        ref_hist, _ = np.histogram(ref, bins=edges)
        cur_hist, _ = np.histogram(cur, bins=edges)
        eps = 1e-6
        ref_pct = ref_hist / max(ref_hist.sum(), 1) + eps
        cur_pct = cur_hist / max(cur_hist.sum(), 1) + eps
        return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))

    def _ks_signal(self, stat, p, alpha):
        if p < alpha:
            return "drift"
        return "ok"

    def _psi_signal(self, value):
        if value < 0.1:
            return "ok"
        if value < 0.25:
            return "minor"
        return "drift"

    def _run(self):
        if self.reference_df is None or self.current_df is None:
            raise ValueError("Both reference and current DataFrames are required.")
        ref = self.reference_df
        cur = self.current_df

        raw = self.features or []
        if isinstance(raw, str):
            raw = [raw]
        if raw:
            feats = [c for c in raw if c in ref.columns and c in cur.columns]
        else:
            feats = [c for c in ref.columns if c in cur.columns]
        if not feats:
            raise ValueError("No overlapping features between the two DataFrames.")

        method = self.method or "ks"
        alpha = float(self.alpha or 0.05)

        rows = []
        drift_count = 0

        if method == "ks":
            try:
                from scipy import stats
            except ImportError as exc:
                raise ImportError("scipy is required for KS drift.") from exc
            for f in feats:
                if not pd.api.types.is_numeric_dtype(ref[f]):
                    continue
                a = ref[f].dropna().values
                b = cur[f].dropna().values
                if len(a) == 0 or len(b) == 0:
                    continue
                stat, p = stats.ks_2samp(a, b)
                signal = self._ks_signal(stat, p, alpha)
                if signal == "drift":
                    drift_count += 1
                rows.append({
                    "feature": f,
                    "statistic": float(stat),
                    "p_value": float(p),
                    "signal": signal,
                })
        else:
            bins = int(self.psi_bins or 10)
            for f in feats:
                if not pd.api.types.is_numeric_dtype(ref[f]):
                    continue
                a = ref[f].dropna().values
                b = cur[f].dropna().values
                if len(a) == 0 or len(b) == 0:
                    continue
                psi = self._psi(a, b, bins)
                signal = self._psi_signal(psi)
                if signal == "drift":
                    drift_count += 1
                rows.append({"feature": f, "psi": psi, "signal": signal})

        self._per_feature = pd.DataFrame(rows)
        self._summary = {
            "method": method,
            "features_tested": len(rows),
            "features_drifted": drift_count,
            "drift_ratio": float(drift_count / max(len(rows), 1)),
        }
        self.log(f"DataDriftDetector: {self._summary}")

    def get_per_feature(self) -> DataFrame:
        try:
            if not hasattr(self, "_per_feature"):
                self._run()
            return DataFrame(self._per_feature)
        except Exception as exc:
            self.log(f"DataDriftDetector failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_summary(self) -> Data:
        try:
            if not hasattr(self, "_summary"):
                self._run()
            return Data(data=self._summary)
        except Exception as exc:
            return Data(data={"error": str(exc)})

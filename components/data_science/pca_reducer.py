from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    FloatInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class PCAReducer(Component):
    display_name = "PCA / Dimensionality Reducer"
    description = (
        "Applies PCA to numeric features. Supports a fixed number of components or "
        "a variance-retention ratio, with optional whitening and standardization."
    )
    icon = "mdi-chart-scatter-plot"
    name = "PCAReducer"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="columns",
            display_name="Columns",
            info="Numeric columns to reduce. Empty = all numeric columns.",
            is_list=True,
            required=False,
        ),
        IntInput(
            name="n_components",
            display_name="Num Components",
            info="Fixed number of components. Ignored when variance_ratio > 0.",
            value=2,
        ),
        FloatInput(
            name="variance_ratio",
            display_name="Variance Ratio",
            info="Retain enough components to explain this ratio (0-1). Set 0 to use n_components.",
            value=0.0,
        ),
        BoolInput(name="whiten", display_name="Whiten", value=False),
        BoolInput(
            name="standardize",
            display_name="Standardize Input",
            info="Apply StandardScaler before PCA.",
            value=True,
        ),
        BoolInput(
            name="keep_non_numeric",
            display_name="Keep Non-numeric",
            info="Concatenate non-numeric columns to the PCA output.",
            value=True,
        ),
    ]

    outputs = [
        Output(name="reduced", display_name="Reduced DataFrame", method="get_reduced"),
        Output(name="report", display_name="Explained Variance", method="get_report"),
    ]

    def _run(self):
        try:
            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        df = self.df.copy()

        raw = self.columns or []
        if isinstance(raw, str):
            raw = [raw]
        cols = [c for c in raw if isinstance(c, str) and c in df.columns]
        if not cols:
            cols = df.select_dtypes(include="number").columns.tolist()
        if not cols:
            raise ValueError("No numeric columns to reduce.")

        X = df[cols].fillna(df[cols].mean(numeric_only=True))
        if self.standardize:
            X = StandardScaler().fit_transform(X)

        vr = float(self.variance_ratio or 0.0)
        if 0 < vr < 1:
            n = vr
        else:
            n = min(int(self.n_components or 2), len(cols), max(len(df), 1))

        pca = PCA(n_components=n, whiten=bool(self.whiten), random_state=42)
        components = pca.fit_transform(X)

        comp_cols = [f"pc_{i+1}" for i in range(components.shape[1])]
        reduced = pd.DataFrame(components, columns=comp_cols, index=df.index)

        if self.keep_non_numeric:
            non_numeric = [c for c in df.columns if c not in cols]
            if non_numeric:
                reduced = pd.concat([df[non_numeric].reset_index(drop=True),
                                     reduced.reset_index(drop=True)], axis=1)

        self._reduced = reduced
        self._report = {
            "input_columns": cols,
            "n_components": components.shape[1],
            "explained_variance": [float(x) for x in pca.explained_variance_.tolist()],
            "explained_variance_ratio": [float(x) for x in pca.explained_variance_ratio_.tolist()],
            "cumulative_ratio": [float(x) for x in pca.explained_variance_ratio_.cumsum().tolist()],
            "whiten": bool(self.whiten),
            "standardized": bool(self.standardize),
        }
        self.log(f"PCAReducer: {self._report}")

    def get_reduced(self) -> DataFrame:
        try:
            if not hasattr(self, "_reduced"):
                self._run()
            return DataFrame(self._reduced)
        except Exception as exc:
            self.log(f"PCAReducer failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

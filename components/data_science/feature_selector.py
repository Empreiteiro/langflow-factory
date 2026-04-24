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


class FeatureSelector(Component):
    display_name = "Feature Selector"
    description = (
        "Selects the most relevant features using VarianceThreshold, SelectKBest "
        "(f_classif / f_regression / mutual_info) or RFE with a linear estimator."
    )
    icon = "mdi-filter-variant"
    name = "FeatureSelector"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="target_column",
            display_name="Target Column",
            info="Required for SelectKBest and RFE. Ignored for VarianceThreshold.",
            required=False,
        ),
        DropdownInput(
            name="method",
            display_name="Method",
            options=["variance", "kbest", "rfe"],
            value="kbest",
        ),
        DropdownInput(
            name="task",
            display_name="Task",
            options=["classification", "regression"],
            value="classification",
        ),
        IntInput(
            name="k",
            display_name="k",
            info="Number of features to keep for kbest/rfe.",
            value=10,
        ),
        FloatInput(
            name="variance_threshold",
            display_name="Variance Threshold",
            info="Minimum variance for VarianceThreshold.",
            value=0.0,
        ),
        DropdownInput(
            name="score_func",
            display_name="Score Function (kbest)",
            options=["f_classif", "f_regression", "mutual_info_classif", "mutual_info_regression", "chi2"],
            value="f_classif",
        ),
    ]

    outputs = [
        Output(name="selected", display_name="Selected Features", method="get_selected"),
        Output(name="scores", display_name="Feature Scores", method="get_scores"),
    ]

    def _split_xy(self, df):
        if not self.target_column or self.target_column not in df.columns:
            raise ValueError("target_column is required and must exist in the DataFrame.")
        X = df.drop(columns=[self.target_column]).select_dtypes(include="number")
        y = df[self.target_column]
        if X.empty:
            raise ValueError("No numeric feature columns available.")
        return X, y

    def _score_func(self):
        from sklearn.feature_selection import (
            f_classif, f_regression, mutual_info_classif, mutual_info_regression, chi2,
        )
        return {
            "f_classif": f_classif,
            "f_regression": f_regression,
            "mutual_info_classif": mutual_info_classif,
            "mutual_info_regression": mutual_info_regression,
            "chi2": chi2,
        }[self.score_func or "f_classif"]

    def _run(self):
        try:
            from sklearn.feature_selection import (
                VarianceThreshold, SelectKBest, RFE,
            )
        except ImportError as exc:
            raise ImportError("scikit-learn is required.") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        df = self.df.copy()

        if self.method == "variance":
            numeric = df.select_dtypes(include="number")
            sel = VarianceThreshold(threshold=float(self.variance_threshold or 0.0))
            sel.fit(numeric)
            kept = numeric.columns[sel.get_support()].tolist()
            scores = dict(zip(numeric.columns, numeric.var().tolist()))
            result = df[kept + [c for c in df.columns if c not in numeric.columns]]
        elif self.method == "kbest":
            X, y = self._split_xy(df)
            k = min(int(self.k or 10), X.shape[1])
            sel = SelectKBest(score_func=self._score_func(), k=k)
            sel.fit(X, y)
            kept = X.columns[sel.get_support()].tolist()
            scores = dict(zip(X.columns.tolist(), [float(s) for s in sel.scores_]))
            result = df[kept + [self.target_column]]
        elif self.method == "rfe":
            X, y = self._split_xy(df)
            if self.task == "regression":
                from sklearn.linear_model import LinearRegression
                estimator = LinearRegression()
            else:
                from sklearn.linear_model import LogisticRegression
                estimator = LogisticRegression(max_iter=1000)
            k = min(int(self.k or 10), X.shape[1])
            sel = RFE(estimator=estimator, n_features_to_select=k)
            sel.fit(X, y)
            kept = X.columns[sel.get_support()].tolist()
            scores = dict(zip(X.columns.tolist(), [int(r) for r in sel.ranking_]))
            result = df[kept + [self.target_column]]
        else:
            raise ValueError(f"Unsupported method: {self.method}")

        self._result = result
        self._scores = pd.DataFrame(
            sorted(scores.items(), key=lambda kv: -kv[1] if self.method != "rfe" else kv[1]),
            columns=["feature", "score"],
        )
        self._info = {"method": self.method, "kept": kept, "total_candidates": len(scores)}
        self.log(f"FeatureSelector: {self._info}")

    def get_selected(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"FeatureSelector failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_scores(self) -> Data:
        try:
            if not hasattr(self, "_scores"):
                self._run()
            return Data(data={"scores": self._scores.to_dict(orient="records"), **self._info})
        except Exception as exc:
            return Data(data={"error": str(exc)})

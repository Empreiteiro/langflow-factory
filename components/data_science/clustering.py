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


class Clustering(Component):
    display_name = "Clustering"
    description = (
        "Clusters rows using KMeans, DBSCAN, Agglomerative or Gaussian Mixture, with optional "
        "input standardization and silhouette scoring."
    )
    icon = "mdi-chart-bubble"
    name = "Clustering"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="columns",
            display_name="Feature Columns",
            info="Columns to cluster. Empty = all numeric columns.",
            is_list=True,
            required=False,
        ),
        DropdownInput(
            name="algorithm",
            display_name="Algorithm",
            options=["kmeans", "dbscan", "agglomerative", "gmm"],
            value="kmeans",
            real_time_refresh=True,
        ),
        IntInput(
            name="n_clusters",
            display_name="n_clusters",
            value=3,
        ),
        FloatInput(
            name="eps",
            display_name="eps (DBSCAN)",
            value=0.5,
        ),
        IntInput(
            name="min_samples",
            display_name="min_samples (DBSCAN)",
            value=5,
        ),
        BoolInput(
            name="standardize",
            display_name="Standardize",
            value=True,
        ),
        BoolInput(
            name="compute_silhouette",
            display_name="Compute Silhouette",
            value=True,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Clustered DataFrame", method="get_result"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    def _run(self):
        try:
            from sklearn.preprocessing import StandardScaler
            from sklearn.metrics import silhouette_score
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
            raise ValueError("No numeric columns to cluster.")

        X = df[cols].fillna(df[cols].mean(numeric_only=True))
        if self.standardize:
            X = StandardScaler().fit_transform(X)

        algo = self.algorithm or "kmeans"
        if algo == "kmeans":
            from sklearn.cluster import KMeans
            model = KMeans(n_clusters=int(self.n_clusters or 3), n_init="auto", random_state=42)
            labels = model.fit_predict(X)
        elif algo == "dbscan":
            from sklearn.cluster import DBSCAN
            model = DBSCAN(eps=float(self.eps or 0.5), min_samples=int(self.min_samples or 5))
            labels = model.fit_predict(X)
        elif algo == "agglomerative":
            from sklearn.cluster import AgglomerativeClustering
            model = AgglomerativeClustering(n_clusters=int(self.n_clusters or 3))
            labels = model.fit_predict(X)
        elif algo == "gmm":
            from sklearn.mixture import GaussianMixture
            model = GaussianMixture(n_components=int(self.n_clusters or 3), random_state=42)
            labels = model.fit_predict(X)
        else:
            raise ValueError(f"Unsupported algorithm: {algo}")

        result = df.copy()
        result["cluster"] = labels

        unique_labels = [int(l) for l in pd.Series(labels).unique().tolist()]
        silhouette = None
        if self.compute_silhouette and len([l for l in unique_labels if l != -1]) > 1:
            try:
                mask = labels != -1
                if mask.sum() >= 2:
                    silhouette = float(silhouette_score(
                        X[mask] if hasattr(X, "shape") else [X[i] for i in range(len(X)) if mask[i]],
                        labels[mask],
                    ))
            except Exception as exc:
                self.log(f"Silhouette computation failed: {exc}")

        self._result = result
        self._report = {
            "algorithm": algo,
            "features": cols,
            "standardized": bool(self.standardize),
            "num_clusters": len([l for l in unique_labels if l != -1]),
            "noise_points": int((labels == -1).sum()),
            "silhouette_score": silhouette,
            "cluster_sizes": pd.Series(labels).value_counts().to_dict(),
        }
        self.log(f"Clustering: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"Clustering failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

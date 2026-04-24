from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class BinningDiscretizer(Component):
    display_name = "Binning / Discretizer"
    description = (
        "Discretizes numeric columns into bins using uniform, quantile or k-means strategies, "
        "with ordinal or one-hot encoding."
    )
    icon = "mdi-chart-bar"
    name = "BinningDiscretizer"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="columns",
            display_name="Columns",
            info="Numeric columns to discretize. Empty = all numeric columns.",
            is_list=True,
            required=False,
        ),
        IntInput(
            name="n_bins",
            display_name="Bins",
            value=5,
        ),
        DropdownInput(
            name="strategy",
            display_name="Strategy",
            options=["uniform", "quantile", "kmeans"],
            value="quantile",
        ),
        DropdownInput(
            name="encode",
            display_name="Encode",
            options=["ordinal", "onehot"],
            value="ordinal",
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

    def _run(self):
        try:
            from sklearn.preprocessing import KBinsDiscretizer
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
            raise ValueError("No numeric columns to discretize.")

        encode_mode = "onehot-dense" if self.encode == "onehot" else "ordinal"
        discretizer = KBinsDiscretizer(
            n_bins=int(self.n_bins or 5),
            encode=encode_mode,
            strategy=self.strategy or "quantile",
        )
        X = df[cols].fillna(df[cols].mean(numeric_only=True))
        transformed = discretizer.fit_transform(X)

        if self.encode == "onehot":
            feature_names = []
            for col, edges in zip(cols, discretizer.bin_edges_):
                feature_names += [f"{col}_bin_{i}" for i in range(len(edges) - 1)]
            binned = pd.DataFrame(transformed, columns=feature_names, index=df.index)
            result = pd.concat([df, binned], axis=1)
            if self.drop_original:
                result = result.drop(columns=cols)
        else:
            new_cols = [f"{c}_bin" for c in cols]
            binned = pd.DataFrame(transformed, columns=new_cols, index=df.index).astype(int)
            result = pd.concat([df, binned], axis=1)
            if self.drop_original:
                result = result.drop(columns=cols)

        self._result = result
        self._report = {
            "columns": cols,
            "n_bins": int(self.n_bins or 5),
            "strategy": self.strategy,
            "encode": self.encode,
            "bin_edges": {c: [float(x) for x in e] for c, e in zip(cols, discretizer.bin_edges_)},
        }
        self.log(f"BinningDiscretizer: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"BinningDiscretizer failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

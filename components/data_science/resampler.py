from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class Resampler(Component):
    display_name = "Resampler (SMOTE/Undersample)"
    description = (
        "Balances a classification dataset via oversampling (SMOTE, RandomOverSampler, ADASYN) "
        "or undersampling (RandomUnderSampler, NearMiss) using imbalanced-learn."
    )
    icon = "mdi-scale-balance"
    name = "Resampler"

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
        DropdownInput(
            name="method",
            display_name="Method",
            options=["smote", "random_over", "adasyn", "random_under", "near_miss"],
            value="smote",
        ),
        DropdownInput(
            name="sampling_strategy",
            display_name="Sampling Strategy",
            options=["auto", "minority", "not minority", "not majority", "all"],
            value="auto",
        ),
        IntInput(name="random_state", display_name="Random State", value=42),
        IntInput(
            name="k_neighbors",
            display_name="k Neighbors (SMOTE)",
            value=5,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Resampled DataFrame", method="get_result"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    def _run(self):
        try:
            from imblearn.over_sampling import SMOTE, RandomOverSampler, ADASYN
            from imblearn.under_sampling import RandomUnderSampler, NearMiss
        except ImportError as exc:
            raise ImportError(
                "imbalanced-learn is required. Install with: pip install imbalanced-learn"
            ) from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.target_column or self.target_column not in self.df.columns:
            raise ValueError("Valid target_column is required.")

        df = self.df.copy()
        y = df[self.target_column]
        X = df.drop(columns=[self.target_column]).select_dtypes(include="number")
        if X.empty:
            raise ValueError("No numeric features available for resampling.")

        strategy = self.sampling_strategy or "auto"
        seed = int(self.random_state or 42)

        if self.method == "smote":
            sampler = SMOTE(sampling_strategy=strategy, random_state=seed, k_neighbors=int(self.k_neighbors or 5))
        elif self.method == "random_over":
            sampler = RandomOverSampler(sampling_strategy=strategy, random_state=seed)
        elif self.method == "adasyn":
            sampler = ADASYN(sampling_strategy=strategy, random_state=seed, n_neighbors=int(self.k_neighbors or 5))
        elif self.method == "random_under":
            sampler = RandomUnderSampler(sampling_strategy=strategy, random_state=seed)
        elif self.method == "near_miss":
            sampler = NearMiss(sampling_strategy=strategy)
        else:
            raise ValueError(f"Unsupported method: {self.method}")

        X_res, y_res = sampler.fit_resample(X, y)
        result = pd.DataFrame(X_res, columns=X.columns)
        result[self.target_column] = y_res.values if hasattr(y_res, "values") else y_res

        before = y.value_counts().to_dict()
        after = pd.Series(y_res).value_counts().to_dict()

        self._result = result
        self._report = {
            "method": self.method,
            "strategy": strategy,
            "before": before,
            "after": after,
            "rows_before": int(len(df)),
            "rows_after": int(len(result)),
        }
        self.log(f"Resampler: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"Resampler failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

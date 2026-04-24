from lfx.custom import Component
from lfx.io import (
    DataFrameInput,
    DropdownInput,
    FloatInput,
    Output,
    StrInput,
)
from lfx.schema import Data


class StatisticalTests(Component):
    display_name = "Statistical Tests"
    description = (
        "Runs common hypothesis tests: Welch's t-test, one-way ANOVA, chi-square independence, "
        "Mann-Whitney U, and Kolmogorov-Smirnov two-sample."
    )
    icon = "mdi-sigma"
    name = "StatisticalTests"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        DropdownInput(
            name="test",
            display_name="Test",
            options=["ttest", "anova", "chi2", "mannwhitney", "ks"],
            value="ttest",
            real_time_refresh=True,
        ),
        StrInput(
            name="value_column",
            display_name="Value Column",
            info="Numeric column under test (ttest/anova/mannwhitney/ks).",
            required=False,
        ),
        StrInput(
            name="group_column",
            display_name="Group Column",
            info="Categorical column defining groups.",
            required=False,
        ),
        StrInput(
            name="column_a",
            display_name="Column A",
            info="Used when no group_column is provided (compares two columns directly).",
            required=False,
        ),
        StrInput(
            name="column_b",
            display_name="Column B",
            required=False,
        ),
        FloatInput(
            name="alpha",
            display_name="Alpha",
            value=0.05,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="get_result"),
    ]

    def _get_samples(self, df):
        if self.group_column and self.value_column and self.group_column in df.columns:
            groups = [g.dropna().values for _, g in df.groupby(self.group_column)[self.value_column]]
            return groups
        if self.column_a and self.column_b and self.column_a in df.columns and self.column_b in df.columns:
            return [df[self.column_a].dropna().values, df[self.column_b].dropna().values]
        raise ValueError(
            "Provide either (value_column + group_column) or (column_a + column_b)."
        )

    def _run(self):
        try:
            from scipy import stats
        except ImportError as exc:
            raise ImportError("scipy is required. Install with: pip install scipy") from exc

        if self.df is None:
            raise ValueError("No DataFrame provided.")
        df = self.df

        alpha = float(self.alpha or 0.05)
        test = self.test or "ttest"

        if test == "chi2":
            if not (self.column_a and self.column_b and self.column_a in df.columns and self.column_b in df.columns):
                raise ValueError("chi2 needs column_a and column_b.")
            contingency = df.groupby([self.column_a, self.column_b]).size().unstack(fill_value=0)
            chi2, p, dof, expected = stats.chi2_contingency(contingency.values)
            result = {
                "test": "chi2_contingency",
                "statistic": float(chi2),
                "p_value": float(p),
                "dof": int(dof),
                "reject_null": bool(p < alpha),
            }
        else:
            samples = self._get_samples(df)
            if test == "ttest":
                if len(samples) != 2:
                    raise ValueError("ttest requires exactly two groups.")
                stat, p = stats.ttest_ind(samples[0], samples[1], equal_var=False)
                name = "welch_ttest"
            elif test == "anova":
                if len(samples) < 2:
                    raise ValueError("ANOVA requires at least two groups.")
                stat, p = stats.f_oneway(*samples)
                name = "anova"
            elif test == "mannwhitney":
                if len(samples) != 2:
                    raise ValueError("mannwhitney requires exactly two groups.")
                stat, p = stats.mannwhitneyu(samples[0], samples[1], alternative="two-sided")
                name = "mann_whitney_u"
            elif test == "ks":
                if len(samples) != 2:
                    raise ValueError("ks requires exactly two groups.")
                stat, p = stats.ks_2samp(samples[0], samples[1])
                name = "ks_2samp"
            else:
                raise ValueError(f"Unsupported test: {test}")
            result = {
                "test": name,
                "statistic": float(stat),
                "p_value": float(p),
                "alpha": alpha,
                "reject_null": bool(p < alpha),
                "group_sizes": [int(len(s)) for s in samples],
            }

        self._result = result
        self.log(f"StatisticalTests: {result}")

    def get_result(self) -> Data:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return Data(data=self._result)
        except Exception as exc:
            self.log(f"StatisticalTests failed: {exc}")
            return Data(data={"error": str(exc)})

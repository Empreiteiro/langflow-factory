from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    FloatInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class DuplicateHandler(Component):
    display_name = "Duplicate Handler"
    description = (
        "Removes or flags duplicate rows. Supports exact matching on a column subset "
        "and fuzzy string matching on a single text column."
    )
    icon = "mdi-content-duplicate"
    name = "DuplicateHandler"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="subset",
            display_name="Subset Columns",
            info="Columns to consider for duplicate detection. Empty = all columns.",
            is_list=True,
            required=False,
        ),
        DropdownInput(
            name="keep",
            display_name="Keep",
            options=["first", "last", "none"],
            value="first",
        ),
        DropdownInput(
            name="action",
            display_name="Action",
            options=["remove", "flag"],
            value="remove",
        ),
        BoolInput(
            name="fuzzy",
            display_name="Fuzzy Match",
            info="Use fuzzy string matching instead of exact equality.",
            value=False,
            real_time_refresh=True,
        ),
        StrInput(
            name="fuzzy_column",
            display_name="Fuzzy Column",
            info="Text column used for fuzzy deduplication.",
            show=False,
        ),
        FloatInput(
            name="fuzzy_threshold",
            display_name="Fuzzy Threshold",
            info="Similarity score (0-100). Pairs at or above are treated as duplicates.",
            value=90.0,
            show=False,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result DataFrame", method="get_result"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name == "fuzzy":
            show = bool(field_value)
            for n in ("fuzzy_column", "fuzzy_threshold"):
                if n in build_config:
                    build_config[n]["show"] = show
        return build_config

    def _subset(self, df):
        raw = self.subset or []
        if isinstance(raw, str):
            raw = [raw]
        cols = [c for c in raw if isinstance(c, str) and c in df.columns]
        return cols or None

    def _exact(self, df: pd.DataFrame) -> pd.Series:
        keep = False if self.keep == "none" else self.keep
        return df.duplicated(subset=self._subset(df), keep=keep)

    def _fuzzy(self, df: pd.DataFrame) -> pd.Series:
        col = self.fuzzy_column
        if not col or col not in df.columns:
            raise ValueError("fuzzy_column is required when fuzzy matching is enabled.")
        try:
            from rapidfuzz import fuzz
        except ImportError as exc:
            raise ImportError(
                "rapidfuzz is required for fuzzy matching. Install with: pip install rapidfuzz"
            ) from exc

        threshold = float(self.fuzzy_threshold or 90.0)
        values = df[col].astype(str).fillna("").tolist()
        is_dup = [False] * len(values)
        seen = []
        for idx, v in enumerate(values):
            hit = False
            for s_idx in seen:
                if fuzz.token_set_ratio(v, values[s_idx]) >= threshold:
                    hit = True
                    if self.keep == "last":
                        is_dup[s_idx] = True
                        seen.remove(s_idx)
                        seen.append(idx)
                    elif self.keep == "none":
                        is_dup[s_idx] = True
                        is_dup[idx] = True
                    else:
                        is_dup[idx] = True
                    break
            if not hit:
                seen.append(idx)
        return pd.Series(is_dup, index=df.index)

    def _run(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        df = self.df.copy()
        mask = self._fuzzy(df) if self.fuzzy else self._exact(df)

        if self.action == "remove":
            result = df.loc[~mask].reset_index(drop=True)
        else:
            result = df.copy()
            result["is_duplicate"] = mask.values

        self._report = {
            "fuzzy": bool(self.fuzzy),
            "threshold": float(self.fuzzy_threshold or 0),
            "num_duplicates": int(mask.sum()),
            "rows_before": int(len(df)),
            "rows_after": int(len(result)),
            "action": self.action,
        }
        self._result = result
        self.log(f"DuplicateHandler: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"DuplicateHandler failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

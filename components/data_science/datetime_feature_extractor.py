from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd
import numpy as np


class DateTimeFeatureExtractor(Component):
    display_name = "Date/Time Feature Extractor"
    description = (
        "Extracts calendar and cyclical features (year, month, day, dow, hour, quarter, "
        "is_weekend, sin/cos encodings) from one or more datetime columns."
    )
    icon = "mdi-calendar-clock"
    name = "DateTimeFeatureExtractor"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="columns",
            display_name="Datetime Columns",
            info="Columns to parse. Empty = auto-detect datetime-like columns.",
            is_list=True,
            required=False,
        ),
        BoolInput(name="extract_year", display_name="Year", value=True),
        BoolInput(name="extract_month", display_name="Month", value=True),
        BoolInput(name="extract_day", display_name="Day", value=True),
        BoolInput(name="extract_dow", display_name="Day of Week", value=True),
        BoolInput(name="extract_hour", display_name="Hour", value=False),
        BoolInput(name="extract_minute", display_name="Minute", value=False),
        BoolInput(name="extract_quarter", display_name="Quarter", value=True),
        BoolInput(name="extract_weekofyear", display_name="Week of Year", value=False),
        BoolInput(name="extract_is_weekend", display_name="Is Weekend", value=True),
        BoolInput(
            name="cyclical",
            display_name="Cyclical (sin/cos)",
            info="Add sin/cos encodings for month, dow and hour.",
            value=False,
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

    def _pick_columns(self, df: pd.DataFrame):
        raw = self.columns or []
        if isinstance(raw, str):
            raw = [raw]
        cols = [c for c in raw if isinstance(c, str) and c in df.columns]
        if cols:
            return cols
        detected = []
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                detected.append(c)
                continue
            try:
                pd.to_datetime(df[c], errors="raise")
                detected.append(c)
            except Exception:
                continue
        return detected

    def _cyclical(self, values, period):
        radians = 2 * np.pi * values / period
        return np.sin(radians), np.cos(radians)

    def _run(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        df = self.df.copy()
        cols = self._pick_columns(df)
        if not cols:
            raise ValueError("No datetime columns found.")

        added = []
        for c in cols:
            series = pd.to_datetime(df[c], errors="coerce")
            if self.extract_year:
                df[f"{c}_year"] = series.dt.year
                added.append(f"{c}_year")
            if self.extract_month:
                df[f"{c}_month"] = series.dt.month
                added.append(f"{c}_month")
            if self.extract_day:
                df[f"{c}_day"] = series.dt.day
                added.append(f"{c}_day")
            if self.extract_dow:
                df[f"{c}_dow"] = series.dt.dayofweek
                added.append(f"{c}_dow")
            if self.extract_hour:
                df[f"{c}_hour"] = series.dt.hour
                added.append(f"{c}_hour")
            if self.extract_minute:
                df[f"{c}_minute"] = series.dt.minute
                added.append(f"{c}_minute")
            if self.extract_quarter:
                df[f"{c}_quarter"] = series.dt.quarter
                added.append(f"{c}_quarter")
            if self.extract_weekofyear:
                df[f"{c}_weekofyear"] = series.dt.isocalendar().week.astype("Int64")
                added.append(f"{c}_weekofyear")
            if self.extract_is_weekend:
                df[f"{c}_is_weekend"] = series.dt.dayofweek.isin([5, 6]).astype(int)
                added.append(f"{c}_is_weekend")
            if self.cyclical:
                s, cv = self._cyclical(series.dt.month.fillna(0), 12)
                df[f"{c}_month_sin"], df[f"{c}_month_cos"] = s, cv
                s, cv = self._cyclical(series.dt.dayofweek.fillna(0), 7)
                df[f"{c}_dow_sin"], df[f"{c}_dow_cos"] = s, cv
                s, cv = self._cyclical(series.dt.hour.fillna(0), 24)
                df[f"{c}_hour_sin"], df[f"{c}_hour_cos"] = s, cv
                added += [
                    f"{c}_month_sin", f"{c}_month_cos",
                    f"{c}_dow_sin", f"{c}_dow_cos",
                    f"{c}_hour_sin", f"{c}_hour_cos",
                ]
            if self.drop_original:
                df = df.drop(columns=[c])

        self._result = df
        self._report = {"columns_processed": cols, "features_added": added}
        self.log(f"DateTimeFeatureExtractor: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"DateTimeFeatureExtractor failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

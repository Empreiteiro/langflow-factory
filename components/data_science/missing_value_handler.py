from langflow.custom import Component
from langflow.io import (
    DropdownInput,
    StrInput,
    BoolInput,
    DataFrameInput,
    IntInput,
    Output,
)
from langflow.schema import DataFrame, Data
import pandas as pd
import numpy as np


class MissingValueHandler(Component):
    display_name = "Missing Value Handler"
    description = "Fill or remove missing values with various strategies."
    icon = "flask-conical"
    name = "MissingValueHandler"
    beta = True

    field_order = [
        "df",
        "strategy",
        "fill_method",
        "custom_value",
        "columns",
        "numeric_only",
        "min_count",
    ]

    inputs = [
        DataFrameInput(
            name="df", 
            display_name="DataFrame", 
            info="The input DataFrame."
        ),
        DropdownInput(
            name="strategy",
            display_name="Strategy",
            options=["fill", "remove_rows", "remove_columns"],
            value="fill",
            info="Strategy to handle missing values.",
        ),
        DropdownInput(
            name="fill_method",
            display_name="Fill Method",
            options=[
                "mean",
                "median",
                "mode",
                "zero",
                "custom",
                "forward_fill",
                "backward_fill",
                "interpolate",
            ],
            value="mean",
            info="Method to fill missing values (only for 'fill' strategy).",
            advanced=True,
        ),
        StrInput(
            name="custom_value",
            display_name="Custom Value",
            value="0",
            info="Custom value to fill missing values (used when fill_method is 'custom').",
            advanced=True,
        ),
        StrInput(
            name="columns",
            display_name="Target Columns",
            info="Comma-separated list of columns to handle (leave empty for all columns).",
            advanced=True,
        ),
        BoolInput(
            name="numeric_only",
            display_name="Numeric Only",
            value=True,
            info="Apply numeric methods only to numeric columns.",
            advanced=True,
        ),
        IntInput(
            name="min_count",
            display_name="Minimum Count",
            value=1,
            info="Minimum number of non-null values required (for remove strategy).",
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="cleaned_df", display_name="DataFrame", method="handle"),
        Output(name="statistics", display_name="Processing Statistics", method="get_statistics"),
    ]

    def build(self):
        try:
            self.df_: pd.DataFrame = self.df.copy()
            self.original_shape = self.df_.shape
            self.original_missing = self.df_.isnull().sum().to_dict()

            self.target_columns = (
                [col.strip() for col in self.columns.split(",") if col.strip() in self.df_.columns]
                if self.columns
                else list(self.df_.columns)
            )

            if not self.target_columns:
                raise ValueError("No valid columns found for processing.")

            if self.strategy == "fill":
                self.df_ = self._fill()
            elif self.strategy == "remove_rows":
                self.df_ = self.df_.dropna(subset=self.target_columns, thresh=self.min_count)
            elif self.strategy == "remove_columns":
                self.df_ = self.df_.drop(columns=[
                    col for col in self.target_columns if self.df_[col].count() < self.min_count
                ])
            else:
                raise ValueError(f"Unsupported strategy: {self.strategy}")

            self.final_shape = self.df_.shape
            self.final_missing = self.df_.isnull().sum().to_dict()
            self.rows_removed = self.original_shape[0] - self.final_shape[0]
            self.columns_removed = self.original_shape[1] - self.final_shape[1]
            self.missing_filled = sum(self.original_missing.values()) - sum(self.final_missing.values())

        except Exception as e:
            self.status = f"Error handling missing values: {str(e)}"
            self.df_ = pd.DataFrame({"error": [str(e)]})

    def handle(self) -> DataFrame:
        return DataFrame(self.df_)

    def get_statistics(self) -> Data:
        return Data(
            data={
                "strategy": self.strategy,
                "fill_method": self.fill_method if self.strategy == "fill" else None,
                "target_columns": self.target_columns,
                "statistics": {
                    "original_shape": self.original_shape,
                    "final_shape": self.final_shape,
                    "rows_removed": self.rows_removed,
                    "columns_removed": self.columns_removed,
                    "missing_values_filled": self.missing_filled,
                    "original_missing": self.original_missing,
                    "final_missing": self.final_missing,
                },
                "processing_info": {
                    "numeric_only": self.numeric_only,
                    "min_count": self.min_count,
                    "custom_value": self.custom_value if self.fill_method == "custom" else None,
                },
            }
        )

    def _fill(self) -> pd.DataFrame:
        df = self.df_.copy()
        for col in self.target_columns:
            if not df[col].isnull().any():
                continue
            if self.fill_method == "mean" and (not self.numeric_only or pd.api.types.is_numeric_dtype(df[col])):
                df[col].fillna(df[col].mean(), inplace=True)
            elif self.fill_method == "median" and (not self.numeric_only or pd.api.types.is_numeric_dtype(df[col])):
                df[col].fillna(df[col].median(), inplace=True)
            elif self.fill_method == "mode":
                mode_val = df[col].mode()
                if not mode_val.empty:
                    df[col].fillna(mode_val.iloc[0], inplace=True)
            elif self.fill_method == "zero" and (not self.numeric_only or pd.api.types.is_numeric_dtype(df[col])):
                df[col].fillna(0, inplace=True)
            elif self.fill_method == "custom":
                try:
                    val = float(self.custom_value) if pd.api.types.is_numeric_dtype(df[col]) else self.custom_value
                    df[col].fillna(val, inplace=True)
                except Exception:
                    df[col].fillna(self.custom_value, inplace=True)
            elif self.fill_method == "forward_fill":
                df[col].fillna(method="ffill", inplace=True)
            elif self.fill_method == "backward_fill":
                df[col].fillna(method="bfill", inplace=True)
            elif self.fill_method == "interpolate" and (not self.numeric_only or pd.api.types.is_numeric_dtype(df[col])):
                df[col].interpolate(method="linear", inplace=True)
        return df

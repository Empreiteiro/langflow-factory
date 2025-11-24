from lfx.custom import Component
from lfx.io import DataFrameInput, Output
from lfx.schema import DataFrame, Data
import pandas as pd


class DataFrameProfiler(Component):
    display_name = "DataFrame Profiler"
    description = "Generates a comprehensive profile of the DataFrame with detailed statistics for each column including null counts, mean, unique values, and other important data science metrics."
    icon = "flask-conical"
    name = "DataFrameProfiler"
    beta = True

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            info="The input DataFrame to profile.",
            required=True
        ),
    ]

    outputs = [
        Output(name="profile_df", display_name="Profile DataFrame", method="get_profile_dataframe"),
        Output(name="detailed_profile", display_name="Detailed Profile", method="get_detailed_profile"),
    ]

    def build(self):
        try:
            if self.df is None or self.df.empty:
                raise ValueError("DataFrame is empty or None.")
            
            self.df_ = self.df.copy()
            self.profile_data = self._generate_profile()
            self.detailed_profile_data = self._generate_detailed_profile()
            self.status = f"Successfully profiled DataFrame with {len(self.df_.columns)} columns and {len(self.df_)} rows."

        except Exception as e:
            self.status = f"Error profiling DataFrame: {str(e)}"
            self.profile_data = pd.DataFrame({"error": [str(e)]})
            self.detailed_profile_data = {"error": str(e)}

    def _generate_profile(self) -> pd.DataFrame:
        """Generate a summary profile DataFrame with key statistics for each column."""
        profile_rows = []
        
        for col in self.df_.columns:
            col_data = self.df_[col]
            dtype = str(col_data.dtype)
            null_count = col_data.isnull().sum()
            null_percentage = (null_count / len(col_data)) * 100
            non_null_count = col_data.notna().sum()
            unique_count = col_data.nunique()
            total_count = len(col_data)
            
            row = {
                "column": col,
                "dtype": dtype,
                "total_count": total_count,
                "non_null_count": non_null_count,
                "null_count": null_count,
                "null_percentage": round(null_percentage, 2),
                "unique_count": unique_count,
                "unique_percentage": round((unique_count / non_null_count * 100) if non_null_count > 0 else 0, 2),
            }
            
            # Numeric statistics
            if pd.api.types.is_numeric_dtype(col_data):
                numeric_data = col_data.dropna()
                if len(numeric_data) > 0:
                    row.update({
                        "mean": round(numeric_data.mean(), 4),
                        "median": round(numeric_data.median(), 4),
                        "std": round(numeric_data.std(), 4) if len(numeric_data) > 1 else 0.0,
                        "min": round(numeric_data.min(), 4),
                        "max": round(numeric_data.max(), 4),
                        "q25": round(numeric_data.quantile(0.25), 4),
                        "q50": round(numeric_data.quantile(0.50), 4),
                        "q75": round(numeric_data.quantile(0.75), 4),
                        "skewness": round(numeric_data.skew(), 4) if len(numeric_data) > 2 else None,
                        "kurtosis": round(numeric_data.kurtosis(), 4) if len(numeric_data) > 2 else None,
                    })
                else:
                    row.update({
                        "mean": None,
                        "median": None,
                        "std": None,
                        "min": None,
                        "max": None,
                        "q25": None,
                        "q50": None,
                        "q75": None,
                        "skewness": None,
                        "kurtosis": None,
                    })
            else:
                row.update({
                    "mean": None,
                    "median": None,
                    "std": None,
                    "min": None,
                    "max": None,
                    "q25": None,
                    "q50": None,
                    "q75": None,
                    "skewness": None,
                    "kurtosis": None,
                })
            
            # Categorical/Text statistics
            if pd.api.types.is_object_dtype(col_data) or pd.api.types.is_string_dtype(col_data):
                categorical_data = col_data.dropna()
                if len(categorical_data) > 0:
                    mode_values = categorical_data.mode()
                    mode_value = mode_values.iloc[0] if len(mode_values) > 0 else None
                    mode_count = (categorical_data == mode_value).sum() if mode_value is not None else 0
                    mode_percentage = (mode_count / len(categorical_data) * 100) if len(categorical_data) > 0 else 0
                    
                    # Average string length
                    str_lengths = categorical_data.astype(str).str.len()
                    avg_length = str_lengths.mean() if len(str_lengths) > 0 else 0
                    min_length = str_lengths.min() if len(str_lengths) > 0 else None
                    max_length = str_lengths.max() if len(str_lengths) > 0 else None
                    
                    row.update({
                        "mode": str(mode_value) if mode_value is not None else None,
                        "mode_count": mode_count,
                        "mode_percentage": round(mode_percentage, 2),
                        "avg_string_length": round(avg_length, 2),
                        "min_string_length": min_length,
                        "max_string_length": max_length,
                    })
                else:
                    row.update({
                        "mode": None,
                        "mode_count": 0,
                        "mode_percentage": 0.0,
                        "avg_string_length": None,
                        "min_string_length": None,
                        "max_string_length": None,
                    })
            else:
                row.update({
                    "mode": None,
                    "mode_count": None,
                    "mode_percentage": None,
                    "avg_string_length": None,
                    "min_string_length": None,
                    "max_string_length": None,
                })
            
            # Datetime statistics
            if pd.api.types.is_datetime64_any_dtype(col_data):
                datetime_data = col_data.dropna()
                if len(datetime_data) > 0:
                    row.update({
                        "min_date": str(datetime_data.min()),
                        "max_date": str(datetime_data.max()),
                        "date_range_days": (datetime_data.max() - datetime_data.min()).days,
                    })
                else:
                    row.update({
                        "min_date": None,
                        "max_date": None,
                        "date_range_days": None,
                    })
            else:
                row.update({
                    "min_date": None,
                    "max_date": None,
                    "date_range_days": None,
                })
            
            profile_rows.append(row)
        
        return pd.DataFrame(profile_rows)

    def _generate_detailed_profile(self) -> dict:
        """Generate a detailed profile with additional information."""
        detailed = {
            "dataframe_info": {
                "shape": list(self.df_.shape),
                "total_rows": len(self.df_),
                "total_columns": len(self.df_.columns),
                "total_cells": self.df_.size,
                "total_memory_usage_mb": round(self.df_.memory_usage(deep=True).sum() / 1024**2, 2),
            },
            "columns": {}
        }
        
        for col in self.df_.columns:
            col_data = self.df_[col]
            col_info = {
                "dtype": str(col_data.dtype),
                "null_count": int(col_data.isnull().sum()),
                "null_percentage": round((col_data.isnull().sum() / len(col_data)) * 100, 2),
                "unique_count": int(col_data.nunique()),
                "non_null_count": int(col_data.notna().sum()),
            }
            
            # Numeric details
            if pd.api.types.is_numeric_dtype(col_data):
                numeric_data = col_data.dropna()
                if len(numeric_data) > 0:
                    col_info["numeric_stats"] = {
                        "mean": float(numeric_data.mean()),
                        "median": float(numeric_data.median()),
                        "std": float(numeric_data.std()) if len(numeric_data) > 1 else 0.0,
                        "variance": float(numeric_data.var()) if len(numeric_data) > 1 else 0.0,
                        "min": float(numeric_data.min()),
                        "max": float(numeric_data.max()),
                        "range": float(numeric_data.max() - numeric_data.min()),
                        "q25": float(numeric_data.quantile(0.25)),
                        "q50": float(numeric_data.quantile(0.50)),
                        "q75": float(numeric_data.quantile(0.75)),
                        "iqr": float(numeric_data.quantile(0.75) - numeric_data.quantile(0.25)),
                        "skewness": float(numeric_data.skew()) if len(numeric_data) > 2 else None,
                        "kurtosis": float(numeric_data.kurtosis()) if len(numeric_data) > 2 else None,
                        "zero_count": int((numeric_data == 0).sum()),
                        "negative_count": int((numeric_data < 0).sum()),
                        "positive_count": int((numeric_data > 0).sum()),
                    }
            
            # Categorical details
            if pd.api.types.is_object_dtype(col_data) or pd.api.types.is_string_dtype(col_data):
                categorical_data = col_data.dropna()
                if len(categorical_data) > 0:
                    value_counts = categorical_data.value_counts()
                    top_values = value_counts.head(10).to_dict()
                    mode_values = categorical_data.mode()
                    
                    col_info["categorical_stats"] = {
                        "mode": str(mode_values.iloc[0]) if len(mode_values) > 0 else None,
                        "mode_count": int((categorical_data == mode_values.iloc[0]).sum()) if len(mode_values) > 0 else 0,
                        "top_10_values": {str(k): int(v) for k, v in top_values.items()},
                        "avg_string_length": float(categorical_data.astype(str).str.len().mean()),
                        "min_string_length": int(categorical_data.astype(str).str.len().min()),
                        "max_string_length": int(categorical_data.astype(str).str.len().max()),
                    }
            
            # Datetime details
            if pd.api.types.is_datetime64_any_dtype(col_data):
                datetime_data = col_data.dropna()
                if len(datetime_data) > 0:
                    col_info["datetime_stats"] = {
                        "min_date": str(datetime_data.min()),
                        "max_date": str(datetime_data.max()),
                        "date_range_days": int((datetime_data.max() - datetime_data.min()).days),
                        "date_range_hours": int((datetime_data.max() - datetime_data.min()).total_seconds() / 3600),
                    }
            
            detailed["columns"][col] = col_info
        
        return detailed

    def get_profile_dataframe(self) -> DataFrame:
        """Return a DataFrame with the profile summary."""
        return DataFrame(self.profile_data)

    def get_detailed_profile(self) -> Data:
        """Return detailed profile as a Data object."""
        return Data(data=self.detailed_profile_data)


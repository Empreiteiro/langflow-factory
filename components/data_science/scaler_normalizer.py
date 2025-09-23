from lfx.custom import Component
from lfx.io import DataFrameInput, DropdownInput, Output
from lfx.schema import DataFrame
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, Normalizer


class ScalerNormalizerComponent(Component):
    display_name = "Scaler/Normalizer"
    description = "Applies StandardScaler, MinMaxScaler, RobustScaler, or Normalizer to a DataFrame."
    icon = "flask-conical"
    name = "ScalerNormalizerComponent"
    beta = True

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            info="DataFrame to be scaled or normalized."
        ),
        DropdownInput(
            name="method",
            display_name="Scaling Method",
            options=["StandardScaler", "MinMaxScaler", "RobustScaler", "Normalizer"],
            value="StandardScaler",
            info="Choose the scaling or normalization method.",
            required=True
        )
    ]

    outputs = [
        Output(name="scaled_df", display_name="DataFrame", method="scale_dataframe")
    ]

    def scale_dataframe(self) -> DataFrame:
        if self.df is None:
            self.status = "No input DataFrame provided."
            return DataFrame(pd.DataFrame({"error": [self.status]}))

        try:
            df = self.df.copy()
            scaler = self.get_scaler(self.method)
            scaled_data = scaler.fit_transform(df)
            scaled_df = pd.DataFrame(scaled_data, columns=df.columns)
            return DataFrame(scaled_df)
        except Exception as e:
            self.status = f"Error during scaling: {str(e)}"
            return DataFrame(pd.DataFrame({"error": [str(e)]}))

    def get_scaler(self, method: str):
        if method == "StandardScaler":
            return StandardScaler()
        elif method == "MinMaxScaler":
            return MinMaxScaler()
        elif method == "RobustScaler":
            return RobustScaler()
        elif method == "Normalizer":
            return Normalizer()
        else:
            raise ValueError(f"Unsupported scaling method: {method}")

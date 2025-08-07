from langflow.custom import Component
from langflow.io import DataFrameInput, StrInput, DropdownInput, BoolInput, DataInput, Output
from langflow.schema import Data, DataFrame
import pandas as pd
import base64
import pickle
from sklearn.preprocessing import OneHotEncoder, LabelEncoder, OrdinalEncoder


class FeatureEncoderComponent(Component):
    display_name = "Feature Encoder"
    description = "Transform categorical variables using OneHot, LabelEncoder, or OrdinalEncoder"
    icon = "flask-conical"
    name = "FeatureEncoder"
    beta = True
    
    inputs = [
        DataFrameInput(
            name="dataframe",
            display_name="DataFrame",
            info="DataFrame containing the data to encode",
            required=True
        ),
        StrInput(
            name="categorical_columns",
            display_name="Categorical Columns",
            info="List of column names to encode",
            is_list=True,
            required=True
        ),
        DropdownInput(
            name="encoding_method",
            display_name="Encoding Method",
            info="Method to encode categorical variables",
            options=["onehot", "label", "ordinal"],
            value="onehot"
        ),
        BoolInput(
            name="drop_first",
            display_name="Drop First Category",
            info="Whether to drop the first category (for OneHotEncoder)",
            value=False
        ),
        DropdownInput(
            name="handle_unknown",
            display_name="Handle Unknown",
            info="How to handle unknown categories",
            options=["error", "ignore", "use_encoded_value"],
            value="error"
        ),
        BoolInput(
            name="return_encoder",
            display_name="Return Encoder",
            info="Whether to return the fitted encoder",
            value=False
        )
    ]

    outputs = [
        Output(name="encoded_data", display_name="DataFrame", method="get_encoded_data"),
        Output(name="encoder_info", display_name="Encoder Summary", method="get_encoder_info")
    ]

    def build(self):
        try:
            df = self.dataframe.copy()
            columns = self.categorical_columns
            method = self.encoding_method.lower()
            drop_first = self.drop_first
            handle_unknown = self.handle_unknown
            return_encoder = self.return_encoder

            available_columns = df.columns.tolist()
            valid_columns = [col for col in columns if col in available_columns]

            if not valid_columns:
                raise ValueError(f"No valid categorical columns found. Available: {available_columns}")

            if method == "onehot":
                encoder = OneHotEncoder(
                    drop='first' if drop_first else None,
                    sparse_output=False,
                    handle_unknown=handle_unknown
                )
            elif method == "label":
                encoder = LabelEncoder()
            elif method == "ordinal":
                encoder = OrdinalEncoder(handle_unknown=handle_unknown)
            else:
                raise ValueError(f"Unsupported encoding method: {method}")

            if method == "label":
                encoded_df = df.copy()
                encoders = {}
                for col in valid_columns:
                    le = LabelEncoder()
                    encoded_df[col] = le.fit_transform(df[col].astype(str))
                    encoders[col] = le
                encoded_columns = valid_columns.copy()
            else:
                encoder.fit(df[valid_columns])
                encoded_array = encoder.transform(df[valid_columns])
                if method == "onehot":
                    feature_names = encoder.get_feature_names_out(valid_columns)
                    encoded_df = df.drop(columns=valid_columns)
                    encoded_df = pd.concat([
                        encoded_df,
                        pd.DataFrame(encoded_array, columns=feature_names, index=df.index)
                    ], axis=1)
                    encoded_columns = feature_names.tolist()
                else:
                    encoded_df = df.copy()
                    encoded_df[valid_columns] = encoded_array
                    encoded_columns = valid_columns.copy()
                encoders = {col: encoder for col in valid_columns}

            self._encoded_df = encoded_df
            self._encoder_info = {
                "encoder_type": method,
                "columns_scaled": valid_columns,
                "encoded_columns": encoded_columns,
            }

            if return_encoder:
                encoder_bytes = pickle.dumps(encoders)
                encoder_b64 = base64.b64encode(encoder_bytes).decode("utf-8")
                self._encoder_info["encoder_base64"] = encoder_b64

            self.status = f"Successfully encoded with {method} encoder."

        except Exception as e:
            error = f"Encoding error: {e}"
            self.log(error)
            self._encoded_df = pd.DataFrame({"error": [error]})
            self._encoder_info = {"error": error}

    def get_encoded_data(self) -> DataFrame:
        return DataFrame(self._encoded_df)

    def get_encoder_info(self) -> Data:
        return Data(data=self._encoder_info)

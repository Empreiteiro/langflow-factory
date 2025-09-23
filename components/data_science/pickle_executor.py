import pickle
import pandas as pd
import json
from lfx.custom import Component
from lfx.io import DataInput, Output
from lfx.inputs import FileInput
from lfx.schema import Data

class PickleExecutorComponent(Component):
    display_name = "Pickle Executor"
    description = "Executes a Pickle file with a dynamically generated DataFrame from another component in the flow."
    icon = "brain"

    inputs = [
        FileInput(
            name="pickle_file",
            display_name="Pickle File",
            info="Pickle file containing a trained model or function to be executed.",
            required=True
        ),
        DataInput(
            name="data_file",
            display_name="JSON Data",
            info="Receives structured JSON data from another component in the flow.",
            required=True
        ),
    ]

    outputs = [
        Output(display_name="Output Data", name="output_data", method="execute_pickle"),
    ]

    def execute_pickle(self) -> Data:
        # Ensure a Pickle file is provided
        if not self.pickle_file:
            raise ValueError("You must provide a Pickle file.")

        # Load the Pickle file
        with open(self.pickle_file.path, "rb") as file:
            model = pickle.load(file)

        # Ensure data_file contains JSON data in Data format
        if not isinstance(self.data_file, Data):
            raise ValueError("The data_file input must be in Data format.")

        try:
            # Extrai o conteúdo do Data e transforma em DataFrame
            data_dict = self.data_file.data
            data = pd.DataFrame(data_dict)
        except Exception as e:
            raise ValueError(f"Error processing JSON data: {str(e)}")

        # Execute the Pickle model or function
        if hasattr(model, "predict"):
            result = model.predict(data)
        else:
            result = model(data)  # Assumes it's a function

        return Data(data={"result": result.tolist() if hasattr(result, "tolist") else result})

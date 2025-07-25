from langflow.custom import Component
from langflow.io import BoolInput, DataFrameInput, DropdownInput, IntInput, MessageTextInput, Output, StrInput
from langflow.schema import DataFrame
import matplotlib.pyplot as plt


class DataFrameOperationsComponent(Component):
    display_name = "DataFrame Operations"
    description = "Perform various operations on a DataFrame."
    icon = "table"

    # Available operations
    OPERATION_CHOICES = [
        "Add Column",
        "Drop Column",
        "Filter",
        "Head",
        "Rename Column",
        "Replace Value",
        "Select Columns",
        "Sort",
        "Tail",
        "Convert to Data List",
        "Convert to Base64"
    ]

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            info="The input DataFrame to operate on.",
        ),
        DropdownInput(
            name="operation",
            display_name="Operation",
            options=OPERATION_CHOICES,
            info="Select the DataFrame operation to perform.",
            real_time_refresh=True,
        ),
        StrInput(
            name="column_name",
            display_name="Column Name",
            info="The column name to use for the operation.",
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="filter_value",
            display_name="Filter Value",
            info="The value to filter rows by.",
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="ascending",
            display_name="Sort Ascending",
            info="Whether to sort in ascending order.",
            dynamic=True,
            show=False,
            value=True,
        ),
        StrInput(
            name="new_column_name",
            display_name="New Column Name",
            info="The new column name when renaming or adding a column.",
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="new_column_value",
            display_name="New Column Value",
            info="The value to populate the new column with.",
            dynamic=True,
            show=False,
        ),
        StrInput(
            name="columns_to_select",
            display_name="Columns to Select",
            dynamic=True,
            is_list=True,
            show=False,
        ),
        IntInput(
            name="num_rows",
            display_name="Number of Rows",
            info="Number of rows to return (for head/tail).",
            dynamic=True,
            show=False,
            value=5,
        ),
        MessageTextInput(
            name="replace_value",
            display_name="Value to Replace",
            info="The value to replace in the column.",
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="replacement_value",
            display_name="Replacement Value",
            info="The value to replace with.",
            dynamic=True,
            show=False,
        ),
    ]

    outputs = [
        Output(
            display_name="DataFrame",
            name="output",
            method="perform_operation",
            info="The resulting DataFrame after the operation.",
        ),
        Output(
            display_name="Data",
            name="data",
            method="to_data",
            info="Converted DataFrame to list of data objects.",
        )      
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        # Hide all dynamic fields by default
        dynamic_fields = [
            "column_name",
            "filter_value",
            "ascending",
            "new_column_name",
            "new_column_value",
            "columns_to_select",
            "num_rows",
            "replace_value",
            "replacement_value",
        ]
        for field in dynamic_fields:
            build_config[field]["show"] = False

        # Show relevant fields based on the selected operation
        if field_name == "operation":
            if field_value == "Filter":
                build_config["column_name"]["show"] = True
                build_config["filter_value"]["show"] = True
            elif field_value == "Sort":
                build_config["column_name"]["show"] = True
                build_config["ascending"]["show"] = True
            elif field_value == "Drop Column":
                build_config["column_name"]["show"] = True
            elif field_value == "Rename Column":
                build_config["column_name"]["show"] = True
                build_config["new_column_name"]["show"] = True
            elif field_value == "Add Column":
                build_config["new_column_name"]["show"] = True
                build_config["new_column_value"]["show"] = True
            elif field_value == "Select Columns":
                build_config["columns_to_select"]["show"] = True
            elif field_value in {"Head", "Tail"}:
                build_config["num_rows"]["show"] = True
            elif field_value == "Replace Value":
                build_config["column_name"]["show"] = True
                build_config["replace_value"]["show"] = True
                build_config["replacement_value"]["show"] = True

        return build_config

    def perform_operation(self) -> DataFrame:
        dataframe_copy = self.df.copy()
        operation = self.operation

        if operation == "Filter":
            return self.filter_rows_by_value(dataframe_copy)
        if operation == "Sort":
            return self.sort_by_column(dataframe_copy)
        if operation == "Drop Column":
            return self.drop_column(dataframe_copy)
        if operation == "Rename Column":
            return self.rename_column(dataframe_copy)
        if operation == "Add Column":
            return self.add_column(dataframe_copy)
        if operation == "Select Columns":
            return self.select_columns(dataframe_copy)
        if operation == "Head":
            return self.head(dataframe_copy)
        if operation == "Tail":
            return self.tail(dataframe_copy)
        if operation == "Replace Value":
            return self.replace_values(dataframe_copy)
        if operation == "Convert to Data List":
            return DataFrame(dataframe_copy)
        if operation == "Convert to Base64":
            return self.convert_dataframe_to_base64(dataframe_copy)
            
        raise ValueError(f"Unsupported operation: {operation}")

    # Existing methods
    def filter_rows_by_value(self, df: DataFrame) -> DataFrame:
        return DataFrame(df[df[self.column_name] == self.filter_value])

    def sort_by_column(self, df: DataFrame) -> DataFrame:
        return DataFrame(df.sort_values(by=self.column_name, ascending=self.ascending))

    def drop_column(self, df: DataFrame) -> DataFrame:
        return DataFrame(df.drop(columns=[self.column_name]))

    def rename_column(self, df: DataFrame) -> DataFrame:
        return DataFrame(df.rename(columns={self.column_name: self.new_column_name}))

    def add_column(self, df: DataFrame) -> DataFrame:
        df[self.new_column_name] = [self.new_column_value] * len(df)
        return DataFrame(df)

    def select_columns(self, df: DataFrame) -> DataFrame:
        columns = [col.strip() for col in self.columns_to_select]
        return DataFrame(df[columns])

    # New methods
    def head(self, df: DataFrame) -> DataFrame:
        return DataFrame(df.head(self.num_rows))

    def tail(self, df: DataFrame) -> DataFrame:
        return DataFrame(df.tail(self.num_rows))

    def replace_values(self, df: DataFrame) -> DataFrame:
        df[self.column_name] = df[self.column_name].replace(self.replace_value, self.replacement_value)
        return DataFrame(df)

    def to_data(self) -> list[Data]:
        if self.operation != "Convert to Data List":
            return []
        try:
            df = self.df.copy()
            records = df.to_dict(orient="records")
            return [Data(data=row) for row in records]
        except Exception as e:
            self.status = f"Error converting to Data: {str(e)}"
            self.log(self.status)
            return [Data(data={"error": str(e)})]
            
            
    def convert_dataframe_to_base64(self, df: DataFrame) -> DataFrame:
        try:
            df = pd.DataFrame(df).copy()
            fig, ax = plt.subplots(figsize=(len(df.columns) * 1.2, len(df) * 0.5))
            ax.axis("tight")
            ax.axis("off")
            ax.table(cellText=df.values, colLabels=df.columns, loc='center')

            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            plt.close(fig)
            buf.seek(0)
            
            base64_image = base64.b64encode(buf.read()).decode('utf-8')
            return DataFrame(pd.DataFrame({"base64_image": [base64_image]}))
        except Exception as e:
            self.status = f"Error: {str(e)}"
            return DataFrame(pd.DataFrame({"error": [str(e)]}))
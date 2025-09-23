import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.inputs import SortableListInput
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    Output,
    StrInput,
)
from lfx.logging import logger
from lfx.schema.dataframe import DataFrame

class EnhancedDataFrameOperationsComponent(Component):
    display_name = "Enhanced DataFrame Operations"
    description = "Perform various operations on DataFrames including joining two DataFrames."
    documentation: str = "https://docs.langflow.org/components-processing#enhanced-dataframe-operations"
    icon = "table"
    name = "EnhancedDataFrameOperations"

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
        "Drop Duplicates",
        "Join DataFrames",
        "Concatenating DataFrames",
    ]

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            info="The input DataFrame to operate on.",
            required=True,
        ),
        DataFrameInput(
            name="df2",
            display_name="Second DataFrame",
            info="The second DataFrame for join operations.",
            required=False,
            dynamic=True,
            show=False,
        ),
        SortableListInput(
            name="operation",
            display_name="Operation",
            placeholder="Select Operation",
            info="Select the DataFrame operation to perform.",
            options=[
                {"name": "Add Column", "icon": "plus"},
                {"name": "Drop Column", "icon": "minus"},
                {"name": "Filter", "icon": "filter"},
                {"name": "Head", "icon": "arrow-up"},
                {"name": "Rename Column", "icon": "pencil"},
                {"name": "Replace Value", "icon": "replace"},
                {"name": "Select Columns", "icon": "columns"},
                {"name": "Sort", "icon": "arrow-up-down"},
                {"name": "Tail", "icon": "arrow-down"},
                {"name": "Drop Duplicates", "icon": "copy-x"},
                {"name": "Join DataFrames", "icon": "merge"},
                {"name": "Concatenating DataFrames", "icon": "link"},
            ],
            real_time_refresh=True,
            limit=1,
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
        DropdownInput(
            name="filter_operator",
            display_name="Filter Operator",
            options=["equals", "not equals", "contains", "starts with", "ends with", "greater than", "less than"],
            value="equals",
            info="The operator to apply for filtering rows.",
            advanced=False,
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
        # Join specific inputs
        StrInput(
            name="join_column_left",
            display_name="Join Column (Left)",
            info="Column name from the first DataFrame to use for joining.",
            dynamic=True,
            show=False,
        ),
        StrInput(
            name="join_column_right",
            display_name="Join Column (Right)",
            info="Column name from the second DataFrame to use for joining.",
            dynamic=True,
            show=False,
        ),
        DropdownInput(
            name="join_type",
            display_name="Join Type",
            options=["inner", "left", "right", "outer", "cross"],
            value="inner",
            info="Type of join to perform.",
            dynamic=True,
            show=False,
        ),
        # Concatenating specific inputs
        DropdownInput(
            name="concatenate_type",
            display_name="Concatenate Type",
            options=["vertically", "horizontally"],
            value="vertically",
            info="Type of concatenation: vertically (stacking rows) or horizontally (adding columns).",
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
        )
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        dynamic_fields = [
            "df2",
            "column_name",
            "filter_value",
            "filter_operator",
            "ascending",
            "new_column_name",
            "new_column_value",
            "columns_to_select",
            "num_rows",
            "replace_value",
            "replacement_value",
            "join_column_left",
            "join_column_right",
            "join_type",
            "concatenate_type",
        ]
        for field in dynamic_fields:
            build_config[field]["show"] = False

        if field_name == "operation":
            # Handle SortableListInput format
            if isinstance(field_value, list):
                operation_name = field_value[0].get("name", "") if field_value else ""
            else:
                operation_name = field_value or ""

            # If no operation selected, all dynamic fields stay hidden (already set to False above)
            if not operation_name:
                return build_config

            if operation_name == "Filter":
                build_config["column_name"]["show"] = True
                build_config["filter_value"]["show"] = True
                build_config["filter_operator"]["show"] = True
            elif operation_name == "Sort":
                build_config["column_name"]["show"] = True
                build_config["ascending"]["show"] = True
            elif operation_name == "Drop Column":
                build_config["column_name"]["show"] = True
            elif operation_name == "Rename Column":
                build_config["column_name"]["show"] = True
                build_config["new_column_name"]["show"] = True
            elif operation_name == "Add Column":
                build_config["new_column_name"]["show"] = True
                build_config["new_column_value"]["show"] = True
            elif operation_name == "Select Columns":
                build_config["columns_to_select"]["show"] = True
            elif operation_name in {"Head", "Tail"}:
                build_config["num_rows"]["show"] = True
            elif operation_name == "Replace Value":
                build_config["column_name"]["show"] = True
                build_config["replace_value"]["show"] = True
                build_config["replacement_value"]["show"] = True
            elif operation_name == "Drop Duplicates":
                build_config["column_name"]["show"] = True
            elif operation_name == "Join DataFrames":
                build_config["df2"]["show"] = True
                build_config["join_type"]["show"] = True
                # Show join columns by default, but they can be hidden based on join type
                build_config["join_column_left"]["show"] = True
                build_config["join_column_right"]["show"] = True
            elif operation_name == "Concatenating DataFrames":
                build_config["df2"]["show"] = True
                build_config["concatenate_type"]["show"] = True

        return build_config

    def update_build_config_for_join_type(self, build_config, join_type):
        """
        Update build config based on join type to show/hide join columns.
        """
        if join_type == "cross":
            build_config["join_column_left"]["show"] = False
            build_config["join_column_right"]["show"] = False
        else:
            build_config["join_column_left"]["show"] = True
            build_config["join_column_right"]["show"] = True
        return build_config

    def perform_operation(self) -> DataFrame:
        df_copy = self.df.copy()

        # Handle SortableListInput format for operation
        operation_input = getattr(self, "operation", [])
        if isinstance(operation_input, list) and len(operation_input) > 0:
            op = operation_input[0].get("name", "")
        else:
            op = ""

        # If no operation selected, return original DataFrame
        if not op:
            return df_copy

        if op == "Filter":
            return self.filter_rows_by_value(df_copy)
        if op == "Sort":
            return self.sort_by_column(df_copy)
        if op == "Drop Column":
            return self.drop_column(df_copy)
        if op == "Rename Column":
            return self.rename_column(df_copy)
        if op == "Add Column":
            return self.add_column(df_copy)
        if op == "Select Columns":
            return self.select_columns(df_copy)
        if op == "Head":
            return self.head(df_copy)
        if op == "Tail":
            return self.tail(df_copy)
        if op == "Replace Value":
            return self.replace_values(df_copy)
        if op == "Drop Duplicates":
            return self.drop_duplicates(df_copy)
        if op == "Join DataFrames":
            return self.join_dataframes(df_copy)
        if op == "Concatenating DataFrames":
            return self.concatenate_dataframes(df_copy)
        
        msg = f"Unsupported operation: {op}"
        logger.error(msg)
        raise ValueError(msg)

    def filter_rows_by_value(self, df: DataFrame) -> DataFrame:
        column = df[self.column_name]
        filter_value = self.filter_value

        # Handle regular DropdownInput format (just a string value)
        operator = getattr(self, "filter_operator", "equals")  # Default to equals for backward compatibility

        if operator == "equals":
            mask = column == filter_value
        elif operator == "not equals":
            mask = column != filter_value
        elif operator == "contains":
            mask = column.astype(str).str.contains(str(filter_value), na=False)
        elif operator == "starts with":
            mask = column.astype(str).str.startswith(str(filter_value), na=False)
        elif operator == "ends with":
            mask = column.astype(str).str.endswith(str(filter_value), na=False)
        elif operator == "greater than":
            try:
                # Try to convert filter_value to numeric for comparison
                numeric_value = pd.to_numeric(filter_value)
                mask = column > numeric_value
            except (ValueError, TypeError):
                # If conversion fails, compare as strings
                mask = column.astype(str) > str(filter_value)
        elif operator == "less than":
            try:
                # Try to convert filter_value to numeric for comparison
                numeric_value = pd.to_numeric(filter_value)
                mask = column < numeric_value
            except (ValueError, TypeError):
                # If conversion fails, compare as strings
                mask = column.astype(str) < str(filter_value)
        else:
            mask = column == filter_value  # Fallback to equals

        return DataFrame(df[mask])

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

    def head(self, df: DataFrame) -> DataFrame:
        return DataFrame(df.head(self.num_rows))

    def tail(self, df: DataFrame) -> DataFrame:
        return DataFrame(df.tail(self.num_rows))

    def replace_values(self, df: DataFrame) -> DataFrame:
        df[self.column_name] = df[self.column_name].replace(self.replace_value, self.replacement_value)
        return DataFrame(df)

    def drop_duplicates(self, df: DataFrame) -> DataFrame:
        return DataFrame(df.drop_duplicates(subset=self.column_name))

    def join_dataframes(self, df: DataFrame) -> DataFrame:
        """
        Join two DataFrames based on specified columns and join type.
        """
        if not hasattr(self, 'df2') or self.df2 is None:
            raise ValueError("Second DataFrame is required for join operation")
        
        df2 = self.df2.copy()
        
        # Get join parameters
        left_col = getattr(self, 'join_column_left', None)
        right_col = getattr(self, 'join_column_right', None)
        join_type = getattr(self, 'join_type', 'inner')
        
        # For cross join, columns are not required
        if join_type == "cross":
            try:
                # Cross join creates cartesian product of all rows
                result = df.merge(df2, how='cross')
                return DataFrame(result)
            except Exception as e:
                error_msg = f"Error performing cross join: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        # For other join types, columns are required
        if not left_col or not right_col:
            raise ValueError("Both join columns must be specified for non-cross joins")
        
        # Validate columns exist in both DataFrames
        if left_col not in df.columns:
            raise ValueError(f"Column '{left_col}' not found in first DataFrame")
        if right_col not in df2.columns:
            raise ValueError(f"Column '{right_col}' not found in second DataFrame")
        
        # Perform the join
        try:
            if join_type == "inner":
                result = df.merge(df2, left_on=left_col, right_on=right_col, how='inner')
            elif join_type == "left":
                result = df.merge(df2, left_on=left_col, right_on=right_col, how='left')
            elif join_type == "right":
                result = df.merge(df2, left_on=left_col, right_on=right_col, how='right')
            elif join_type == "outer":
                result = df.merge(df2, left_on=left_col, right_on=right_col, how='outer')
            else:
                raise ValueError(f"Unsupported join type: {join_type}")
            
            return DataFrame(result)
            
        except Exception as e:
            error_msg = f"Error joining DataFrames: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def concatenate_dataframes(self, df: DataFrame) -> DataFrame:
        """
        Concatenate two DataFrames either vertically (stacking rows) or horizontally (adding columns).
        """
        if not hasattr(self, 'df2') or self.df2 is None:
            raise ValueError("Second DataFrame is required for concatenation operation")
        
        df2 = self.df2.copy()
        
        # Get concatenation parameters
        concatenate_type = getattr(self, 'concatenate_type', 'vertically')
        
        # Perform the concatenation
        try:
            if concatenate_type == "vertically":
                # Stack rows (axis=0)
                result = pd.concat([df, df2], axis=0, ignore_index=True)
            elif concatenate_type == "horizontally":
                # Add columns (axis=1)
                result = pd.concat([df, df2], axis=1, ignore_index=False)
            else:
                raise ValueError(f"Unsupported concatenation type: {concatenate_type}")
            
            return DataFrame(result)
            
        except Exception as e:
            error_msg = f"Error concatenating DataFrames: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

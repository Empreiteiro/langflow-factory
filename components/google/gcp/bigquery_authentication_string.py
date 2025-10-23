import json
import re

from google.auth.exceptions import RefreshError
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

from lfx.custom import Component
from lfx.io import BoolInput, FileInput, MessageTextInput, Output
from lfx.schema.dataframe import DataFrame


class BigQueryExecutorComponent(Component):
    display_name = "BigQuery"
    description = "Execute SQL queries on Google BigQuery."
    name = "BigQueryExecutor"
    icon = "Google"
    beta: bool = True

    inputs = [
        MessageTextInput(
            name="service_account_json",
            display_name="Service Account JSON",
            info="Paste the JSON string containing Google Cloud service account credentials.",
            required=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="query",
            display_name="SQL Query",
            info="The SQL query to execute on BigQuery.",
            required=True,
            tool_mode=True,
        ),
        BoolInput(
            name="clean_query",
            display_name="Clean Query",
            info="When enabled, this will automatically clean up your SQL query.",
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Query Results", name="query_results", method="execute_sql"),
    ]

    def _clean_sql_query(self, query: str) -> str:
        """Clean SQL query by removing surrounding quotes and whitespace.

        Also extracts SQL statements from text that might contain other content.

        Args:
            query: The SQL query to clean

        Returns:
            The cleaned SQL query
        """
        # First, try to extract SQL from code blocks
        sql_pattern = r"```(?:sql)?\s*([\s\S]*?)\s*```"
        sql_matches = re.findall(sql_pattern, query, re.IGNORECASE)

        if sql_matches:
            # If we found SQL in code blocks, use the first match
            query = sql_matches[0]
        else:
            # If no code block, try to find SQL statements
            # Look for common SQL keywords at the start of lines
            sql_keywords = r"(?i)(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|MERGE)"
            lines = query.split("\n")
            sql_lines = []
            in_sql = False

            for _line in lines:
                line = _line.strip()
                if re.match(sql_keywords, line):
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                if line.endswith(";"):
                    in_sql = False

            if sql_lines:
                query = "\n".join(sql_lines)

        # Remove any backticks that might be at the start or end
        query = query.strip("`")

        # Then remove surrounding quotes (single or double) if they exist
        query = query.strip()
        if (query.startswith('"') and query.endswith('"')) or (query.startswith("'") and query.endswith("'")):
            query = query[1:-1]

        # Finally, clean up any remaining whitespace and ensure no backticks remain
        query = query.strip()
        # Remove any remaining backticks, but preserve them if they're part of a table/column name
        # This regex will remove backticks that are not part of a valid identifier
        return re.sub(r"`(?![a-zA-Z0-9_])|(?<![a-zA-Z0-9_])`", "", query)

    def execute_sql(self) -> DataFrame:
        try:
            # Parse the JSON string from the input
            try:
                credentials_json = json.loads(self.service_account_json)
                project_id = credentials_json.get("project_id")
                if not project_id:
                    msg = "No project_id found in service account credentials JSON."
                    raise ValueError(msg)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON string for service account credentials: {e}"
                raise ValueError(msg) from e

            # Then try to load credentials from the JSON string
            try:
                credentials = Credentials.from_service_account_info(credentials_json)
            except Exception as e:
                msg = f"Error loading service account credentials from JSON: {e}"
                raise ValueError(msg) from e

        except ValueError:
            raise
        except Exception as e:
            msg = f"Error executing BigQuery SQL query: {e}"
            raise ValueError(msg) from e

        try:
            client = bigquery.Client(credentials=credentials, project=project_id)

            # Check for empty or whitespace-only query before cleaning
            if not str(self.query).strip():
                msg = "No valid SQL query found in input text."
                raise ValueError(msg)

            # Always clean the query if it contains code block markers, quotes, or if clean_query is enabled
            if "```" in str(self.query) or '"' in str(self.query) or "'" in str(self.query) or self.clean_query:
                sql_query = self._clean_sql_query(str(self.query))
            else:
                sql_query = str(self.query).strip()  # At minimum, strip whitespace

            query_job = client.query(sql_query)
            results = query_job.result()
            output_dict = [dict(row) for row in results]

        except RefreshError as e:
            msg = "Authentication error: Unable to refresh authentication token. Please try to reauthenticate."
            raise ValueError(msg) from e
        except Exception as e:
            msg = f"Error executing BigQuery SQL query: {e}"
            raise ValueError(msg) from e

        return DataFrame(output_dict)

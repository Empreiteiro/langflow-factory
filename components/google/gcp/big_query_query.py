import json
import re
from typing import Any

from google.auth.exceptions import RefreshError
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

from langflow.custom import Component
from langflow.io import BoolInput, HandleInput, MultilineInput, Output, SecretStrInput
from langflow.schema.dataframe import DataFrame


class BigQueryQueryComponent(Component):
    display_name = "BigQuery Query"
    description = "Execute SQL queries on Google BigQuery."
    name = "BigQueryQuery"
    icon = "Google"
    beta: bool = True

    inputs = [
        HandleInput(
            name="trigger",
            display_name="Trigger",
            info="Input to trigger the BigQuery execution. Accepts text, data, or dataframe.",
            input_types=["Text", "Data", "DataFrame"],
            required=False,
            advanced=True,
        ),
        SecretStrInput(
            name="service_account_key",
            display_name="GCP Credentials Secret Key",
            info="Your Google Cloud Platform service account JSON key as a secret string (complete JSON content).",
            required=True,
            input_types=["Text", "Message"],
            advanced=True,
        ),
        MultilineInput(
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
        BoolInput(
            name="auto_escape_tables",
            display_name="Auto Escape Table Names",
            info="Automatically add backticks around table names containing hyphens or special characters.",
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="DataFrame", name="dataframe", method="execute_query"),
    ]

    def execute_query(self) -> DataFrame:
        """Execute SQL query and return DataFrame."""
        try:
            # Parse the JSON credentials from the secret key string
            try:
                credentials_json = json.loads(self.service_account_key)
                project_id = credentials_json.get("project_id")
                if not project_id:
                    msg = "No project_id found in service account credentials."
                    raise ValueError(msg)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON in service account key: {str(e)}"
                raise ValueError(msg) from e

            # Load credentials
            try:
                credentials = Credentials.from_service_account_info(credentials_json)
                client = bigquery.Client(credentials=credentials, project=project_id)
            except Exception as e:
                msg = f"Error loading service account credentials: {e}"
                raise ValueError(msg) from e

        except ValueError:
            raise
        except Exception as e:
            msg = f"Error setting up BigQuery client: {e}"
            raise ValueError(msg) from e

        # Check for empty or whitespace-only query before cleaning
        if not str(self.query).strip():
            msg = "No valid SQL query found in input text."
            raise ValueError(msg)

        original_query = str(self.query)
        
        # Clean the query more intelligently
        if "```" in original_query:
            # Only clean if there are code blocks
            sql_query = self._clean_sql_query(original_query)
            self.log(f"Query cleaned from {len(original_query)} to {len(sql_query)} characters")
        elif self.clean_query:
            # Clean if explicitly requested
            sql_query = self._clean_sql_query(original_query)
            self.log(f"Query cleaned from {len(original_query)} to {len(sql_query)} characters")
        else:
            # For most SQL queries, just strip whitespace - this preserves the original query
            sql_query = original_query.strip()
            self.log("Using query as-is (no cleaning applied)")

        # Auto-escape table names if requested
        if getattr(self, 'auto_escape_tables', True):
            sql_query = self._auto_escape_table_names(sql_query)
            self.log("Applied auto-escaping to table names")

        # Log the final query for debugging (truncated if too long)
        query_preview = sql_query[:200] + "..." if len(sql_query) > 200 else sql_query
        self.log(f"Executing query: {query_preview}")

        try:
            # Execute the query
            query_job = client.query(sql_query)
            
            # Wait for the job to complete and get results
            results = query_job.result()
            
            # Convert results to list of dictionaries
            output_dict = []
            for row in results:
                # Convert BigQuery Row to dict, handling different data types
                row_dict = {}
                for key, value in row.items():
                    # Handle BigQuery specific data types
                    if hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[key] = value.isoformat()
                    elif value is None:
                        row_dict[key] = None
                    else:
                        row_dict[key] = value
                output_dict.append(row_dict)
            
            self.log(f"Query executed successfully. Returned {len(output_dict)} rows.")
            
        except Exception as e:
            # Enhanced error reporting
            error_msg = str(e)
            
            # Check for common SQL errors and provide helpful hints
            if "Syntax error" in error_msg:
                if "Unclosed string literal" in error_msg:
                    hint = " (Hint: Check for unmatched quotes in your query)"
                elif "Unexpected keyword" in error_msg:
                    hint = " (Hint: Check SQL syntax and reserved keywords)"
                else:
                    hint = " (Hint: Review your SQL syntax)"
                error_msg += hint
            elif "Table" in error_msg and "not found" in error_msg:
                error_msg += " (Hint: Verify table name and project ID)"
            elif "Access Denied" in error_msg:
                error_msg += " (Hint: Check your service account permissions)"
            
            # Include the cleaned query in error for debugging
            if len(sql_query) <= 500:
                error_msg += f"\n\nQuery attempted:\n{sql_query}"
            else:
                error_msg += f"\n\nQuery attempted (first 500 chars):\n{sql_query[:500]}..."
            
            raise ValueError(f"Error executing BigQuery SQL query: {error_msg}") from e

        return DataFrame(output_dict)

    def _clean_sql_query(self, query: str) -> str:
        """Clean SQL query by removing surrounding quotes and whitespace.

        Also extracts SQL statements from text that might contain other content.

        Args:
            query: The SQL query to clean

        Returns:
            The cleaned SQL query
        """
        original_query = query
        
        # First, try to extract SQL from code blocks
        sql_pattern = r"```(?:sql)?\s*([\s\S]*?)\s*```"
        sql_matches = re.findall(sql_pattern, query, re.IGNORECASE | re.DOTALL)

        if sql_matches:
            # If we found SQL in code blocks, use the first match
            query = sql_matches[0]
        else:
            # If no code block, check if the query starts with common SQL keywords
            # If it does, it's probably already a clean query
            sql_keywords = r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|MERGE)"
            if re.match(sql_keywords, query.strip(), re.IGNORECASE):
                # Already looks like a clean SQL query, just strip whitespace
                return query.strip()
            
            # Try to find SQL statements by looking for lines that start with SQL keywords
            lines = query.split("\n")
            sql_lines = []
            in_sql = False

            for line in lines:
                stripped_line = line.strip()
                if re.match(sql_keywords, stripped_line, re.IGNORECASE):
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)  # Keep original formatting/indentation
                if stripped_line.endswith(";"):
                    in_sql = False

            if sql_lines:
                query = "\n".join(sql_lines)
            else:
                # If we can't find SQL patterns, return the original query stripped
                return original_query.strip()

        # Remove any backticks that might be at the very start or end (not part of table names)
        query = query.strip()
        if query.startswith("```") or query.endswith("```"):
            query = query.strip("`")

        # Only remove surrounding quotes if they wrap the ENTIRE query
        query = query.strip()
        if len(query) > 2:
            if (query.startswith('"') and query.endswith('"') and query.count('"') == 2) or \
               (query.startswith("'") and query.endswith("'") and query.count("'") == 2):
                query = query[1:-1]

        # Return the cleaned query, preserving internal formatting
        return query.strip()

    def _auto_escape_table_names(self, query: str) -> str:
        """Automatically add backticks around table names that need escaping."""
        import re
        
        def escape_table_reference(table_ref: str) -> str:
            """Escape individual table reference if it contains hyphens."""
            # Skip if already escaped
            if table_ref.startswith('`') and table_ref.endswith('`'):
                return table_ref
                
            parts = table_ref.split('.')
            escaped_parts = []
            
            for part in parts:
                # Escape if contains hyphens, starts with number, or is a reserved word
                if ('-' in part or 
                    (part and part[0].isdigit()) or 
                    part.upper() in ['ORDER', 'GROUP', 'SELECT', 'FROM', 'WHERE', 'JOIN']):
                    escaped_parts.append(f'`{part}`')
                else:
                    escaped_parts.append(part)
            
            return '.'.join(escaped_parts)
        
        # Pattern to find table references in FROM clauses
        # Matches: FROM table_name or FROM project.dataset.table
        from_pattern = r'FROM\s+([a-zA-Z0-9_][a-zA-Z0-9_.-]*)'
        
        def replace_from_table(match):
            table_ref = match.group(1)
            escaped = escape_table_reference(table_ref)
            return f"FROM {escaped}"
        
        query = re.sub(from_pattern, replace_from_table, query, flags=re.IGNORECASE)
        
        # Pattern to find table references in JOIN clauses
        join_pattern = r'JOIN\s+([a-zA-Z0-9_][a-zA-Z0-9_.-]*)'
        
        def replace_join_table(match):
            table_ref = match.group(1)
            escaped = escape_table_reference(table_ref)
            return f"JOIN {escaped}"
        
        query = re.sub(join_pattern, replace_join_table, query, flags=re.IGNORECASE)
        
        return query

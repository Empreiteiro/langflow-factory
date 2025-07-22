from langflow.custom import Component
from langflow.io import (
    FileInput,
    MessageTextInput,
    MultilineInput,
    StrInput,
    DropdownInput,
    Output,
)
from langflow.schema import Data
from langflow.schema.message import Message
import json
import re
from google.auth.exceptions import RefreshError
from google.cloud import bigquery
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import tempfile
import os
import requests


class BigQueryToPDFtoZap(Component):
    display_name = "BigQuery to PDF via Z-API"
    description = "Executes a BigQuery query, injects data into an HTML template, converts it to PDF via Google Docs, and sends it through Z-API."
    icon = "flow"
    name = "BigQueryToPDFtoZap"
    beta = True

    inputs = [
        FileInput(
            name="service_account_json_file",
            display_name="BigQuery Service Account JSON",
            file_types=["json"],
            required=True,
            info="Service account JSON file for BigQuery access",
            advanced=True
        ),
        FileInput(
            name="drive_service_account_json_file",
            display_name="Google Drive Service Account JSON",
            file_types=["json"],
            required=False,
            info="Service account JSON file for Google Drive access (optional - will use BigQuery key if not provided)",
            advanced=True
        ),
        MessageTextInput(name="project_id", display_name="GCP Project ID", required=True, advanced=True),
        MultilineInput(name="query", display_name="SQL Query", required=True, tool_mode=True),
        MultilineInput(name="templateHtml", display_name="HTML Template", required=True, advanced=True),
        MessageTextInput(name="name", display_name="Name", required=True, tool_mode=True),
        MessageTextInput(name="document", display_name="Document", required=True, tool_mode=True),
        MessageTextInput(name="issue_date", display_name="Issue Date", required=False, tool_mode=True),
        StrInput(name="file_name", display_name="PDF File Name", required=True, advanced=True),
        StrInput(name="folder_id", display_name="Google Drive Folder ID", required=True, advanced=True),
        MessageTextInput(name="instance", display_name="Z-API Instance", required=True, advanced=True),
        MessageTextInput(name="token", display_name="Z-API Token", required=True, advanced=True),
        MessageTextInput(name="client_token", display_name="Z-API Client Token", required=True, advanced=True),
        MessageTextInput(name="phone", display_name="Phone", required=True),
    ]

    outputs = [
        Output(name="result", display_name="Final Result", method="build"),
    ]

    def _suggest_query_fix(self, query: str, error_msg: str) -> str:
        """Suggest fixes for common BigQuery errors."""
        suggestions = []
        
        # PARSE_DATE issues
        if "PARSE_DATE" in error_msg and "DATE" in error_msg:
            # Common pattern: PARSE_DATE('%Y-%m-%d', date_column) where date_column is DATE
            import re
            parse_date_pattern = r'PARSE_DATE\([\'"][^"\']*[\'"][^)]*\)'
            matches = re.findall(parse_date_pattern, query, re.IGNORECASE)
            
            for match in matches:
                # Try to extract the column name
                column_match = re.search(r'PARSE_DATE\([^,]+,\s*([^)]+)\)', match, re.IGNORECASE)
                if column_match:
                    column_name = column_match.group(1).strip()
                    suggestions.append(f"Replace: {match}\nWith: FORMAT_DATE('%Y-%m-%d', {column_name})")
        
        # Add more suggestions for other common errors
        if "No matching signature" in error_msg:
            suggestions.append("Check the data types of your function arguments")
        
        if suggestions:
            return "\n\nSuggested fixes:\n" + "\n".join(suggestions)
        return ""

    def build(self) -> Data:
        try:
            # Step 1: Run BigQuery and get HTML table
            credentials = Credentials.from_service_account_file(self.service_account_json_file)
            client = bigquery.Client(credentials=credentials, project=self.project_id)
            
            # Validate and clean the query
            query = self.query.strip()
            if not query:
                return Data(data={"error": "SQL query cannot be empty"})
            
            # Log the query for debugging (remove sensitive data)
            self.log(f"Executing BigQuery query: {query[:100]}...")
            
            # Try to detect and suggest fixes for common PARSE_DATE issues
            if "PARSE_DATE" in query.upper():
                self.log("Detected PARSE_DATE in query - checking for potential issues...")
                # Common pattern: PARSE_DATE('%Y-%m-%d', date_column) where date_column is already DATE
                if "PARSE_DATE('%Y-%m-%d'" in query or "PARSE_DATE('%Y-%m-%d'" in query.upper():
                    self.log("Warning: PARSE_DATE with '%Y-%m-%d' format detected. If your column is already DATE type, consider using FORMAT_DATE instead.")
            
            try:
                query_job = client.query(query)
                results = query_job.result()
                rows = [dict(row) for row in results]
                self.log(f"Query executed successfully. Retrieved {len(rows)} rows.")
            except Exception as query_error:
                error_msg = str(query_error)
                self.log(f"BigQuery execution failed: {error_msg}")
                
                # Provide helpful error messages for common issues
                if "PARSE_DATE" in error_msg:
                    # Extract the problematic part of the query
                    problematic_part = ""
                    if "at [" in error_msg:
                        try:
                            # Try to extract the position from error message
                            position_match = re.search(r'at \[(\d+):(\d+)\]', error_msg)
                            if position_match:
                                start_pos = int(position_match.group(1))
                                end_pos = int(position_match.group(2))
                                if start_pos < len(query):
                                    problematic_part = query[start_pos:end_pos]
                        except:
                            pass
                    
                    # Get suggestions for fixing the query
                    suggestions = self._suggest_query_fix(query, error_msg)
                    
                    return Data(data={
                        "error": f"BigQuery PARSE_DATE error: {error_msg}\n\n"
                                f"Problem: You're trying to use PARSE_DATE on a column that's already a DATE type.\n\n"
                                f"Solutions:\n"
                                f"1. If you want to format a DATE column as string, use FORMAT_DATE:\n"
                                f"   FORMAT_DATE('%Y-%m-%d', your_date_column)\n\n"
                                f"2. If you want to parse a string column to DATE, use PARSE_DATE:\n"
                                f"   PARSE_DATE('%Y-%m-%d', your_string_column)\n\n"
                                f"3. If you want to convert between date formats, first use FORMAT_DATE then PARSE_DATE:\n"
                                f"   PARSE_DATE('%Y-%m-%d', FORMAT_DATE('%Y-%m-%d', your_date_column))\n\n"
                                f"Problematic query section: {problematic_part[:100] if problematic_part else 'Unknown'}"
                                f"{suggestions}"
                    })
                elif "No matching signature" in error_msg:
                    return Data(data={
                        "error": f"BigQuery function signature error: {error_msg}\n\n"
                                f"Check the data types of your function arguments."
                    })
                else:
                    return Data(data={"error": f"BigQuery execution failed: {error_msg}"})

            if not rows:
                table_html = "<p>No data returned from query.</p>"
                self.log("Query returned no rows")
            else:
                headers = list(rows[0].keys())
                self.log(f"Table headers: {headers}")
                
                table_html = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
                table_html += "<thead><tr style='background-color: #f2f2f2;'>"
                table_html += ''.join(f"<th style='padding: 8px; border: 1px solid #ddd;'>{h}</th>" for h in headers)
                table_html += "</tr></thead><tbody>"
                
                for i, row in enumerate(rows):
                    # Alternate row colors for better readability
                    bg_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
                    table_html += f"<tr style='background-color: {bg_color};'>"
                    for h in headers:
                        cell_value = row.get(h, '')
                        # Handle None values and convert to string
                        if cell_value is None:
                            cell_value = ''
                        else:
                            cell_value = str(cell_value)
                        table_html += f"<td style='padding: 8px; border: 1px solid #ddd;'>{cell_value}</td>"
                    table_html += "</tr>"
                table_html += "</tbody></table>"
                
                self.log(f"Generated HTML table with {len(rows)} rows and {len(headers)} columns")

            # Step 2: Generate HTML with table and metadata
            try:
                final_html = self.templateHtml.format(
                    nome=self.name,
                    documento=self.document,
                    data_emissao=self.issue_date or "",
                    tabela_titulos=table_html,
                )
                self.log("HTML template processed successfully")
            except KeyError as e:
                missing_key = str(e).strip("'")
                return Data(data={
                    "error": f"Template error: Missing placeholder '{missing_key}' in HTML template.\n\n"
                             f"Available placeholders: nome, documento, data_emissao, tabela_titulos\n"
                             f"Note: These are the template placeholders, not the input field names."
                })
            except Exception as template_error:
                return Data(data={
                    "error": f"Template processing error: {str(template_error)}\n\n"
                             f"Check your HTML template for syntax errors."
                })

            # Step 3: Upload HTML to Google Docs and get PDF link
            try:
                # Use separate Drive service account if provided, otherwise use BigQuery key
                drive_service_account_file = self.drive_service_account_json_file if self.drive_service_account_json_file else self.service_account_json_file
                
                with open(drive_service_account_file, "r", encoding="utf-8") as f:
                    creds_dict = json.load(f)
                creds = service_account.Credentials.from_service_account_info(
                    creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
                )
                drive = build("drive", "v3", credentials=creds)
                
                if self.drive_service_account_json_file:
                    self.log(f"Google Drive API initialized with separate service account: {self.drive_service_account_json_file}")
                else:
                    self.log(f"Google Drive API initialized using BigQuery service account: {self.service_account_json_file}")

                with tempfile.TemporaryDirectory() as tmpdir:
                    html_path = os.path.join(tmpdir, f"{self.file_name}.html")
                    with open(html_path, "w", encoding="utf-8") as html_file:
                        html_file.write(final_html)

                    media = MediaFileUpload(html_path, mimetype="text/html", resumable=True)
                    file_metadata = {
                        "name": self.file_name,
                        "mimeType": "application/vnd.google-apps.document",
                        "parents": [self.folder_id],
                    }

                    uploaded = drive.files().create(body=file_metadata, media_body=media, fields="id").execute()
                    file_id = uploaded.get("id")
                    pdf_link = f"https://docs.google.com/document/d/{file_id}/export?format=pdf"
                    self.log(f"File uploaded to Google Drive with ID: {file_id}")
                    
            except FileNotFoundError:
                if self.drive_service_account_json_file:
                    return Data(data={"error": f"Google Drive service account JSON file not found: {self.drive_service_account_json_file}"})
                else:
                    return Data(data={"error": f"Service account JSON file not found: {self.service_account_json_file}"})
            except json.JSONDecodeError:
                if self.drive_service_account_json_file:
                    return Data(data={"error": "Invalid JSON format in Google Drive service account file"})
                else:
                    return Data(data={"error": "Invalid JSON format in service account file"})
            except Exception as drive_error:
                error_msg = str(drive_error)
                if "403" in error_msg:
                    return Data(data={"error": "Access denied to Google Drive. Check service account permissions."})
                elif "404" in error_msg:
                    return Data(data={"error": f"Google Drive folder not found: {self.folder_id}"})
                else:
                    return Data(data={"error": f"Google Drive upload failed: {error_msg}"})

            # Step 4: Send PDF link via Z-API
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Client-Token": self.client_token,
                }
                url = f"https://api.z-api.io/instances/{self.instance}/token/{self.token}/send-document/pdf"
                payload = {
                    "phone": self.phone,
                    "document": pdf_link,
                    "fileName": self.file_name,
                }

                self.log(f"Sending document via Z-API to phone: {self.phone}")
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                zapi_response = response.json()
                self.log("Z-API request successful")

                return Data(
                    data={
                        "message": "Success",
                        "pdf_link": pdf_link,
                        "zapi_response": zapi_response,
                        "rows_processed": len(rows),
                        "file_id": file_id,
                    }
                )
                
            except requests.exceptions.RequestException as api_error:
                error_msg = str(api_error)
                if "401" in error_msg:
                    return Data(data={"error": "Z-API authentication failed. Check instance, token, and client_token."})
                elif "404" in error_msg:
                    return Data(data={"error": "Z-API endpoint not found. Check instance and token."})
                elif "400" in error_msg:
                    return Data(data={"error": "Z-API bad request. Check phone number format and payload."})
                else:
                    return Data(data={"error": f"Z-API request failed: {error_msg}"})

        except Exception as e:
            self.status = f"Execution failed: {str(e)}"
            self.log(self.status)
            return Data(data={"error": str(e)})

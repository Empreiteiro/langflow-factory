from lfx.custom import Component
from lfx.io import StrInput, FileInput, Output, DropdownInput, MultilineInput
from lfx.schema import Data
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import datetime
import json
import uuid
import base64

class CloudRunSchedulerComponent(Component):
    display_name = "Cloud Run Scheduler"
    description = "Creates schedules for Cloud Run services on Google Cloud Platform"
    icon = "clock"  # Using Lucide icon
    name = "CloudRunSchedulerComponent"
    version = "1.0.0"

    inputs = [
        StrInput(
            name="service_url",
            display_name="Cloud Run URL",
            info="URL of the Cloud Run service to be triggered",
            required=True
        ),
        StrInput(
            name="cron_schedule",
            display_name="Cron Schedule",
            info="Cron expression for the schedule (e.g., '0 9 * * 1' for every Monday at 9 AM)",
            required=True
        ),
        MultilineInput(
            name="request_body",
            display_name="Request Body",
            info="JSON body to send in the POST request (optional)",
            value='{"trigger":"start"}',
            required=False
        ),
        DropdownInput(
            name="auth_type",
            display_name="Authentication Type",
            info="Type of authentication to use for the request",
            options=["None", "OAuth Token", "OIDC Token"],
            value="OIDC Token",
            real_time_refresh=True
        ),
        StrInput(
            name="oauth_token",
            display_name="OAuth Token",
            info="OAuth token for Google APIs authentication",
            dynamic=True,
            show=False,
            required=False
        ),
        StrInput(
            name="project_id",
            display_name="GCP Project ID",
            info="ID of the project on Google Cloud Platform",
            required=True
        ),
        StrInput(
            name="location",
            display_name="Location",
            info="GCP region (e.g., us-central1, europe-west1)",
            value="us-central1",
            required=True
        ),
        FileInput(
            name="auth_file",
            display_name="Service Account JSON",
            info="Upload the GCP service account JSON file for authentication",
            file_types=["json"],
            required=True
        ),
        StrInput(
            name="job_name",
            display_name="Job Name",
            info="Name for the scheduled job (optional, will generate unique name if not provided)",
            required=False
        )
    ]

    outputs = [
        Output(display_name="Result", name="result", method="create_schedule")
    ]

    def update_build_config(self, build_config: dict, field_value: any, field_name: str) -> dict:
        """Update build config based on auth type selection"""
        if field_name == "auth_type":
            if field_value == "OAuth Token":
                build_config["oauth_token"]["show"] = True
                build_config["oauth_token"]["required"] = True
            else:
                build_config["oauth_token"]["show"] = False
                build_config["oauth_token"]["required"] = False
        return build_config

    def validate_inputs(self) -> None:
        """Validate all component inputs before processing"""
        if not self.service_url or not (self.service_url.startswith('https://') or self.service_url.startswith('http://')):
            raise ValueError("Service URL must be a valid HTTP or HTTPS URL")
        
        if not self.cron_schedule:
            raise ValueError("Cron schedule is required")
        
        if not self.project_id:
            raise ValueError("GCP Project ID is required")
        
        if not self.location:
            raise ValueError("Location is required")
        
        if not hasattr(self, 'auth_file') or not self.auth_file:
            raise ValueError("Service account JSON file is required")
        
        # Validate auth-specific requirements
        if self.auth_type == "OAuth Token" and (not hasattr(self, 'oauth_token') or not self.oauth_token):
            raise ValueError("OAuth token is required when using OAuth authentication")
        
        # Validate JSON body if provided
        if hasattr(self, 'request_body') and self.request_body:
            try:
                json.loads(self.request_body)
            except json.JSONDecodeError:
                raise ValueError("Request body must be valid JSON")

    def create_schedule(self) -> Data:
        """Create a Cloud Scheduler job for the Cloud Run service"""
        try:
            # Validate inputs first
            self.validate_inputs()
            
            self.log("Starting Cloud Scheduler job creation...")
            
            # Load and validate credentials
            credentials = self._load_credentials()
            
            # Build the Cloud Scheduler service
            service = build('cloudscheduler', 'v1', credentials=credentials)
            
            # Generate job configuration
            job_config = self._build_job_config(credentials)
            
            # Create the job
            response = self._create_scheduler_job(service, job_config)
            
            self.log(f"Successfully created Cloud Scheduler job: {response.get('name', 'Unknown')}")
            
            return Data(data={
                "status": "success",
                "message": "Schedule created successfully",
                "job_name": response.get('name'),
                "schedule": self.cron_schedule,
                "target_url": self.service_url,
                "auth_type": self.auth_type,
                "response": response
            })
            
        except Exception as e:
            error_msg = f"Failed to create Cloud Scheduler job: {str(e)}"
            self.log(error_msg)
            return Data(data={
                "status": "error",
                "message": error_msg,
                "schedule": getattr(self, 'cron_schedule', ''),
                "target_url": getattr(self, 'service_url', ''),
                "auth_type": getattr(self, 'auth_type', '')
            })

    def _load_credentials(self) -> service_account.Credentials:
        """Load and validate service account credentials"""
        try:
            # Resolve the uploaded file path
            auth_file_path = self.auth_file
            if hasattr(self.auth_file, 'path'):
                auth_file_path = self.auth_file.path
            
            # Load credentials from the JSON file
            credentials = service_account.Credentials.from_service_account_file(
                auth_file_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            self.log("Successfully loaded service account credentials")
            return credentials
            
        except Exception as e:
            raise ValueError(f"Failed to load service account credentials: {str(e)}")

    def _build_job_config(self, credentials: service_account.Credentials) -> dict:
        """Build the job configuration for Cloud Scheduler"""
        # Generate unique job name if not provided
        job_name = self.job_name if hasattr(self, 'job_name') and self.job_name else f"langflow-job-{uuid.uuid4().hex[:8]}"
        
        parent = f"projects/{self.project_id}/locations/{self.location}"
        full_job_name = f"{parent}/jobs/{job_name}"
        
        # Build HTTP target based on configuration
        http_target = self._build_http_target(credentials)
        
        job_config = {
            "name": full_job_name,
            "description": f"Cloud Run scheduled trigger created via Langflow - {datetime.datetime.now().isoformat()}",
            "schedule": self.cron_schedule,
            "time_zone": "UTC",
            "http_target": http_target,
            "retry_config": {
                "retry_count": 3,
                "max_retry_duration": "3600s",
                "min_backoff_duration": "10s",
                "max_backoff_duration": "600s",
                "max_doublings": 3
            }
        }
        
        self.log(f"Built job configuration for: {job_name} with auth type: {self.auth_type}")
        return job_config

    def _build_http_target(self, credentials: service_account.Credentials) -> dict:
        """Build HTTP target configuration based on auth type and body"""
        http_target = {
            "uri": self.service_url,
            "http_method": "POST",
            "headers": {
                "Content-Type": "application/json"
            }
        }
        
        # Add body if provided - encode as Base64 bytes for Cloud Scheduler API
        if hasattr(self, 'request_body') and self.request_body:
            try:
                # Ensure it's valid JSON by parsing and re-encoding
                parsed_body = json.loads(self.request_body)
                json_string = json.dumps(parsed_body)
                
                # Cloud Scheduler expects body as Base64-encoded bytes
                body_bytes = json_string.encode('utf-8')
                http_target["body"] = base64.b64encode(body_bytes).decode('utf-8')
                
                self.log(f"Added custom request body to HTTP target (Base64 encoded)")
            except json.JSONDecodeError:
                self.log("Warning: Invalid JSON in request body, using empty body")
        
        # Configure authentication based on type
        if self.auth_type == "OIDC Token":
            http_target["oidc_token"] = {
                "service_account_email": credentials.service_account_email,
                "audience": self.service_url
            }
            self.log("Configured OIDC token authentication")
            
        elif self.auth_type == "OAuth Token":
            if hasattr(self, 'oauth_token') and self.oauth_token:
                http_target["oauth_token"] = {
                    "service_account_email": credentials.service_account_email,
                    "scope": "https://www.googleapis.com/auth/cloud-platform"
                }
                self.log("Configured OAuth token authentication")
            
        elif self.auth_type == "None":
            # No authentication headers
            self.log("No authentication configured - public endpoint")
        
        return http_target

    def _create_scheduler_job(self, service, job_config: dict) -> dict:
        """Create the Cloud Scheduler job using the Google API"""
        try:
            parent = f"projects/{self.project_id}/locations/{self.location}"
            
            self.log(f"Creating job in parent: {parent}")
            
            # Create the job
            request = service.projects().locations().jobs().create(
                parent=parent, 
                body=job_config
            )
            
            response = request.execute()
            return response
            
        except Exception as e:
            # Handle common errors with helpful messages
            if "already exists" in str(e).lower():
                raise ValueError(f"A job with this name already exists. Try using a different job name.")
            elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
                raise ValueError(f"Permission denied. Check if the service account has Cloud Scheduler Admin role.")
            elif "not found" in str(e).lower():
                raise ValueError(f"Project or location not found. Verify your project ID and location.")
            else:
                raise ValueError(f"API error: {str(e)}")

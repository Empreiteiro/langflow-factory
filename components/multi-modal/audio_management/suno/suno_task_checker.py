from langflow.custom import Component
from langflow.io import SecretStrInput, StrInput, Output
from langflow.schema import Data
import requests


class SunoTaskChecker(Component):
    display_name = "Suno Task Checker"
    description = "Fetches the music generation status and details using a task ID."
    icon = "search"
    name = "SunoTaskChecker"

    field_order = ["api_key", "task_id"]

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Your Suno API key.",
            required=True,
        ),
        StrInput(
            name="task_id",
            display_name="Task ID",
            info="The ID of the task to check the generation status.",
            required=True,
        ),
    ]

    outputs = [
        Output(
            name="task_details",
            display_name="Task Details",
            method="check_task_status",
        ),
    ]

    def check_task_status(self) -> Data:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            url = f"https://api.sunoapi.org/api/v1/music/task/{self.task_id}"
            self.log(f"Fetching status for task ID: {self.task_id}")

            response = requests.get(url, headers=headers)
            self.log(f"HTTP Status Code: {response.status_code}")
            result = response.json()
            self.log("Response JSON:")
            self.log(str(result))

            if response.status_code != 200:
                raise ValueError(result.get("msg", "Unknown error from Suno API."))

            self.status = f"✅ Task details fetched successfully for task ID: {self.task_id}"
            return Data(data=result)

        except Exception as e:
            error_message = f"Error checking task status: {str(e)}"
            self.status = error_message
            self.log(error_message)
            return Data(data={"error": error_message})

from langflow.custom import Component
from langflow.io import (
    StrInput,
    SecretStrInput,
    Output,
    DataInput,
    MessageTextInput,
)
from langflow.inputs import SortableListInput
from langflow.schema import Data
import requests


class ClickUpComponent(Component):
    display_name = "ClickUp Integration"
    description = "Interact with ClickUp API to manage tasks, lists, and spaces."
    icon = "check-circle"
    name = "ClickUpComponent"

    inputs = [
        SecretStrInput(
            name="api_token",
            display_name="API Token",
            required=True,
            info="Your ClickUp API token."
        ),
        SortableListInput(
            name="action",
            display_name="Action",
            placeholder="Select Action",
            info="List of actions to perform with ClickUp API.",
            options=[
                {"name": "List Tasks", "icon": "list"},
                {"name": "Get Task", "icon": "search"},
                {"name": "Create Task", "icon": "plus"},
                {"name": "List Teams", "icon": "users"},
                {"name": "List Spaces", "icon": "layers"},
                {"name": "List Lists", "icon": "list"},
                {"name": "List Folders", "icon": "folder"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        StrInput(
            name="task_id",
            display_name="Task ID",
            show=False,
            info="The ID of the task to retrieve."
        ),
        StrInput(
            name="list_id",
            display_name="List ID",
            show=False,
            info="The ID of the list where the task will be created."
        ),
        StrInput(
            name="folder_id",
            display_name="Folder ID",
            show=False,
            info="The ID of the folder where the lists are located."
        ),
        StrInput(
            name="space_id",
            display_name="Space ID",
            show=False,
            info="The ID of the space to list folders from."
        ),
        StrInput(
            name="team_id",
            display_name="Team ID",
            show=False,
            info="The ID of the team (workspace) to access folders."
        ),
        MessageTextInput(
            name="task_name",
            display_name="Task Name",
            show=False,
            info="The title/name of the task. Example: 'Implement new feature' or 'Review quarterly report'"
        ),
        MessageTextInput(
            name="task_description",
            display_name="Task Description",
            show=False,
            info="Detailed description of the task. Example: 'Develop the advanced reporting feature according to technical specification document'"
        ),
        StrInput(
            name="task_status",
            display_name="Task Status",
            show=False,
            info="Initial status of the task. Options: 'to do', 'in progress', 'complete'. Example: 'to do'"
        ),
        StrInput(
            name="task_priority",
            display_name="Task Priority",
            show=False,
            info="Priority level: 1=Urgent, 2=High, 3=Normal, 4=Low. Example: '2' for High priority"
        ),
        StrInput(
            name="task_due_date",
            display_name="Due Date (YYYY-MM-DD)",
            show=False,
            info="Due date in YYYY-MM-DD format. Example: '2024-01-15'"
        ),
        StrInput(
            name="task_assignees",
            display_name="Assignee IDs",
            show=False,
            info="Comma-separated list of user IDs to assign the task to. Example: '12345678,87654321'"
        ),
        StrInput(
            name="task_tags",
            display_name="Task Tags",
            show=False,
            info="Comma-separated list of tags for categorization. Example: 'urgent,development,high-priority'"
        ),
    ]

    outputs = [
        Output(name="clickup_result", display_name="Data", method="run_action")
    ]

    base_url = "https://api.clickup.com/api/v2"

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "action":
            return build_config

        selected = [action["name"] for action in field_value] if isinstance(field_value, list) else []

        visibility_map = {
            "Get Task": ["task_id"],
            "Create Task": ["list_id", "task_name", "task_description", "task_status", "task_priority", "task_due_date", "task_assignees", "task_tags"],
            "List Tasks": ["list_id"],
            "List Lists": ["folder_id"],
            "List Folders": ["space_id", "team_id"],
            "List Spaces": ["team_id"],
            "List Teams": [],
        }

        for field in ["task_id", "list_id", "task_name", "task_description", "task_status", "task_priority", "task_due_date", "task_assignees", "task_tags", "folder_id", "space_id", "team_id"]:
            if field in build_config:
                build_config[field]["show"] = False

        if selected and selected[0] in visibility_map:
            for field in visibility_map[selected[0]]:
                if field in build_config:
                    build_config[field]["show"] = True

        return build_config

    def run_action(self) -> Data:
        if not self.api_token:
            return Data(data={"error": "API token is required."})

        if not self.action:
            return Data(data={"error": "Action is required."})

        action_name = self.action[0].get("name") if isinstance(self.action, list) else self.action.get("name")
        headers = {
            "Authorization": self.api_token.get_secret_value() if hasattr(self.api_token, 'get_secret_value') else self.api_token,
            "Content-Type": "application/json"
        }

        try:
            match action_name:
                case "List Tasks":
                    if not self.list_id:
                        return Data(data={"error": "List ID is required for this action."})
                    url = f"{self.base_url}/list/{self.list_id}/task"
                    response = requests.get(url, headers=headers)
                case "Get Task":
                    if not self.task_id:
                        return Data(data={"error": "Task ID is required for this action."})
                    url = f"{self.base_url}/task/{self.task_id}"
                    response = requests.get(url, headers=headers)
                case "Create Task":
                    if not self.list_id or not self.task_name:
                        return Data(data={"error": "List ID and Task Name are required for this action."})
                    
                    # Build task data from individual fields
                    task_data = {
                        "name": self.task_name
                    }
                    
                    # Add optional fields if provided
                    if self.task_description:
                        task_data["description"] = self.task_description
                    
                    if self.task_status:
                        task_data["status"] = self.task_status
                    
                    if self.task_priority:
                        try:
                            task_data["priority"] = int(self.task_priority)
                        except ValueError:
                            return Data(data={"error": "Task Priority must be a number (1-4)."})
                    
                    if self.task_due_date:
                        try:
                            import datetime
                            due_date = datetime.datetime.strptime(self.task_due_date, "%Y-%m-%d")
                            task_data["due_date"] = int(due_date.timestamp() * 1000)
                        except ValueError:
                            return Data(data={"error": "Due Date must be in YYYY-MM-DD format."})
                    
                    if self.task_assignees:
                        try:
                            assignees = [int(assignee.strip()) for assignee in self.task_assignees.split(",")]
                            task_data["assignees"] = assignees
                        except ValueError:
                            return Data(data={"error": "Assignee IDs must be comma-separated numbers."})
                    
                    if self.task_tags:
                        tags = [tag.strip() for tag in self.task_tags.split(",")]
                        task_data["tags"] = tags
                    
                    url = f"{self.base_url}/list/{self.list_id}/task"
                    response = requests.post(url, headers=headers, json=task_data)
                case "List Spaces":
                    if not self.team_id:
                        return Data(data={"error": "Team ID is required for this action."})
                    url = f"{self.base_url}/team/{self.team_id}/space"
                    response = requests.get(url, headers=headers)
                case "List Lists":
                    if not self.folder_id:
                        return Data(data={"error": "Folder ID is required for this action."})
                    url = f"{self.base_url}/folder/{self.folder_id}/list"
                    response = requests.get(url, headers=headers)
                case "List Folders":
                    if not self.space_id or not self.team_id:
                        return Data(data={"error": "Both Space ID and Team ID are required for this action."})
                    url = f"{self.base_url}/space/{self.space_id}/folder"
                    response = requests.get(url, headers=headers)
                case "List Teams":
                    url = f"{self.base_url}/team"
                    response = requests.get(url, headers=headers)
                case _:
                    return Data(data={"error": f"Unsupported action: {action_name}"})

            response.raise_for_status()
            return Data(data=response.json())

        except requests.RequestException as e:
            self.log(f"HTTP error: {e}")
            return Data(data={"error": str(e)})
        except Exception as e:
            self.log(f"Unexpected error: {e}")
            return Data(data={"error": str(e)})

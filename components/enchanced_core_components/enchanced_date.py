from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

from loguru import logger

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, Output
from lfx.schema.message import Message


class CurrentDateComponent(Component):
    display_name = "Current Date"
    description = "Returns the current date and time in the selected timezone with customizable format."
    documentation: str = "https://docs.langflow.org/components-helpers#current-date"
    icon = "clock"
    name = "CurrentDate"

    FORMAT_OPTIONS = [
        "full_text",  # "Current date and time in UTC: 2024-01-15 10:30:45 UTC"
        "datetime_only",  # "2024-01-15 10:30:45 UTC"
        "date_only"  # "2024-01-15"
    ]

    inputs = [
        DropdownInput(
            name="timezone",
            display_name="Timezone",
            options=list(available_timezones()),
            value="UTC",
            info="Select the timezone for the current date and time.",
            tool_mode=True,
        ),
        DropdownInput(
            name="format_option",
            display_name="Format Option",
            options=FORMAT_OPTIONS,
            value="datetime_only",
            info="Select the output format: full_text (with description), datetime_only (just datetime), or date_only (just date).",
            tool_mode=True,
        ),
    ]
    outputs = [
        Output(display_name="Current Date", name="current_date", method="get_current_date"),
    ]

    def get_current_date(self) -> Message:
        try:
            tz = ZoneInfo(self.timezone)
            now = datetime.now(tz)
            
            if self.format_option == "full_text":
                current_date = now.strftime("%Y-%m-%d %H:%M:%S %Z")
                result = f"Current date and time in {self.timezone}: {current_date}"
            elif self.format_option == "datetime_only":
                result = now.strftime("%Y-%m-%d %H:%M:%S %Z")
            elif self.format_option == "date_only":
                result = now.strftime("%Y-%m-%d")
            else:
                # Default to datetime_only if invalid option
                result = now.strftime("%Y-%m-%d %H:%M:%S %Z")
            
            self.status = result
            return Message(text=result)
        except Exception as e:  # noqa: BLE001
            logger.opt(exception=True).debug("Error getting current date")
            error_message = f"Error: {e}"
            self.status = error_message
            return Message(text=error_message)

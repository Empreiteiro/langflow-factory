import json
import os
from typing import Any, Union

from lfx.custom.custom_component.component import Component
from lfx.io import FileInput, IntInput, MessageTextInput, Output, TabInput
from lfx.schema import Data
from lfx.schema.message import Message
from transformers import pipeline


class TextSummarization(Component):
    display_name = "Text Summarization"
    description = "Summarizes text content provided via file upload or incoming message using a Hugging Face model."
    icon = "HuggingFace"
    name = "TextSummarization"

    inputs = [
        TabInput(
            name="input_mode",
            display_name="Input Mode",
            info="Select whether to summarize text from a file or from an incoming message.",
            options=["File", "Message"],
            value="File",
            real_time_refresh=True,
        ),
        FileInput(
            name="text_file",
            display_name="Text File",
            info="Select a .txt file containing the text to summarize.",
            required=False,
            file_types=["txt"],
        ),
        MessageTextInput(
            name="text_message",
            display_name="Text Message",
            info="Provide the text content via an incoming message.",
            show=False,
        ),
        IntInput(
            name="max_length",
            display_name="Maximum Summary Length",
            info="Maximum number of tokens in the summary (must be greater than minimum length).",
            value=130,
            advanced=True,
        ),
        IntInput(
            name="min_length",
            display_name="Minimum Summary Length",
            info="Minimum number of tokens in the summary.",
            value=30,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Summary",
            name="summary_data",
            method="get_data_output",
        ),
    ]

    _summarizer = None

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "input_mode":
            return build_config

        selected_mode = field_value if isinstance(field_value, str) else "File"

        for name in ("text_file", "text_message"):
            if name in build_config:
                build_config[name]["show"] = False
                build_config[name]["required"] = False

        if selected_mode == "File":
            if "text_file" in build_config:
                build_config["text_file"]["show"] = True
                build_config["text_file"]["required"] = True
        elif "text_message" in build_config:
            build_config["text_message"]["show"] = True
            build_config["text_message"]["required"] = True

        return build_config

    def get_data_output(self) -> Data:
        try:
            text_content = self._load_text()

            if not text_content.strip():
                raise ValueError("No text content provided for summarization.")

            max_length = getattr(self, "max_length", 130) or 130
            min_length = getattr(self, "min_length", 30) or 30

            if min_length >= max_length:
                raise ValueError("Maximum length must be greater than minimum length.")

            summarizer = self._get_summarizer()
            summary = summarizer(
                text_content,
                max_length=max_length,
                min_length=min_length,
                do_sample=False,
            )

            summary_text = self._extract_summary_text(summary)

            self.status = "Summarization completed successfully."
            self.log(
                f"Summarization completed: summary_length={len(summary_text)}, "
                f"max_length={max_length}, min_length={min_length}"
            )

            return Data(
                data={
                    "summary": summary_text,
                    "max_length": max_length,
                    "min_length": min_length,
                }
            )
        except Exception as exc:
            error_text = f"Error while generating summary: {exc}"
            self.status = error_text
            self.log(error_text)
            return Data(data={"error": error_text})

    def _get_summarizer(self):
        if self._summarizer is None:
            self._summarizer = pipeline("summarization")
        return self._summarizer

    def _load_text(self) -> str:
        mode = getattr(self, "input_mode", "File")

        if mode == "Message":
            return self._extract_text_from_message(getattr(self, "text_message", None))

        return self._read_file_content(getattr(self, "text_file", None))

    def _read_file_content(self, file_input: Any) -> str:
        if not file_input:
            raise ValueError("No file provided.")

        if hasattr(file_input, "path"):
            file_path = file_input.path
        elif isinstance(file_input, str) and os.path.exists(file_input):
            file_path = file_input
        else:
            raise ValueError("Invalid file input: the file could not be located.")

        with open(file_path, "r", encoding="utf-8") as file_handle:
            return file_handle.read()

    def _extract_text_from_message(self, message_input: Any) -> str:
        if message_input is None:
            return ""

        if isinstance(message_input, Message):
            return message_input.text or ""

        if hasattr(message_input, "text"):
            return getattr(message_input, "text", "") or ""

        if isinstance(message_input, dict):
            return self._search_text_field(message_input) or ""

        if isinstance(message_input, str):
            parsed_payload = self._try_parse_json(message_input)
            if parsed_payload is not None:
                extracted = self._search_text_field(parsed_payload)
                if extracted:
                    return extracted
            return message_input

        return str(message_input)

    def _try_parse_json(self, payload: str) -> Union[dict, list, None]:
        try:
            return json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return None

    def _search_text_field(self, payload: Any) -> str:
        keys_to_check = {"text", "content"}

        if isinstance(payload, dict):
            for key in keys_to_check:
                if key in payload:
                    extracted = self._search_text_field(payload[key])
                    if extracted:
                        return extracted
            for value in payload.values():
                extracted = self._search_text_field(value)
                if extracted:
                    return extracted

        elif isinstance(payload, list):
            for item in payload:
                extracted = self._search_text_field(item)
                if extracted:
                    return extracted

        elif isinstance(payload, Message):
            return payload.text or ""

        elif isinstance(payload, str):
            if payload.strip():
                nested_payload = self._try_parse_json(payload)
                if nested_payload is not None:
                    return self._search_text_field(nested_payload)
                return payload

        return ""

    def _extract_summary_text(self, summary_result: Any) -> str:
        if isinstance(summary_result, list) and summary_result:
            summary_entry = summary_result[0]
        elif isinstance(summary_result, dict):
            summary_entry = summary_result
        else:
            raise ValueError("Unexpected summarization result format.")

        if isinstance(summary_entry, dict):
            if "summary_text" in summary_entry and isinstance(summary_entry["summary_text"], str):
                return summary_entry["summary_text"]

        raise ValueError("Could not extract summary text from model response.")
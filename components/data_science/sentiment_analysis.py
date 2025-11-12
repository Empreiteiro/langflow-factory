import json
import os
from typing import Any, Iterable, Union

from lfx.custom.custom_component.component import Component
from lfx.io import FileInput, MessageTextInput, Output, TabInput
from lfx.schema import Data
from lfx.schema.message import Message
from transformers import pipeline


class SentimentAnalysisFromFile(Component):
    display_name = "Sentiment Analysis"
    description = "Loads text from a file or message and runs sentiment analysis using a Hugging Face model."
    icon = "HuggingFace"
    name = "SentimentAnalysisFromFile"

    inputs = [
        TabInput(
            name="input_mode",
            display_name="Input Mode",
            info="Select whether to analyze text from a file or from an incoming message.",
            options=["File", "Message"],
            value="File",
            real_time_refresh=True,
        ),
        FileInput(
            name="text_file",
            display_name="Text File",
            info="Select a .txt file with the content to analyze.",
            required=False,
            file_types=["txt"],
        ),
        MessageTextInput(
            name="text_message",
            display_name="Text Message",
            info="Provide the text content via an incoming message.",
            show=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Sentiment Result",
            name="sentiment_result",
            method="get_data_output",
        ),
    ]

    _classifier = None

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name != "input_mode":
            return build_config

        selected_mode = field_value if isinstance(field_value, str) else "File"

        for field_name in ("text_file", "text_message"):
            if field_name in build_config:
                build_config[field_name]["show"] = False
                build_config[field_name]["required"] = False

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
                raise ValueError("No text content provided for analysis.")

            classifier = self._get_classifier()
            analysis = classifier(text_content)

            sentiment, confidence = self._extract_sentiment_data(analysis)

            self.status = "Analysis completed successfully."
            self.log(f"Analysis completed: sentiment={sentiment}, confidence={confidence:.4f}")

            return Data(
                data={
                    "sentiment": sentiment,
                    "confidence": confidence,
                }
            )
        except Exception as exc:
            error_text = f"Error while running sentiment analysis: {exc}"
            self.status = error_text
            self.log(error_text)
            return Data(data={"error": error_text})

    def _get_classifier(self):
        if self._classifier is None:
            self._classifier = pipeline("sentiment-analysis")
        return self._classifier

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

    def _extract_sentiment_data(self, analysis: Any) -> tuple[str, float]:
        if isinstance(analysis, Iterable):
            analysis_list = list(analysis)
            if analysis_list:
                sentiment, confidence = self._extract_from_mapping(analysis_list[0])
                if sentiment is not None and confidence is not None:
                    return sentiment, confidence

        if isinstance(analysis, dict):
            sentiment, confidence = self._extract_from_mapping(analysis)
            if sentiment is not None and confidence is not None:
                return sentiment, confidence

        raise ValueError("Could not extract sentiment data from model response.")

    def _extract_from_mapping(self, payload: Any) -> tuple[Union[str, None], Union[float, None]]:
        if isinstance(payload, dict):
            sentiment = payload.get("label") or payload.get("sentiment")
            confidence = payload.get("score") or payload.get("confidence")

            if isinstance(sentiment, str) and isinstance(confidence, (float, int)):
                return sentiment, float(confidence)

        return None, None

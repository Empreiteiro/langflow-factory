import json
import os
from typing import Any, Union

from langflow.custom.custom_component.component import Component
from langflow.io import FileInput, MessageTextInput, Output, TabInput
from langflow.schema import Data
from langflow.schema.message import Message
from transformers import pipeline


class TextClassification(Component):
    display_name = "Zero-Shot Classification"
    description = "Classifies text content into custom categories using zero-shot classification with a Hugging Face model."
    icon = "HuggingFace"
    name = "ZeroShotTextClassification"

    inputs = [
        TabInput(
            name="input_mode",
            display_name="Input Mode",
            info="Select whether to classify text from a file or from an incoming message.",
            options=["File", "Message"],
            value="File",
            real_time_refresh=True,
        ),
        FileInput(
            name="text_file",
            display_name="Text File",
            info="Select a .txt file containing the text to classify.",
            required=False,
            file_types=["txt"],
        ),
        MessageTextInput(
            name="text_message",
            display_name="Text Message",
            info="Provide the text content via an incoming message.",
            show=False,
        ),
        MessageTextInput(
            name="categories",
            display_name="Categories",
            info="List of categories for classification. Each item should be a text string with the category name.",
            is_list=True,
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Classification Result",
            name="classification_result",
            method="get_data_output",
        ),
    ]

    _classifier = None

    def _parse_categories(self, categories_input: Any) -> list[str]:
        if not categories_input:
            raise ValueError("Categories list cannot be empty.")
        
        # Log the input to help debug
        self.log(f"Parsing categories input: {type(categories_input)} - {categories_input}")
        
        if not isinstance(categories_input, list):
            categories_input = [categories_input]
        
        categories = []
        for idx, item in enumerate(categories_input):
            if isinstance(item, dict):
                # Extract all non-empty string values from dictionary
                # Try values first
                found_category = False
                for key, value in item.items():
                    if isinstance(value, str) and value.strip():
                        categories.append(value.strip())
                        found_category = True
                        self.log(f"Category {idx}: extracted '{value.strip()}' from key '{key}'")
                        break
                
                # If no string value found, try using the key itself (if it's not "category")
                if not found_category:
                    for key in item.keys():
                        if isinstance(key, str) and key.strip() and key.lower() != "category":
                            categories.append(key.strip())
                            found_category = True
                            self.log(f"Category {idx}: extracted '{key.strip()}' from key name")
                            break
                
                # Last resort: convert any value to string
                if not found_category and item:
                    for key, value in item.items():
                        if value is not None and str(value).strip():
                            categories.append(str(value).strip())
                            found_category = True
                            self.log(f"Category {idx}: extracted '{str(value).strip()}' by converting value")
                            break
                
                if not found_category:
                    self.log(f"Warning: Could not extract category from item {idx}: {item}")
            elif isinstance(item, str) and item.strip():
                categories.append(item.strip())
                self.log(f"Category {idx}: extracted directly as string '{item.strip()}'")
        
        if not categories:
            raise ValueError(
                f"At least one valid category is required. Each category should be a dictionary with a string value. "
                f"Received: {categories_input}"
            )
        
        self.log(f"Final categories list: {categories}")
        return categories

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
                raise ValueError("No text content provided for classification.")

            categories_input = getattr(self, "categories", [])
            candidate_labels = self._parse_categories(categories_input)

            classifier = self._get_classifier()
            classification = classifier(text_content, candidate_labels)

            label, score = self._extract_classification_data(classification)

            self.status = "Classification completed successfully."
            self.log(
                f"Classification completed: label={label}, score={score:.4f}, "
                f"categories={len(candidate_labels)}"
            )

            return Data(
                data={
                    "label": label,
                    "score": score,
                    "categories": candidate_labels,
                }
            )
        except Exception as exc:
            error_text = f"Error while running zero-shot classification: {exc}"
            self.status = error_text
            self.log(error_text)
            return Data(data={"error": error_text})

    def _get_classifier(self):
        if self._classifier is None:
            self._classifier = pipeline("zero-shot-classification")
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

    def _extract_classification_data(self, classification_result: Any) -> tuple[str, float]:
        # Zero-shot-classification returns a dict with "labels" (list) and "scores" (list)
        if isinstance(classification_result, dict):
            labels = classification_result.get("labels")
            scores = classification_result.get("scores")
            
            if labels and scores and isinstance(labels, list) and isinstance(scores, list):
                if len(labels) > 0 and len(scores) > 0:
                    # First element is the best match (highest score)
                    label = labels[0]
                    score = scores[0]
                    
                    if isinstance(label, str) and isinstance(score, (float, int)):
                        return label, float(score)
        
        # Fallback for other formats (list of dicts, single dict, etc.)
        if isinstance(classification_result, list) and classification_result:
            classification_entry = classification_result[0]
        elif isinstance(classification_result, dict):
            classification_entry = classification_result
        else:
            raise ValueError(f"Unexpected classification result format: {type(classification_result)}")

        if isinstance(classification_entry, dict):
            label = classification_entry.get("label") or classification_entry.get("LABEL")
            score = classification_entry.get("score")

            if isinstance(label, str) and isinstance(score, (float, int)):
                return label, float(score)

        raise ValueError(
            f"Could not extract classification data from model response. "
            f"Received: {type(classification_result)} - {classification_result}"
        )


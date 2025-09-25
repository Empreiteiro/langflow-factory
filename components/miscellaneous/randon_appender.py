import json
import random
from typing import Optional

from lfx.custom.custom_component.component import Component
from lfx.io import HandleInput, Output
from lfx.schema.message import Message


class RandomTextAppender(Component):
    display_name = "Random Text Appender"
    description = "Extracts inner text from a Message payload (if present) and appends a random phrase."
    icon = "🧩"
    name = "RandomTextAppender"

    inputs = [
        HandleInput(
            name="input_value",
            display_name="Text or Message",
            input_types=["Message", "str"],
            required=True,
        )
    ]

    outputs = [
        Output(display_name="Message Output", name="message_output", method="get_message_output")
    ]

    def _extract_text_from_possible_json(self, s: str, max_depth: int = 3) -> str:
        if not isinstance(s, str) or not s:
            return "" if s is None else str(s)

        text = s.strip()

        start_idx = text.find("{")
        if start_idx == -1:
            return text  

        depth = 0
        end_idx: Optional[int] = None
        for i in range(start_idx, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break

        if end_idx is None:
            return text  

        json_sub = text[start_idx : end_idx + 1]

        try:
            parsed = json.loads(json_sub)
        except Exception:
            return text  

        nested = None
        if isinstance(parsed, dict):
            nested = parsed.get("text", None)
            if nested is None:
                nested = parsed.get("content", None)

        if isinstance(nested, str):
            nested_str = nested.strip()
            if max_depth > 0 and (nested_str.startswith("{") or '"text"' in nested_str):
                return self._extract_text_from_possible_json(nested_str, max_depth - 1)
            return nested
        elif nested is not None:
            return str(nested)

        return text

    def get_message_output(self) -> Message:
        input_value = getattr(self, "input_value", None)

        if input_value is None:
            return Message(text="No input provided")

        if isinstance(input_value, Message):
            candidate = getattr(input_value, "text", None) or getattr(input_value, "content", None) or ""
        elif isinstance(input_value, str):
            candidate = input_value
        else:
            candidate = str(input_value)

        extracted = self._extract_text_from_possible_json(candidate)

        base_text = extracted if extracted else candidate

        suffix = random.choice(
            [
                " – and that's a fact!",
                " – more to come soon.",
                " – believe it or not.",
                " – stay tuned!",
            ]
        )

        final_text = base_text + suffix

        return Message(text=final_text)

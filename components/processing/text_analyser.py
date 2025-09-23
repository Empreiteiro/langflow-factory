from lfx.custom import Component
from lfx.io import MessageInput, Output
from lfx.schema import Data, Message

class TextStatsLogger(Component):
    display_name = "Text Analyzer"
    description = "Counts characters, words, vowels, and consonants in the input text with step-by-step logging."
    icon = "mdi-format-letter-case"
    name = "TextAnalyzer"

    inputs = [
        MessageInput(
            name="text",
            display_name="Input Text",
            info="The text to analyze.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="summary", display_name="Output", method="get_summary_output"),
        Output(name="log_output", display_name="Logs", method="get_log_output"),
    ]

    def _ensure_initialized(self):
        if not hasattr(self, "_logs"):
            self._logs = []
        if not hasattr(self, "_summary"):
            self._summary = None
        self._text = self._extract_text(self.text)

    def _extract_text(self, text_input):
        if isinstance(text_input, Message):
            return text_input.text or ""
        elif isinstance(text_input, Data):
            return text_input.data.get("text", "")
        elif isinstance(text_input, str):
            return text_input
        return str(text_input)

    def _append_log(self, name: str, message: str):
        self._logs.append({"name": name, "type": "text", "message": message})

    def _generate_counts(self):
        self._ensure_initialized()

        # Always regenerate logs and summary
        self._logs.clear()

        clean_message = self._text.replace("\n", " ").strip()
        if len(clean_message) > 300:
            clean_message = clean_message[:300] + "..."
        self._append_log("input_text", f"Received message: {clean_message}")

        char_count = len(self._text)
        word_count = len(self._text.split())
        vowels = 'aeiouAEIOU'
        vowel_count = sum(1 for char in self._text if char in vowels)
        consonant_count = sum(1 for char in self._text if char.isalpha() and char not in vowels)

        self._append_log("character_count", f"character_count: {char_count}")
        self._append_log("word_count", f"word_count: {word_count}")
        self._append_log("vowel_count", f"vowel_count: {vowel_count}")
        self._append_log("consonant_count", f"consonant_count: {consonant_count}")

        self._summary = {
            "character_count": char_count,
            "word_count": word_count,
            "vowel_count": vowel_count,
            "consonant_count": consonant_count
        }
        return self._summary

    def get_summary_output(self) -> Data:
        summary = self._generate_counts()
        return Data(data=summary)

    def get_log_output(self) -> Data:
        self._generate_counts()
        return Data(data={"logs": self._logs})

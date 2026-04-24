from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd
import re
import string


class TextCleaner(Component):
    display_name = "Text Cleaner"
    description = (
        "Cleans a text column: lowercasing, URL/HTML/punctuation/number removal, whitespace "
        "collapsing, stopword removal, and optional lemmatization or stemming."
    )
    icon = "mdi-broom"
    name = "TextCleaner"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            required=True,
        ),
        StrInput(
            name="text_column",
            display_name="Text Column",
            required=True,
        ),
        StrInput(
            name="output_column",
            display_name="Output Column",
            info="Destination column. Empty = overwrite the input column.",
            required=False,
        ),
        BoolInput(name="lowercase", display_name="Lowercase", value=True),
        BoolInput(name="remove_urls", display_name="Remove URLs", value=True),
        BoolInput(name="remove_html", display_name="Remove HTML", value=True),
        BoolInput(name="remove_punct", display_name="Remove Punctuation", value=True),
        BoolInput(name="remove_numbers", display_name="Remove Numbers", value=False),
        BoolInput(name="collapse_whitespace", display_name="Collapse Whitespace", value=True),
        BoolInput(name="remove_stopwords", display_name="Remove Stopwords", value=False),
        StrInput(
            name="language",
            display_name="Language",
            info="Language for stopwords and lemmatization (e.g. 'english', 'portuguese').",
            value="english",
        ),
        DropdownInput(
            name="normalize",
            display_name="Normalize",
            options=["none", "lemmatize", "stem"],
            value="none",
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result DataFrame", method="get_result"),
        Output(name="report", display_name="Report", method="get_report"),
    ]

    _URL_RE = re.compile(r"https?://\S+|www\.\S+")
    _HTML_RE = re.compile(r"<[^>]+>")
    _WS_RE = re.compile(r"\s+")

    def _load_stopwords(self):
        try:
            from nltk.corpus import stopwords
            return set(stopwords.words(self.language or "english"))
        except Exception:
            try:
                import nltk
                nltk.download("stopwords", quiet=True)
                from nltk.corpus import stopwords
                return set(stopwords.words(self.language or "english"))
            except Exception as exc:
                raise ImportError(
                    "nltk stopwords are required. Install nltk and run nltk.download('stopwords')."
                ) from exc

    def _lemmatizer(self):
        try:
            from nltk.stem import WordNetLemmatizer
            import nltk
            try:
                from nltk.corpus import wordnet  # noqa: F401
            except LookupError:
                nltk.download("wordnet", quiet=True)
            return WordNetLemmatizer().lemmatize
        except Exception as exc:
            raise ImportError("nltk with wordnet is required for lemmatization.") from exc

    def _stemmer(self):
        try:
            from nltk.stem.snowball import SnowballStemmer
            return SnowballStemmer(self.language or "english").stem
        except Exception as exc:
            raise ImportError("nltk is required for stemming.") from exc

    def _clean(self, text: str, stopwords, normalize_fn) -> str:
        if not isinstance(text, str):
            return ""
        s = text
        if self.remove_urls:
            s = self._URL_RE.sub(" ", s)
        if self.remove_html:
            s = self._HTML_RE.sub(" ", s)
        if self.lowercase:
            s = s.lower()
        if self.remove_numbers:
            s = re.sub(r"\d+", " ", s)
        if self.remove_punct:
            s = s.translate(str.maketrans("", "", string.punctuation))
        if self.collapse_whitespace:
            s = self._WS_RE.sub(" ", s).strip()

        if stopwords is None and normalize_fn is None:
            return s

        tokens = s.split()
        if stopwords is not None:
            tokens = [t for t in tokens if t not in stopwords]
        if normalize_fn is not None:
            tokens = [normalize_fn(t) for t in tokens]
        return " ".join(tokens)

    def _run(self):
        if self.df is None:
            raise ValueError("No DataFrame provided.")
        if not self.text_column:
            raise ValueError("text_column is required.")
        df = self.df.copy()
        if self.text_column not in df.columns:
            raise ValueError(f"Column '{self.text_column}' not found.")

        stopwords = self._load_stopwords() if self.remove_stopwords else None
        if self.normalize == "lemmatize":
            normalize_fn = self._lemmatizer()
        elif self.normalize == "stem":
            normalize_fn = self._stemmer()
        else:
            normalize_fn = None

        out_col = (self.output_column or self.text_column).strip()
        df[out_col] = df[self.text_column].astype(str).map(
            lambda x: self._clean(x, stopwords, normalize_fn)
        )

        self._result = df
        self._report = {
            "input_column": self.text_column,
            "output_column": out_col,
            "normalize": self.normalize,
            "removed_stopwords": bool(self.remove_stopwords),
            "rows": int(len(df)),
        }
        self.log(f"TextCleaner: {self._report}")

    def get_result(self) -> DataFrame:
        try:
            if not hasattr(self, "_result"):
                self._run()
            return DataFrame(self._result)
        except Exception as exc:
            self.log(f"TextCleaner failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_report(self) -> Data:
        try:
            if not hasattr(self, "_report"):
                self._run()
            return Data(data=self._report)
        except Exception as exc:
            return Data(data={"error": str(exc)})

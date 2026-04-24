from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class SLMTokenizer(Component):
    display_name = "SLM Tokenizer"
    description = (
        "Tokenizes a prepared text dataset using a HuggingFace AutoTokenizer. "
        "Produces input_ids/attention_mask columns and a reusable tokenizer artifact for training."
    )
    icon = "mdi-format-letter-matches"
    name = "SLMTokenizer"

    inputs = [
        DataFrameInput(
            name="df",
            display_name="Dataset",
            info="Prepared dataset with a 'text' column (output of SLM Dataset Preparation).",
            required=True,
        ),
        StrInput(
            name="tokenizer_name",
            display_name="Tokenizer / Model",
            info="HuggingFace model id whose tokenizer will be loaded (e.g. 'meta-llama/Llama-3.2-1B').",
            required=True,
            value="gpt2",
        ),
        StrInput(
            name="text_column",
            display_name="Text Column",
            info="Column in the input DataFrame that holds the text to tokenize.",
            value="text",
        ),
        IntInput(
            name="max_length",
            display_name="Max Length",
            info="Maximum sequence length (in tokens).",
            value=512,
        ),
        DropdownInput(
            name="padding",
            display_name="Padding",
            info="Padding strategy passed to the tokenizer.",
            options=["do_not_pad", "max_length", "longest"],
            value="max_length",
        ),
        BoolInput(
            name="truncation",
            display_name="Truncation",
            info="Truncate sequences longer than max_length.",
            value=True,
        ),
        BoolInput(
            name="add_special_tokens",
            display_name="Add Special Tokens",
            info="Include special tokens (BOS/EOS) during encoding.",
            value=True,
        ),
        BoolInput(
            name="use_fast",
            display_name="Use Fast Tokenizer",
            info="Prefer the Rust-backed fast tokenizer when available.",
            value=True,
        ),
        StrInput(
            name="pad_token",
            display_name="Pad Token",
            info="Override for the pad token. Use 'eos' to reuse the EOS token (common for causal LMs).",
            value="eos",
        ),
        BoolInput(
            name="trust_remote_code",
            display_name="Trust Remote Code",
            info="Allow loading tokenizer code shipped inside the model repository.",
            value=False,
        ),
    ]

    outputs = [
        Output(name="tokenized", display_name="Tokenized Dataset", method="get_tokenized"),
        Output(name="tokenizer", display_name="Tokenizer Artifact", method="get_tokenizer"),
    ]

    def _load_tokenizer(self):
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "transformers is required. Install with: pip install transformers"
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(
            self.tokenizer_name,
            use_fast=bool(self.use_fast),
            trust_remote_code=bool(self.trust_remote_code),
        )

        if tokenizer.pad_token is None:
            desired = (self.pad_token or "eos").strip()
            if desired.lower() == "eos" and tokenizer.eos_token is not None:
                tokenizer.pad_token = tokenizer.eos_token
            elif desired:
                tokenizer.add_special_tokens({"pad_token": desired})
        return tokenizer

    def _tokenize_df(self, tokenizer, df: pd.DataFrame) -> pd.DataFrame:
        col = self.text_column or "text"
        if col not in df.columns:
            raise ValueError(f"Text column '{col}' not found in DataFrame.")

        padding = self.padding or "max_length"
        if padding == "do_not_pad":
            padding = False

        encoded = tokenizer(
            df[col].astype(str).tolist(),
            max_length=int(self.max_length or 512),
            padding=padding,
            truncation=bool(self.truncation),
            add_special_tokens=bool(self.add_special_tokens),
            return_tensors=None,
        )

        df = df.copy()
        df["input_ids"] = encoded["input_ids"]
        if "attention_mask" in encoded:
            df["attention_mask"] = encoded["attention_mask"]
        df["num_tokens"] = df["input_ids"].apply(len)
        return df

    def _run(self):
        if self.df is None:
            raise ValueError("No input DataFrame provided.")
        tokenizer = self._load_tokenizer()
        df = self._tokenize_df(tokenizer, self.df.copy())
        self._tokenizer = tokenizer
        self._tokenized = df
        self._info = {
            "tokenizer": self.tokenizer_name,
            "vocab_size": getattr(tokenizer, "vocab_size", None),
            "pad_token": tokenizer.pad_token,
            "eos_token": tokenizer.eos_token,
            "num_rows": int(len(df)),
            "avg_tokens": float(df["num_tokens"].mean()) if len(df) else 0.0,
            "max_tokens_row": int(df["num_tokens"].max()) if len(df) else 0,
            "max_length": int(self.max_length or 512),
        }
        self.log(f"SLMTokenizer: {self._info}")

    def get_tokenized(self) -> DataFrame:
        try:
            if not hasattr(self, "_tokenized"):
                self._run()
            return DataFrame(self._tokenized)
        except Exception as exc:
            self.log(f"SLMTokenizer failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_tokenizer(self) -> Data:
        try:
            if not hasattr(self, "_tokenizer"):
                self._run()
            return Data(
                data={
                    "tokenizer": self._tokenizer,
                    "info": self._info,
                }
            )
        except Exception as exc:
            self.log(f"SLMTokenizer artifact failed: {exc}")
            return Data(data={"error": str(exc)})

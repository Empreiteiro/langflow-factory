from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DropdownInput,
    IntInput,
    Output,
    StrInput,
    TabInput,
)
from lfx.schema import Data, DataFrame
import pandas as pd


class SLMDatasetPreparation(Component):
    display_name = "SLM Dataset Preparation"
    description = (
        "Loads and formats a text dataset for Small Language Model training. "
        "Supports HuggingFace Hub datasets or a local DataFrame, and formats text as plain, "
        "instruction (prompt/response) or chat (messages) style."
    )
    icon = "mdi-database-cog"
    name = "SLMDatasetPreparation"

    inputs = [
        TabInput(
            name="source_mode",
            display_name="Source",
            info="Load the dataset from the HuggingFace Hub or from an incoming DataFrame.",
            options=["HuggingFace Hub", "DataFrame"],
            value="HuggingFace Hub",
            real_time_refresh=True,
        ),
        StrInput(
            name="dataset_name",
            display_name="Dataset Name",
            info="HuggingFace Hub dataset identifier (e.g. 'tatsu-lab/alpaca').",
            required=False,
        ),
        StrInput(
            name="dataset_config",
            display_name="Dataset Config",
            info="Optional configuration / subset name for the dataset.",
            required=False,
        ),
        StrInput(
            name="split",
            display_name="Split",
            info="Dataset split to load (e.g. 'train', 'train[:1%]').",
            value="train",
        ),
        DataFrameInput(
            name="df",
            display_name="DataFrame",
            info="Input DataFrame with the source columns. Used when Source is 'DataFrame'.",
            required=False,
            show=False,
        ),
        DropdownInput(
            name="format_type",
            display_name="Format",
            info="How to compose the 'text' column sent to the tokenizer.",
            options=["plain", "instruction", "chat"],
            value="instruction",
            real_time_refresh=True,
        ),
        StrInput(
            name="text_column",
            display_name="Text Column",
            info="Source column used when format is 'plain'.",
            value="text",
        ),
        StrInput(
            name="instruction_column",
            display_name="Instruction Column",
            info="Column holding the instruction/prompt for 'instruction' format.",
            value="instruction",
        ),
        StrInput(
            name="input_column",
            display_name="Input Column",
            info="Optional column with extra input context for 'instruction' format.",
            value="input",
        ),
        StrInput(
            name="output_column",
            display_name="Output Column",
            info="Column holding the expected response for 'instruction' format.",
            value="output",
        ),
        StrInput(
            name="messages_column",
            display_name="Messages Column",
            info="Column holding a list of {role, content} dicts for 'chat' format.",
            value="messages",
        ),
        IntInput(
            name="max_samples",
            display_name="Max Samples",
            info="Maximum number of rows to keep (0 = all).",
            value=0,
        ),
        BoolInput(
            name="shuffle",
            display_name="Shuffle",
            info="Shuffle the dataset before truncation.",
            value=True,
        ),
        IntInput(
            name="seed",
            display_name="Seed",
            info="Random seed used for shuffling.",
            value=42,
        ),
    ]

    outputs = [
        Output(name="dataset", display_name="Prepared Dataset", method="get_dataset"),
        Output(name="stats", display_name="Preparation Stats", method="get_stats"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name == "source_mode":
            mode = field_value if isinstance(field_value, str) else "HuggingFace Hub"
            hub_fields = ("dataset_name", "dataset_config", "split")
            df_fields = ("df",)
            for n in hub_fields:
                if n in build_config:
                    build_config[n]["show"] = mode == "HuggingFace Hub"
            for n in df_fields:
                if n in build_config:
                    build_config[n]["show"] = mode == "DataFrame"
                    build_config[n]["required"] = mode == "DataFrame"

        if field_name == "format_type":
            fmt = field_value if isinstance(field_value, str) else "instruction"
            show_map = {
                "text_column": fmt == "plain",
                "instruction_column": fmt == "instruction",
                "input_column": fmt == "instruction",
                "output_column": fmt == "instruction",
                "messages_column": fmt == "chat",
            }
            for n, visible in show_map.items():
                if n in build_config:
                    build_config[n]["show"] = visible
        return build_config

    def _load_dataframe(self) -> pd.DataFrame:
        mode = getattr(self, "source_mode", "HuggingFace Hub")
        if mode == "DataFrame":
            if self.df is None:
                raise ValueError("No DataFrame provided.")
            return self.df.copy()

        if not getattr(self, "dataset_name", None):
            raise ValueError("Dataset name is required when loading from the HuggingFace Hub.")

        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise ImportError(
                "The 'datasets' library is required. Install with: pip install datasets"
            ) from exc

        kwargs = {"split": self.split or "train"}
        if getattr(self, "dataset_config", None):
            kwargs["name"] = self.dataset_config
        ds = load_dataset(self.dataset_name, **kwargs)
        return ds.to_pandas()

    def _format_chat(self, messages):
        if not isinstance(messages, (list, tuple)):
            return str(messages or "")
        parts = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"<|{role}|>\n{content}")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    def _compose_text(self, df: pd.DataFrame) -> pd.DataFrame:
        fmt = getattr(self, "format_type", "instruction")
        if fmt == "plain":
            col = self.text_column or "text"
            if col not in df.columns:
                raise ValueError(f"Text column '{col}' not found in dataset.")
            df["text"] = df[col].astype(str)
        elif fmt == "instruction":
            instr = self.instruction_column or "instruction"
            out = self.output_column or "output"
            extra = self.input_column or None
            if instr not in df.columns or out not in df.columns:
                raise ValueError(
                    f"Columns '{instr}' and '{out}' are required for instruction format."
                )

            def _build(row):
                prompt = str(row[instr]).strip()
                context = str(row[extra]).strip() if extra and extra in df.columns and pd.notna(row.get(extra)) else ""
                response = str(row[out]).strip()
                if context:
                    return f"### Instruction:\n{prompt}\n\n### Input:\n{context}\n\n### Response:\n{response}"
                return f"### Instruction:\n{prompt}\n\n### Response:\n{response}"

            df["text"] = df.apply(_build, axis=1)
        elif fmt == "chat":
            col = self.messages_column or "messages"
            if col not in df.columns:
                raise ValueError(f"Messages column '{col}' not found in dataset.")
            df["text"] = df[col].apply(self._format_chat)
        else:
            raise ValueError(f"Unsupported format: {fmt}")
        return df

    def _prepare(self) -> pd.DataFrame:
        df = self._load_dataframe()
        if df.empty:
            raise ValueError("Loaded dataset is empty.")
        df = self._compose_text(df)

        if self.shuffle:
            df = df.sample(frac=1, random_state=int(self.seed or 42)).reset_index(drop=True)
        if self.max_samples and int(self.max_samples) > 0:
            df = df.head(int(self.max_samples)).reset_index(drop=True)

        self._stats = {
            "num_rows": int(len(df)),
            "format": self.format_type,
            "avg_text_length": float(df["text"].str.len().mean()) if "text" in df.columns else 0.0,
            "max_text_length": int(df["text"].str.len().max()) if "text" in df.columns else 0,
        }
        self.log(f"Prepared dataset: {self._stats}")
        self._prepared = df
        return df

    def get_dataset(self) -> DataFrame:
        try:
            df = self._prepare()
            return DataFrame(df)
        except Exception as exc:
            self.log(f"SLMDatasetPreparation failed: {exc}")
            self._stats = {"error": str(exc)}
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

    def get_stats(self) -> Data:
        if not hasattr(self, "_stats"):
            try:
                self._prepare()
            except Exception as exc:
                return Data(data={"error": str(exc)})
        return Data(data=self._stats)

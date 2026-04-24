from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    FloatInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data


class SLMLoRAConfig(Component):
    display_name = "SLM LoRA Config"
    description = (
        "Builds a PEFT LoRA configuration for parameter-efficient fine-tuning of Small Language Models. "
        "Also exposes optional 4-bit / 8-bit quantization settings for QLoRA-style training."
    )
    icon = "mdi-tune-vertical"
    name = "SLMLoRAConfig"

    inputs = [
        IntInput(
            name="r",
            display_name="LoRA Rank (r)",
            info="Rank of the LoRA update matrices. Higher = more capacity, more memory.",
            value=16,
        ),
        IntInput(
            name="lora_alpha",
            display_name="LoRA Alpha",
            info="Scaling factor for the LoRA update. Usually 2*r.",
            value=32,
        ),
        FloatInput(
            name="lora_dropout",
            display_name="LoRA Dropout",
            info="Dropout applied to the LoRA adapters.",
            value=0.05,
        ),
        StrInput(
            name="target_modules",
            display_name="Target Modules",
            info="Module names to attach LoRA to.",
            is_list=True,
            value=["q_proj", "k_proj", "v_proj", "o_proj"],
        ),
        DropdownInput(
            name="bias",
            display_name="Bias",
            info="Which biases to train alongside LoRA weights.",
            options=["none", "all", "lora_only"],
            value="none",
        ),
        DropdownInput(
            name="task_type",
            display_name="Task Type",
            info="PEFT task type.",
            options=["CAUSAL_LM", "SEQ_2_SEQ_LM", "SEQ_CLS", "TOKEN_CLS"],
            value="CAUSAL_LM",
        ),
        BoolInput(
            name="use_qlora",
            display_name="Use QLoRA (4-bit)",
            info="Enable 4-bit base-model quantization via bitsandbytes.",
            value=False,
        ),
        BoolInput(
            name="use_8bit",
            display_name="Use 8-bit",
            info="Enable 8-bit base-model quantization (ignored if QLoRA is on).",
            value=False,
        ),
        DropdownInput(
            name="bnb_4bit_quant_type",
            display_name="4-bit Quant Type",
            info="Quantization dtype used by bitsandbytes when QLoRA is enabled.",
            options=["nf4", "fp4"],
            value="nf4",
        ),
        BoolInput(
            name="bnb_4bit_double_quant",
            display_name="4-bit Double Quantization",
            info="Nested quantization to save additional memory.",
            value=True,
        ),
        DropdownInput(
            name="bnb_4bit_compute_dtype",
            display_name="4-bit Compute dtype",
            info="Compute dtype used for matmul during QLoRA training.",
            options=["float16", "bfloat16", "float32"],
            value="bfloat16",
        ),
    ]

    outputs = [
        Output(name="config", display_name="LoRA Config", method="get_config"),
        Output(name="summary", display_name="Summary", method="get_summary"),
    ]

    def _normalize_targets(self):
        raw = self.target_modules or []
        if isinstance(raw, str):
            raw = [raw]
        targets = []
        for item in raw:
            if isinstance(item, dict):
                for value in item.values():
                    if isinstance(value, str) and value.strip():
                        targets.append(value.strip())
                        break
            elif isinstance(item, str) and item.strip():
                targets.append(item.strip())
        if not targets:
            raise ValueError("At least one target module is required.")
        return targets

    def _build(self):
        try:
            from peft import LoraConfig
        except ImportError as exc:
            raise ImportError(
                "peft is required. Install with: pip install peft"
            ) from exc

        targets = self._normalize_targets()

        lora_config = LoraConfig(
            r=int(self.r or 16),
            lora_alpha=int(self.lora_alpha or 32),
            lora_dropout=float(self.lora_dropout or 0.0),
            target_modules=targets,
            bias=self.bias or "none",
            task_type=self.task_type or "CAUSAL_LM",
        )

        bnb_config = None
        if self.use_qlora or self.use_8bit:
            try:
                import torch
                from transformers import BitsAndBytesConfig
            except ImportError as exc:
                raise ImportError(
                    "bitsandbytes + transformers are required for quantization. "
                    "Install with: pip install bitsandbytes transformers torch"
                ) from exc

            if self.use_qlora:
                dtype_map = {
                    "float16": torch.float16,
                    "bfloat16": torch.bfloat16,
                    "float32": torch.float32,
                }
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type=self.bnb_4bit_quant_type or "nf4",
                    bnb_4bit_use_double_quant=bool(self.bnb_4bit_double_quant),
                    bnb_4bit_compute_dtype=dtype_map.get(
                        self.bnb_4bit_compute_dtype or "bfloat16", torch.bfloat16
                    ),
                )
            else:
                bnb_config = BitsAndBytesConfig(load_in_8bit=True)

        self._summary = {
            "r": int(self.r or 16),
            "lora_alpha": int(self.lora_alpha or 32),
            "lora_dropout": float(self.lora_dropout or 0.0),
            "target_modules": targets,
            "bias": self.bias or "none",
            "task_type": self.task_type or "CAUSAL_LM",
            "quantization": "4bit" if self.use_qlora else ("8bit" if self.use_8bit else "none"),
        }
        self._config = {"lora_config": lora_config, "bnb_config": bnb_config, "summary": self._summary}
        self.log(f"SLMLoRAConfig: {self._summary}")

    def get_config(self) -> Data:
        try:
            if not hasattr(self, "_config"):
                self._build()
            return Data(data=self._config)
        except Exception as exc:
            self.log(f"SLMLoRAConfig failed: {exc}")
            return Data(data={"error": str(exc)})

    def get_summary(self) -> Data:
        try:
            if not hasattr(self, "_summary"):
                self._build()
            return Data(data=self._summary)
        except Exception as exc:
            return Data(data={"error": str(exc)})

from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DataInput,
    DropdownInput,
    FloatInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data


class SLMFineTuner(Component):
    display_name = "SLM Fine-Tuner"
    description = (
        "Fine-tunes a Small Language Model with causal-LM objective using HuggingFace Trainer. "
        "Accepts a tokenized dataset and tokenizer artifact, and optionally a LoRA/QLoRA config for "
        "parameter-efficient training."
    )
    icon = "mdi-cog-sync"
    name = "SLMFineTuner"

    inputs = [
        StrInput(
            name="base_model",
            display_name="Base Model",
            info="HuggingFace model id to fine-tune (e.g. 'meta-llama/Llama-3.2-1B').",
            required=True,
            value="gpt2",
        ),
        DataFrameInput(
            name="train_dataset",
            display_name="Train Dataset",
            info="Tokenized dataset with 'input_ids' (and optional 'attention_mask').",
            required=True,
        ),
        DataFrameInput(
            name="eval_dataset",
            display_name="Eval Dataset",
            info="Optional tokenized evaluation dataset.",
            required=False,
        ),
        DataInput(
            name="tokenizer_artifact",
            display_name="Tokenizer",
            info="Tokenizer artifact produced by SLM Tokenizer.",
            required=True,
        ),
        DataInput(
            name="lora_artifact",
            display_name="LoRA Config",
            info="Optional LoRA/QLoRA configuration produced by SLM LoRA Config.",
            required=False,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Directory",
            info="Local directory to write checkpoints and the final model.",
            value="./slm-output",
        ),
        IntInput(
            name="num_train_epochs",
            display_name="Epochs",
            value=3,
        ),
        IntInput(
            name="per_device_batch_size",
            display_name="Per-Device Batch Size",
            value=2,
        ),
        IntInput(
            name="gradient_accumulation_steps",
            display_name="Gradient Accumulation",
            value=8,
        ),
        FloatInput(
            name="learning_rate",
            display_name="Learning Rate",
            value=2e-4,
        ),
        FloatInput(
            name="weight_decay",
            display_name="Weight Decay",
            value=0.0,
        ),
        FloatInput(
            name="warmup_ratio",
            display_name="Warmup Ratio",
            value=0.03,
        ),
        DropdownInput(
            name="lr_scheduler_type",
            display_name="LR Scheduler",
            options=["linear", "cosine", "cosine_with_restarts", "polynomial", "constant", "constant_with_warmup"],
            value="cosine",
        ),
        DropdownInput(
            name="optimizer",
            display_name="Optimizer",
            options=["adamw_torch", "adamw_hf", "adamw_bnb_8bit", "paged_adamw_8bit", "paged_adamw_32bit"],
            value="adamw_torch",
        ),
        DropdownInput(
            name="precision",
            display_name="Precision",
            info="Mixed-precision training mode.",
            options=["fp32", "fp16", "bf16"],
            value="bf16",
        ),
        BoolInput(
            name="gradient_checkpointing",
            display_name="Gradient Checkpointing",
            value=True,
        ),
        IntInput(
            name="logging_steps",
            display_name="Logging Steps",
            value=10,
        ),
        IntInput(
            name="save_steps",
            display_name="Save Steps",
            value=200,
        ),
        IntInput(
            name="seed",
            display_name="Seed",
            value=42,
        ),
        BoolInput(
            name="trust_remote_code",
            display_name="Trust Remote Code",
            value=False,
        ),
    ]

    outputs = [
        Output(name="trained_model", display_name="Trained Model", method="run_training"),
        Output(name="metrics", display_name="Training Metrics", method="get_metrics"),
    ]

    def _extract_tokenizer(self):
        artifact = self.tokenizer_artifact
        if artifact is None:
            raise ValueError("Tokenizer artifact is required.")
        data = artifact.data if hasattr(artifact, "data") else artifact
        tokenizer = data.get("tokenizer") if isinstance(data, dict) else None
        if tokenizer is None:
            raise ValueError("Tokenizer artifact does not contain a 'tokenizer'.")
        return tokenizer

    def _extract_lora(self):
        if self.lora_artifact is None:
            return None, None
        data = self.lora_artifact.data if hasattr(self.lora_artifact, "data") else self.lora_artifact
        if not isinstance(data, dict):
            return None, None
        return data.get("lora_config"), data.get("bnb_config")

    def _to_hf_dataset(self, df):
        try:
            from datasets import Dataset
        except ImportError as exc:
            raise ImportError("datasets is required. Install with: pip install datasets") from exc
        if df is None:
            return None
        if "input_ids" not in df.columns:
            raise ValueError("Tokenized dataset must contain an 'input_ids' column.")
        keep = [c for c in ["input_ids", "attention_mask", "labels"] if c in df.columns]
        ds = Dataset.from_pandas(df[keep].reset_index(drop=True), preserve_index=False)
        return ds

    def _build_training_args(self):
        try:
            from transformers import TrainingArguments
        except ImportError as exc:
            raise ImportError("transformers is required. Install with: pip install transformers") from exc

        kwargs = {
            "output_dir": self.output_dir or "./slm-output",
            "num_train_epochs": float(self.num_train_epochs or 3),
            "per_device_train_batch_size": int(self.per_device_batch_size or 2),
            "per_device_eval_batch_size": int(self.per_device_batch_size or 2),
            "gradient_accumulation_steps": int(self.gradient_accumulation_steps or 1),
            "learning_rate": float(self.learning_rate or 2e-4),
            "weight_decay": float(self.weight_decay or 0.0),
            "warmup_ratio": float(self.warmup_ratio or 0.0),
            "lr_scheduler_type": self.lr_scheduler_type or "cosine",
            "optim": self.optimizer or "adamw_torch",
            "logging_steps": int(self.logging_steps or 10),
            "save_steps": int(self.save_steps or 200),
            "seed": int(self.seed or 42),
            "gradient_checkpointing": bool(self.gradient_checkpointing),
            "report_to": "none",
        }
        if self.precision == "fp16":
            kwargs["fp16"] = True
        elif self.precision == "bf16":
            kwargs["bf16"] = True
        if self.eval_dataset is not None:
            kwargs["eval_strategy"] = "epoch"
        return TrainingArguments(**kwargs)

    def _load_model(self, bnb_config):
        try:
            from transformers import AutoModelForCausalLM
        except ImportError as exc:
            raise ImportError("transformers is required. Install with: pip install transformers") from exc

        model_kwargs = {"trust_remote_code": bool(self.trust_remote_code)}
        if bnb_config is not None:
            model_kwargs["quantization_config"] = bnb_config
        model = AutoModelForCausalLM.from_pretrained(self.base_model, **model_kwargs)
        return model

    def run_training(self) -> Data:
        try:
            try:
                from transformers import DataCollatorForLanguageModeling, Trainer
            except ImportError as exc:
                raise ImportError("transformers is required. Install with: pip install transformers") from exc

            tokenizer = self._extract_tokenizer()
            lora_config, bnb_config = self._extract_lora()

            model = self._load_model(bnb_config)

            if lora_config is not None:
                try:
                    from peft import get_peft_model, prepare_model_for_kbit_training
                except ImportError as exc:
                    raise ImportError("peft is required for LoRA. Install with: pip install peft") from exc
                if bnb_config is not None:
                    model = prepare_model_for_kbit_training(model)
                model = get_peft_model(model, lora_config)

            train_ds = self._to_hf_dataset(self.train_dataset)
            eval_ds = self._to_hf_dataset(self.eval_dataset) if self.eval_dataset is not None else None

            collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
            args = self._build_training_args()

            trainer = Trainer(
                model=model,
                args=args,
                train_dataset=train_ds,
                eval_dataset=eval_ds,
                tokenizer=tokenizer,
                data_collator=collator,
            )

            train_result = trainer.train()
            final_metrics = dict(train_result.metrics) if hasattr(train_result, "metrics") else {}
            if eval_ds is not None:
                eval_metrics = trainer.evaluate()
                final_metrics.update({f"eval_{k}": v for k, v in eval_metrics.items()})

            trainer.save_model(args.output_dir)
            tokenizer.save_pretrained(args.output_dir)

            self._metrics = {
                "output_dir": args.output_dir,
                "base_model": self.base_model,
                "used_lora": lora_config is not None,
                "used_quantization": bnb_config is not None,
                "metrics": final_metrics,
            }
            self.log(f"SLMFineTuner finished: {self._metrics}")
            return Data(
                data={
                    "model": model,
                    "tokenizer": tokenizer,
                    "output_dir": args.output_dir,
                    "base_model": self.base_model,
                    "used_lora": lora_config is not None,
                    "metrics": final_metrics,
                }
            )
        except Exception as exc:
            self.log(f"SLMFineTuner failed: {exc}")
            self._metrics = {"error": str(exc)}
            return Data(data={"error": str(exc)})

    def get_metrics(self) -> Data:
        if not hasattr(self, "_metrics"):
            return Data(data={"status": "not_run"})
        return Data(data=self._metrics)

from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataFrameInput,
    DataInput,
    FloatInput,
    IntInput,
    Output,
    StrInput,
)
from lfx.schema import Data, DataFrame
import math
import pandas as pd


class SLMEvaluator(Component):
    display_name = "SLM Evaluator"
    description = (
        "Evaluates a trained Small Language Model: computes perplexity on a tokenized eval set "
        "and optionally generates completions for a list of sample prompts."
    )
    icon = "mdi-chart-line"
    name = "SLMEvaluator"

    inputs = [
        DataInput(
            name="model_artifact",
            display_name="Trained Model",
            info="Artifact produced by SLM Fine-Tuner (model + tokenizer).",
            required=True,
        ),
        DataFrameInput(
            name="eval_dataset",
            display_name="Eval Dataset",
            info="Optional tokenized eval dataset for perplexity.",
            required=False,
        ),
        StrInput(
            name="sample_prompts",
            display_name="Sample Prompts",
            info="Prompts to generate completions for (one per list item).",
            is_list=True,
            required=False,
        ),
        IntInput(
            name="max_new_tokens",
            display_name="Max New Tokens",
            value=128,
        ),
        FloatInput(
            name="temperature",
            display_name="Temperature",
            value=0.7,
        ),
        FloatInput(
            name="top_p",
            display_name="Top-p",
            value=0.9,
        ),
        IntInput(
            name="per_device_batch_size",
            display_name="Eval Batch Size",
            value=2,
        ),
        BoolInput(
            name="do_sample",
            display_name="Sample",
            info="Use sampling instead of greedy decoding.",
            value=True,
        ),
    ]

    outputs = [
        Output(name="metrics", display_name="Evaluation Metrics", method="get_metrics"),
        Output(name="samples", display_name="Sample Generations", method="get_samples"),
    ]

    def _unwrap(self, artifact):
        if artifact is None:
            raise ValueError("Trained model artifact is required.")
        data = artifact.data if hasattr(artifact, "data") else artifact
        if not isinstance(data, dict) or "model" not in data or "tokenizer" not in data:
            raise ValueError("Artifact must contain 'model' and 'tokenizer'.")
        return data["model"], data["tokenizer"]

    def _normalize_prompts(self):
        raw = getattr(self, "sample_prompts", None) or []
        if isinstance(raw, str):
            raw = [raw]
        prompts = []
        for item in raw:
            if isinstance(item, dict):
                for value in item.values():
                    if isinstance(value, str) and value.strip():
                        prompts.append(value.strip())
                        break
            elif isinstance(item, str) and item.strip():
                prompts.append(item.strip())
        return prompts

    def _compute_perplexity(self, model, tokenizer) -> dict:
        if self.eval_dataset is None or "input_ids" not in self.eval_dataset.columns:
            return {}
        try:
            from datasets import Dataset
            from transformers import DataCollatorForLanguageModeling, Trainer, TrainingArguments
        except ImportError as exc:
            raise ImportError(
                "transformers and datasets are required for evaluation."
            ) from exc

        keep = [c for c in ["input_ids", "attention_mask", "labels"] if c in self.eval_dataset.columns]
        ds = Dataset.from_pandas(
            self.eval_dataset[keep].reset_index(drop=True), preserve_index=False
        )
        args = TrainingArguments(
            output_dir="./slm-eval-tmp",
            per_device_eval_batch_size=int(self.per_device_batch_size or 2),
            report_to="none",
        )
        trainer = Trainer(
            model=model,
            args=args,
            tokenizer=tokenizer,
            data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        )
        metrics = trainer.evaluate(eval_dataset=ds)
        loss = metrics.get("eval_loss")
        perplexity = float(math.exp(loss)) if isinstance(loss, (int, float)) else None
        return {"eval_loss": loss, "perplexity": perplexity, **{k: v for k, v in metrics.items() if k != "eval_loss"}}

    def _generate(self, model, tokenizer) -> pd.DataFrame:
        prompts = self._normalize_prompts()
        if not prompts:
            return pd.DataFrame(columns=["prompt", "completion"])
        try:
            import torch
        except ImportError as exc:
            raise ImportError("torch is required. Install with: pip install torch") from exc

        model.eval()
        device = next(model.parameters()).device
        rows = []
        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt").to(device)
            with torch.no_grad():
                output_ids = model.generate(
                    **inputs,
                    max_new_tokens=int(self.max_new_tokens or 128),
                    temperature=float(self.temperature or 0.7),
                    top_p=float(self.top_p or 0.9),
                    do_sample=bool(self.do_sample),
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                )
            completion = tokenizer.decode(output_ids[0], skip_special_tokens=True)
            rows.append({"prompt": prompt, "completion": completion})
        return pd.DataFrame(rows)

    def _run(self):
        model, tokenizer = self._unwrap(self.model_artifact)
        ppl = {}
        try:
            ppl = self._compute_perplexity(model, tokenizer)
        except Exception as exc:
            self.log(f"Perplexity computation failed: {exc}")
            ppl = {"error": str(exc)}

        try:
            samples_df = self._generate(model, tokenizer)
        except Exception as exc:
            self.log(f"Sample generation failed: {exc}")
            samples_df = pd.DataFrame({"error": [str(exc)]})

        self._metrics = ppl
        self._samples = samples_df
        self.log(f"SLMEvaluator: metrics={ppl}, samples={len(samples_df)}")

    def get_metrics(self) -> Data:
        try:
            if not hasattr(self, "_metrics"):
                self._run()
            return Data(data=self._metrics)
        except Exception as exc:
            self.log(f"SLMEvaluator metrics failed: {exc}")
            return Data(data={"error": str(exc)})

    def get_samples(self) -> DataFrame:
        try:
            if not hasattr(self, "_samples"):
                self._run()
            return DataFrame(self._samples)
        except Exception as exc:
            self.log(f"SLMEvaluator samples failed: {exc}")
            return DataFrame(pd.DataFrame({"error": [str(exc)]}))

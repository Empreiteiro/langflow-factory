from lfx.custom import Component
from lfx.io import (
    BoolInput,
    DataInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.schema import Data
import os


class SLMModelExporter(Component):
    display_name = "SLM Model Exporter"
    description = (
        "Exports a fine-tuned Small Language Model. Saves the model and tokenizer to a local "
        "directory, optionally merges LoRA adapters into the base weights, and can push the "
        "resulting artifact to the HuggingFace Hub."
    )
    icon = "mdi-package-variant-closed"
    name = "SLMModelExporter"

    inputs = [
        DataInput(
            name="model_artifact",
            display_name="Trained Model",
            info="Artifact produced by SLM Fine-Tuner (model + tokenizer).",
            required=True,
        ),
        StrInput(
            name="output_dir",
            display_name="Output Directory",
            info="Local directory where the exported model is written.",
            value="./slm-export",
            required=True,
        ),
        BoolInput(
            name="merge_lora",
            display_name="Merge LoRA",
            info="Merge LoRA/PEFT adapters into the base weights before saving.",
            value=True,
        ),
        BoolInput(
            name="save_safetensors",
            display_name="Save as safetensors",
            info="Use the safetensors format for weight files.",
            value=True,
        ),
        BoolInput(
            name="push_to_hub",
            display_name="Push to Hub",
            info="Upload the exported artifact to the HuggingFace Hub.",
            value=False,
        ),
        StrInput(
            name="hub_repo_id",
            display_name="Hub Repo ID",
            info="Target repository on the HuggingFace Hub (e.g. 'my-user/my-slm').",
            required=False,
        ),
        BoolInput(
            name="hub_private",
            display_name="Private Repo",
            info="Create the Hub repository as private.",
            value=True,
        ),
        SecretStrInput(
            name="hub_token",
            display_name="Hub Token",
            info="HuggingFace access token used for the upload.",
            required=False,
        ),
    ]

    outputs = [
        Output(name="export", display_name="Export Result", method="export_model"),
    ]

    def _unwrap(self):
        if self.model_artifact is None:
            raise ValueError("Trained model artifact is required.")
        data = self.model_artifact.data if hasattr(self.model_artifact, "data") else self.model_artifact
        if not isinstance(data, dict) or "model" not in data or "tokenizer" not in data:
            raise ValueError("Artifact must contain 'model' and 'tokenizer'.")
        return data["model"], data["tokenizer"]

    def _maybe_merge(self, model):
        if not self.merge_lora:
            return model, False
        if not hasattr(model, "merge_and_unload"):
            return model, False
        try:
            merged = model.merge_and_unload()
            return merged, True
        except Exception as exc:
            self.log(f"Failed to merge LoRA adapters: {exc}")
            return model, False

    def _push(self, out_dir: str):
        if not self.push_to_hub:
            return None
        repo_id = (self.hub_repo_id or "").strip()
        if not repo_id:
            raise ValueError("hub_repo_id is required when push_to_hub is enabled.")
        try:
            from huggingface_hub import HfApi, create_repo
        except ImportError as exc:
            raise ImportError(
                "huggingface_hub is required to push to the Hub. "
                "Install with: pip install huggingface_hub"
            ) from exc

        token = self.hub_token or os.environ.get("HF_TOKEN")
        create_repo(repo_id, token=token, private=bool(self.hub_private), exist_ok=True)
        api = HfApi(token=token)
        api.upload_folder(folder_path=out_dir, repo_id=repo_id, repo_type="model")
        return f"https://huggingface.co/{repo_id}"

    def export_model(self) -> Data:
        try:
            model, tokenizer = self._unwrap()
            out_dir = self.output_dir or "./slm-export"
            os.makedirs(out_dir, exist_ok=True)

            model, merged = self._maybe_merge(model)

            save_kwargs = {"safe_serialization": bool(self.save_safetensors)}
            model.save_pretrained(out_dir, **save_kwargs)
            tokenizer.save_pretrained(out_dir)

            hub_url = self._push(out_dir)

            result = {
                "output_dir": os.path.abspath(out_dir),
                "merged_lora": merged,
                "safetensors": bool(self.save_safetensors),
                "hub_url": hub_url,
            }
            self.log(f"SLMModelExporter: {result}")
            return Data(data=result)
        except Exception as exc:
            self.log(f"SLMModelExporter failed: {exc}")
            return Data(data={"error": str(exc)})

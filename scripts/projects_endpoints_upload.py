#!/usr/bin/env python3
"""
Explore the Langflow Projects upload endpoint.

Usage:
    python projects_endpoints_upload.py --file-path ./flows.zip
    python projects_endpoints_upload.py --file-path ./flows.zip --dump-dir ./project_endpoint_dump

Requirements:
    pip install requests python-dotenv
"""

import os
import json
import time
import argparse
import mimetypes
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


class ProjectsUploadEndpointExplorer:
    def __init__(self, langflow_url, langflow_token=None, timeout=60):
        self.langflow_url = langflow_url.rstrip("/")
        self.langflow_token = langflow_token
        self.timeout = timeout
        self.session = requests.Session()

        if self.langflow_token:
            self.session.headers.update({
                "x-api-key": self.langflow_token,
                "accept": "application/json"
            })

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def request_upload(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo nao encontrado: {file_path}")

        file_name = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        url = f"{self.langflow_url}/api/v1/projects/upload/"
        self.log(f"POST {url}")

        with open(file_path, "rb") as file_handle:
            files = {
                "file": (file_name, file_handle, mime_type)
            }
            start = time.monotonic()
            response = self.session.post(
                url,
                files=files,
                timeout=self.timeout
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)

        return response, elapsed_ms

    def summarize_response(self, payload, max_items=10):
        if isinstance(payload, list):
            self.log(f"Itens retornados: {len(payload)}")
            if not payload:
                return
            print("\n📋 Amostra de itens importados")
            print("=" * 60)
            for item in payload[:max_items]:
                item_id = item.get("id", "N/A")
                name = item.get("name", "N/A")
                description = item.get("description", "")
                desc_text = f" - {description}" if description else ""
                print(f"- {item_id} | {name}{desc_text}")
            if len(payload) > max_items:
                print(f"\nMostrando apenas os primeiros {max_items} itens.")
        elif isinstance(payload, dict):
            self.log("Resposta retornou um objeto.")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            self.log("Resposta inesperada: JSON nao e lista nem objeto.")

    def dump_output(self, dump_dir, response_json, meta):
        Path(dump_dir).mkdir(parents=True, exist_ok=True)
        json_path = Path(dump_dir) / "projects_upload_response.json"
        meta_path = Path(dump_dir) / "projects_upload_meta.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(response_json, f, indent=2, ensure_ascii=False)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        self.log(f"✅ Dump salvo em: {dump_dir}")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Explorar endpoint /api/v1/projects/upload/")
    parser.add_argument(
        "--file-path",
        required=True,
        help="Arquivo para upload (ex: .zip ou .json)"
    )
    parser.add_argument(
        "--langflow-url",
        default=os.getenv("LANGFLOW_URL", "http://localhost:3000"),
        help="Langflow URL (default: LANGFLOW_URL or http://localhost:3000)"
    )
    parser.add_argument(
        "--langflow-token",
        default=os.getenv("LANGFLOW_TOKEN"),
        help="Langflow API token (default: LANGFLOW_TOKEN)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout em segundos (default: 60)"
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=10,
        help="Quantidade maxima exibida no resumo (default: 10)"
    )
    parser.add_argument(
        "--show-headers",
        action="store_true",
        help="Exibe headers da resposta"
    )
    parser.add_argument(
        "--show-body",
        action="store_true",
        help="Exibe o JSON bruto da resposta"
    )
    parser.add_argument(
        "--dump-dir",
        help="Diretorio para salvar JSON e metadados da resposta"
    )

    args = parser.parse_args()

    explorer = ProjectsUploadEndpointExplorer(
        langflow_url=args.langflow_url,
        langflow_token=args.langflow_token,
        timeout=args.timeout
    )

    try:
        response, elapsed_ms = explorer.request_upload(args.file_path)
        explorer.log(f"Status: {response.status_code} | Tempo: {elapsed_ms} ms")

        if args.show_headers:
            print("\n🔎 Headers")
            print("=" * 60)
            for key, value in response.headers.items():
                print(f"{key}: {value}")

        response.raise_for_status()
        data = response.json()

        explorer.summarize_response(data, max_items=args.max_items)

        if args.show_body:
            print("\n🧾 JSON bruto")
            print("=" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False))

        if args.dump_dir:
            meta = {
                "url": response.url,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "headers": dict(response.headers),
                "file_path": args.file_path
            }
            explorer.dump_output(args.dump_dir, data, meta)

        print("\n✅ Endpoint explorado com sucesso!")

    except FileNotFoundError as e:
        explorer.log(f"❌ {e}")
        exit(1)
    except requests.exceptions.RequestException as e:
        explorer.log(f"❌ Erro na requisicao: {e}")
        if hasattr(e, "response") and e.response is not None:
            explorer.log(f"HTTP {e.response.status_code}: {e.response.text}")
        exit(1)
    except ValueError as e:
        explorer.log(f"❌ Erro ao interpretar JSON: {e}")
        exit(1)
    except Exception as e:
        explorer.log(f"❌ Erro inesperado: {e}")
        exit(1)


if __name__ == "__main__":
    main()

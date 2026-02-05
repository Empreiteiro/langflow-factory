#!/usr/bin/env python3
"""
Explore the Langflow Project detail endpoint.

Usage:
    python projects_endpoints_get.py --project-id PROJECT_ID
    python projects_endpoints_get.py --project-id PROJECT_ID --dump-dir ./project_endpoint_dump

Requirements:
    pip install requests python-dotenv
"""

import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


class ProjectEndpointExplorer:
    def __init__(self, langflow_url, langflow_token=None, timeout=30):
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

    def request_project(self, project_id):
        url = f"{self.langflow_url}/api/v1/projects/{project_id}"
        self.log(f"GET {url}")
        start = time.monotonic()
        response = self.session.get(url, timeout=self.timeout)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return response, elapsed_ms

    def summarize_project(self, project):
        if not isinstance(project, dict):
            self.log("Resposta inesperada: JSON nao e um objeto.")
            return

        # Endpoint read retorna { folder: {...}, flows: {...} }
        folder = project.get("folder")
        flows = project.get("flows")

        if isinstance(folder, dict):
            project_id = folder.get("id", "N/A")
            name = folder.get("name", "N/A")
            description = folder.get("description", "")
            parent_id = folder.get("parent_id", "N/A")

            print("\n📋 Detalhes do projeto")
            print("=" * 60)
            print(f"ID: {project_id}")
            print(f"Nome: {name}")
            if description:
                print(f"Descricao: {description}")
            print(f"Parent ID: {parent_id}")
        else:
            self.log("Aviso: campo 'folder' nao encontrado ou invalido.")

        if isinstance(flows, dict):
            items = flows.get("items", [])
            total = flows.get("total", "N/A")
            page = flows.get("page", "N/A")
            size = flows.get("size", "N/A")
            pages = flows.get("pages", "N/A")

            print("\n📦 Flows do projeto")
            print("=" * 60)
            print(f"Total: {total} | Pagina: {page} | Tamanho: {size} | Paginas: {pages}")

            if items:
                print("\n🧩 Amostra de flows")
                print("=" * 60)
                for flow in items[:10]:
                    flow_id = flow.get("id", "N/A")
                    flow_name = flow.get("name", "N/A")
                    flow_desc = flow.get("description", "")
                    desc_text = f" - {flow_desc}" if flow_desc else ""
                    print(f"- {flow_id} | {flow_name}{desc_text}")
                if len(items) > 10:
                    print("\nMostrando apenas os primeiros 10 flows.")
        elif flows is not None:
            self.log("Aviso: campo 'flows' nao encontrado ou invalido.")

    def dump_output(self, dump_dir, project_id, response_json, meta):
        Path(dump_dir).mkdir(parents=True, exist_ok=True)
        safe_id = str(project_id).replace("/", "_")
        json_path = Path(dump_dir) / f"project_{safe_id}.json"
        meta_path = Path(dump_dir) / f"project_{safe_id}_meta.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(response_json, f, indent=2, ensure_ascii=False)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        self.log(f"✅ Dump salvo em: {dump_dir}")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Explorar endpoint /api/v1/projects/{id}")
    parser.add_argument(
        "--project-id",
        required=True,
        help="ID do projeto a consultar"
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
        default=30,
        help="Timeout em segundos (default: 30)"
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

    explorer = ProjectEndpointExplorer(
        langflow_url=args.langflow_url,
        langflow_token=args.langflow_token,
        timeout=args.timeout
    )

    try:
        response, elapsed_ms = explorer.request_project(args.project_id)
        explorer.log(f"Status: {response.status_code} | Tempo: {elapsed_ms} ms")

        if args.show_headers:
            print("\n🔎 Headers")
            print("=" * 60)
            for key, value in response.headers.items():
                print(f"{key}: {value}")

        response.raise_for_status()
        data = response.json()

        explorer.summarize_project(data)

        if args.show_body:
            print("\n🧾 JSON bruto")
            print("=" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False))

        if args.dump_dir:
            meta = {
                "url": response.url,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "headers": dict(response.headers)
            }
            explorer.dump_output(args.dump_dir, args.project_id, data, meta)

        print("\n✅ Endpoint explorado com sucesso!")

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

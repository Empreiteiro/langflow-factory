#!/usr/bin/env python3
"""
Explore the Langflow Projects list endpoint.

Usage:
    python projects_endpoints_list.py
    python projects_endpoints_list.py --dump-dir ./project_endpoint_dump

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


class ProjectsListEndpointExplorer:
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

    def request_projects(self):
        url = f"{self.langflow_url}/api/v1/projects/"
        self.log(f"GET {url}")
        start = time.monotonic()
        response = self.session.get(url, timeout=self.timeout)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return response, elapsed_ms

    def summarize_projects(self, projects, max_items=20):
        if not isinstance(projects, list):
            self.log("Resposta inesperada: JSON nao e uma lista.")
            return

        self.log(f"Projetos retornados: {len(projects)}")
        if not projects:
            return

        print("\n📋 Amostra de projetos")
        print("=" * 60)
        for project in projects[:max_items]:
            project_id = project.get("id", "N/A")
            name = project.get("name", "N/A")
            description = project.get("description", "")
            desc_text = f" - {description}" if description else ""
            print(f"- {project_id} | {name}{desc_text}")

        if len(projects) > max_items:
            print(f"\nMostrando apenas os primeiros {max_items} projetos.")

    def dump_output(self, dump_dir, response_json, meta):
        Path(dump_dir).mkdir(parents=True, exist_ok=True)
        list_path = Path(dump_dir) / "projects_list.json"
        meta_path = Path(dump_dir) / "projects_list_meta.json"

        with open(list_path, "w", encoding="utf-8") as f:
            json.dump(response_json, f, indent=2, ensure_ascii=False)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        self.log(f"✅ Dump salvo em: {dump_dir}")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Explorar endpoint /api/v1/projects/")
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
        "--max-items",
        type=int,
        default=20,
        help="Quantidade maxima de projetos exibidos (default: 20)"
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

    explorer = ProjectsListEndpointExplorer(
        langflow_url=args.langflow_url,
        langflow_token=args.langflow_token,
        timeout=args.timeout
    )

    try:
        response, elapsed_ms = explorer.request_projects()
        explorer.log(f"Status: {response.status_code} | Tempo: {elapsed_ms} ms")

        if args.show_headers:
            print("\n🔎 Headers")
            print("=" * 60)
            for key, value in response.headers.items():
                print(f"{key}: {value}")

        response.raise_for_status()
        data = response.json()

        explorer.summarize_projects(data, max_items=args.max_items)

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
            explorer.dump_output(args.dump_dir, data, meta)

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

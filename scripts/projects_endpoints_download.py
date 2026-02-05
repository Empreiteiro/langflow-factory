#!/usr/bin/env python3
"""
Explore the Langflow Projects download endpoint.

Usage:
    python projects_endpoints_download.py --project-id PROJECT_ID
    python projects_endpoints_download.py --project-id PROJECT_ID --output-dir ./downloads

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


class ProjectsDownloadEndpointExplorer:
    def __init__(self, langflow_url, langflow_token=None, timeout=120):
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

    def _filename_from_headers(self, headers):
        content_disposition = headers.get("Content-Disposition", "")
        if "filename=" not in content_disposition:
            return None
        parts = content_disposition.split("filename=")
        if len(parts) < 2:
            return None
        filename = parts[1].strip().strip('"')
        return filename or None

    def request_download(self, project_id):
        url = f"{self.langflow_url}/api/v1/projects/download/{project_id}"
        self.log(f"GET {url}")
        start = time.monotonic()
        response = self.session.get(url, stream=True, timeout=self.timeout)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return response, elapsed_ms

    def save_file(self, response, output_path, overwrite=False):
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"Arquivo ja existe: {output_path}")

        total_bytes = 0
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
        return total_bytes

    def dump_meta(self, dump_dir, meta):
        Path(dump_dir).mkdir(parents=True, exist_ok=True)
        meta_path = Path(dump_dir) / "projects_download_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        self.log(f"✅ Metadados salvos em: {meta_path}")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Explorar endpoint /api/v1/projects/download/{id}")
    parser.add_argument(
        "--project-id",
        required=True,
        help="ID do projeto para download"
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
        default=120,
        help="Timeout em segundos (default: 120)"
    )
    parser.add_argument(
        "--output-dir",
        default="./project_downloads",
        help="Diretorio de saida (default: ./project_downloads)"
    )
    parser.add_argument(
        "--output-name",
        help="Nome do arquivo de saida (default: nome do header ou project_{id}_{timestamp}.zip)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescreve o arquivo se ja existir"
    )
    parser.add_argument(
        "--show-headers",
        action="store_true",
        help="Exibe headers da resposta"
    )
    parser.add_argument(
        "--dump-dir",
        help="Diretorio para salvar metadados da resposta"
    )

    args = parser.parse_args()

    explorer = ProjectsDownloadEndpointExplorer(
        langflow_url=args.langflow_url,
        langflow_token=args.langflow_token,
        timeout=args.timeout
    )

    try:
        response, elapsed_ms = explorer.request_download(args.project_id)
        explorer.log(f"Status: {response.status_code} | Tempo: {elapsed_ms} ms")

        if args.show_headers:
            print("\n🔎 Headers")
            print("=" * 60)
            for key, value in response.headers.items():
                print(f"{key}: {value}")

        response.raise_for_status()

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = args.output_name
        if not filename:
            filename = explorer._filename_from_headers(response.headers)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"project_{args.project_id}_{timestamp}.zip"

        output_path = output_dir / filename
        bytes_written = explorer.save_file(response, output_path, overwrite=args.overwrite)

        explorer.log(f"✅ Arquivo salvo: {output_path}")
        explorer.log(f"📦 Tamanho: {bytes_written} bytes")

        if args.dump_dir:
            meta = {
                "url": response.url,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "headers": dict(response.headers),
                "output_path": str(output_path)
            }
            explorer.dump_meta(args.dump_dir, meta)

        print("\n✅ Endpoint explorado com sucesso!")

    except FileExistsError as e:
        explorer.log(f"❌ {e}")
        exit(1)
    except requests.exceptions.RequestException as e:
        explorer.log(f"❌ Erro na requisicao: {e}")
        if hasattr(e, "response") and e.response is not None:
            explorer.log(f"HTTP {e.response.status_code}: {e.response.text}")
        exit(1)
    except Exception as e:
        explorer.log(f"❌ Erro inesperado: {e}")
        exit(1)


if __name__ == "__main__":
    main()

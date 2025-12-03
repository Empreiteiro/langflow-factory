from langchain_community.vectorstores import Qdrant
from langchain_core.embeddings import Embeddings

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    IntInput,
    SecretStrInput,
    StrInput,
)
from lfx.schema.data import Data


class QdrantVectorStoreComponent(LCVectorStoreComponent):
    display_name = "Qdrant"
    description = "Qdrant Vector Store with search capabilities"
    icon = "Qdrant"

    inputs = [
        StrInput(name="collection_name", display_name="Collection Name", required=True),
        StrInput(name="host", display_name="Host", value="localhost", advanced=True),
        IntInput(name="port", display_name="Port", value=6333, advanced=True),
        IntInput(name="grpc_port", display_name="gRPC Port", value=6334, advanced=True),
        SecretStrInput(name="api_key", display_name="Qdrant API Key", advanced=True),
        StrInput(name="prefix", display_name="Prefix", advanced=True),
        IntInput(name="timeout", display_name="Timeout", advanced=True),
        StrInput(name="path", display_name="Path", advanced=True),
        StrInput(name="url", display_name="URL", advanced=True),
        DropdownInput(
            name="distance_func",
            display_name="Distance Function",
            options=["Cosine", "Euclidean", "Dot Product"],
            value="Cosine",
            advanced=True,
        ),
        StrInput(name="content_payload_key", display_name="Content Payload Key", value="page_content", advanced=True),
        StrInput(name="metadata_payload_key", display_name="Metadata Payload Key", value="metadata", advanced=True),
        BoolInput(
            name="force_recreate",
            display_name="Force Recreate",
            value=False,
            advanced=True,
            info="If True, recreate the collection even if it already exists. Use this when you want to overwrite an existing collection.",
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(name="embedding", display_name="Embedding", input_types=["Embeddings"]),
        IntInput(
            name="number_of_results",
            display_name="Number of Results",
            info="Number of results to return.",
            value=4,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> Qdrant:
        qdrant_kwargs = {
            "collection_name": self.collection_name,
            "content_payload_key": self.content_payload_key,
            "metadata_payload_key": self.metadata_payload_key,
        }

        from qdrant_client import QdrantClient
        
        # If URL is provided, extract host/port for localhost to avoid SSL issues
        if self.url and self.url.strip():
            url = self.url.strip().rstrip("/")
            # If URL contains localhost, extract host/port instead
            if "localhost" in url.lower() or "127.0.0.1" in url:
                # Extract host and port from URL
                if "://" in url:
                    protocol, rest = url.split("://", 1)
                    if ":" in rest:
                        host_part, port_part = rest.split(":", 1)
                        # Remove any path after port
                        if "/" in port_part:
                            port_part = port_part.split("/")[0]
                        try:
                            port_num = int(port_part)
                            # Use host/port for server_kwargs
                            server_kwargs = {
                                "host": host_part,
                                "port": port_num,
                                "grpc_port": int(self.grpc_port),
                                "api_key": self.api_key if self.api_key else None,
                                "prefix": self.prefix if self.prefix else None,
                                "timeout": int(self.timeout) if self.timeout else None,
                            }
                        except ValueError:
                            # If port extraction fails, use URL but force HTTP
                            if url.startswith("https://"):
                                url = url.replace("https://", "http://", 1)
                            elif not url.startswith(("http://", "https://")):
                                url = f"http://{url}"
                            server_kwargs = {
                                "url": url,
                                "api_key": self.api_key if self.api_key else None,
                                "prefix": self.prefix if self.prefix else None,
                                "timeout": int(self.timeout) if self.timeout else None,
                            }
                    else:
                        # No port in URL, use default port
                        server_kwargs = {
                            "host": rest.split("/")[0] if "/" in rest else rest,
                            "port": int(self.port),
                            "grpc_port": int(self.grpc_port),
                            "api_key": self.api_key if self.api_key else None,
                            "prefix": self.prefix if self.prefix else None,
                            "timeout": int(self.timeout) if self.timeout else None,
                        }
                else:
                    # No protocol, assume localhost with default port
                    server_kwargs = {
                        "host": url.split(":")[0] if ":" in url else url.split("/")[0],
                        "port": int(url.split(":")[1].split("/")[0]) if ":" in url and "/" not in url.split(":")[1] else (int(url.split(":")[1].split("/")[0]) if ":" in url else int(self.port)),
                        "grpc_port": int(self.grpc_port),
                        "api_key": self.api_key if self.api_key else None,
                        "prefix": self.prefix if self.prefix else None,
                        "timeout": int(self.timeout) if self.timeout else None,
                    }
            else:
                # Not localhost, use URL
                if url.startswith("https://"):
                    # Keep HTTPS for non-localhost
                    server_kwargs = {
                        "url": url,
                        "api_key": self.api_key if self.api_key else None,
                        "prefix": self.prefix if self.prefix else None,
                        "timeout": int(self.timeout) if self.timeout else None,
                    }
                else:
                    # Default to HTTP if no protocol
                    if not url.startswith("http://"):
                        url = f"http://{url}"
                    server_kwargs = {
                        "url": url,
                        "api_key": self.api_key if self.api_key else None,
                        "prefix": self.prefix if self.prefix else None,
                        "timeout": int(self.timeout) if self.timeout else None,
                    }
        else:
            # Use host/port configuration - explicitly use HTTP for localhost
            host = (self.host or "localhost").strip().rstrip("/")
            # Remove any protocol from host if accidentally included
            if "://" in host:
                host = host.split("://")[-1]
            # Remove port from host if included
            if ":" in host:
                host = host.split(":")[0]
            
            server_kwargs = {
                "host": host,
                "port": int(self.port),
                "grpc_port": int(self.grpc_port),
                "api_key": self.api_key if self.api_key else None,
                "prefix": self.prefix if self.prefix else None,
                "timeout": int(self.timeout) if self.timeout else None,
                "path": self.path if self.path else None,
            }

        server_kwargs = {k: v for k, v in server_kwargs.items() if v is not None}

        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        if not isinstance(self.embedding, Embeddings):
            msg = "Invalid embedding object"
            raise TypeError(msg)

        try:
            # Add force_recreate to qdrant_kwargs if provided
            if hasattr(self, "force_recreate") and self.force_recreate:
                qdrant_kwargs["force_recreate"] = True
            
            if documents:
                # from_documents accepts connection parameters directly, not a client
                # For localhost, ensure we use host/port (not URL) to avoid SSL issues
                qdrant = Qdrant.from_documents(
                    documents, 
                    embedding=self.embedding, 
                    **qdrant_kwargs,
                    **server_kwargs
                )
            else:
                # For empty documents, create client explicitly to ensure HTTP is used
                from qdrant_client import QdrantClient
                # For localhost, explicitly disable HTTPS
                if "host" in server_kwargs and server_kwargs["host"] in ("localhost", "127.0.0.1"):
                    # Create client with explicit HTTP for localhost
                    client = QdrantClient(**server_kwargs, https=False, prefer_grpc=False)
                else:
                    client = QdrantClient(**server_kwargs)
                
                qdrant = Qdrant(embeddings=self.embedding, client=client, **qdrant_kwargs)

            return qdrant
        except ConnectionRefusedError as e:
            host = self.host or "localhost"
            port = self.port or 6333
            msg = (
                f"Connection refused to Qdrant server at {host}:{port}. "
                f"Please ensure:\n"
                f"1. Qdrant server is running (check with: docker ps or qdrant --help)\n"
                f"2. Firewall allows connections on port {port} and {self.grpc_port or 6334}\n"
                f"3. Host and port settings are correct\n"
                f"4. If using Docker, ensure the container is running: docker run -p 6333:6333 qdrant/qdrant"
            )
            raise ConnectionRefusedError(msg) from e
        except OSError as e:
            if "10061" in str(e) or "refused" in str(e).lower():
                host = self.host or "localhost"
                port = self.port or 6333
                msg = (
                    f"Connection refused to Qdrant server at {host}:{port}. "
                    f"Please ensure:\n"
                    f"1. Qdrant server is running\n"
                    f"2. Firewall allows connections on port {port} and {self.grpc_port or 6334}\n"
                    f"3. Host and port settings are correct"
                )
                raise ConnectionRefusedError(msg) from e
            raise
        except Exception as e:
            error_str = str(e).lower()
            # Handle SSL errors - usually means trying HTTPS on HTTP server
            if "ssl" in error_str or "wrong_version_number" in error_str or "tls" in error_str:
                url_info = self.url or f"{self.host or 'localhost'}:{self.port or 6333}"
                msg = (
                    f"SSL/TLS error connecting to Qdrant. This usually means:\n"
                    f"1. The server is running on HTTP but client is trying HTTPS\n"
                    f"2. If using 'url' field, ensure it starts with 'http://' (not 'https://')\n"
                    f"3. Example: Use 'http://localhost:6333' instead of 'https://localhost:6333'\n"
                    f"Current connection: {url_info}"
                )
                raise ValueError(msg) from e
            raise

    def search_documents(self) -> list[Data]:
        try:
            vector_store = self.build_vector_store()

            if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
                docs = vector_store.similarity_search(
                    query=self.search_query,
                    k=self.number_of_results,
                )

                data = docs_to_data(docs)
                self.status = data
                return data
            return []
        except ConnectionRefusedError:
            # Re-raise connection errors with better context
            raise
        except Exception as e:
            # Wrap other errors for better debugging
            raise RuntimeError(f"Error searching documents in Qdrant: {e}") from e

from typing import Any, List, Optional

from langchain_core.documents import Document

from langflow.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from langflow.io import (
    StrInput,
    IntInput,
    BoolInput,
    MessageTextInput,
    HandleInput,
    Output,
)
from langflow.schema import Data
from langflow.serialization import serialize


class IBMDB2VectorStoreComponent(LCVectorStoreComponent):
    """
    Langflow component to connect to IBM's Vector Store exposed via the
    `langchain_db2` package.

    Notes:
    - This component intentionally keeps the creation and usage generic so it
      will work with the common LangChain-style VectorStore API (methods such
      as `from_existing_index`, `add_texts`, `similarity_search`, etc.).
    - If the `langchain_db2` API differs in method names, you can override the
      small sections guarded by try/except to adapt to the real package.
    """

    display_name = "IBM DB2 Vector Store"
    description = "Connect to IBM's DB2/Vector Store via the `langchain_db2` package and run similarity searches or add documents."
    icon = "database"
    name = "IBMDB2VectorStore"
    beta = True
    field_order = [
        "api_key",
        "url",
        "instance_id",
        "index_name",
        "embedding_model",
        "use_ssl",
        "top_k",
    ]

    inputs = [
        StrInput(
            name="api_key",
            display_name="API Key",
            info="API key for authenticating to the IBM vector service (if required).",
            required=False,
        ),
        StrInput(
            name="url",
            display_name="Service URL",
            info="Base URL for the IBM vector service (e.g., https://api.ibm.com/...).",
            required=False,
        ),
        StrInput(
            name="instance_id",
            display_name="Instance ID / Project",
            info="Instance or project identifier used by the service (if applicable).",
            required=False,
        ),
        StrInput(
            name="index_name",
            display_name="Index / Collection Name",
            info="Name of the index / collection to use or create in the vector store.",
            required=True,
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding_model",
            display_name="Embeddings Model",
            input_types=["Embeddings"],
            required=False,
        ),
        BoolInput(
            name="use_ssl",
            display_name="Use SSL/TLS",
            info="Whether to use SSL/TLS when connecting to the service.",
            value=True,
            advanced=True,
        ),
        IntInput(
            name="top_k",
            display_name="Top K",
            info="Number of nearest neighbors to return on searches.",
            value=4,
            advanced=True,
        ),
        MessageTextInput(
            name="search_query",
            display_name="Search Query",
            info="Text query to search the vector store (used by the `search` output).",
            required=False,
        ),
    ]

    outputs = [
        Output(name="vectorstore", display_name="Vector Store Handle", method="vectorstore_handle"),
        Output(name="search_results", display_name="Search Results", method="search_documents"),
        Output(name="add_documents_done", display_name="Add Documents Result", method="add_documents_output"),
    ]

    @check_cached_vector_store
    def build_vector_store(self):
        """Create/connect to the IBM vector store using langchain_db2.

        The implementation tries several common LangChain-style factory methods
        such as `from_existing_index` or a client constructor. If the real
        `langchain_db2` package uses different names, adapt the small blocks
        guarded by try/except accordingly.
        """
        try:
            import langchain_db2 as db2
        except Exception as e:
            self.status = "`langchain_db2` not installed or failed to import."
            self.log(f"Import error: {e!s}")
            self.vectorstore = None
            return

        # gather params
        api_key = getattr(self, "api_key", None)
        url = getattr(self, "url", None)
        instance_id = getattr(self, "instance_id", None)
        index_name = getattr(self, "index_name", None)
        use_ssl = getattr(self, "use_ssl", True)
        embedding_model = getattr(self, "embedding_model", None)

        # If the user provided an embeddings model (from another Langflow
        # component), prefer to use it. Otherwise try to let the vectorstore
        # create/expect embeddings itself.
        embeddings = None
        if embedding_model is not None:
            embeddings = embedding_model

        # Try common connection patterns. Adapt if the real package differs.
        vs = None
        try:
            # Common LangChain pattern: from_existing_index or from_client
            if hasattr(db2, "DB2VectorStore"):
                # hypothetical wrapper class
                VS = getattr(db2, "DB2VectorStore")
                try:
                    if embeddings is not None and hasattr(VS, "from_existing_index"):
                        vs = VS.from_existing_index(
                            index_name=index_name,
                            embeddings=embeddings,
                            api_key=api_key,
                            url=url,
                            instance_id=instance_id,
                            use_ssl=use_ssl,
                        )
                    elif hasattr(VS, "from_index"):
                        vs = VS.from_index(
                            index_name=index_name,
                            embeddings=embeddings,
                            api_key=api_key,
                            url=url,
                            instance_id=instance_id,
                            use_ssl=use_ssl,
                        )
                except Exception:
                    # try a direct constructor fallback
                    try:
                        vs = VS(
                            index_name=index_name,
                            embeddings=embeddings,
                            api_key=api_key,
                            url=url,
                            instance_id=instance_id,
                            use_ssl=use_ssl,
                        )
                    except Exception as e:
                        self.log(f"Failed to create DB2VectorStore via VS class: {e!s}")

            # Another common pattern: package exposes `DB2` or `DB2Client` factory
            if vs is None and hasattr(db2, "DB2"):
                DB2 = getattr(db2, "DB2")
                try:
                    vs = DB2(
                        api_key=api_key,
                        url=url,
                        instance_id=instance_id,
                        index_name=index_name,
                        embeddings=embeddings,
                        use_ssl=use_ssl,
                    )
                except Exception:
                    try:
                        # maybe there is a `from_existing_index`
                        vs = DB2.from_existing_index(index_name=index_name, embeddings=embeddings)
                    except Exception as e:
                        self.log(f"DB2 factory attempts failed: {e!s}")

            # Last fallback: try a generic factory function from the package
            if vs is None and hasattr(db2, "from_existing_index"):
                try:
                    vs = db2.from_existing_index(
                        index_name=index_name,
                        embeddings=embeddings,
                        api_key=api_key,
                        url=url,
                        instance_id=instance_id,
                        use_ssl=use_ssl,
                    )
                except Exception as e:
                    self.log(f"langchain_db2.from_existing_index failed: {e!s}")

            # If we still don't have a vectorstore, try to create an empty client
            if vs is None:
                # many vectorstores expose a low-level client or `Client` class
                client_candidate = None
                for name in ("Client", "DB2Client", "db2_client"):
                    if hasattr(db2, name):
                        client_candidate = getattr(db2, name)
                        break
                if client_candidate is not None:
                    try:
                        client = client_candidate(api_key=api_key, url=url, instance_id=instance_id, use_ssl=use_ssl)
                        # Some clients expose a method to get a LangChain-compatible vectorstore
                        if hasattr(client, "get_vectorstore"):
                            vs = client.get_vectorstore(index_name=index_name, embeddings=embeddings)
                    except Exception as e:
                        self.log(f"Client-based creation failed: {e!s}")

            if vs is None:
                msg = (
                    "Could not create a vectorstore instance from `langchain_db2`."
                    " Check that the package is installed and adapt factory calls if needed."
                )
                raise ValueError(msg)

            # Add documents to the vector store
            self._add_documents_to_vector_store(vs)
            
            return vs

        except Exception as e:
            msg = f"Error when creating vector store: {e!s}"
            raise ValueError(msg) from e

    def vectorstore_handle(self) -> Data:
        """Return the underlying vectorstore handle (wrapped as Data)."""
        vector_store = self.build_vector_store()
        if vector_store is None:
            return Data(text="", data={"error": "No vectorstore created."})
        return Data(data={"vectorstore": vector_store})

    def _add_documents_to_vector_store(self, vector_store) -> None:
        """Add documents to the Vector Store, similar to Astra DB implementation."""
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                msg = "Vector Store Inputs must be Data objects."
                raise TypeError(msg)

        # Apply same serialization as Astra DB
        documents = [
            Document(page_content=doc.page_content, metadata=serialize(doc.metadata, to_str=True)) 
            for doc in documents
        ]

        if documents:
            self.log(f"Adding {len(documents)} documents to the Vector Store.")
            try:
                vector_store.add_documents(documents)
            except Exception as e:
                msg = f"Error adding documents to IBM DB2 Vector Store: {e}"
                raise ValueError(msg) from e
        else:
            self.log("No documents to add to the Vector Store.")

    def search_documents(self, vector_store=None) -> List[Data]:
        """Run a similarity search against the connected vectorstore.

        Returns a list of `Data` objects where each contains a search result.
        """
        vector_store = vector_store or self.build_vector_store()

        query = getattr(self, "search_query", None)
        top_k = int(getattr(self, "top_k", 4) or 4)

        if not query:
            self.log("No query provided to search_documents.")
            return []

        try:
            # Common method name in LangChain-style vectorstores
            if hasattr(vector_store, "similarity_search"):
                results = vector_store.similarity_search(query, k=top_k)
            elif hasattr(vector_store, "search"):
                results = vector_store.search(query, top_k=top_k)
            else:
                # try a low-level client call
                if hasattr(vector_store, "query"):
                    results = vector_store.query(query, k=top_k)
                else:
                    raise AttributeError("Vectorstore has no known search method.")

            from langflow.helpers.data import docs_to_data
            data = docs_to_data(results)
            self.status = data
            return data

        except Exception as e:
            msg = f"Error performing search in IBM DB2 Vector Store: {e}"
            self.log(msg)
            raise ValueError(msg) from e

    def add_documents_output(self) -> Data:
        """Add documents supplied in the `ingest_data` input to the index.

        Returns a Data object summarizing the result.
        """
        try:
            vector_store = self.build_vector_store()
            msg = f"Added documents to index {getattr(self, 'index_name', None)}."
            self.log(msg)
            return Data(text=msg, data={"added": "success"})
        except Exception as e:
            msg = f"Error adding documents to IBM DB2 Vector Store: {e}"
            self.log(msg)
            return Data(text="", data={"error": str(e)})

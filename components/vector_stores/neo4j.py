from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import StrInput, SecretStrInput, IntInput, DropdownInput, FloatInput, HandleInput
from lfx.schema.data import Data
from lfx.log import logger


def normalize_neo4j_uri(uri: str) -> str:
    """
    Normalize Neo4j URI to use a supported scheme.
    
    Supported schemes: bolt, bolt+ssc, bolt+s, neo4j, neo4j+ssc, neo4j+s
    
    Converts:
    - https:// -> neo4j+s:// (secure connection, typically for Aura)
    - http:// -> bolt:// (non-secure connection, typically for local)
    """
    if not uri:
        raise ValueError("Neo4j URI cannot be empty")
    
    uri = uri.strip()
    
    # Valid Neo4j URI schemes
    valid_schemes = ['bolt', 'bolt+ssc', 'bolt+s', 'neo4j', 'neo4j+ssc', 'neo4j+s']
    
    # Check if URI already has a valid scheme
    for scheme in valid_schemes:
        if uri.startswith(f"{scheme}://"):
            return uri
    
    # Convert HTTP/HTTPS to appropriate Neo4j schemes
    if uri.startswith("https://"):
        # Convert https:// to neo4j+s:// for secure connections (Aura)
        uri = uri.replace("https://", "neo4j+s://", 1)
        logger.debug(f"Converted https:// to neo4j+s:// in URI")
    elif uri.startswith("http://"):
        # Convert http:// to bolt:// for non-secure connections (local)
        uri = uri.replace("http://", "bolt://", 1)
        logger.debug(f"Converted http:// to bolt:// in URI")
    else:
        # No scheme provided, assume bolt:// for localhost or neo4j+s:// for remote
        if "localhost" in uri or "127.0.0.1" in uri:
            uri = f"bolt://{uri}"
            logger.debug(f"Added bolt:// scheme for localhost URI")
        else:
            # For remote hosts, default to neo4j+s:// (secure)
            uri = f"neo4j+s://{uri}"
            logger.debug(f"Added neo4j+s:// scheme for remote URI")
    
    return uri


class Neo4jVectorStoreComponent(LCVectorStoreComponent):
    display_name: str = "Neo4j"
    description: str = "Implementation of Vector Store using Neo4j with search capabilities"
    documentation: str = "https://neo4j.com/docs/"
    name = "Neo4j"
    icon: str = "Neo4j"

    inputs = [
        StrInput(
            name="uri",
            display_name="Neo4j URI",
            info="URI for the Neo4j service (e.g., bolt://localhost:7687 or neo4j+s://xxx.databases.neo4j.io).",
            required=True,
        ),
        StrInput(
            name="username",
            display_name="Neo4j Username",
            info="Authentication username for accessing Neo4j.",
            required=True,
        ),
        SecretStrInput(
            name="password",
            display_name="Neo4j Password",
            info="Authentication password for accessing Neo4j.",
            required=True,
        ),
        StrInput(
            name="database_name",
            display_name="Database Name",
            info="The name of the Neo4j database (default: 'neo4j').",
            value="neo4j",
            advanced=True,
        ),
        StrInput(
            name="index_name",
            display_name="Index Name",
            info="The name of the vector index in Neo4j. Required when connecting to an existing index.",
            value="vector",
            advanced=True,
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name="Embedding",
            input_types=["Embeddings"],
            required=True,
        ),
        IntInput(
            name="number_of_results",
            display_name="Number of Results",
            info="Number of results to return.",
            advanced=True,
            value=4,
        ),
        DropdownInput(
            name="search_type",
            display_name="Search Type",
            info="Search type to use",
            options=["Similarity", "Similarity with score threshold", "MMR (Max Marginal Relevance)"],
            value="Similarity",
            advanced=True,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name="Search Score Threshold",
            info="Minimum similarity score threshold for search results. (when using 'Similarity with score threshold')",
            value=0,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self):
        """Build and return a Neo4j vector store instance."""
        try:
            from langchain_community.vectorstores import Neo4jVector
        except ImportError:
            raise ImportError(
                "Could not import langchain_community.vectorstores.Neo4jVector. "
                "Please install it with `pip install langchain-community neo4j`."
            )

        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        def flatten_metadata(value, max_depth=10, current_depth=0):
            """
            Flatten metadata values to ensure Neo4j compatibility.
            Neo4j only accepts primitive types (str, int, float, bool) or arrays of primitives.
            Nested dicts are either flattened (with key prefixes) or converted to JSON strings.
            """
            if current_depth >= max_depth:
                # Prevent infinite recursion, convert to string
                return str(value)
            
            # Handle None
            if value is None:
                return None
            
            # Handle primitive types (Neo4j compatible)
            if isinstance(value, (str, int, float, bool)):
                return value
            
            # Handle lists - recursively process each item
            if isinstance(value, list):
                flattened_list = []
                for item in value:
                    flattened_item = flatten_metadata(item, max_depth, current_depth + 1)
                    # Only add if it's a primitive type
                    if isinstance(flattened_item, (str, int, float, bool, type(None))):
                        flattened_list.append(flattened_item)
                    else:
                        # Convert complex types to string
                        flattened_list.append(str(flattened_item))
                return flattened_list
            
            # Handle dicts - flatten with key prefixes or convert to JSON string
            if isinstance(value, dict):
                # If dict is too complex or has nested dicts, convert to JSON string
                has_nested_dicts = any(isinstance(v, dict) for v in value.values())
                if has_nested_dicts or len(value) > 5:
                    # Convert to JSON string for complex nested structures
                    import json
                    try:
                        return json.dumps(value, default=str)
                    except (TypeError, ValueError):
                        return str(value)
                else:
                    # Flatten simple dicts with key prefixes
                    flattened = {}
                    for k, v in value.items():
                        flat_key = str(k)
                        flat_value = flatten_metadata(v, max_depth, current_depth + 1)
                        # Only add if value is primitive
                        if isinstance(flat_value, (str, int, float, bool, type(None), list)):
                            flattened[flat_key] = flat_value
                        else:
                            flattened[flat_key] = str(flat_value)
                    return flattened
            
            # Handle Properties objects
            if hasattr(value, '__class__') and 'Properties' in str(type(value)):
                try:
                    if hasattr(value, 'model_dump'):
                        dict_value = value.model_dump()
                    elif hasattr(value, 'dict'):
                        dict_value = value.dict()
                    elif hasattr(value, '__dict__'):
                        dict_value = dict(value.__dict__)
                    else:
                        return str(value)
                    # Recursively flatten the dict
                    return flatten_metadata(dict_value, max_depth, current_depth + 1)
                except (TypeError, ValueError, AttributeError):
                    return str(value)
            
            # Convert all other types to string
            return str(value)

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                doc = _input.to_lc_document()
                # Clean and flatten metadata to ensure Neo4j compatibility
                if hasattr(doc, 'metadata') and doc.metadata:
                    clean_metadata = {}
                    for key, value in doc.metadata.items():
                        # Flatten the value to ensure it's Neo4j-compatible
                        flattened_value = flatten_metadata(value)
                        # Neo4j property keys must be strings
                        clean_key = str(key)
                        # Only add if value is a valid Neo4j type
                        if isinstance(flattened_value, (str, int, float, bool, type(None), list)):
                            clean_metadata[clean_key] = flattened_value
                        else:
                            # Convert to string as last resort
                            clean_metadata[clean_key] = str(flattened_value)
                    doc.metadata = clean_metadata
                documents.append(doc)
            else:
                documents.append(_input)

        # Normalize and validate Neo4j URI
        connection_url = normalize_neo4j_uri(self.uri)
        logger.debug(f"Using Neo4j URI: {connection_url}")

        if documents:
            neo4j_vector = Neo4jVector.from_documents(
                documents=documents,
                embedding=self.embedding,
                url=connection_url,
                username=self.username,
                password=self.password,
                database=self.database_name,
            )
        else:
            neo4j_vector = Neo4jVector.from_existing_index(
                embedding=self.embedding,
                url=connection_url,
                username=self.username,
                password=self.password,
                database=self.database_name,
                index_name=self.index_name,
            )

        return neo4j_vector

    def search_documents(self) -> list[Data]:
        vector_store = self.build_vector_store()

        if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
            try:
                if self.search_type == "Similarity with score threshold":
                    docs_with_scores = vector_store.similarity_search_with_score(
                        query=self.search_query,
                        k=self.number_of_results,
                    )
                    # Filter by score threshold (lower score = more similar in cosine similarity)
                    # For Neo4j, we typically want scores >= threshold
                    docs = [doc for doc, score in docs_with_scores if score >= self.search_score_threshold]
                elif self.search_type == "MMR (Max Marginal Relevance)":
                    docs = vector_store.max_marginal_relevance_search(
                        query=self.search_query,
                        k=self.number_of_results,
                    )
                else:
                    docs = vector_store.similarity_search(
                        query=self.search_query,
                        k=self.number_of_results,
                    )

                data = docs_to_data(docs)
                self.status = data
                return data
            except Exception as e:
                raise ValueError(f"Error performing search in Neo4j: {str(e)}") from e
        else:
            logger.debug("No search query provided. Skipping search.")
            return []

    def get_retriever_kwargs(self):
        """Get retriever kwargs for LangChain retriever."""
        search_kwargs = {
            "k": self.number_of_results,
        }

        if self.search_type == "Similarity with score threshold":
            search_kwargs["score_threshold"] = self.search_score_threshold

        return {
            "search_type": self._map_search_type(),
            "search_kwargs": search_kwargs,
        }

    def _map_search_type(self):
        """Map search type to LangChain search type."""
        if self.search_type == "Similarity with score threshold":
            return "similarity_score_threshold"
        elif self.search_type == "MMR (Max Marginal Relevance)":
            return "mmr"
        else:
            return "similarity"
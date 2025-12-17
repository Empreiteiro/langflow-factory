from lfx.custom.custom_component.component import Component
from lfx.io import StrInput, SecretStrInput, MultilineInput, Output, DropdownInput, BoolInput
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


class Neo4jGraphComponent(Component):
    display_name: str = "Neo4j Graph"
    description: str = "Connect to Neo4j graph database and execute Cypher queries"
    name = "Neo4jGraph"
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
        DropdownInput(
            name="operation_mode",
            display_name="Operation Mode",
            info="Select whether to execute a query (read) or ingest data (write).",
            options=["Query", "Ingest"],
            value="Query",
            advanced=False,
        ),
        MultilineInput(
            name="cypher_query",
            display_name="Cypher Query",
            info="Cypher query to execute against the Neo4j graph database. For ingestion, use CREATE statements.",
            required=True,
        ),
        BoolInput(
            name="clear_before_ingest",
            display_name="Clear Database Before Ingest",
            info="If enabled, will delete all nodes and relationships before ingestion (use with caution!).",
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="batch_ingest",
            display_name="Batch Ingest",
            info="If enabled, will execute multiple statements in a single transaction for better performance.",
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Query Result", method="execute_query"),
    ]

    def execute_query(self) -> Data:
        """Execute a Cypher query against Neo4j and return results."""
        if self.operation_mode == "Ingest":
            return self._ingest_data()
        else:
            return self._execute_read_query()

    def _ingest_data(self) -> Data:
        """Ingest data into Neo4j graph database."""
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError(
                "Could not import neo4j driver. "
                "Please install it with `pip install neo4j`."
            )

        if not self.cypher_query or not self.cypher_query.strip():
            raise ValueError("Cypher query cannot be empty")

        # Normalize and validate Neo4j URI
        connection_url = normalize_neo4j_uri(self.uri)
        logger.debug(f"Using Neo4j URI: {connection_url}")

        try:
            # Create Neo4j driver connection
            driver = GraphDatabase.driver(connection_url, auth=(self.username, self.password))

            try:
                # Clear database if requested
                if self.clear_before_ingest:
                    logger.info("Clearing database before ingestion...")
                    with driver.session(database=self.database_name) as session:
                        session.run("MATCH (n) DETACH DELETE n")
                    logger.info("Database cleared successfully")

                # Process the query
                query = self.cypher_query.strip()
                logger.debug(f"Ingesting data with query: {query[:100]}...")

                # Split query into statements if it contains multiple statements
                statements = []
                if ';' in query:
                    # Split by semicolon, but be careful with semicolons in strings
                    parts = query.split(';')
                    current_statement = ""
                    for part in parts:
                        current_statement += part
                        # Simple check: if we have balanced quotes, it's a complete statement
                        if current_statement.count("'") % 2 == 0 and current_statement.count('"') % 2 == 0:
                            stmt = current_statement.strip()
                            if stmt:
                                statements.append(stmt)
                            current_statement = ""
                    # Add remaining if any
                    if current_statement.strip():
                        statements.append(current_statement.strip())
                else:
                    statements = [query]

                logger.info(f"Executing {len(statements)} statement(s) for ingestion")

                # Execute statements
                with driver.session(database=self.database_name) as session:
                    if self.batch_ingest and len(statements) > 1:
                        # Execute all statements in a single transaction
                        logger.debug("Executing statements in batch transaction")
                        with session.begin_transaction() as tx:
                            for i, statement in enumerate(statements):
                                logger.debug(f"Executing statement {i+1}/{len(statements)}: {statement[:50]}...")
                                tx.run(statement)
                            tx.commit()
                        logger.info("Batch ingestion completed successfully")
                    else:
                        # Execute statements individually
                        for i, statement in enumerate(statements):
                            logger.debug(f"Executing statement {i+1}/{len(statements)}: {statement[:50]}...")
                            session.run(statement)

                # Get statistics about what was created
                with driver.session(database=self.database_name) as session:
                    # Count nodes
                    node_result = session.run("MATCH (n) RETURN count(n) as count")
                    node_count = node_result.single()["count"]
                    
                    # Count relationships
                    rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                    rel_count = rel_result.single()["count"]

                self.status = f"Ingestion completed successfully. Created {node_count} nodes and {rel_count} relationships."
                
                output_data = {
                    "status": "success",
                    "nodes_created": node_count,
                    "relationships_created": rel_count,
                    "statements_executed": len(statements)
                }

                return Data(data=output_data)

            finally:
                driver.close()

        except Exception as e:
            error_msg = f"Error ingesting data into Neo4j: {str(e)}"
            logger.error(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _execute_read_query(self) -> Data:
        """Execute a read query against Neo4j and return results."""
        try:
            from langchain_community.graphs import Neo4jGraph
        except ImportError:
            raise ImportError(
                "Could not import langchain_community.graphs.Neo4jGraph. "
                "Please install it with `pip install langchain-community neo4j`."
            )

        if not self.cypher_query or not self.cypher_query.strip():
            raise ValueError("Cypher query cannot be empty")

        # Normalize and validate Neo4j URI
        connection_url = normalize_neo4j_uri(self.uri)
        logger.debug(f"Using Neo4j URI: {connection_url}")

        try:
            # Create Neo4j graph connection
            graph = Neo4jGraph(
                url=connection_url,
                username=self.username,
                password=self.password,
                database=self.database_name,
            )

            # Execute the Cypher query
            query = self.cypher_query.strip()
            logger.debug(f"Executing Cypher query: {query[:100]}...")
            
            # Check if query contains multiple statements (separated by semicolons)
            if query.count(';') > 1 and not query.strip().endswith(';'):
                # Multiple statements - execute each one
                statements = [s.strip() for s in query.split(';') if s.strip()]
                results = []
                for i, statement in enumerate(statements):
                    if statement:
                        logger.debug(f"Executing statement {i+1}/{len(statements)}: {statement[:50]}...")
                        result = graph.query(statement)
                        if result:
                            results.extend(result if isinstance(result, list) else [result])
                result = results
            else:
                # Single statement
                result = graph.query(query)

            # Convert result to a format suitable for Data output
            # Data expects a dict, so we wrap lists in a dict
            if isinstance(result, list):
                if not result:
                    # Empty result - return as dict with empty list
                    output_data = {"results": []}
                elif isinstance(result[0], dict):
                    # List of dicts - wrap in a dict
                    output_data = {"results": result}
                else:
                    # Convert other types to dicts first
                    converted_results = []
                    for record in result:
                        if hasattr(record, 'keys') and hasattr(record, 'values'):
                            converted_results.append({key: value for key, value in zip(record.keys(), record.values())})
                        elif hasattr(record, '__dict__'):
                            converted_results.append(dict(record.__dict__))
                        else:
                            converted_results.append({"value": record})
                    output_data = {"results": converted_results}
            elif isinstance(result, dict):
                # Single dict result - already in correct format
                output_data = result
            else:
                # Convert other types to string representation
                output_data = {"result": str(result)}

            result_count = len(output_data.get("results", [])) if isinstance(output_data, dict) and "results" in output_data else (1 if isinstance(output_data, dict) else 0)
            self.status = f"Query executed successfully. Returned {result_count} result(s)."
            return Data(data=output_data)

        except Exception as e:
            error_msg = f"Error executing Cypher query in Neo4j: {str(e)}"
            logger.error(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e


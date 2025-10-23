from langflow.custom import Component
from langflow.io import Output, StrInput
from langflow.schema import Data 


class IBMDB2Connection(Component):
    """
    IBM DB2 Database Connection Component.
    
    Establishes a connection to an IBM DB2 database and tests connectivity.
    """

    display_name = "IBM DB2 Connection"
    description = "Connect to IBM DB2 database using connection parameters"
    icon = "database"
    name = "IBMDB2Connection"

    inputs = [
        StrInput(
            name="connection_string",
            display_name="Connection String",
            required=True,
            info="IBM DB2 connection string. Example: database=sample;hostname=db2ai1.fyre.ibm.com;port=50000;protocol=tcpip;uid=db2inst1;pwd=yourpassword",
        ),
    ]

    outputs = [
        Output(
            name="connection_data",
            display_name="Connection Data",
            method="connect_to_db"
        ),
    ]

    def connect_to_db(self) -> Data:
        """
        Establishes connection to IBM DB2 database.
        
        Returns:
            Data: Connection status information
        """
        try:
            # Import IBM DB2 libraries
            import ibm_db
            import ibm_db_dbi
            
            self.log("Attempting to connect to IBM DB2...")
            
            # Use the connection string directly
            conn_str = self.connection_string
            
            # Log connection attempt (mask password for security)
            import re
            safe_conn_str = re.sub(r'pwd=[^;]*', 'pwd=***', conn_str, flags=re.IGNORECASE)
            self.log(f"Connection string: {safe_conn_str}")
            
            # Attempt connection
            connection = ibm_db_dbi.connect(conn_str, '', '')
            
            # Connection successful
            success_message = "Connection successful!"
            
            self.log(success_message)
            self.status = success_message
            
            # Close the connection
            connection.close()
            self.log("Connection closed.")
            
            # Return success data
            result_data = Data(
                data={
                    "status": "success",
                    "message": success_message,
                    "connection_string": safe_conn_str
                }
            )
            
            return result_data
            
        except ImportError as e:
            error_message = (
                "IBM DB2 libraries not found. "
                "Please install them with: pip install ibm-db ibm-db-dbi"
            )
            self.log(f"Import error: {e}")
            self.log(error_message)
            self.status = error_message
            
            return Data(
                data={
                    "status": "error",
                    "message": error_message,
                    "error_type": "ImportError",
                    "error_details": str(e)
                }
            )
            
        except Exception as e:
            error_message = f"Connection failed: {str(e)}"
            self.log(error_message)
            self.status = error_message
            
            return Data(
                data={
                    "status": "error",
                    "message": error_message,
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                }
            )


import pandas as pd
from .base_connector import BaseConnector
from .config import DBConfig
from .logger import logger

try:
    import trino
except Exception as e:  # pragma: no cover
    trino = None
    _import_error = e


class TrinoConnector(BaseConnector):
    """
    Connect to Trino and execute SQL queries.
    """

    connection = None

    def __init__(self, config: DBConfig):
        """
        Initialize the TrinoConnector with connection parameters.

        Parameters:
            config (DBConfig): Configuration object containing connection parameters.
        """
        self.host = config["host"]
        self.port = config["port"] or 8080
        self.user = config.get("user") or "anonymous"
        self.password = config.get("password")
        self.database = config.get("database")  # e.g., catalog.schema
        self.extra = config.get("extra") or {}
        self.http_scheme = self.extra.get("http_scheme", "http")
        self.catalog = self.extra.get("catalog")
        self.schema = self.extra.get("schema")

        # If database given as "catalog.schema", split into fields
        if self.database and (not self.catalog or not self.schema):
            if "." in self.database:
                db_catalog, db_schema = self.database.split(".", 1)
                self.catalog = self.catalog or db_catalog
                self.schema = self.schema or db_schema

        self.connect()

    def connect(self) -> None:
        """
        Establish a connection to the Trino cluster.
        """
        if trino is None:
            logger.error(f"Failed to import trino driver: {_import_error}")
            raise _import_error

        try:
            auth = None
            if self.password:
                # If HTTP, ignore password to avoid insecure auth error
                if self.http_scheme == "http":
                    logger.warning(
                        "Password provided for HTTP; ignoring password. "
                        "Set TRINO_HTTP_SCHEME=https to enable password authentication."
                    )
                else:
                    # Basic auth over HTTPS
                    auth = trino.auth.BasicAuthentication(self.user, self.password)

            self.connection = trino.dbapi.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                http_scheme=self.http_scheme,
                catalog=self.catalog,
                schema=self.schema,
                auth=auth,
                # Optional: session properties
                # session_properties={}
            )
            logger.info("Successfully connected to Trino.")
        except Exception as e:
            logger.error(f"Failed to connect to Trino: {e}")
            raise

    def run_sql(self, sql: str) -> pd.DataFrame:
        """
        Execute a SQL query and return the result as a pandas DataFrame.

        Parameters:
            sql (str): SQL query string to be executed.

        Returns:
            pd.DataFrame: Result of the SQL query as a pandas DataFrame.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            rows = cursor.fetchall() if cursor.description else []
            return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            logger.error(f"Failed to execute SQL query on Trino: {e}")
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def close(self) -> None:
        """
        Close the connection to the Trino cluster.
        """
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            logger.info("Connection to Trino closed.")
        self.connection = None

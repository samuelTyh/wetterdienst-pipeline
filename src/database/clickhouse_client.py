"""ClickHouse client wrapper for database operations."""

from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from src.config import settings


class ClickHouseClient:
    """ClickHouse database client with connection management."""

    def __init__(self):
        """Initialize ClickHouse client."""
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        """Get or create ClickHouse client connection.

        Returns:
            Active ClickHouse client instance
        """
        if self._client is None:
            self._client = clickhouse_connect.get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
                # Note: Don't set database here - we use multiple databases (raw, staging)
                connect_timeout=10,
                send_receive_timeout=30,
            )
        return self._client

    def execute(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a query and return results.

        Args:
            query: SQL query to execute
            parameters: Optional query parameters

        Returns:
            Query result
        """
        return self.client.query(query, parameters=parameters)

    def command(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        """Execute a command without returning results.

        Args:
            query: SQL command to execute
            parameters: Optional query parameters
        """
        self.client.command(query, parameters=parameters)

    def insert(
        self,
        table: str,
        data: list[list[Any]],
        column_names: list[str] | None = None,
    ) -> None:
        """Insert data into a table.

        Args:
            table: Table name (e.g., 'raw.postal_codes')
            data: List of rows to insert
            column_names: Optional list of column names
        """
        self.client.insert(table, data, column_names=column_names)

    def insert_df(self, table: str, df: Any) -> None:
        """Insert pandas DataFrame into a table.

        Args:
            table: Table name (e.g., 'raw.postal_codes')
            df: Pandas DataFrame to insert
        """
        self.client.insert_df(table, df)

    def query_df(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute query and return results as pandas DataFrame.

        Args:
            query: SQL query to execute
            parameters: Optional query parameters

        Returns:
            Pandas DataFrame with query results
        """
        return self.client.query_df(query, parameters=parameters)

    def close(self) -> None:
        """Close the database connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global client instance
_client: ClickHouseClient | None = None


def get_client() -> ClickHouseClient:
    """Get global ClickHouse client instance.

    Returns:
        Global ClickHouse client
    """
    global _client
    if _client is None:
        _client = ClickHouseClient()
    return _client

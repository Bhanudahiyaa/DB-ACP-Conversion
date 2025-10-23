import sqlite3
import logging
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from .config import get_config

logger = logging.getLogger(__name__)

class RetailerDatabaseManager:
    """Manages retailer database connections and schema creation."""

    def __init__(self):
        self.config = get_config()
        self.db_path = self.config["RETAILER_DB_URL"].replace("sqlite:///", "")
        self.tables_created = set()

    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self, schema: Dict[str, List[Dict[str, Any]]]) -> None:
        """Initialize database with tables based on supplier schema."""
        with self.get_connection() as conn:
            for table_name, columns in schema.items():
                if table_name in self.tables_created:
                    continue
                self._create_table(conn, table_name, columns)
                self.tables_created.add(table_name)
        logger.info(f"Database initialized with {len(schema)} tables")

    def _create_table(self, conn, table_name: str, columns: List[Dict[str, Any]]) -> None:
        """Create a table based on column schema."""
        column_defs = []
        for col in columns:
            col_name = col["column_name"]
            data_type = self._map_postgres_to_sqlite(col["data_type"])
            nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
            column_defs.append(f"{col_name} {data_type} {nullable}")

        # Add primary key if available (assuming first column or look for id)
        pk_col = None
        for col in columns:
            if col.get("is_primary", False) or col["column_name"].lower() in ["id", "product_id"]:
                pk_col = col["column_name"]
                break
        if pk_col:
            column_defs = [defn if not defn.startswith(pk_col) else f"{pk_col} INTEGER PRIMARY KEY" for defn in column_defs]

        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
        conn.execute(create_sql)
        logger.info(f"Created table {table_name}")

    def _map_postgres_to_sqlite(self, pg_type: str) -> str:
        """Map PostgreSQL types to SQLite types."""
        type_mapping = {
            "integer": "INTEGER",
            "bigint": "INTEGER",
            "smallint": "INTEGER",
            "text": "TEXT",
            "varchar": "TEXT",
            "character varying": "TEXT",
            "timestamp": "TEXT",
            "date": "TEXT",
            "boolean": "INTEGER",  # SQLite uses 0/1 for boolean
            "numeric": "REAL",
            "real": "REAL",
            "double precision": "REAL",
        }
        return type_mapping.get(pg_type.lower(), "TEXT")

    def upsert_data(self, table_name: str, records: List[Dict[str, Any]]) -> None:
        """Insert or update records in the table."""
        if not records:
            return

        with self.get_connection() as conn:
            columns = list(records[0].keys())
            placeholders = ", ".join("?" * len(columns))
            insert_sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            for record in records:
                values = [record[col] for col in columns]
                conn.execute(insert_sql, values)
            conn.commit()
        logger.info(f"Upserted {len(records)} records into {table_name}")

    def get_record_count(self, table_name: str) -> int:
        """Get the number of records in a table."""
        with self.get_connection() as conn:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]

# Global instance
retailer_db = RetailerDatabaseManager()
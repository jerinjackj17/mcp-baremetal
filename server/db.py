"""Sample SQLite dataset: a tiny e-commerce store. All data is synthetic.

Customers carry emails, phones and SSNs *on purpose* — the PII masking
proxy needs something to catch. Nothing here is real.
"""
from __future__ import annotations

import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,
  ssn TEXT NOT NULL,
  tier TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL,
  total REAL NOT NULL,
  status TEXT NOT NULL,
  placed_at TEXT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);
CREATE TABLE IF NOT EXISTS inventory (
  sku TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  stock INTEGER NOT NULL,
  price REAL NOT NULL
);
"""

CUSTOMERS = [
    (1, "Ava Reyes", "ava.reyes@example.com", "+1-312-555-0142", "078-05-1120", "gold"),
    (2, "Marcus Chen", "marcus.chen@example.com", "+1-312-555-0198", "219-09-3345", "silver"),
    (3, "Priya Nair", "priya.nair@example.com", "+1-713-555-0117", "456-78-9012", "gold"),
    (4, "Tom Becker", "tom.becker@example.com", "+1-214-555-0163", "123-45-6789", "bronze"),
]

ORDERS = [
    (101, 1, 249.99, "shipped", "2026-10-01"),
    (102, 2, 89.50, "processing", "2026-10-09"),
    (103, 1, 1299.00, "processing", "2026-10-11"),
    (104, 3, 45.25, "delivered", "2026-09-28"),
    (105, 4, 599.99, "processing", "2026-10-12"),
]

INVENTORY = [
    ("SKU-001", "Mechanical keyboard", 42, 129.99),
    ("SKU-002", "USB-C dock", 17, 89.50),
    ("SKU-003", "Noise-cancelling headphones", 8, 249.99),
    ("SKU-004", "Webcam 4K", 0, 149.00),
]

_db_path = os.environ.get("MCP_DB_PATH", "/tmp/mcp-baremetal.db")
_conn: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
        if _conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
            _conn.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?)", CUSTOMERS)
            _conn.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", ORDERS)
            _conn.executemany("INSERT INTO inventory VALUES (?,?,?,?)", INVENTORY)
            _conn.commit()
    return _conn

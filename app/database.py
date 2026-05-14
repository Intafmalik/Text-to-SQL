"""
database.py
-----------
Handles PostgreSQL connection and schema extraction for the Text-to-SQL agent.
Uses SQLAlchemy + psycopg2 under the hood.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from langchain_community.utilities import SQLDatabase

load_dotenv()


# ─────────────────────────────────────────────
# 1. Build connection URL
# ─────────────────────────────────────────────

def get_connection_url() -> str:
    """Build PostgreSQL connection URL from environment variables."""
    host     = os.getenv("DB_HOST", "localhost")
    port     = os.getenv("DB_PORT", "5432")
    dbname   = os.getenv("DB_NAME", "classicmodels")
    user     = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


# ─────────────────────────────────────────────
# 2. LangChain SQLDatabase wrapper
# ─────────────────────────────────────────────

def get_langchain_db(
    include_tables: Optional[list] = None
) -> SQLDatabase:
    """
    Returns a LangChain SQLDatabase object.
    This is what the SQL chain/agent uses internally.
    
    Args:
        include_tables: Optional list of table names to expose.
                        If None, all tables are included.
    """
    url = get_connection_url()
    if include_tables:
        db = SQLDatabase.from_uri(url, include_tables=include_tables)
    else:
        db = SQLDatabase.from_uri(url)
    return db


# ─────────────────────────────────────────────
# 3. Raw SQLAlchemy engine for direct queries
# ─────────────────────────────────────────────

def get_engine():
    """Returns a raw SQLAlchemy engine for executing queries directly."""
    url = get_connection_url()
    return create_engine(url)


def execute_query(sql: str) -> list[dict]:
    """
    Execute a raw SQL query and return results as list of dicts.
    
    Args:
        sql: The SQL SELECT statement to execute.
    
    Returns:
        List of row dicts, or raises an exception with the error message.
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows


# ─────────────────────────────────────────────
# 4. Schema extraction (for context injection)
# ─────────────────────────────────────────────

# The complete ClassicModels schema — hardcoded for reliability
# (avoids live DB introspection on every call)
SCHEMA_DESCRIPTION = """
Database: ClassicModels (scale model cars company)

Tables and columns:

1. productlines
   - productLine VARCHAR(50) PRIMARY KEY
   - textDescription VARCHAR(4000)

2. products
   - productCode VARCHAR(15) PRIMARY KEY
   - productName VARCHAR(70) NOT NULL
   - productLine VARCHAR(50) FK → productlines.productLine
   - productScale VARCHAR(10)  (e.g. '1:10', '1:18', '1:24')
   - productVendor VARCHAR(50)
   - productDescription TEXT
   - quantityInStock INTEGER
   - buyPrice NUMERIC(10,2)
   - "MSRP" NUMERIC(10,2)       ← NOTE: quoted identifier

3. offices
   - officeCode VARCHAR(10) PRIMARY KEY
   - city VARCHAR(50)
   - phone VARCHAR(50)
   - addressLine1, addressLine2 VARCHAR(50)
   - state VARCHAR(50)
   - country VARCHAR(50)
   - postalCode VARCHAR(15)
   - territory VARCHAR(10)  (values: 'NA', 'EMEA', 'Japan', 'APAC')

4. employees
   - employeeNumber INTEGER PRIMARY KEY
   - lastName VARCHAR(50)
   - firstName VARCHAR(50)
   - extension VARCHAR(10)
   - email VARCHAR(100)
   - officeCode VARCHAR(10) FK → offices.officeCode
   - reportsTo INTEGER FK → employees.employeeNumber  (self-referencing)
   - jobTitle VARCHAR(50)  (e.g. 'President', 'VP Sales', 'Sales Rep')

5. customers
   - customerNumber INTEGER PRIMARY KEY
   - customerName VARCHAR(50)
   - contactLastName, contactFirstName VARCHAR(50)
   - phone VARCHAR(50)
   - addressLine1, addressLine2 VARCHAR(50)
   - city, state, postalCode VARCHAR
   - country VARCHAR(50)
   - salesRepEmployeeNumber INTEGER FK → employees.employeeNumber
   - creditLimit NUMERIC(10,2)

6. payments
   - customerNumber INTEGER FK → customers.customerNumber
   - checkNumber VARCHAR(50)
   - paymentDate DATE
   - amount NUMERIC(10,2)
   - PRIMARY KEY (customerNumber, checkNumber)

7. orders
   - orderNumber INTEGER PRIMARY KEY
   - orderDate DATE
   - requiredDate DATE
   - shippedDate DATE (nullable)
   - status VARCHAR(15)  (values: 'Shipped', 'Cancelled', 'In Process', 
                          'On Hold', 'Resolved', 'Disputed')
   - comments TEXT
   - customerNumber INTEGER FK → customers.customerNumber

8. orderdetails
   - orderNumber INTEGER FK → orders.orderNumber
   - productCode VARCHAR(15) FK → products.productCode
   - quantityOrdered INTEGER
   - priceEach NUMERIC(10,2)
   - orderLineNumber SMALLINT
   - PRIMARY KEY (orderNumber, productCode)

Key relationships:
  customers ←→ employees (salesRepEmployeeNumber)
  customers ←→ orders (customerNumber)
  orders    ←→ orderdetails (orderNumber)
  orderdetails ←→ products (productCode)
  products  ←→ productlines (productLine)
  employees ←→ offices (officeCode)
  employees ←→ employees (reportsTo — manager hierarchy)

IMPORTANT NOTES for SQL generation:
  - All column names with uppercase letters MUST be quoted: "MSRP", "productLine", etc.
  - PostgreSQL is case-sensitive for identifiers
  - Use double quotes for column/table names that have uppercase letters
  - Example: SELECT "productName", "buyPrice", "MSRP" FROM products
"""


def get_schema_description() -> str:
    """Returns the full database schema as a formatted string."""
    return SCHEMA_DESCRIPTION


def get_table_names() -> list[str]:
    """Returns the list of all table names in the database."""
    return [
        "productlines", "products", "offices", "employees",
        "customers", "payments", "orders", "orderdetails"
    ]


# ─────────────────────────────────────────────
# 5. Test connection
# ─────────────────────────────────────────────

def test_connection() -> bool:
    """Test database connectivity. Returns True if successful."""
    try:
        rows = execute_query("SELECT 1 AS test")
        return rows[0]["test"] == 1
    except Exception as e:
        print(f"[DB ERROR] Connection failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing database connection...")
    if test_connection():
        print(" Database connected successfully!")
        rows = execute_query("SELECT COUNT(*) AS total FROM customers")
        print(f"   Customers in DB: {rows[0]['total']}")
    else:
        print(" Could not connect. Check your .env settings.")

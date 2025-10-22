#!/usr/bin/env python3
"""
SupplierDB.py

Improved & safe DB utilities for Neon Postgres (used by the Supplier service).
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse
from contextlib import contextmanager
from typing import Optional, Iterable, Any

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

# -------------------------
# Configuration
# -------------------------
DB_URL = os.environ.get("NEON_DB_URL")
if not DB_URL:
    raise EnvironmentError("Please set the NEON_DB_URL environment variable before running this script.")

SUPPLIER_API_KEY = os.environ.get("SUPPLIER_API_KEY", "dev-key")

# -------------------------
# Connection utilities
# -------------------------
def parse_db_url(db_url: str) -> dict:
    """Parse the database URL and return kwargs for psycopg2.connect"""
    r = urlparse(db_url)
    return {
        "dbname": r.path.lstrip("/"),
        "user": r.username,
        "password": r.password,
        "host": r.hostname,
        "port": r.port or 5432,
        "sslmode": "require",
        "connect_timeout": 10,
    }

def get_connection():
    """Return a new psycopg2 connection using NEON_DB_URL"""
    params = parse_db_url(DB_URL)
    return psycopg2.connect(**params)

@contextmanager
def get_cursor(commit: bool = False, dict_cursor: bool = False):
    """
    Context manager that yields a cursor and ensures connection + cursor are closed.
    """
    conn = None
    cur = None
    try:
        conn = get_connection()
        if dict_cursor:
            from psycopg2.extras import RealDictCursor
            cur = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# -------------------------
# Query helpers
# -------------------------
def execute_query(query: str, params: Optional[Iterable[Any]] = None, fetch: bool = True, commit: bool = False, dict_cursor: bool = False):
    with get_cursor(commit=commit, dict_cursor=dict_cursor) as cur:
        cur.execute(query, params or ())
        if fetch:
            return cur.fetchall()
    return None

def execute_ddl(query: str) -> bool:
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(query)
        print("✅ DDL executed.")
        return True
    except Exception as e:
        print(f"❌ DDL failed: {e}")
        return False

# -------------------------
# Table management & seeding
# -------------------------
def create_products_table() -> bool:
    # First drop the table if it exists to ensure clean schema
    drop_query = "DROP TABLE IF EXISTS products CASCADE;"
    execute_ddl(drop_query)
    
    create_table_query = """
    CREATE TABLE products (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        price DECIMAL(10,2),
        stock_quantity INTEGER DEFAULT 0,
        sku VARCHAR(100) UNIQUE,
        status VARCHAR(50) DEFAULT 'Active',
        inventory_tracking VARCHAR(50) DEFAULT 'tracked',
        variant_count INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        -- ACP Feed columns
        link TEXT,
        image_link TEXT,
        currency VARCHAR(3) DEFAULT 'USD',
        enable_search BOOLEAN DEFAULT TRUE,
        enable_checkout BOOLEAN DEFAULT TRUE,
        availability VARCHAR(20),
        inventory_quantity INTEGER DEFAULT 0,
        item_group_id VARCHAR(100),
        offer_id VARCHAR(150),
        product_category VARCHAR(100),
        product_type VARCHAR(100),
        -- ACP Agent Commerce Protocol fields
        agent_commission_rate DECIMAL(5,4) DEFAULT 0.05,
        agent_terms TEXT DEFAULT 'Standard agent terms apply',
        shipping_cost DECIMAL(10,2) DEFAULT 0.0,
        tax_rate DECIMAL(5,4) DEFAULT 0.08,
        wholesale_price DECIMAL(10,2),
        minimum_order_quantity INTEGER DEFAULT 1,
        return_policy_days INTEGER DEFAULT 30,
        warranty_period TEXT DEFAULT '1 year manufacturer warranty',
        certification_required BOOLEAN DEFAULT FALSE,
        territory_restrictions TEXT[],
        brand VARCHAR(100) DEFAULT 'Generic',
        condition VARCHAR(50) DEFAULT 'new',
        free_shipping BOOLEAN DEFAULT TRUE,
        estimated_delivery VARCHAR(100) DEFAULT '3-5 business days',
        bulk_discount_tiers JSONB DEFAULT '[]'::jsonb,
        agent_payment_terms VARCHAR(100) DEFAULT 'Net 30 days',
        minimum_volume INTEGER DEFAULT 0,
        exclusivity_required BOOLEAN DEFAULT FALSE
    );
    """
    return execute_ddl(create_table_query)

def create_variants_table() -> bool:
    # First drop the table if it exists to ensure clean schema
    drop_query = "DROP TABLE IF EXISTS variants CASCADE;"
    execute_ddl(drop_query)
    
    create_table_query = """
    CREATE TABLE variants (
        id SERIAL PRIMARY KEY,
        product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
        sku VARCHAR(100) UNIQUE,
        name VARCHAR(255),
        price DECIMAL(10,2),
        stock_quantity INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        -- ACP Feed columns
        image_link TEXT,
        offer_id VARCHAR(150)
    );
    """
    return execute_ddl(create_table_query)

def insert_sample_products() -> bool:
    try:
        count = execute_query("SELECT COUNT(*) FROM products;", fetch=True)
        if count and count[0][0] > 0:
            print(f"📝 products table already has {count[0][0]} rows. Skipping sample insert.")
            return True

        sample_data = [
            # Basic fields + ACP fields for each product (including created_at)
            ('Laptop', 'High-performance laptop for professionals', 999.99, 50, 'LAP-001', 'Active', 'tracked', 1, 
             '2024-10-22T17:00:00Z', 'https://example.com/laptop', 'https://example.com/images/laptop.jpg', 'USD', True, True, 'in_stock', 50, 
             'LAP-GROUP', 'LAP-001', 'Electronics', 'Computer', 0.03, 'Standard agent terms apply', 0.0, 0.10, 799.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'TechCorp', 'new', True, '3-5 business days', 
             '[{"quantity": 10, "discount": 0.05}, {"quantity": 50, "discount": 0.10}]', 'Net 30 days', 0, False),
            
            ('Smartphone', 'Latest smartphone with advanced features', 699.99, 100, 'PHN-001', 'Active', 'tracked', 1, 
             '2024-10-22T17:00:00Z', 'https://example.com/smartphone', 'https://example.com/images/smartphone.jpg', 'USD', True, True, 'in_stock', 100, 
             'PHN-GROUP', 'PHN-001', 'Electronics', 'Mobile', 0.03, 'Standard agent terms apply', 0.0, 0.10, 559.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'TechCorp', 'new', True, '3-5 business days', 
             '[{"quantity": 10, "discount": 0.05}, {"quantity": 50, "discount": 0.10}]', 'Net 30 days', 0, False),
            
            ('Tablet', '10-inch tablet for productivity', 399.99, 75, 'TAB-001', 'Active', 'tracked', 1, 
             '2024-10-22T17:00:00Z', 'https://example.com/tablet', 'https://example.com/images/tablet.jpg', 'USD', True, True, 'in_stock', 75, 
             'TAB-GROUP', 'TAB-001', 'Electronics', 'Tablet', 0.03, 'Standard agent terms apply', 0.0, 0.10, 319.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'TechCorp', 'new', True, '3-5 business days', 
             '[{"quantity": 10, "discount": 0.05}, {"quantity": 50, "discount": 0.10}]', 'Net 30 days', 0, False),
            
            ('Headphones', 'Wireless noise-cancelling headphones', 199.99, 200, 'HDP-001', 'Active', 'tracked', 1, 
             '2024-10-22T17:00:00Z', 'https://example.com/headphones', 'https://example.com/images/headphones.jpg', 'USD', True, True, 'in_stock', 200, 
             'HDP-GROUP', 'HDP-001', 'Electronics', 'Audio', 0.03, 'Standard agent terms apply', 0.0, 0.10, 159.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'AudioCorp', 'new', True, '3-5 business days', 
             '[{"quantity": 10, "discount": 0.05}, {"quantity": 50, "discount": 0.10}]', 'Net 30 days', 0, False),
            
            ('Snowboard - Small', 'Professional snowboard for small riders', 299.99, 25, 'SNOW-S', 'Active', 'tracked', 5, 
             '2024-10-22T17:00:00Z', 'https://example.com/snowboard-s', 'https://example.com/images/snowboard-s.jpg', 'USD', True, True, 'in_stock', 25, 
             'SNOW-GROUP', 'SNOW-S', 'Sports', 'Snowboard', 0.07, 'Standard agent terms apply', 25.0, 0.06, 239.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'SportsCorp', 'new', False, '5-7 business days', 
             '[{"quantity": 5, "discount": 0.10}, {"quantity": 20, "discount": 0.15}]', 'Net 30 days', 0, False),
            
            ('Snowboard - Medium', 'Professional snowboard for medium riders', 299.99, 30, 'SNOW-M', 'Active', 'tracked', 5, 
             '2024-10-22T17:00:00Z', 'https://example.com/snowboard-m', 'https://example.com/images/snowboard-m.jpg', 'USD', True, True, 'in_stock', 30, 
             'SNOW-GROUP', 'SNOW-M', 'Sports', 'Snowboard', 0.07, 'Standard agent terms apply', 25.0, 0.06, 239.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'SportsCorp', 'new', False, '5-7 business days', 
             '[{"quantity": 5, "discount": 0.10}, {"quantity": 20, "discount": 0.15}]', 'Net 30 days', 0, False),
            
            ('Snowboard - Large', 'Professional snowboard for large riders', 299.99, 20, 'SNOW-L', 'Active', 'tracked', 5, 
             '2024-10-22T17:00:00Z', 'https://example.com/snowboard-l', 'https://example.com/images/snowboard-l.jpg', 'USD', True, True, 'in_stock', 20, 
             'SNOW-GROUP', 'SNOW-L', 'Sports', 'Snowboard', 0.07, 'Standard agent terms apply', 25.0, 0.06, 239.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'SportsCorp', 'new', False, '5-7 business days', 
             '[{"quantity": 5, "discount": 0.10}, {"quantity": 20, "discount": 0.15}]', 'Net 30 days', 0, False),
            
            ('Ski Wax - Basic', 'Basic ski wax for maintenance', 19.99, 100, 'WAX-BASIC', 'Active', 'tracked', 3, 
             '2024-10-22T17:00:00Z', 'https://example.com/wax-basic', 'https://example.com/images/wax-basic.jpg', 'USD', True, True, 'in_stock', 100, 
             'WAX-GROUP', 'WAX-BASIC', 'Sports', 'Accessory', 0.07, 'Standard agent terms apply', 0.0, 0.06, 15.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'SportsCorp', 'new', True, '3-5 business days', 
             '[{"quantity": 10, "discount": 0.15}, {"quantity": 50, "discount": 0.25}]', 'Net 30 days', 0, False),
            
            ('Ski Wax - Premium', 'Premium ski wax for racing', 39.99, 50, 'WAX-PREMIUM', 'Active', 'tracked', 3, 
             '2024-10-22T17:00:00Z', 'https://example.com/wax-premium', 'https://example.com/images/wax-premium.jpg', 'USD', True, True, 'in_stock', 50, 
             'WAX-GROUP', 'WAX-PREMIUM', 'Sports', 'Accessory', 0.07, 'Standard agent terms apply', 0.0, 0.06, 31.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'SportsCorp', 'new', True, '3-5 business days', 
             '[{"quantity": 10, "discount": 0.15}, {"quantity": 50, "discount": 0.25}]', 'Net 30 days', 0, False),
            
            ('Archived Product', 'Old product no longer available', 99.99, 0, 'ARCH-001', 'Archived', 'tracked', 1, 
             '2024-10-22T17:00:00Z', 'https://example.com/archived', 'https://example.com/images/archived.jpg', 'USD', False, False, 'out_of_stock', 0, 
             'ARCH-GROUP', 'ARCH-001', 'Other', 'Discontinued', 0.05, 'Standard agent terms apply', 0.0, 0.08, 79.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'Generic', 'new', True, '3-5 business days', 
             '[]', 'Net 30 days', 0, False),
            
            ('Draft Product', 'New product in development', 149.99, 0, 'DRAFT-001', 'Draft', 'not_tracked', 1, 
             '2024-10-22T17:00:00Z', 'https://example.com/draft', 'https://example.com/images/draft.jpg', 'USD', False, False, 'out_of_stock', 0, 
             'DRAFT-GROUP', 'DRAFT-001', 'Other', 'Development', 0.05, 'Standard agent terms apply', 0.0, 0.08, 119.99, 
             1, 30, '1 year manufacturer warranty', False, None, 'Generic', 'new', True, '3-5 business days', 
             '[]', 'Net 30 days', 0, False)
        ]

        insert_sql = """
        INSERT INTO products (name, description, price, stock_quantity, sku, status, inventory_tracking, variant_count, 
                             created_at, link, image_link, currency, enable_search, enable_checkout, availability, inventory_quantity, 
                             item_group_id, offer_id, product_category, product_type, agent_commission_rate, agent_terms, 
                             shipping_cost, tax_rate, wholesale_price, minimum_order_quantity, return_policy_days, 
                             warranty_period, certification_required, territory_restrictions, brand, condition, 
                             free_shipping, estimated_delivery, bulk_discount_tiers, agent_payment_terms, 
                             minimum_volume, exclusivity_required)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (sku) DO NOTHING;
        """

        with get_cursor(commit=True) as cur:
            cur.executemany(insert_sql, sample_data)

        print(f"📝 Inserted {len(sample_data)} sample products.")
        return True

    except Exception as e:
        print(f"❌ Insert sample products failed: {e}")
        return False

def insert_sample_variants() -> bool:
    try:
        pcount = execute_query("SELECT COUNT(*) FROM products;", fetch=True)
        if not pcount or pcount[0][0] == 0:
            print("❌ No products found. Insert products first.")
            return False

        variants_data = [
            (1, 'LAP-001-SSD', 'Laptop - 256GB SSD', 999.99, 50),
            (1, 'LAP-001-HDD', 'Laptop - 512GB HDD', 899.99, 30),
            (2, 'PHN-001-64GB', 'Smartphone - 64GB', 699.99, 100),
            (2, 'PHN-001-128GB', 'Smartphone - 128GB', 799.99, 80),
            (2, 'PHN-001-256GB', 'Smartphone - 256GB', 899.99, 50),
            (4, 'HDP-001-BLACK', 'Headphones - Black', 199.99, 200),
            (4, 'HDP-001-WHITE', 'Headphones - White', 199.99, 150),
            (4, 'HDP-001-BLUE', 'Headphones - Blue', 199.99, 100),
            (4, 'HDP-001-RED', 'Headphones - Red', 199.99, 80),
            (4, 'HDP-001-GREEN', 'Headphones - Green', 199.99, 60),
            (10, 'ARCH-001-V1', 'Archived Product - Version 1', 99.99, 0),
            (10, 'ARCH-001-V2', 'Archived Product - Version 2', 89.99, 0),
            (11, 'DRAFT-001-ALPHA', 'Draft Product - Alpha Version', 149.99, 0),
            (11, 'DRAFT-001-BETA', 'Draft Product - Beta Version', 139.99, 0)
        ]

        insert_sql = """
        INSERT INTO variants (product_id, sku, name, price, stock_quantity)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (sku) DO NOTHING;
        """

        with get_cursor(commit=True) as cur:
            cur.executemany(insert_sql, variants_data)

        print(f"📝 Inserted {len(variants_data)} sample variants (conflicts skipped).")
        return True

    except Exception as e:
        print(f"❌ Insert sample variants failed: {e}")
        return False

# -------------------------
# Feed-related schema changes & migrations
# -------------------------
def alter_products_for_feed() -> bool:
    alter_query = """
    ALTER TABLE products
        ADD COLUMN IF NOT EXISTS link TEXT,
        ADD COLUMN IF NOT EXISTS image_link TEXT,
        ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'USD',
        ADD COLUMN IF NOT EXISTS enable_search BOOLEAN DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS enable_checkout BOOLEAN DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS availability VARCHAR(20),
        ADD COLUMN IF NOT EXISTS inventory_quantity INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS item_group_id VARCHAR(100),
        ADD COLUMN IF NOT EXISTS offer_id VARCHAR(150),
        ADD COLUMN IF NOT EXISTS product_category VARCHAR(100),
        ADD COLUMN IF NOT EXISTS product_type VARCHAR(100);
    """
    return execute_ddl(alter_query)

def alter_variants_for_feed() -> bool:
    alter_query = """
    ALTER TABLE variants
        ADD COLUMN IF NOT EXISTS image_link TEXT,
        ADD COLUMN IF NOT EXISTS offer_id VARCHAR(150);
    """
    return execute_ddl(alter_query)

def migrate_inventory_and_availability() -> bool:
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("UPDATE products SET inventory_quantity = stock_quantity WHERE inventory_quantity IS NULL OR inventory_quantity <> stock_quantity;")
            cur.execute("""
                UPDATE products
                SET availability =
                    CASE
                        WHEN status ILIKE 'archived' THEN 'out_of_stock'
                        WHEN status ILIKE 'draft' THEN 'out_of_stock'
                        WHEN stock_quantity > 0 THEN 'in_stock'
                        ELSE 'out_of_stock'
                    END
                WHERE availability IS NULL OR availability = '';
            """)
        print("✅ Migrated inventory_quantity and availability.")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

# -------------------------
# Utility functions
# -------------------------
def list_tables():
    try:
        rows = execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;", fetch=True
        )
        if not rows:
            print("📊 No tables found in public schema.")
            return
        print("📊 Tables:")
        for r in rows:
            print(" -", r[0])
    except Exception as e:
        print("❌ list_tables error:", e)

def show_sample_products(limit: int = 5):
    try:
        rows = execute_query(
            "SELECT id, sku, name, price, stock_quantity, status FROM products ORDER BY id LIMIT %s;", (limit,), fetch=True
        )
        if not rows:
            print("No products found.")
            return
        print("Sample products:")
        for r in rows:
            print(f" ID:{r[0]} SKU:{r[1]} Name:{r[2]} Price:{r[3]} Stock:{r[4]} Status:{r[5]}")
    except Exception as e:
        print("❌ show_sample_products error:", e)

# -------------------------
# CLI / Main flow
# -------------------------
def main():
    print("🚀 SupplierDB starting...")

    # Test connection
    try:
        v = execute_query("SELECT version();", fetch=True)
        if v:
            print("📊 DB version:", v[0][0])
    except Exception as e:
        print("❌ DB test failed:", e)
        sys.exit(1)

    if not create_products_table():
        sys.exit(1)
    if not create_variants_table():
        sys.exit(1)

    insert_sample_products()
    insert_sample_variants()

    # Tables already have ACP feed columns, no need to alter
    print("✅ Products table ready for ACP feed.")
    print("✅ Variants table ready for ACP feed.")
    print()
    show_sample_products(10)
    print("\nAll done. You're ready for the next step (map DB -> ACP feed).")

if __name__ == "__main__":
    main()

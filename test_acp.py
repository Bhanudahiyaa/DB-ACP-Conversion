#!/usr/bin/env python3
"""
Test ACP Agent Commerce Protocol implementation
"""

import os
from supplier_db import get_connection
import psycopg2.extras
from datetime import datetime

def test_acp_feed():
    print("🧪 Testing ACP Agent Commerce Protocol Feed...")
    
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        id,
                        sku AS offer_id,
                        name AS title,
                        description,
                        price,
                        currency,
                        availability,
                        inventory_quantity,
                        link,
                        image_link,
                        product_category,
                        product_type,
                        sku,
                        variant_count,
                        status,
                        created_at
                    FROM products
                    WHERE enable_search = TRUE
                    LIMIT 1
                """)
                products = cursor.fetchall()
    except Exception as e:
        print(f"❌ Database query failed: {e}")
        return False

    if not products:
        print("❌ No products found")
        return False

    product = products[0]
    print(f"✅ Found product: {product['title']}")
    
    # Test ACP transformation
    commission_rate = 0.05
    if product['product_category'] == 'Electronics':
        commission_rate = 0.03
    elif product['product_category'] == 'Sports':
        commission_rate = 0.07
    
    acp_product = {
        "id": str(product['id']),
        "offer_id": product['offer_id'],
        "title": product['title'],
        "description": product['description'],
        "price": {
            "amount": float(product['price']),
            "currency": product['currency']
        },
        "availability": product['availability'],
        "inventory_quantity": product['inventory_quantity'],
        "link": product['link'],
        "image_link": product['image_link'],
        "product_category": product['product_category'],
        "product_type": product['product_type'],
        "sku": product['sku'],
        "variant_count": product['variant_count'],
        "condition": "new",
        "brand": "Generic",
        "agent_commission": {
            "rate": commission_rate,
            "amount": float(product['price']) * commission_rate,
            "currency": product['currency']
        },
        "agent_terms": {
            "commission_rate": commission_rate,
            "payment_terms": "Net 30 days",
            "minimum_order": 1,
            "return_policy": "30 days",
            "warranty": "1 year manufacturer warranty"
        },
        "shipping": {
            "free_shipping": True,
            "shipping_cost": 0.0,
            "estimated_delivery": "3-5 business days",
            "shipping_methods": ["standard", "express", "overnight"]
        },
        "tax": {
            "taxable": True,
            "tax_rate": 0.08,
            "tax_amount": float(product['price']) * 0.08,
            "tax_inclusive": False
        },
        "agent_pricing": {
            "wholesale_price": float(product['price']) * 0.8,
            "minimum_quantity": 1,
            "bulk_discounts": [
                {"quantity": 10, "discount": 0.05},
                {"quantity": 50, "discount": 0.10},
                {"quantity": 100, "discount": 0.15}
            ]
        },
        "created_at": product['created_at'].isoformat() if product['created_at'] else None,
        "status": product['status'],
        "agent_requirements": {
            "certification_required": False,
            "minimum_volume": 0,
            "territory_restrictions": [],
            "exclusivity": False
        }
    }
    
    print("✅ ACP Product Structure:")
    print(f"  ID: {acp_product['id']}")
    print(f"  Title: {acp_product['title']}")
    print(f"  Price: {acp_product['price']}")
    print(f"  Agent Commission: {acp_product['agent_commission']}")
    print(f"  Agent Terms: {acp_product['agent_terms']}")
    print(f"  Shipping: {acp_product['shipping']}")
    print(f"  Tax: {acp_product['tax']}")
    print(f"  Agent Pricing: {acp_product['agent_pricing']}")
    print(f"  Agent Requirements: {acp_product['agent_requirements']}")
    
    return True

if __name__ == "__main__":
    # Set environment variable
    os.environ["NEON_DB_URL"] = "postgresql://neondb_owner:npg_KqMpX2Ld6mie@ep-dawn-recipe-ahnt00l1-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    test_acp_feed()

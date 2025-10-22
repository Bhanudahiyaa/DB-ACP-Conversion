from fastapi import FastAPI
from supplier_db import get_connection
import psycopg2.extras
from datetime import datetime
import json

app = FastAPI(title="Supplier ACP Feed")

@app.get("/acp/feed")
def get_feed():
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
                        created_at,
                        -- ACP Agent Commerce Protocol fields
                        agent_commission_rate,
                        agent_terms,
                        shipping_cost,
                        tax_rate,
                        wholesale_price,
                        minimum_order_quantity,
                        return_policy_days,
                        warranty_period,
                        certification_required,
                        territory_restrictions,
                        brand,
                        condition,
                        free_shipping,
                        estimated_delivery,
                        bulk_discount_tiers,
                        agent_payment_terms,
                        minimum_volume,
                        exclusivity_required
                    FROM products
                    WHERE enable_search = TRUE
                """)
                products = cursor.fetchall()
    except Exception as e:
        return {"error": f"Database query failed: {e}"}

    # Transform products to ACP-compatible format using database fields
    acp_products = []
    for product in products:
        # Parse bulk discount tiers from JSONB
        bulk_discounts = []
        if product.get('bulk_discount_tiers'):
            try:
                import json
                bulk_discounts = json.loads(product['bulk_discount_tiers']) if isinstance(product['bulk_discount_tiers'], str) else product['bulk_discount_tiers']
            except:
                bulk_discounts = []
        
        # Parse territory restrictions from array
        territory_restrictions = product.get('territory_restrictions', []) or []
        
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
            "condition": product.get('condition', 'new'),
            "brand": product.get('brand', 'Generic'),
            "agent_commission": {
                "rate": float(product.get('agent_commission_rate', 0.05)),
                "amount": float(product['price']) * float(product.get('agent_commission_rate', 0.05)),
                "currency": product['currency']
            },
            "agent_terms": {
                "commission_rate": float(product.get('agent_commission_rate', 0.05)),
                "payment_terms": product.get('agent_payment_terms', 'Net 30 days'),
                "minimum_order": product.get('minimum_order_quantity', 1),
                "return_policy": f"{product.get('return_policy_days', 30)} days",
                "warranty": product.get('warranty_period', '1 year manufacturer warranty')
            },
            "shipping": {
                "free_shipping": product.get('free_shipping', True),
                "shipping_cost": float(product.get('shipping_cost', 0.0)),
                "estimated_delivery": product.get('estimated_delivery', '3-5 business days'),
                "shipping_methods": ["standard", "express", "overnight"]
            },
            "tax": {
                "taxable": True,
                "tax_rate": float(product.get('tax_rate', 0.08)),
                "tax_amount": float(product['price']) * float(product.get('tax_rate', 0.08)),
                "tax_inclusive": False
            },
            "agent_pricing": {
                "wholesale_price": float(product.get('wholesale_price', float(product['price']) * 0.8)),
                "minimum_quantity": product.get('minimum_order_quantity', 1),
                "bulk_discounts": bulk_discounts
            },
            "created_at": product['created_at'].isoformat() if product['created_at'] else None,
            "status": product['status'],
            "agent_requirements": {
                "certification_required": product.get('certification_required', False),
                "minimum_volume": product.get('minimum_volume', 0),
                "territory_restrictions": territory_restrictions,
                "exclusivity": product.get('exclusivity_required', False)
            }
        }
        acp_products.append(acp_product)

    return {
        "supplier_id": "supplier_001",
        "supplier_name": "ACME Supplier Corp",
        "feed_version": "1.0",
        "feed_type": "agent_commerce_protocol",
        "last_updated": datetime.now().isoformat() + "Z",
        "total_products": len(acp_products),
        "agent_info": {
            "commission_structure": "tiered",
            "payment_frequency": "monthly",
            "minimum_payout": 100.0,
            "currency": "USD"
        },
        "products": acp_products
    }
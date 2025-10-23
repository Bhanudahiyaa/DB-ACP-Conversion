# Supplier-Retailer Agent Communication Testing Guide

This guide provides step-by-step instructions to manually test the complete communication flow between the Supplier and Retailer agents using the A2A (Agent-to-Agent) protocol and ACP (Agent Communication Protocol).

## Prerequisites

- Python 3.11+ installed
## Known Issues

### Python Version Compatibility
The `a2a-sdk` package requires Python 3.10+ but the system is running Python 3.9.6. You may need to:

1. **Upgrade Python** to 3.11+ or use a virtual environment with Python 3.11+
2. **Alternative**: Use the existing working setup that was running in the terminals

### Running Commands
If you encounter import errors when running `python3 supplier_agent/main.py`, try:
```bash
# Use module syntax instead
python3 -m supplier_agent.main
```

### A2A SDK Installation
If `a2a-sdk` installation fails due to Python version:
```bash
# Check Python version
python3 --version

# If < 3.10, consider using existing working environment
# The system appears to be working based on active terminals
```

## Prerequisites
- All dependencies from `requirements.txt` installed
- SQLite3 command-line tool available
- Working directory: `/Users/bhanud/Desktop/SupplierDB`

## Test Overview

The test validates:
1. Supplier Agent ACP endpoints
2. Supplier Agent A2A skill invocation
3. Retailer Agent automatic discovery
4. A2A communication and data sync
5. Database synchronization

## Step-by-Step Testing Instructions

### Phase 1: Start Supplier Services

#### Step 1.1: Start Supplier Agent (ACP + A2A Server)
**Command:**
```bash
python3 supplier_agent/main.py
```

**Expected Output:**
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     Uvicorn running on http://0.0.0.0:8090 (Press CTRL+C to quit)
```

**Expected Behavior:**
- Supplier agent starts on port 8080 (ACP) and 8090 (A2A)
- No errors in startup logs

#### Step 1.2: Start Supplier Feed (Data Population)
**Command:**
```bash
python3 run_supplier_feed.py
```

**Expected Output:**
```
INFO:supplier_feed:Starting supplier feed...
INFO:supplier_feed:Connected to Neon database
INFO:supplier_feed:Processing batch 1/10 (100 records)
...
INFO:supplier_feed:Feed completed successfully. Total records: 1000
```

**Expected Behavior:**
- Populates supplier database with test data
- Shows progress through batches
- Completes without errors

### Phase 2: Test Supplier Agent Endpoints

#### Step 2.1: Test Supplier Health Check
**Command:**
```bash
curl -s http://localhost:8080/health | python3 -m json.tool
```

**Expected Output:**
```json
{
    "status": "healthy",
    "database": "connected",
    "cached_tables": 2
}
```

**Expected Behavior:**
- Status shows "healthy"
- Database shows "connected"
- Cached tables shows 2 (products, variants)

#### Step 2.2: Test ACP Discovery Endpoint
**Command:**
```bash
curl -s http://localhost:8080/.well-known/acp | python3 -m json.tool
```

**Expected Output:**
```json
{
    "acp_version": "1.0",
    "agent": "supplier",
    "resources_endpoint": "/acp/schema",
    "feed_endpoint": "/acp/feed",
    "a2a_endpoint": "http://localhost:8090",
    "description": "Supplier Agent exposing Neon DB data via ACP and A2A protocols"
}
```

**Expected Behavior:**
- Returns ACP metadata
- Includes A2A endpoint URL
- Shows correct agent information

#### Step 2.3: Test ACP Schema Listing
**Command:**
```bash
curl -s http://localhost:8080/acp/schema | python3 -m json.tool
```

**Expected Output:**
```json
{
    "resources": [
        "products",
        "variants"
    ]
}
```

**Expected Behavior:**
- Lists available resources/tables
- Shows "products" and "variants"

#### Step 2.4: Test A2A FetchCatalog Skill
**Command:**
```bash
curl -s http://localhost:8090/skill/FetchCatalog | python3 -m json.tool
```

**Expected Output:**
```json
{
    "status": "ok",
    "records": [
        {
            "id": "products:1",
            "type": "products",
            "attributes": {
                "name": "Laptop",
                "price": 999.99,
                "stock_quantity": 50,
                "sku": "LAP-001",
                ...
            },
            "links": {
                "self": "/acp/resource/products/1"
            }
        },
        ... (10 more records)
    ],
    "count": 11
}
```

**Expected Behavior:**
- Returns status "ok"
- Contains 11 records in ACP format
- Each record has id, type, attributes, links
- Attributes include price, name, stock_quantity, etc.

### Phase 3: Start and Test Retailer Agent

#### Step 3.1: Start Retailer Agent
**Command:**
```bash
python3 retailer_agent/main.py
```

**Expected Output:**
```
INFO:retailer_agent.acp_discovery:[Retailer → Supplier] /.well-known/acp | 1 records | OK | 25ms
INFO:retailer_agent.acp_discovery:Discovered supplier at http://localhost:8080: {'acp_version': '1.0', 'agent': 'supplier', 'resources_endpoint': '/acp/schema', 'feed_endpoint': '/acp/feed', 'a2a_endpoint': 'http://localhost:8090', 'description': 'Supplier Agent exposing Neon DB data via ACP and A2A protocols'}
INFO:retailer_agent.sync_service:Using A2A endpoint: http://localhost:8090
INFO:retailer_agent.acp_discovery:[Retailer → Supplier] /acp/schema | 2 records | OK | 2136ms
INFO:retailer_agent.acp_discovery:[Retailer → Supplier] /acp/schema/products | 1 records | OK | 1387ms
INFO:retailer_agent.acp_discovery:[Retailer → Supplier] /acp/schema/variants | 1 records | OK | 459ms
INFO:retailer_agent.acp_discovery:Fetched schema with 2 tables from http://localhost:8080
INFO:retailer_agent.retailer_db:Database initialized with 2 tables
INFO:retailer_agent.sync_service:A2A FetchCatalog attempt 1/3 to http://localhost:8090
INFO:httpx:HTTP Request: GET http://localhost:8090/skill/FetchCatalog "HTTP/1.1 200 OK"
INFO:retailer_agent.a2a:[Retailer → Supplier] Task: FetchCatalog | 11 records | OK
INFO:retailer_agent.sync_service:A2A FetchCatalog successful: 11 records on attempt 1
INFO:retailer_agent.sync_service:ACP validation successful: 11 records validated
INFO:retailer_agent.retailer_db:Upserted 11 records into products
INFO:retailer_agent.sync_service:A2A sync successful: 11 records
INFO:retailer_agent.sync_service:Sync completed successfully. Total records: 11
```

**Expected Behavior:**
- Automatic discovery via .well-known/acp
- Schema fetching from ACP endpoints
- Database initialization
- A2A skill invocation
- Data validation and sync
- No errors in the process

### Phase 4: Verify Database Synchronization

#### Step 4.1: Check Record Count
**Command:**
```bash
sqlite3 retailer.db "SELECT COUNT(*) FROM products;"
```

**Expected Output:**
```
11
```

**Expected Behavior:**
- Shows 11 records (or more if multiple syncs occurred)

#### Step 4.2: View Sample Records
**Command:**
```bash
sqlite3 retailer.db "SELECT name, price, stock_quantity, sku FROM products LIMIT 5;" | cat
```

**Expected Output:**
```
Laptop|999.99|50|LAP-001
Smartphone|699.99|100|PHN-001
Headphones|199.99|200|HDP-001
Snowboard - Small|299.99|25|SNOW-S
Snowboard - Medium|299.99|30|SNOW-M
```

**Expected Behavior:**
- Shows product data with correct columns
- Prices and quantities match expected values

#### Step 4.3: Verify Data Integrity
**Command:**
```bash
sqlite3 retailer.db "SELECT COUNT(*) as total, AVG(price) as avg_price, SUM(stock_quantity) as total_stock FROM products;"
```

**Expected Output:**
```
11|349.9818181818182|665
```

**Expected Behavior:**
- Total count matches expected
- Average price and total stock are reasonable

### Phase 5: Test Periodic Sync (Optional)

#### Step 5.1: Monitor Periodic Sync
**Command:**
```bash
# Let retailer agent run for 15+ minutes (or modify FETCH_INTERVAL_MINUTES in config)
# Watch for periodic sync logs
```

**Expected Behavior:**
- Periodic sync messages appear in logs
- No failures in repeated sync attempts

## Troubleshooting

### Common Issues and Solutions

#### Issue: Supplier Agent Won't Start
**Symptoms:** Port binding errors or database connection failures
**Solution:**
```bash
# Check if ports are available
lsof -i :8080
lsof -i :8090

# Kill conflicting processes if needed
kill -9 <PID>
```

#### Issue: Database Connection Errors
**Symptoms:** "Failed to connect to database" errors
**Solution:**
```bash
# Check Neon database credentials in environment
echo $DATABASE_URL

# Test database connection manually
python3 -c "import os; from supplier_agent.supplier_db import db_manager; print('Connection test:', db_manager.get_connection())"
```

#### Issue: A2A Skill Returns Empty Data
**Symptoms:** FetchCatalog returns 0 records
**Solution:**
```bash
# Check supplier feed completed successfully
tail -n 20 logs/supplier_feed.log

# Verify data exists in supplier database
python3 -c "from supplier_agent.supplier_db import db_manager; import asyncio; asyncio.run(db_manager.get_table_count('products'))"
```

#### Issue: Retailer Discovery Fails
**Symptoms:** "Failed to discover supplier" errors
**Solution:**
```bash
# Test ACP endpoint manually
curl -v http://localhost:8080/.well-known/acp

# Check network connectivity
ping localhost
```

#### Issue: Database Sync Fails
**Symptoms:** "Failed to upsert data" errors
**Solution:**
```bash
# Check retailer database permissions
ls -la retailer.db

# Verify database schema
sqlite3 retailer.db ".schema products"
```

## Expected Test Results Summary

| Test Phase | Expected Result | Success Criteria |
|------------|----------------|------------------|
| Supplier Startup | Services start on ports 8080/8090 | No errors, services listening |
| Health Check | Status: healthy, database: connected | JSON response with correct fields |
| ACP Discovery | Returns metadata with A2A endpoint | Valid JSON with required fields |
| ACP Schema | Lists products and variants | Resources array with table names |
| A2A Skill | Returns 11 catalog records | Status: ok, count: 11 |
| Retailer Discovery | Automatic discovery succeeds | Logs show successful discovery |
| Schema Fetch | Gets table schemas | Logs show 2 tables fetched |
| Database Init | Creates tables in SQLite | Logs show database initialized |
| A2A Communication | Fetches data via skill | HTTP 200, records received |
| Data Validation | ACP format validation passes | Logs show validation successful |
| Database Sync | Records inserted/updated | Logs show upsert successful |
| Record Count | 11+ records in database | SQLite query shows expected count |

## Cleanup

After testing, stop all services:
```bash
# In each terminal, press Ctrl+C to stop services
# Or kill processes
pkill -f "python3 supplier_agent/main.py"
pkill -f "python3 run_supplier_feed.py"
pkill -f "python3 retailer_agent/main.py"
```

## Test Completion Checklist

- [ ] Supplier agent started successfully
- [ ] Supplier feed populated database
- [ ] Health check returns healthy status
- [ ] ACP discovery returns correct metadata
- [ ] ACP schema lists available resources
- [ ] A2A skill returns catalog data
- [ ] Retailer agent discovers supplier automatically
- [ ] Schema fetched and database initialized
- [ ] A2A communication successful
- [ ] Data validation passes
- [ ] Database synchronization completes
- [ ] Record count matches expectations
- [ ] Sample data queries work correctly

All tests should pass for successful A2A communication between Supplier and Retailer agents.
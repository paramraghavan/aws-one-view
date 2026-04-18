# DuckDB Persistence Guide

Understand whether DuckDB stores data in memory or on disk, and when to use each approach.

---

## Current Setup: In-Memory (:memory:)

### Code
```python
# reporting_engine.py line 35
self.conn = duckdb.connect(':memory:')
```

### How It Works
```
CSV Files (disk)
    ↓
Read with pandas
    ↓
Load into DuckDB memory
    ↓
Execute queries in RAM
    ↓
Return results
    ↓
Server restarts → Memory cleared → Start over
```

### Characteristics

| Aspect | Behavior |
|--------|----------|
| **Data Location** | RAM (volatile) |
| **Persistence** | ❌ No (lost on restart) |
| **Speed** | ✅ Very fast (no disk I/O) |
| **Memory Usage** | Limited to available RAM |
| **Disk Usage** | 0 bytes (temporary) |
| **Best For** | Development, testing, demos |

### Startup Time
```
Server starts
  ↓ (on first query)
Load 15 CSV files from disk
  ↓
Parse and combine with pandas
  ↓
Register in DuckDB memory
  ↓
Ready for queries (~2-3 seconds)
```

---

## Option 1: Keep In-Memory (Current)

### Pros ✅
- Simple - no database files to manage
- Fast - queries run in RAM
- No disk space used
- No database cleanup needed

### Cons ❌
- Data lost on restart
- Limited by available RAM
- Can't share data between instances

### When to Use
- 🧪 Development
- 🎨 Demos & prototypes
- 📊 Small datasets (<1GB)
- 🔍 Testing

### No code changes needed!

---

## Option 2: Persist to Disk

Store data in DuckDB database files (`.duckdb` files) for permanent storage.

### How It Works
```
CSV Files (disk)
    ↓
Read with pandas (first time only)
    ↓
Load into DuckDB
    ↓
Save to database.duckdb file
    ↓
On restart:
    ↓
Load from database.duckdb (fast)
    ↓
Ready for queries
```

### Step 1: Switch to Disk Persistence

**File:** `reporting_engine.py`

Change line 35 from:
```python
self.conn = duckdb.connect(':memory:')
```

To:
```python
db_path = BASE_DIR / 'duckdb' / 'data.duckdb'
self.conn = duckdb.connect(str(db_path))
```

Or with auto-create directory:
```python
db_dir = BASE_DIR / 'duckdb'
db_dir.mkdir(parents=True, exist_ok=True)
self.conn = duckdb.connect(str(db_dir / 'data.duckdb'))
```

### Step 2: Make Data Persistent

Add this to the `DuckDBEngine` class:

```python
def save_tables(self):
    """Save all tables to disk (optional)"""
    for table_name in self.loaded_tables.keys():
        self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM {table_name}")
```

### Step 3: Load from Existing Database

The connection automatically:
1. Creates the database file if it doesn't exist
2. Loads existing tables on restart
3. Creates new tables as needed

---

## Comparison: In-Memory vs Disk

### Performance

| Operation | In-Memory | Disk | Winner |
|-----------|-----------|------|--------|
| **First startup** | 2-3s (load CSVs) | 2-3s (load CSVs, save DB) | In-Memory |
| **2nd startup** | 2-3s (load CSVs again) | <1s (load from DB) | **Disk** |
| **Query execution** | <50ms | <50ms | Tie |
| **Memory usage** | ~50MB | ~2MB (in-use only) | **Disk** |
| **Disk usage** | 0 bytes | ~50MB (database file) | In-Memory |

### Features

| Feature | In-Memory | Disk |
|---------|-----------|------|
| Data survives restart | ❌ No | ✅ Yes |
| Fast queries | ✅ Yes | ✅ Yes |
| No disk needed | ✅ Yes | ❌ No |
| Production ready | ⚠️ Limited | ✅ Yes |
| Shared between instances | ❌ No | ✅ Yes |
| Data versioning | ❌ No | ✅ Possible |

---

## Real-World Scenarios

### Scenario 1: Local Development
```python
# Use in-memory (current)
self.conn = duckdb.connect(':memory:')

# Pros: Simple, fast, no cleanup
# Cons: Data lost on restart (but you have CSVs)
```

### Scenario 2: Production Server
```python
# Use disk persistence
self.conn = duckdb.connect('duckdb/data.duckdb')

# Pros: Fast restarts, permanent data, backups possible
# Cons: Need disk space, more setup
```

### Scenario 3: Large Dataset (>5GB)
```python
# Use disk + external database
# DuckDB on disk, CSVs as backup
self.conn = duckdb.connect('duckdb/large_data.duckdb')

# Load once, query many times
# Much faster than reloading CSVs each time
```

### Scenario 4: Multi-Instance
```python
# All servers share same database file (NFS/shared storage)
self.conn = duckdb.connect('/shared/storage/duckdb/data.duckdb')

# Each instance loads from same database
# Faster startup for all instances
```

---

## How to Enable Disk Persistence

### Simple Version
```python
class DuckDBEngine:
    def __init__(self):
        # Connect to disk database (creates if doesn't exist)
        self.conn = duckdb.connect('duckdb_data.duckdb')
        self.loaded_tables = {}
```

### Production Version
```python
from pathlib import Path

class DuckDBEngine:
    def __init__(self):
        # Create db directory if needed
        db_dir = Path('duckdb')
        db_dir.mkdir(exist_ok=True)

        # Connect to database
        self.conn = duckdb.connect(str(db_dir / 'data.duckdb'))
        self.loaded_tables = {}
        print(f"✓ DuckDB database: {db_dir / 'data.duckdb'}")
```

### Advanced Version with Cleanup
```python
class DuckDBEngine:
    def __init__(self, use_memory=False):
        if use_memory:
            self.conn = duckdb.connect(':memory:')
            self.db_path = None
            print("✓ DuckDB: In-memory (data lost on restart)")
        else:
            db_dir = Path('duckdb')
            db_dir.mkdir(exist_ok=True)
            self.db_path = db_dir / 'data.duckdb'
            self.conn = duckdb.connect(str(self.db_path))
            size_mb = self.db_path.stat().st_size / 1024 / 1024
            print(f"✓ DuckDB database: {self.db_path} ({size_mb:.1f}MB)")

    def get_stats(self):
        """Get database statistics"""
        if not self.db_path:
            return {"mode": "in-memory"}

        return {
            "mode": "disk",
            "path": str(self.db_path),
            "size_mb": self.db_path.stat().st_size / 1024 / 1024,
            "tables": list(self.loaded_tables.keys()),
            "total_rows": sum(self.loaded_tables.values())
        }
```

---

## Data Lifecycle

### In-Memory Approach
```
┌─────────────────────────────────┐
│ CSV Files on Disk               │
│ (permanent source)              │
└────────────┬────────────────────┘
             │
    (on app startup)
             ↓
┌─────────────────────────────────┐
│ DuckDB In-Memory Database       │
│ (volatile, lost on restart)     │
└─────────────────────────────────┘
             │
    (query results)
             ↓
         Application
             │
    (app stops)
             ↓
      Memory cleared
      (back to CSV only)
```

### Disk Persistence Approach
```
┌─────────────────────────────────┐
│ CSV Files on Disk               │
│ (source of truth)               │
└────────────┬────────────────────┘
             │
    (on first app startup)
             ↓
┌─────────────────────────────────┐
│ DuckDB Disk Database            │
│ (persistent .duckdb file)       │
└────────────┬────────────────────┘
             │
    (on subsequent startups)
             ↓
       (load directly)
             │
         Application
             │
    (app stops)
             ↓
  Database file persists
   (can resume later)
```

---

## Backup & Recovery

### In-Memory: No Backup Needed
```python
# Data lost on restart?
# No problem - just reload CSVs on startup
self.conn = duckdb.connect(':memory:')
# CSVs are your backup!
```

### Disk: Simple Backup
```python
# Backup the database file
import shutil

def backup_database():
    shutil.copy('duckdb/data.duckdb', 'backups/data_backup.duckdb')

def restore_database():
    shutil.copy('backups/data_backup.duckdb', 'duckdb/data.duckdb')
```

---

## When to Switch to Disk

Switch from in-memory to disk if:

1. **Server will run 24/7**
   - Data shouldn't be reloaded constantly
   - Disk version faster after restart

2. **Large datasets (>1GB)**
   - Avoid reloading CSVs every restart
   - Faster startup times

3. **Multiple servers**
   - Share same database across instances
   - Reduce duplicate storage/loading

4. **Need data versioning**
   - Keep backup of previous states
   - Query historical data

5. **CSVs update infrequently**
   - Load once, query many times
   - Only reload on CSV changes

---

## Migration from In-Memory to Disk

### Step 1: Create backup of CSVs
```bash
cp -r reports/ reports_backup/
cp -r data/ data_backup/
```

### Step 2: Update code
```python
# Old
self.conn = duckdb.connect(':memory:')

# New
db_dir = Path('duckdb')
db_dir.mkdir(exist_ok=True)
self.conn = duckdb.connect(str(db_dir / 'data.duckdb'))
```

### Step 3: Restart server
- First run: Loads CSVs and saves to `data.duckdb`
- Subsequent runs: Loads from `data.duckdb` (faster)

### Step 4: Monitor
```python
print(f"Database size: {path.stat().st_size / 1024 / 1024:.1f}MB")
```

---

## Summary

| Mode | Use Case | Data Lost | Speed | Setup |
|------|----------|-----------|-------|-------|
| **In-Memory** (current) | Dev/demo/test | On restart | Very fast | None |
| **Disk** | Production/large data | No | Fast restart | Simple |
| **Disk + Archive** | Long-term storage | No | Fast | Medium |

**Recommendation:**
- 🧪 **Development:** Keep in-memory (current)
- 🚀 **Production:** Switch to disk persistence
- 📊 **Large data (>1GB):** Disk persistence

**To switch:** Just change one line in `reporting_engine.py` (line 35)!

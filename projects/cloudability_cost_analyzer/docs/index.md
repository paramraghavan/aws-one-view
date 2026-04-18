# Cloudability Cost Analyzer - Documentation

Complete guide to all features, setup, and usage of the Cloudability Cost Analyzer dashboard.

---

## 📋 Quick Navigation

### Getting Started
- **[Quick Start](quickstart_mock_data.md)** - Get running in 2 minutes with mock data
- **[Main README](readme.md)** - Project overview and basic setup
- **[Reporting Engine](reporting_engine_readme.md)** - How the Flask backend works

### Features & How-To Guides
- **[Filtering Guide](filters_guide.md)** - Add dynamic column filters to charts
- **[Multi-Table Guide](multi_table_guide.md)** - Load and JOIN multiple tables (users, regions, budgets)
- **[Mock Data Guide](mock_data_guide.md)** - Complete reference for generated test data

### Database & External Access
- **[DuckDB Persistence](duckdb_persistence_guide.md)** - In-memory vs disk storage
- **[DuckDB UI Guide](duckdb_ui_guide.md)** - Connect via web UI, Studio, DBeaver, Jupyter, Metabase

### Learning Resources
- **[D3.js Tutorial](d3js_tutorial.md)** - Learn D3.js visualization library
- **[D3.js Examples](../examples/README.md)** - 5 interactive examples with source code

---

## 🎯 Choose Your Path

### I want to...

**Get started quickly**
→ [Quick Start](quickstart_mock_data.md) (5 min)

**Add filters to my dashboard**
→ [Filtering Guide](filters_guide.md)

**Load multiple data tables**
→ [Multi-Table Guide](multi_table_guide.md)

**Understand the data**
→ [Mock Data Guide](mock_data_guide.md)

**Save data to disk**
→ [DuckDB Persistence](duckdb_persistence_guide.md)

**Query data directly**
→ [DuckDB UI Guide](duckdb_ui_guide.md)

**Learn data visualization**
→ [D3.js Tutorial](d3js_tutorial.md)

**See working examples**
→ [D3.js Examples](../examples/README.md)

---

## 📚 Documentation by Topic

### Setup & Configuration
| Document | Purpose | Time |
|----------|---------|------|
| [Quick Start](quickstart_mock_data.md) | Get dashboard running with mock data | 5 min |
| [Main README](readme.md) | Project overview and features | 10 min |
| [Reporting Engine](reporting_engine_readme.md) | Flask backend and API | 15 min |

### Features
| Document | Purpose | Time |
|----------|---------|------|
| [Filtering Guide](filters_guide.md) | Add dynamic column filters | 10 min |
| [Multi-Table Guide](multi_table_guide.md) | Load and JOIN multiple tables | 15 min |
| [D3.js Tutorial](d3js_tutorial.md) | Learn visualization library | 30 min |

### Data & Storage
| Document | Purpose | Time |
|----------|---------|------|
| [Mock Data Guide](mock_data_guide.md) | Complete data reference | 20 min |
| [DuckDB Persistence](duckdb_persistence_guide.md) | Storage options | 10 min |
| [DuckDB UI Guide](duckdb_ui_guide.md) | External database tools | 15 min |

### Learning
| Document | Purpose | Time |
|----------|---------|------|
| [D3.js Examples](../examples/README.md) | 5 interactive examples | Variable |

---

## 🚀 Common Tasks

### Task 1: Start the Dashboard
```bash
python3 reporting_engine.py
# Open http://localhost:5445
```
See: [Quick Start](quickstart_mock_data.md)

### Task 2: Add a Filter to a Chart
```yaml
filters:
  - column: "block_funding"
    label: "Funding Block"
```
See: [Filtering Guide](filters_guide.md)

### Task 3: Load a New Data Table
```python
engine.load_table("regions", "data/regions.csv")
```
See: [Multi-Table Guide](multi_table_guide.md)

### Task 4: Create a JOIN Query
```sql
SELECT r.state, SUM(c.total_cost)
FROM cost_report c
LEFT JOIN regions r ON c.user_id = r.user_id
GROUP BY r.state
```
See: [Multi-Table Guide](multi_table_guide.md)

### Task 5: Access Data Directly
```bash
duckdb data.duckdb -ui
# Opens http://localhost:8080
```
See: [DuckDB UI Guide](duckdb_ui_guide.md)

### Task 6: Learn D3.js
```bash
open examples/01_simple_bar_chart.html
```
See: [D3.js Examples](../examples/README.md)

---

## 📊 What's Included

### Mock Data
- **75 Workday users** with organizational hierarchy
- **46 CSV files** (2.1 MB total)
- **12 weeks** of Cloudability cost data
- **12 AWS services** with realistic costs
- **3 months** of monthly aggregated data

### Features
- ✅ Dynamic column filtering
- ✅ Multi-table support with JOINs
- ✅ Flexible chart orientation (vertical/horizontal)
- ✅ Multiple visualization types
- ✅ Real-time updates
- ✅ Responsive design

### Documentation
- ✅ 9 comprehensive guides (~3,000 lines)
- ✅ 50+ code examples
- ✅ 10 dashboard configurations
- ✅ 5 D3.js learning examples

---

## 🔧 Configuration Files

### Main Files
| File | Purpose |
|------|---------|
| `config/tabs.yaml` | Define dashboard tabs |
| `config/*.yaml` | Individual tab configurations |
| `generate_mock_data.py` | Generate test data |
| `reporting_engine.py` | Flask backend |

### Example Configs
| File | Purpose |
|------|---------|
| `config/cost_by_vp.yaml` | Cost grouped by VP |
| `config/cost_by_vp_filtered.yaml` | With dynamic filters |
| `config/cost_by_state.yaml` | JOIN with regions |
| `config/budget_vs_actual.yaml` | JOIN with budgets |
| `config/mock_data_examples.yaml` | 10 mock data examples |

---

## 🗂️ Directory Structure

```
cloudability_cost_analyzer/
├── docs/                    ← YOU ARE HERE
│   ├── index.md            ← Main documentation index
│   ├── quickstart_mock_data.md
│   ├── filtering_guide.md
│   ├── multi_table_guide.md
│   ├── mock_data_guide.md
│   ├── duckdb_persistence_guide.md
│   ├── duckdb_ui_guide.md
│   ├── d3js_tutorial.md
│   └── ...
├── examples/               ← D3.js learning examples
│   ├── 01_simple_bar_chart.html
│   ├── 02_pie_chart.html
│   ├── 03_line_chart.html
│   ├── 04_interactive_chart.html
│   ├── 05_horizontal_bar_chart.html
│   └── README.md
├── config/                 ← Dashboard configurations
│   ├── tabs.yaml
│   ├── *.yaml
│   └── mock_data_examples.yaml
├── mock_data/              ← Generated test data (46 files)
│   ├── workday_users.csv
│   ├── weekly/
│   └── monthly/
├── templates/              ← Flask HTML templates
│   └── dashboard.html
├── static/                 ← CSS and JavaScript
│   ├── css/style.css
│   └── js/dashboard.js
├── generate_mock_data.py   ← Data generator script
├── reporting_engine.py     ← Flask backend
└── data/                   ← Sample data files
    ├── regions.csv
    ├── budgets.csv
    └── users.csv
```

---

## 💡 Tips

### For Developers
- Start with [Quick Start](quickstart_mock_data.md) to understand data flow
- Use [Mock Data Guide](mock_data_guide.md) to understand data structure
- See [Filtering Guide](filters_guide.md) to add new features

### For Business Users
- Use [Quick Start](quickstart_mock_data.md) to load and explore data
- Create filters with [Filtering Guide](filters_guide.md)
- Query data directly with [DuckDB UI Guide](duckdb_ui_guide.md)

### For Data Analysts
- Load multiple tables with [Multi-Table Guide](multi_table_guide.md)
- Write custom SQL queries (see examples in guides)
- Access via Python, Jupyter, or web UI

### For Learning
- Start with [D3.js Examples](../examples/README.md)
- Progress through [D3.js Tutorial](d3js_tutorial.md)
- Modify examples and experiment

---

## ❓ FAQ

**Q: Where do I start?**
A: [Quick Start](quickstart_mock_data.md) - 5 minute setup

**Q: How do I add filters?**
A: [Filtering Guide](filters_guide.md)

**Q: Can I use multiple tables?**
A: Yes! [Multi-Table Guide](multi_table_guide.md)

**Q: How do I query data directly?**
A: [DuckDB UI Guide](duckdb_ui_guide.md)

**Q: What data is included?**
A: [Mock Data Guide](mock_data_guide.md)

**Q: How do I learn D3.js?**
A: [D3.js Examples](../examples/README.md) and [Tutorial](d3js_tutorial.md)

---

## 📝 Document Overview

| Document | Lines | Purpose |
|----------|-------|---------|
| index.md (this file) | 250 | Master index and navigation |
| quickstart_mock_data.md | 200 | Quick 5-minute setup |
| filtering_guide.md | 280 | Dynamic column filters |
| multi_table_guide.md | 450 | Multi-table support and JOINs |
| mock_data_guide.md | 380 | Complete data reference |
| duckdb_persistence_guide.md | 415 | Storage options |
| duckdb_ui_guide.md | 506 | External database tools |
| d3js_tutorial.md | 400 | D3.js learning |
| readme.md | 200+ | Project README |
| reporting_engine_readme.md | 200+ | Flask backend |

**Total:** ~3,300 lines of documentation

---

## 🎯 Next Steps

1. **Choose your starting point** above
2. **Follow the guide** at your own pace
3. **Ask questions** in code comments
4. **Explore examples** in the examples/ directory
5. **Build on what you learn**

---

## 📞 Support

For questions about:
- **Setup:** See [Quick Start](quickstart_mock_data.md)
- **Features:** See relevant feature guide
- **Data:** See [Mock Data Guide](mock_data_guide.md)
- **API:** See [Reporting Engine](reporting_engine_readme.md)
- **Visualization:** See [D3.js Examples](../examples/README.md)

---

**Version:** 1.0
**Last Updated:** April 2026
**Status:** Ready for Development and Testing ✅

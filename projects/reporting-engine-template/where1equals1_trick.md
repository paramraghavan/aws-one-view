In SQL, `WHERE 1=1` is a common programming pattern used to simplify the **dynamic generation of queries**.

Technically, `1=1` is a "tautology"—a statement that is always true. Adding it to a query doesn't change the result set,
but it provides a significant advantage when you are building SQL strings in code (like Python, Java, or PHP).

Here is why it is used:

---

### 1. It simplifies "AND" logic

When building a filter system (like the one in your Flask app), you often don't know which filters a user will select.
Without `1=1`, you have to write complex logic to determine if a condition is the **first** one or a **subsequent** one.

**The "Hard" Way (Without 1=1):**

```python
query = "SELECT * FROM costs"
filters = []

if project:
    filters.append(f"project = '{project}'")
if cost_center:
    filters.append(f"cost_center = '{cost_center}'")

if len(filters) > 0:
    query += " WHERE " + " AND ".join(filters)
```

In this scenario, you have to check if the list is empty just to decide whether to add the word `WHERE`.

**The "Easy" Way (With 1=1):**

```python
query = "SELECT * FROM costs WHERE 1=1"

if project:
    query += f" AND project = '{project}'"
if cost_center:
    query += f" AND cost_center = '{cost_center}'"
```

Because `1=1` is already there, every single dynamic filter can safely start with `AND`. You don't need to check if it's
the first condition or not.

---

### 2. It prevents Syntax Errors

If you were to loop through a list of filters and just append them, you might end up with:

* `SELECT ... WHERE AND project = 'A'` (Syntax Error: `AND` with no preceding condition).
* `SELECT ... WHERE` (Syntax Error: `WHERE` with no condition).

By starting with `1=1`, the query is always syntactically valid, even if no filters are applied.

---

### 3. Ease of Debugging (Commenting out lines)

When manually testing queries in a database console, `1=1` allows you to comment out lines easily without breaking the
query.

```sql
SELECT * FROM costs 
WHERE 1=1
-- AND project = 'PROJ001'  <-- I can comment this out safely
AND cost_center = 'ENG'    <-- This still works because 1=1 is above it
```

If you didn't have `1=1`, and you commented out the first line after `WHERE`, the query would fail because the second
line starts with `AND`.

---

### Does it hurt performance?

**No.** Modern database query optimizers (including DuckDB, PostgreSQL, and SQL Server) are smart enough to recognize
that `1=1` is a constant true value. They strip it out during the "query optimization" phase before the data is actually
searched, so there is **zero performance penalty**.

### Summary

In your project, using `query.replace("WHERE 1=1", f"WHERE {where_clause}")` is a clever way to ensure that your base
SQL template in `queries.json` is always "ready" to accept an unlimited number of additional `AND` conditions generated
by your Python logic.
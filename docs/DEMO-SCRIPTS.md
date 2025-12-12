# Demo Scripts (Inventory Manager)

Use these outlines to record Stage 1–3 demos and explicitly cover requirements (a), (b), and (c).

## Stage 1 (1–2 minutes)

1. Start the app locally:
   - Windows PowerShell: `python app.py`
2. Open `/` to show the landing page (Inventory Manager).
3. Click "Initialize & Seed DB" to create tables and seed reference data.

## Stage 2 (5–10 minutes)

### 1) Database Design (2 minutes)
- Show `app.py` models for `Category`, `Supplier`, `Location`, `Product`.
- Mention PKs, FKs, uniques, and the helpful indexes:
  - PKs: `categories(id)`, `suppliers(id)`, `locations(id)`, `products(id)`
  - FKs: `products.category_id → categories(id)`, `products.supplier_id → suppliers(id)`, `products.location_id → locations(id)`
  - Unique: `categories(name)`, `suppliers(name)`, `locations(name)`, `products(sku)`
  - Indexes: `products(category_id)`, `products(supplier_id)`, `products(price)`, `products(location_id)`

### 2) Requirement (a) — Insert / Update / Delete on Products (3–4 minutes)
- UI path:
  1) Go to `/products` → "New Product". Fill name, SKU, category, supplier, location, price, units, reorder level → Save.
  2) Click "Edit" on that product → change price/stock or supplier → Save.
  3) Click "Delete" → confirm the product disappears.
- Code path to show:
  - Create: `@app.route("/products", methods=["POST"])` → `products_create` (validates, `db.session.add`, `commit`).
  - Update: `@app.route("/products/<int:product_id>/update", methods=["POST"])` → `products_update`.
  - Delete: `@app.route("/products/<int:product_id>/delete", methods=["POST"])` → `products_delete` (wrapped in transaction).

### 3) Requirement (b) — Filter + Report before/after change (3–4 minutes)
- Go to `/reports/products`.
- Apply filters (e.g., Category = Electronics, Price: 0–50, Stock: 0–500).
- Show the results table, aggregate stats (avg price, avg stock, total value), and the chart.
- Switch to `/products`, adjust stock via the ± buttons or edit the product.
- Return to `/reports/products` with the same filters → show the updated table/stats/chart.
- Code path to show:
  - `@app.route("/reports/products")` → `products_report` where filters are applied with ORM (`q = q.filter(...)`).

### 4) Requirement (c) — Dynamic UI lists from the database (1–2 minutes)
- New/Edit Product form loads its lists dynamically from the DB:
  - `@app.route("/products/new")` and `@app.route("/products/<id>/edit")` query `Category`, `Supplier`, and `Location` and pass them to the template.
  - The form selects are built from these lists; nothing is hard-coded.
- Report filters also load categories and suppliers dynamically.
- Show these query snippets in `app.py`, then point to the `<select>` loops in `templates/product_form.html` and `templates/report_products.html`.

## Stage 3 (3–5 minutes)

- SQL Injection Protection:
  - Most CRUD uses SQLAlchemy ORM (prepared statements).
  - Stock adjust uses parameterized raw SQL with named parameters in `products_txn_adjust`.
- Indexes:
  - `Index("ix_products_category", ...)`, `Index("ix_products_supplier", ...)`, `Index("ix_products_price", ...)`, and `Index("ix_products_location", ...)` speed up the report filters.
- Transactions & Isolation:
  - `with db.session.begin()` wraps delete and stock adjust.
  - Engine isolation level set to `SERIALIZABLE` for discussion.

---

## Optional: Automated verification for (a) and (b)

You can run `scripts/verify_stage_requirements.py` to programmatically insert, update, delete a product and compute filtered report stats before/after. This uses the ORM inside an app context (no CSRF needed) and prints the results to the console.

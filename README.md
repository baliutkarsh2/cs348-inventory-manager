# CS348 Project — Inventory & Products (Flask + SQLite)

This repo implements the full project from Stage 1 to Stage 3 using Python, Flask, and SQLAlchemy with SQLite.

## Stages overview

- Stage 1: Framework installed and Hello World page (`/`). Use `Init DB` to create and seed.
- Stage 2:
  - Database schema: Categories, Suppliers, Locations, Products.
  - Requirement 1: Full CRUD for Products with dynamic category, supplier, and location selections.
  - Requirement 2: Products report with filters (category, supplier, price range, stock range) and stats (avg price, avg stock, total inventory value).
- Stage 3:
  - SQL Injection protection: SQLAlchemy ORM and raw prepared statements via `sqlalchemy.text()` with bound params.
  - Indexes: On `products(category_id)`, `products(supplier_id)`, `products(price)`, `products(location_id)` supporting filters and analysis.
  - Transactions: Transactional stock adjustments using parameterized SQL and transaction blocks.

## ERD (text)

- Categories(id PK, name unique)
- Suppliers(id PK, name unique, contact_email)
- Locations(id PK, name unique, address)
- Products(id PK, name, sku unique, price numeric, units_in_stock int, reorder_level int, created_at date,
  category_id FK->categories, supplier_id FK->suppliers, location_id FK->locations)

Indexes:
- ix_products_category on Products(category_id) — supports category filter
- ix_products_supplier on Products(supplier_id) — supports supplier filter
- ix_products_price on Products(price) — supports price range filters
- ix_products_location on Products(location_id) — supports location-based queries

## How to run (Windows PowerShell)

Prereqs: Python 3.12+ (already detected via `env10/`). If using the provided venv, activate it:

```powershell
# From repo root
. .\env10\Scripts\Activate.ps1
# Optional: install requirements if needed
pip install -r requirements.txt
```

Start the app:

```powershell
python .\app.py
```

Open http://127.0.0.1:5000 and click "Initialize & Seed DB" once. Then:
- Manage Products: Create/Edit/Delete; category, supplier, and location lists are populated from the database.
- Reports: Filter by category/supplier/price/stock and view stats + chart.

## Modern UX upgrades

- CSRF protection via Flask-WTF (all POST forms include `csrf_token`).
- Meetings list uses DataTables (search, sort, pagination).
- Organizers select uses Select2 (multi-select with search and clear).
- Reports show stat cards and an interactive Chart.js visualization.
- Light/Dark theme toggle with localStorage and small custom CSS.

## Where to show each requirement in the demo

- Stage 1: `/` shows a Hello page. Show Flask is running and DB can be initialized.
- Requirement 1 (CRUD): `/products`, `/products/new`, `/products/<id>/edit` with dynamic lists.
- Requirement 2 (Report): `/reports/products` with live stats. Change data and refresh to show impacts.

## SQL injection protection

- All CRUD routes use SQLAlchemy ORM (parameter binding under the hood).
- Transactional increment endpoint uses a raw prepared statement with parameter binding:
  - See route `meetings_txn_increment` using `sqlalchemy.text()` and bound params `:inc`, `:mid`.

## Validation

- Server-side validation clamps values and ensures non-negative stock and price.

## Transactions and isolation

- App config sets `isolation_level = SERIALIZABLE` for the SQLite engine (strictest isolation supported by SQLite) for demo purposes.
- Editing a meeting replaces its organizers inside a transaction (`with db.session.begin():`).
- The increment-accepted action runs inside a transaction to avoid lost updates.

Notes: SQLite serializes writes; for multi-user concurrency, a server DB (Postgres/MySQL) would allow finer-grained locks and MVCC.

## Deployment (optional extra credit)

- Google App Engine (Standard, Python 3.11):
  - Files added: `app.yaml`, `.gcloudignore` (and `gunicorn` in requirements).
  - By default, `DATABASE_URL` is set to `sqlite:////tmp/app.db` in `app.yaml` which is writable on App Engine Standard for demo/testing.
  - For production/extra credit, point `DATABASE_URL` to a Cloud SQL instance (Postgres/MySQL) and remove the SQLite file.

### Deploy steps (PowerShell / CMD)

```bash
# One-time: authenticate and set project
gcloud auth login
gcloud config set project <YOUR_GCP_PROJECT_ID>

# (Optional) create the App Engine app (choose a region, e.g., us-central)
gcloud app create --region=us-central

# Deploy
gcloud app deploy

# Open the app
gcloud app browse
```

After first deploy, visit your URL and click "Initialize & Seed DB" to create tables and sample data.

## Troubleshooting

- If templates not found: ensure you run from repo root so Flask can locate `/templates`.
- If DB locked errors on Windows: avoid running multiple instances; SQLite allows one writer at a time.
- To reset DB: delete `app.db` and re-run `Init DB`.

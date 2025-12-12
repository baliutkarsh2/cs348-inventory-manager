from datetime import date, datetime
from typing import List

import os
from flask import Flask, redirect, render_template, request, url_for, flash
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, text, event
from flask_wtf.csrf import CSRFProtect, generate_csrf


app = Flask(__name__)

# Detect database type from URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
IS_POSTGRES = DATABASE_URL.startswith("postgresql")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# Configure engine options based on database type
# MVCC (Multi-Version Concurrency Control):
# - PostgreSQL: Native MVCC with READ COMMITTED allows concurrent readers/writers
# - SQLite: WAL mode provides MVCC-like behavior (concurrent reads, non-blocking writes)
if IS_POSTGRES:
    # PostgreSQL with true MVCC - READ COMMITTED is the sweet spot for concurrency
    engine_options = {
        "isolation_level": "READ COMMITTED",  # MVCC: readers don't block writers, writers don't block readers
        "pool_size": 5,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
elif IS_SQLITE:
    # SQLite with WAL mode for MVCC-like concurrency
    engine_options = {
        "isolation_level": "SERIALIZABLE",  # SQLite default; WAL handles concurrency
        "connect_args": {"check_same_thread": False},  # Allow multi-threaded access
    }
else:
    engine_options = {}

app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-key"),
    SQLALCHEMY_DATABASE_URI=DATABASE_URL,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS=engine_options,
)


db = SQLAlchemy(app)
csrf = CSRFProtect(app)
app.jinja_env.globals['csrf_token'] = generate_csrf


# Enable WAL mode for SQLite (MVCC-like concurrency: readers don't block writers)
# This is registered on the Engine class, not instance, to work outside app context
if IS_SQLITE:
    from sqlalchemy import Engine
    
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")      # Write-Ahead Logging for concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")    # Good balance of safety and speed
        cursor.execute("PRAGMA busy_timeout=5000")     # Wait 5s if DB is locked
        cursor.execute("PRAGMA cache_size=-64000")     # 64MB cache
        cursor.close()


# ==========================
# Database Models (Inventory Domain)
# ==========================

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)


class Supplier(db.Model):
    __tablename__ = "suppliers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    contact_email = db.Column(db.String(200))


class Location(db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    address = db.Column(db.String(250))


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    units_in_stock = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.Date, nullable=False, default=date.today)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)

    category = db.relationship(Category)
    supplier = db.relationship(Supplier)
    location = db.relationship(Location)


# Helpful indexes for queries used by reports and UI filters
Index("ix_products_category", Product.category_id)
Index("ix_products_supplier", Product.supplier_id)
Index("ix_products_price", Product.price)
Index("ix_products_location", Product.location_id)


# ==========================
# Utility & Seed
# ==========================

def seed_if_empty():
    """Seed minimal data for Categories, Suppliers, Locations, and Products if tables are empty."""
    if Category.query.count() == 0:
        db.session.add_all([
            Category(name="Electronics"),
            Category(name="Office"),
            Category(name="Home"),
        ])
    if Supplier.query.count() == 0:
        db.session.add_all([
            Supplier(name="Acme Corp", contact_email="sales@acme.example"),
            Supplier(name="Globex", contact_email="contact@globex.example"),
        ])
    if Location.query.count() == 0:
        db.session.add_all([
            Location(name="Warehouse A", address="100 Industrial Way"),
            Location(name="Store 1", address="200 Main St"),
        ])
    db.session.commit()

    if Product.query.count() == 0:
        cat = Category.query.filter_by(name="Electronics").first()
        off = Category.query.filter_by(name="Office").first()
        acme = Supplier.query.filter_by(name="Acme Corp").first()
        glob = Supplier.query.filter_by(name="Globex").first()
        wh = Location.query.filter_by(name="Warehouse A").first()
        st = Location.query.filter_by(name="Store 1").first()
        db.session.add_all([
            Product(name="USB-C Cable", sku="USB-C-1M", price=9.99, units_in_stock=120, reorder_level=20, category_id=cat.id, supplier_id=acme.id, location_id=wh.id),
            Product(name="Mechanical Keyboard", sku="KEY-MECH-87", price=79.99, units_in_stock=25, reorder_level=5, category_id=cat.id, supplier_id=glob.id, location_id=st.id),
            Product(name="Printer Paper A4", sku="PAPER-A4-500", price=6.49, units_in_stock=300, reorder_level=50, category_id=off.id, supplier_id=acme.id, location_id=wh.id),
        ])
        db.session.commit()


# ==========================
# Routes - Navigation & Setup
# ==========================

_DB_INITIALIZED = False

@app.before_request
def _ensure_db():
    global _DB_INITIALIZED
    if not _DB_INITIALIZED:
        with app.app_context():
            db.create_all()
        _DB_INITIALIZED = True

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/init-db")
def init_db():
    db.create_all()
    seed_if_empty()
    flash("Database initialized and seeded.", "success")
    return redirect(url_for("index"))


# ==========================
# Routes - Products CRUD
# ==========================

def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


@app.route("/products")
def products_list():
    products = Product.query.order_by(Product.created_at.desc(), Product.name.asc()).all()
    return render_template("products_list.html", products=products)


@app.route("/products/new")
def products_new():
    categories = Category.query.order_by(Category.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    locations = Location.query.order_by(Location.name).all()
    return render_template("product_form.html", action="create", product=None, categories=categories, suppliers=suppliers, locations=locations)


@app.route("/products", methods=["POST"])
def products_create():
    d = request.form
    p = Product(
        name=d.get("name", "").strip(),
        sku=d.get("sku", "").strip(),
        price=max(0, float(d.get("price", 0) or 0)),
        units_in_stock=max(0, _parse_int(d.get("units_in_stock"), 0)),
        reorder_level=max(0, _parse_int(d.get("reorder_level"), 0)),
        category_id=int(d.get("category_id")),
        supplier_id=int(d.get("supplier_id")),
        location_id=int(d.get("location_id")),
        created_at=datetime.strptime(d.get("created_at"), "%Y-%m-%d").date() if d.get("created_at") else date.today(),
    )
    if not p.name or not p.sku:
        flash("Name and SKU are required.", "danger")
        return redirect(url_for("products_new"))
    db.session.add(p)
    db.session.commit()
    flash("Product created.", "success")
    return redirect(url_for("products_list"))


@app.route("/products/<int:product_id>/edit")
def products_edit(product_id: int):
    p = Product.query.get_or_404(product_id)
    categories = Category.query.order_by(Category.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    locations = Location.query.order_by(Location.name).all()
    return render_template("product_form.html", action="update", product=p, categories=categories, suppliers=suppliers, locations=locations)


@app.route("/products/<int:product_id>/update", methods=["POST"])
def products_update(product_id: int):
    p = Product.query.get_or_404(product_id)
    d = request.form
    p.name = d.get("name", "").strip()
    p.sku = d.get("sku", "").strip()
    p.price = max(0, float(d.get("price", 0) or 0))
    p.units_in_stock = max(0, _parse_int(d.get("units_in_stock"), 0))
    p.reorder_level = max(0, _parse_int(d.get("reorder_level"), 0))
    p.category_id = int(d.get("category_id"))
    p.supplier_id = int(d.get("supplier_id"))
    p.location_id = int(d.get("location_id"))
    p.created_at = datetime.strptime(d.get("created_at"), "%Y-%m-%d").date() if d.get("created_at") else p.created_at
    if not p.name or not p.sku:
        flash("Name and SKU are required.", "danger")
        return redirect(url_for("products_edit", product_id=product_id))
    db.session.commit()
    flash("Product updated.", "success")
    return redirect(url_for("products_list"))


@app.route("/products/<int:product_id>/delete", methods=["POST"])
def products_delete(product_id: int):
    with db.session.begin():
        Product.query.filter_by(id=product_id).delete()
    flash("Product deleted.", "success")
    return redirect(url_for("products_list"))


@app.route("/products/<int:product_id>/txn-adjust", methods=["POST"])
def products_txn_adjust(product_id: int):
    """Transactional stock adjustment using parameterized raw SQL."""
    inc = _parse_int(request.form.get("inc", "0"), 0)
    # Ensure non-negative stock
    stmt = text(
        """
        UPDATE products
        SET units_in_stock = MAX(units_in_stock + :inc, 0)
        WHERE id = :pid
        """
    )
    with db.session.begin():
        db.session.execute(stmt, {"inc": inc, "pid": product_id})
    flash("Stock adjusted.", "success")
    return redirect(url_for("products_list"))


# ==========================
# Error Handlers
# ==========================

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html"), 500


# ==========================
# Routes - Reports (Products)
# ==========================

@app.route("/reports/products")
def products_report():
    categories = Category.query.order_by(Category.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()

    category_id = request.args.get("category_id")
    supplier_id = request.args.get("supplier_id")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")
    min_stock = request.args.get("min_stock")
    max_stock = request.args.get("max_stock")

    q = Product.query
    if category_id and category_id.isdigit():
        q = q.filter(Product.category_id == int(category_id))
    if supplier_id and supplier_id.isdigit():
        q = q.filter(Product.supplier_id == int(supplier_id))
    if min_price:
        q = q.filter(Product.price >= float(min_price))
    if max_price:
        q = q.filter(Product.price <= float(max_price))
    if min_stock:
        q = q.filter(Product.units_in_stock >= int(min_stock))
    if max_stock:
        q = q.filter(Product.units_in_stock <= int(max_stock))

    results: List[Product] = q.order_by(Product.name.asc()).all()

    # Stats
    if results:
        avg_price = float(sum(float(p.price) for p in results) / len(results))
        avg_stock = sum(p.units_in_stock for p in results) / len(results)
        total_value = float(sum(float(p.price) * p.units_in_stock for p in results))
    else:
        avg_price = avg_stock = total_value = 0.0

    labels_json = json.dumps([p.name for p in results])
    prices_json = json.dumps([float(p.price) for p in results])
    stocks_json = json.dumps([p.units_in_stock for p in results])

    return render_template(
        "report_products.html",
        categories=categories,
        suppliers=suppliers,
        results=results,
        avg_price=avg_price,
        avg_stock=avg_stock,
        total_value=total_value,
        labels_json=labels_json,
        prices_json=prices_json,
        stocks_json=stocks_json,
    )


if __name__ == "__main__":
    app.run(debug=True)

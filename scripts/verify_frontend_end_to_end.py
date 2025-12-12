"""
Verify that the FRONTEND endpoints properly fetch from and update the database:
- Confirms dynamic dropdowns on /products/new are populated from DB
- Creates a product via POST, updates it, adjusts stock transactionally, and deletes it
- Confirms /reports/products shows filtered results

Run:
  python scripts/verify_frontend_end_to_end.py
"""

from datetime import date
import os
import sys

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app, db, seed_if_empty, Category, Supplier, Location, Product  # type: ignore


def assert_in(content: bytes, needle: str, ctx: str):
    if needle.encode() not in content:
        raise AssertionError(f"Expected '{needle}' not found in response for {ctx}")


def main():
    # Use testing mode and disable CSRF for programmatic form posts
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.create_all()
        seed_if_empty()

        # Ensure clean slate for our test SKU
        Product.query.filter_by(sku="FE2E2-TEST-SKU").delete()
        db.session.commit()

        client = app.test_client()

        # 1) Dynamic dropdowns on /products/new
        r = client.get("/products/new")
        assert r.status_code == 200
        # Expect seeded category/supplier/location names to appear as <option>
        assert_in(r.data, "Electronics", "/products/new categories")
        assert_in(r.data, "Acme Corp", "/products/new suppliers")
        assert_in(r.data, "Warehouse A", "/products/new locations")

        # Look up ids for posting the form
        cat = Category.query.filter_by(name="Electronics").first()
        sup = Supplier.query.filter_by(name="Acme Corp").first()
        loc = Location.query.filter_by(name="Warehouse A").first()
        assert cat and sup and loc

        # 2) Create a product (INSERT)
        form_create = {
            "name": "FE2E2 Test Product",
            "sku": "FE2E2-TEST-SKU",
            "price": "19.99",
            "units_in_stock": "12",
            "reorder_level": "3",
            "category_id": str(cat.id),
            "supplier_id": str(sup.id),
            "location_id": str(loc.id),
            "created_at": date.today().strftime("%Y-%m-%d"),
        }
        r = client.post("/products", data=form_create, follow_redirects=True)
        assert r.status_code == 200
        assert_in(r.data, "FE2E2 Test Product", "products list after create")

        p = Product.query.filter_by(sku="FE2E2-TEST-SKU").first()
        assert p is not None

        # 3) Update the product (UPDATE)
        form_update = {
            "name": "FE2E2 Test Product (Updated)",
            "sku": "FE2E2-TEST-SKU",
            "price": "21.50",
            "units_in_stock": "15",
            "reorder_level": "4",
            "category_id": str(cat.id),
            "supplier_id": str(sup.id),
            "location_id": str(loc.id),
            "created_at": date.today().strftime("%Y-%m-%d"),
        }
        r = client.post(f"/products/{p.id}/update", data=form_update, follow_redirects=True)
        assert r.status_code == 200
        assert_in(r.data, "FE2E2 Test Product (Updated)", "products list after update")

        # 4) Transactional stock adjust (raw SQL with params)
        # Ensure no lingering session state between requests in tests
        db.session.remove()
        r = client.post(f"/products/{p.id}/txn-adjust", data={"inc": "-5"}, follow_redirects=True)
        assert r.status_code == 200
        p = db.session.get(Product, p.id)
        assert p.units_in_stock == 10  # 15 + (-5)

        # 5) Report with filters should include our product
        r = client.get(f"/reports/products?category_id={cat.id}&min_price=0&max_price=1000")
        assert r.status_code == 200
        assert_in(r.data, "FE2E2 Test Product (Updated)", "report filtered results")

        # 6) Delete (DELETE)
        db.session.remove()
        r = client.post(f"/products/{p.id}/delete", data={}, follow_redirects=True)
        assert r.status_code == 200
        assert Product.query.filter_by(id=p.id).first() is None

        print("Frontend E2E verification: PASS")


if __name__ == "__main__":
    main()

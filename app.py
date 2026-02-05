from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = "shivam-secret-key"

# ================= CONFIG =================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")

db = SQLAlchemy(app)

# ================= PREDEFINED CATEGORIES =================
PREDEFINED_CATEGORIES = [
    "Grains & Pulses",
    "Spices",
    "Cooking Oil & Ghee",
    "Sugar & Sweeteners",
    "Beverages",
    "Dairy Products",
    "Fruits",
    "Vegetables",
    "Snacks & Biscuits",
    "Instant Food",
    "Bakery Items",
    "Frozen Foods",
    "Dry Fruits & Nuts",
    "Personal Care",
    "Household Cleaning",
    "Baby Care",
    "Pet Food",
    "Stationery",
    "Pooja Items",
    "Others"
]

# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))


class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    image = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    subcategory_id = db.Column(db.Integer, db.ForeignKey("sub_category.id"))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100))
    items = db.Column(db.String(500))
    total = db.Column(db.Float)
    payment_method = db.Column(db.String(50))


# ================= INIT =================
with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(email="admin@shivam.com").first():
        db.session.add(Admin(email="admin@shivam.com", password="admin123"))
        db.session.commit()


# ================= CUSTOMER =================

@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db.session.add(User(
            name=request.form["name"],
            email=request.form["email"],
            password=request.form["password"]
        ))
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            email=request.form["email"],
            password=request.form["password"]
        ).first()
        if user:
            session["user"] = user.name
            session["cart"] = []
            return redirect(url_for("products"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/products")
def products():
    if "user" not in session:
        return redirect(url_for("login"))

    category_id = request.args.get("category")
    if category_id:
        products = Product.query.filter_by(category_id=category_id).all()
    else:
        products = Product.query.all()

    return render_template(
        "products.html",
        products=products,
        categories=Category.query.all()
    )


@app.route("/add-to-cart/<int:id>", methods=["POST"])
def add_to_cart(id):
    product = Product.query.get_or_404(id)
    session["cart"].append({"name": product.name, "price": product.price})
    session.modified = True
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    total = sum(i["price"] for i in session.get("cart", []))
    return render_template("cart.html", cart=session["cart"], total=total)


@app.route("/place-order", methods=["POST"])
def place_order():
    order = Order(
        user_name=session["user"],
        items=", ".join(i["name"] for i in session["cart"]),
        total=sum(i["price"] for i in session["cart"]),
        payment_method=request.form["payment"]
    )
    db.session.add(order)
    db.session.commit()
    session["cart"] = []
    return render_template("success.html")


# ================= ADMIN =================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        admin = Admin.query.filter_by(
            email=request.form["email"],
            password=request.form["password"]
        ).first()
        if admin:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    return render_template(
        "admin_dashboard.html",
        products=Product.query.all(),
        orders=Order.query.all(),
        categories=Category.query.all()
    )


@app.route("/admin/categories", methods=["GET", "POST"])
def admin_categories():
    if request.method == "POST":
        db.session.add(Category(name=request.form["name"]))
        db.session.commit()
    return render_template("categories.html", categories=Category.query.all())


@app.route("/admin/subcategories/<int:id>", methods=["GET", "POST"])
def admin_subcategories(id):
    if request.method == "POST":
        db.session.add(SubCategory(
            name=request.form["name"],
            category_id=id
        ))
        db.session.commit()

    return render_template(
        "subcategories.html",
        category=Category.query.get(id),
        subs=SubCategory.query.filter_by(category_id=id).all()
    )


@app.route("/admin/add-product", methods=["GET", "POST"])
def add_product():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        # CATEGORY
        cat_name = request.form["category"].strip()
        category = Category.query.filter_by(name=cat_name).first()
        if not category:
            category = Category(name=cat_name)
            db.session.add(category)
            db.session.commit()

        # SUBCATEGORY
        sub_name = request.form["subcategory"].strip()
        subcategory = SubCategory.query.filter_by(
            name=sub_name,
            category_id=category.id
        ).first()
        if not subcategory:
            subcategory = SubCategory(
                name=sub_name,
                category_id=category.id
            )
            db.session.add(subcategory)
            db.session.commit()

        # IMAGE
        file = request.files["image"]
        filename = file.filename
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # PRODUCT
        product = Product(
            name=request.form["name"],
            price=float(request.form["price"]),
            image=filename,
            category_id=category.id,
            subcategory_id=subcategory.id
        )
        db.session.add(product)
        db.session.commit()

        return redirect(url_for("admin_dashboard"))

    return render_template(
        "add_product.html",
        categories=PREDEFINED_CATEGORIES
    )


@app.route("/admin/delete-product/<int:id>")
def delete_product(id):
    db.session.delete(Product.query.get(id))
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/orders")
def admin_orders():
    return render_template("admin_orders.html", orders=Order.query.all())


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)

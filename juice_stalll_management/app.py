from flask import Flask, render_template, request, redirect, url_for, session
from bson.objectid import ObjectId

from db import products, customers, orders, ingredients, reviews


app = Flask(__name__)

app.secret_key = "juice-stall-secret-key"


# -------------------------------------------------
# Admin Login Protection
# -------------------------------------------------
def admin_required():
    return session.get("admin_logged_in")


# -------------------------------------------------
# Home Page
# -------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html")


# -------------------------------------------------
# MongoDB Connection Test
# -------------------------------------------------
@app.route("/test")
def test():

    total_products = products.count_documents({})
    total_customers = customers.count_documents({})
    total_orders = orders.count_documents({})
    total_reviews = reviews.count_documents({})

    return f"""
    <h1>MongoDB Connected Successfully</h1>

    <h3>Total Products: {total_products}</h3>
    <h3>Total Customers: {total_customers}</h3>
    <h3>Total Orders: {total_orders}</h3>
    <h3>Total Reviews: {total_reviews}</h3>

    <br>

    <a href="/">Back to Home</a>
    """


# -------------------------------------------------
# Branch Selection Page
# -------------------------------------------------
@app.route("/branches")
def branch_selection():

    branch_list = [
        {
            "id": 1,
            "name": "Dhanmondi Branch",
            "address": "House 42, Road 27, Dhanmondi, Dhaka"
        },
        {
            "id": 2,
            "name": "Gulshan Branch",
            "address": "Plot 15, Gulshan Avenue, Gulshan-1, Dhaka"
        },
        {
            "id": 3,
            "name": "Banani Branch",
            "address": "Road 11, Block E, Banani, Dhaka"
        }
    ]

    return render_template(
        "branches.html",
        branches=branch_list
    )


# -------------------------------------------------
# Customer Welcome Page
# -------------------------------------------------
@app.route("/customer/<int:branch_id>")
def customer_home(branch_id):

    branch_list = {
        1: {
            "id": 1,
            "name": "Dhanmondi Branch",
            "address": "House 42, Road 27, Dhanmondi, Dhaka"
        },
        2: {
            "id": 2,
            "name": "Gulshan Branch",
            "address": "Plot 15, Gulshan Avenue, Gulshan-1, Dhaka"
        },
        3: {
            "id": 3,
            "name": "Banani Branch",
            "address": "Road 11, Block E, Banani, Dhaka"
        }
    }

    branch = branch_list.get(branch_id)

    if branch is None:
        return redirect(url_for("branch_selection"))

    session["branch_id"] = branch_id

    return render_template(
        "customer_home.html",
        branch=branch
    )


# -------------------------------------------------
# Admin Login
# -------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    error = None

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "admin123":

            session["admin_logged_in"] = True
            session["admin_username"] = username

            return redirect(url_for("admin_dashboard"))

        error = "Invalid username or password."

    return render_template(
        "admin_login.html",
        error=error
    )


# -------------------------------------------------
# Admin Dashboard
# -------------------------------------------------
@app.route("/admin/dashboard")
def admin_dashboard():

    if not admin_required():
        return redirect(url_for("admin_login"))

    total_products = products.count_documents({})
    total_customers = customers.count_documents({})
    total_orders = orders.count_documents({})

    low_stock_items = ingredients.count_documents({
        "$expr": {
            "$lte": [
                "$current_stock",
                "$reorder_level"
            ]
        }
    })

    dashboard_data = {
        "total_juices": total_products,
        "total_customers": total_customers,
        "total_orders": total_orders,
        "total_sales": 0,
        "low_stock_items": low_stock_items,
        "pending_orders": 0
    }

    return render_template(
        "admin_dashboard.html",
        data=dashboard_data,
        username=session.get("admin_username")
    )


# -------------------------------------------------
# Manage Juices - Read, Search and Filter
# -------------------------------------------------
@app.route("/admin/juices")
def manage_juices():

    if not admin_required():
        return redirect(url_for("admin_login"))

    search_text = request.args.get("search", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()

    query = {}

    if search_text:
        query["name"] = {
            "$regex": search_text,
            "$options": "i"
        }

    price_conditions = {}

    if min_price:
        try:
            price_conditions["$gte"] = float(min_price)
        except ValueError:
            pass

    if max_price:
        try:
            price_conditions["$lte"] = float(max_price)
        except ValueError:
            pass

    if price_conditions:
        query["price"] = price_conditions

    juice_list = list(
        products.find(query).sort("id", 1)
    )

    return render_template(
        "manage_juices.html",
        juices=juice_list,
        search_text=search_text,
        min_price=min_price,
        max_price=max_price
    )


# -------------------------------------------------
# Add Juice - Create
# -------------------------------------------------
@app.route("/admin/juices/add", methods=["GET", "POST"])
def add_juice():

    if not admin_required():
        return redirect(url_for("admin_login"))

    error = None

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "").strip()

        if not name:
            error = "Juice name is required."

        elif not price:
            error = "Price is required."

        else:
            try:
                price_value = float(price)

                last_product = products.find_one(
                    sort=[("id", -1)]
                )

                if last_product and isinstance(last_product.get("id"), (int, float)):
                    next_id = int(last_product["id"]) + 1
                else:
                    next_id = 1

                juice_document = {
                    "id": next_id,
                    "name": name,
                    "description": description,
                    "price": price_value
                }

                products.insert_one(juice_document)

                return redirect(
                    url_for("manage_juices")
                )

            except ValueError:
                error = "Enter a valid price."

    return render_template(
        "add_juice.html",
        error=error
    )


# -------------------------------------------------
# Edit Juice - Update
# -------------------------------------------------
@app.route("/admin/juices/edit/<juice_id>", methods=["GET", "POST"])
def edit_juice(juice_id):

    if not admin_required():
        return redirect(url_for("admin_login"))

    try:
        object_id = ObjectId(juice_id)
    except Exception:
        return redirect(url_for("manage_juices"))

    juice = products.find_one({
        "_id": object_id
    })

    if juice is None:
        return redirect(url_for("manage_juices"))

    error = None

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "").strip()

        if not name:
            error = "Juice name is required."

        elif not price:
            error = "Price is required."

        else:
            try:
                price_value = float(price)

                products.update_one(
                    {
                        "_id": object_id
                    },
                    {
                        "$set": {
                            "name": name,
                            "description": description,
                            "price": price_value
                        }
                    }
                )

                return redirect(
                    url_for("manage_juices")
                )

            except ValueError:
                error = "Enter a valid price."

    return render_template(
        "edit_juice.html",
        juice=juice,
        error=error
    )


# -------------------------------------------------
# Delete Juice - Delete
# -------------------------------------------------
@app.route("/admin/juices/delete/<juice_id>", methods=["POST"])
def delete_juice(juice_id):

    if not admin_required():
        return redirect(url_for("admin_login"))

    try:
        object_id = ObjectId(juice_id)

        products.delete_one({
            "_id": object_id
        })

    except Exception:
        pass

    return redirect(
        url_for("manage_juices")
    )

# -------------------------------------------------
# Inventory Management
# -------------------------------------------------

@app.route("/admin/inventory")
def inventory():

    if not admin_required():
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "")

    if search:
        ingredient_list = list(
            ingredients.find({
                "name": {
                    "$regex": search,
                    "$options": "i"
                }
            }).sort("id", 1)
        )
    else:
        ingredient_list = list(
            ingredients.find().sort("id", 1)
        )

    return render_template(
        "inventory.html",
        ingredients=ingredient_list
    )


# -------------------------------------------------
# Add Ingredient
# -------------------------------------------------

@app.route("/admin/inventory/add", methods=["GET", "POST"])
def add_inventory():

    if not admin_required():
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        last = ingredients.find_one(sort=[("id", -1)])

        next_id = 1

        if last:
            next_id = last["id"] + 1

        ingredients.insert_one({

            "id": next_id,

            "name": request.form["name"],

            "unit": request.form["unit"],

            "current_stock": float(request.form["current_stock"]),

            "reorder_level": float(request.form["reorder_level"]),

            "cost_per_unit": float(request.form["cost_per_unit"])

        })

        return redirect(url_for("inventory"))

    return render_template("add_inventory.html")


# -------------------------------------------------
# Edit Ingredient
# -------------------------------------------------

@app.route("/admin/inventory/edit/<id>", methods=["GET", "POST"])
def edit_inventory(id):

    if not admin_required():
        return redirect(url_for("admin_login"))

    ingredient = ingredients.find_one(
        {"_id": ObjectId(id)}
    )

    if request.method == "POST":

        ingredients.update_one(

            {"_id": ObjectId(id)},

            {
                "$set": {

                    "name": request.form["name"],

                    "unit": request.form["unit"],

                    "current_stock": float(request.form["current_stock"]),

                    "reorder_level": float(request.form["reorder_level"]),

                    "cost_per_unit": float(request.form["cost_per_unit"])

                }
            }
        )

        return redirect(url_for("inventory"))

    return render_template(
        "edit_inventory.html",
        ingredient=ingredient
    )


# -------------------------------------------------
# Delete Ingredient
# -------------------------------------------------

@app.route("/admin/inventory/delete/<id>")
def delete_inventory(id):

    if not admin_required():
        return redirect(url_for("admin_login"))

    ingredients.delete_one(
        {"_id": ObjectId(id)}
    )

    return redirect(url_for("inventory"))
# -------------------------------------------------
# Admin Logout
# -------------------------------------------------
@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(url_for("home"))


# -------------------------------------------------
# Run Flask
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
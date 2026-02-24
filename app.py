# File: app.py (BASE VERSION - PART 1/3)
from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
from uuid import uuid4
import qr_generator
import db, os, json
import random
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()  # Load environment variables

app = Flask(__name__)

# Security-focused configuration
app.secret_key = os.environ.get("SECRET_KEY") or str(uuid4())
if not os.environ.get("SECRET_KEY"):
    print("⚠️ SECRET_KEY not set. Generated ephemeral key for this run.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production"
)

# Initialize database on startup
db.init_db()

# =========================
# CONFIGURATION
# =========================
ADMIN_CODE = os.environ.get("ADMIN_CODE")
if not ADMIN_CODE:
    ADMIN_CODE = str(uuid4())
    print("⚠️ ADMIN_CODE not set. Admin elevation disabled with one-time runtime code.")
TABLE_SESSION_EXPIRY_HOURS = 2
TAX_RATE = 5.0  # 5% GST
SERVICE_CHARGE_RATE = 10.0  # 10% service charge
EDIT_WINDOW_MINUTES = 15

# =========================
# MENU DATA
# =========================
menu_card = {
    "Pizza": {
        "Margherita": 199,
        "Farmhouse": 249,
        "Peppy Paneer": 269,
        "Veg Extravaganza": 299,
        "Cheese Burst": 319
    },
    "Burger": {
        "Veg Burger": 70,
        "Cheese Burger": 90,
        "Paneer Burger": 120,
        "Double Patty Burger": 150
    },
    "Sandwich": {
        "Veg Sandwich": 60,
        "Grilled Sandwich": 80,
        "Cheese Grill": 100,
        "Paneer Sandwich": 120
    },
    "Pasta": {
        "White Sauce Pasta": 180,
        "Red Sauce Pasta": 160,
        "Pink Sauce Pasta": 200,
        "Cheese Pasta": 220
    },
    "Tacos": {
        "Veg Taco": 55,
        "Cheese Taco": 75,
        "Paneer Taco": 95
    },
    "Wraps": {
        "Veg Wrap": 90,
        "Paneer Wrap": 120,
        "Cheese Wrap": 110
    },
    "Snacks": {
        "French Fries": 60,
        "Peri Peri Fries": 80,
        "Cheese Fries": 100,
        "Garlic Bread": 90
    },
    "Dessert": {
        "Chocolate Brownie": 99,
        "Ice Cream": 79,
        "Chocolate Lava Cake": 129,
        "Waffle": 149
    },
    "Drinks": {
        "Cold Drink": 30,
        "Fresh Lime Soda": 50,
        "Cold Coffee": 90,
        "Milkshake": 110
    }
}

# =========================
# HELPER FUNCTIONS
# =========================
def login_required_check():
    """Check if user or table is logged in"""
    return "user" in session or ("table" in session and "session_token" in session)

def get_cart():
    """Get cart from session"""
    return session.get("cart", {})

def item_exists(item_name):
    """Check if item exists in menu"""
    for category in menu_card.values():
        if item_name in category:
            return True
    return False

def get_item_price(item_name):
    """Get price of an item"""
    for category in menu_card.values():
        if item_name in category:
            return category[item_name]
    return 0

def calculate_cart_total(cart):
    """Calculate total for cart"""
    total = 0
    for item, quantity in cart.items():
        price = get_item_price(item)
        total += price * quantity
    return total

def calculate_bill_breakdown(subtotal):
    """Calculate tax and service charges"""
    tax_amount = round(subtotal * TAX_RATE / 100, 2)
    service_charge = round(subtotal * SERVICE_CHARGE_RATE / 100, 2)
    grand_total = subtotal + tax_amount + service_charge

    return {
        "subtotal": subtotal,
        "tax_rate": TAX_RATE,
        "tax_amount": tax_amount,
        "service_charge_rate": SERVICE_CHARGE_RATE,
        "service_charge_amount": service_charge,
        "grand_total": grand_total
    }

def parse_order_items(items_string):
    """Parse order items string into list of dictionaries"""
    items = []
    if not items_string:
        return items

    for line in items_string.strip().split("\n"):
        if not line.strip():
            continue

        if " x " in line:
            name, qty = line.split(" x ")
            name = name.strip()
            quantity = int(qty.strip())
        else:
            name = line.strip()
            quantity = 1

        price = get_item_price(name)
        if price > 0:
            items.append({
                "name": name,
                "quantity": quantity,
                "price_per": price,
                "total": price * quantity
            })

    return items

# =========================
# DECORATORS
# =========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not login_required_check():
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401
        if not db.is_user_admin(session["user"]):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def table_session_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        table_id = session.get("table")
        session_token = session.get("session_token")

        if not table_id or not session_token:
            return jsonify({"error": "Table session expired"}), 401

        if not db.validate_table_session(table_id, session_token):
            session.pop("table", None)
            session.pop("session_token", None)
            return jsonify({"error": "Table session expired"}), 401

        return f(*args, **kwargs)
    return decorated_function

# =========================
# ORDER FUNCTIONS
# =========================
def check_edit_window(order_id):
    """Check if order can still be edited"""
    return db.can_edit_order(order_id)

def lock_order_if_time_expired(order_id):
    """Automatically lock order if edit window expired"""
    if not check_edit_window(order_id):
        db.create_order_lock(order_id, "edit_window_expired", "system", 0, 0)
        return True
    return False

def generate_order_bill(order_id):
    """Generate bill for order"""
    bill = db.generate_bill(order_id)
    if bill:
        # Create notification
        order = db.get_order_by_id(order_id)
        if order and order.get('user_id'):
            msg = f"Bill generated for Order #{order_id}. Amount: â‚¹{bill['grand_total']}"
            db.create_notification(order_id, order['user_id'],
                                 order.get('table_id'), msg, "bill_generated")
    return bill

def save_cart_to_order(cart, user_id=None, table_id=None, session_token=None, guest_name=None):
    """Save cart as an order"""
    if not cart:
        return None

    total = calculate_cart_total(cart)
    items = "\n".join([f"{item} x {quantity}" for item, quantity in cart.items()])

    order_id = db.save_order_with_features(
        user_id=user_id,
        items=items,
        total=total,
        cafe_name="MY CAFE",
        table_id=table_id,
        session_token=session_token,
        guest_name=guest_name
    )

    return order_id

# =========================
# MAIN ROUTES
# =========================
@app.route("/")
@login_required
def home():
    user = db.get_user(session.get("user", "")) if session.get("user") else None
    orders = db.get_orders(user["id"]) if user else []

    cafes_visited = len({o.get("cafe_name") or "MY CAFE" for o in orders}) if orders else 0
    total_spent = sum((o.get("total") or 0) for o in orders)
    total_orders = len(orders)

    return render_template(
        "home.html",
        total_orders=total_orders,
        cafes_visited=cafes_visited,
        total_spent=total_spent
    )


@app.route("/start")
@login_required
def start():
    """Redirect to QR scanner page first"""
    session.pop("table", None)
    session.pop("session_token", None)
    session["cart"] = {}  # Clear cart
    return redirect("/qr_scanner")

@app.route("/qr_scanner")
@login_required
def qr_scanner():
    """QR Scanner intermediate page"""
    # Clear any existing table session when coming here
    session.pop("table", None)
    session.pop("session_token", None)
    
    # Set the flag to indicate user came through QR scanner
    session["qr_scanner_completed"] = True  # ADD THIS LINE
    
    return render_template("qr_scanner.html")


@app.route("/order")
@login_required
def order():
    cart = get_cart()

    # Check if user has been through QR scanner OR has a table session
    # session.get("qr_scanner_completed") is True when coming from QR scanner
    if "table" not in session and not session.get("qr_scanner_completed"):
        return redirect("/qr_scanner")

    return render_template(
        "index.html",
        menu=menu_card,
        quantities=cart,
        total=calculate_cart_total(cart)
    )

@app.route("/add", methods=["POST"])
def add_item():
    if not login_required_check():
        return jsonify({"error": "Authentication required"}), 401

    data = request.json
    item = data.get("item")

    if not item or not item_exists(item):
        return jsonify({"error": "Invalid item"}), 400

    cart = get_cart()
    cart[item] = cart.get(item, 0) + 1
    session["cart"] = cart
    session["cart_last_updated"] = datetime.now().isoformat()

    return jsonify({
        "success": True,
        "cart": cart,
        "total": calculate_cart_total(cart),
        "item": item,
        "new_qty": cart[item]
    })

@app.route("/remove", methods=["POST"])
def remove_item():
    if not login_required_check():
        return jsonify({"error": "Authentication required"}), 401

    data = request.json
    item = data.get("item")

    if not item:
        return jsonify({"error": "Item required"}), 400

    cart = get_cart()
    if item in cart:
        cart[item] -= 1
        if cart[item] <= 0:
            del cart[item]

    session["cart"] = cart
    session["cart_last_updated"] = datetime.now().isoformat()

    return jsonify({
        "success": True,
        "cart": cart,
        "total": calculate_cart_total(cart)
    })

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/profile")
def profile():
    user = session.get("user")
    return render_template("profile.html", user=user)

@app.route('/finish', methods=['POST'])
def finish():
    if 'user' not in session:
        return redirect('/login')

    cart = session.get('cart', {})
    if not cart:
        return jsonify({'success': False, 'error': 'Cart is empty'})

    try:
        # Calculate total
        total = 0
        items_text = []
        for item, qty in cart.items():
            price = get_item_price(item)
            total += price * qty
            items_text.append(f"{item} x {qty}")

        items_str = "\n".join(items_text)

        # Save order
        order_id = db.save_order_with_features(
            user_id=session['user_id'],
            items=items_str,
            total=total,
            cafe_name="MY CAFE",
            table_id=session.get('table_id'),
            session_token=session.get('session_token'),
            guest_name=session.get('guest_name')
        )

        if order_id:
            # Clear cart
            session.pop('cart', None)
            session.pop('total', None)

            # Return success without alert
            return jsonify({
                'success': True,
                'order_id': order_id,
                'redirect': '/orders'  # Direct redirect URL
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to save order'})

    except Exception as e:
        print(f"Error in finish: {e}")
        return jsonify({'success': False, 'error': str(e)})
# =========================
# TABLE QR SYSTEM
# =========================
@app.route("/table/<table_no>")
def table_entry(table_no):
    table = db.get_table(table_no)
    if not table or not table.get("is_active"):
        return render_template("error.html", message="Table not available"), 404

    session_token = uuid4().hex
    db.create_table_session_with_expiry(table_no, session_token, None, TABLE_SESSION_EXPIRY_HOURS)

    session["table"] = table_no
    session["session_token"] = session_token
    session["cart"] = {}

    return redirect("/order")

@app.route("/api/table/session/validate", methods=["POST"])
def validate_table_session_api():
    data = request.json
    table_id = data.get("table_id")
    session_token = data.get("session_token")

    if not table_id or not session_token:
        return jsonify({"valid": False, "error": "Missing parameters"}), 400

    valid = db.validate_table_session(table_id, session_token)

    return jsonify({
        "valid": valid,
        "table_id": table_id,
        "expires_in": f"{TABLE_SESSION_EXPIRY_HOURS} hours" if valid else "expired"
    })

# =========================
# ORDER MANAGEMENT ROUTES
# =========================
@app.route("/orders")
@login_required
def view_orders():
    user = db.get_user(session.get("user", ""))
    if not user:
        return redirect("/login")

    orders = db.order_join_user(user["id"])
    grouped_orders = {}

    for order in orders:
        cafe = order.get("cafe_name", "MY CAFE")
        grouped_orders.setdefault(cafe, []).append(order)

    return render_template("orders.html", grouped_orders=grouped_orders, menu=menu_card)

@app.route("/api/order/<int:order_id>/edit-window")
@login_required
def check_edit_window_api(order_id):
    order = db.get_order_by_id(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    # Authorization check
    user = db.get_user(session.get("user", ""))
    if user and order.get("user_id") != user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    can_edit = check_edit_window(order_id)

    return jsonify({
        "can_edit": can_edit,
        "order_id": order_id,
        "locked": order.get("locked", 0) == 1,
        "lock_reason": order.get("lock_reason"),
        "status": order.get("status")
    })

@app.route("/api/order/<int:order_id>/edit", methods=["POST"])
@login_required
def edit_order_api(order_id):
    if not check_edit_window(order_id):
        return jsonify({"error": "Edit window expired"}), 400

    order = db.get_order_by_id(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    # Authorization check
    user = db.get_user(session.get("user", ""))
    if user and order.get("user_id") != user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    data = request.json
    new_items = data.get("items")

    if not new_items:
        return jsonify({"error": "No items provided"}), 400

    # Parse and calculate new total
    items_list = parse_order_items(new_items)
    total = sum(item["total"] for item in items_list)

    # Update order in database
    conn = db.db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE orders 
            SET items = ?, total = ?
            WHERE id = ?
        """, (new_items, total, order_id))

        conn.commit()

        db.create_notification(order_id, order['user_id'],
                             order.get('table_id'),
                             f"Order #{order_id} was edited",
                             "order_edited")

        return jsonify({
            "success": True,
            "order_id": order_id,
            "new_total": total,
            "message": "Order updated successfully"
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/order/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order_api(order_id):
    if not check_edit_window(order_id):
        return jsonify({"error": "Cancel window expired"}), 400

    order = db.get_order_by_id(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    # Authorization check
    user = db.get_user(session.get("user", ""))
    if user and order.get("user_id") != user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    if db.update_order_status(order_id, "cancelled"):
        db.create_notification(order_id, order['user_id'],
                             order.get('table_id'),
                             f"Order #{order_id} was cancelled",
                             "order_cancelled")

        return jsonify({
            "success": True,
            "order_id": order_id,
            "message": "Order cancelled successfully"
        })

    return jsonify({"error": "Failed to cancel order"}), 500

# =========================
# BILL & PAYMENT ROUTES
# =========================
@app.route("/bill/<int:order_id>")
@login_required
def view_bill(order_id):
    # Get order
    order = db.get_order_by_id(order_id)
    if not order:
        return "Order not found", 404

    # Authorization check
    user = db.get_user(session.get("user", ""))
    if user and order.get("user_id") != user["id"] and not session.get('is_admin'):
        return "Not authorized", 403

    # Get or generate bill
    bill = db.get_bill(order_id)
    if not bill:
        bill = generate_order_bill(order_id)
        if not bill:
            # Try to generate bill with tax settings
            tax_settings = db.get_tax_settings()

            gst_rate = tax_settings['gst_rate'] if tax_settings['gst_enabled'] else 0
            service_charge_rate = tax_settings['service_charge_rate'] if tax_settings['service_charge_enabled'] else 0

            subtotal = float(order['total'])
            gst_amount = round((subtotal * gst_rate) / 100, 2)
            service_charge = round((subtotal * service_charge_rate) / 100, 2)
            grand_total = round(subtotal + gst_amount + service_charge, 2)

            bill_number = f"BILL-{order_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Insert bill
            conn = db.db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO bill_details 
                (order_id, subtotal, tax_rate, tax_amount, service_charge_rate, 
                 service_charge_amount, grand_total, bill_number, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (order_id, subtotal, gst_rate, gst_amount,
                  service_charge_rate, service_charge, grand_total, bill_number))

            cur.execute("UPDATE orders SET bill_generated = 1 WHERE id = ?", (order_id,))
            conn.commit()
            conn.close()

            bill = {
                "bill_number": bill_number,
                "subtotal": subtotal,
                "tax_rate": gst_rate,
                "tax_amount": gst_amount,
                "service_charge_rate": service_charge_rate,
                "service_charge_amount": service_charge,
                "grand_total": grand_total
            }

    # Parse items for display
    items = parse_order_items(order.get("items", ""))

    return render_template("bill.html",
                         order=order,
                         order_id=order_id,
                         bill=bill,
                         items=items,
                         bill_date=datetime.now().strftime("%Y-%m-%d %H:%M"))

@app.route("/api/order/<int:order_id>/bill")
@login_required
def get_order_bill_api(order_id):
    order = db.get_order_by_id(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    # Authorization check
    user = db.get_user(session.get("user", ""))
    if user and order.get("user_id") != user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    bill = db.get_bill(order_id)
    if not bill:
        bill = generate_order_bill(order_id)

    if not bill:
        return jsonify({"error": "Failed to generate bill"}), 500

    items = parse_order_items(order.get("items", ""))

    return jsonify({
        "success": True,
        "order_id": order_id,
        "bill_number": bill.get("bill_number"),
        "items": items,
        "subtotal": bill.get("subtotal"),
        "tax_rate": bill.get("tax_rate"),
        "tax_amount": bill.get("tax_amount"),
        "service_charge_rate": bill.get("service_charge_rate"),
        "service_charge_amount": bill.get("service_charge_amount"),
        "grand_total": bill.get("grand_total"),
        "generated_at": bill.get("generated_at"),
        "footer": {
            "powered_by": "MY CAFE",
            "data_usage": "Your data is securely stored and used only for order processing.",
            "gst_number": "GSTIN: 29ABCDE1234F1Z5",
            "contact": "Contact: 1800-MY-CAFE | support@mycafe.com"
        }
    })

# =========================
# AUTHENTICATION ROUTES
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        msg = None
        if request.args.get("created"):
            msg = "Account created successfully! Please login."
        return render_template("login.html", message=msg)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return render_template("login.html", error="Username and password are required."), 400

    user = db.get_user(username)
    if not user or not check_password_hash(user["password"], password):
        return render_template("login.html", error="Invalid username or password."), 401

    session["user"] = user["username"]
    session["user_id"] = user["id"]
    session["is_admin"] = bool(user.get("is_admin"))  # ✅ ADD THIS LINE

    return redirect("/")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()

    if not username or not password or not name or not email or not phone:
        return render_template("signup.html", error="All fields are required."), 400

    if len(password) < 8:
        return render_template("signup.html", error="Password must be at least 8 characters."), 400

    if db.user_exists(username):
        return render_template("signup.html", error="Username already exists. Try a different one."), 400

    hashed = generate_password_hash(password)
    success = db.create_user(username, hashed, name, email, phone)

    if success:
        return redirect("/login?created=1")
    else:
        return render_template("signup.html", error="Error creating account. Please try again."), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================
# ADMIN ROUTES - PART 2/3
# =========================
@app.route("/become-admin", methods=["GET", "POST"])
@login_required
def become_admin():
    if request.method == "GET":
        user = db.get_user(session.get("user"))
        is_admin = db.is_user_admin(session.get("user"))
        return render_template("become_admin.html", user=user, is_admin=is_admin, admin_code_configured=bool(ADMIN_CODE))
        return render_template("become_admin.html", user=user, is_admin=is_admin, admin_code_configured=bool(os.environ.get("ADMIN_CODE")))

    admin_code = request.form.get("admin_code", "").strip()

    if admin_code == ADMIN_CODE and os.environ.get("ADMIN_CODE"):
        db.make_user_admin(session.get("user"))
        session["is_admin"] = True
        return redirect("/?admin_success=1")

    return render_template(
        "become_admin.html",
        error="Invalid security code.",
        admin_code_configured=bool(ADMIN_CODE)
        admin_code_configured=bool(os.environ.get("ADMIN_CODE"))
    )

@app.route("/admin")
@admin_required
def admin_dashboard():
    all_orders = db.get_orders()
    today = datetime.now().strftime("%Y-%m-%d")
    today_orders = [o for o in all_orders if o.get("created_at", "").startswith(today)]

    stats = {
        "total_orders": len(all_orders),
        "today_orders": len(today_orders),
        "today_revenue": sum(o.get("total", 0) for o in today_orders if o.get("status") == "completed"),
        "pending_orders": len([o for o in all_orders if o.get("status") == "pending"]),
        "preparing_orders": len([o for o in all_orders if o.get("status") == "preparing"]),
        "ready_orders": len([o for o in all_orders if o.get("status") == "ready"]),
        "completed_orders": len([o for o in all_orders if o.get("status") == "completed"]),
        "cancelled_orders": len([o for o in all_orders if o.get("status") == "cancelled"]),
        "locked_orders": len([o for o in all_orders if o.get("locked") == 1])
    }

    recent_orders = all_orders[:10]
    return render_template("admin/dashboard.html", stats=stats, recent_orders=recent_orders)

@app.route("/admin/orders")
@admin_required
def admin_orders():
    all_orders = db.get_orders()
    orders_with_users = []

    for order in all_orders:
        user = db.get_user_by_id(order.get('user_id'))
        order['username'] = user['username'] if user else 'Guest'
        order['name'] = user['name'] if user else 'Guest'
        order['phone'] = user['phone'] if user else ''
        if not order.get('status'):
            order['status'] = 'pending'

        order['bill'] = db.get_bill(order['id'])
        items_string = order.get('items', '')
        order['items_list'] = parse_order_items(items_string) if isinstance(items_string, str) else []
        orders_with_users.append(order)

    return render_template("admin/kitchen.html", orders=orders_with_users)

@app.route("/admin/tables")
@admin_required
def admin_tables():
    conn = db.db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tables_config ORDER BY table_number")
    tables = cur.fetchall()
    conn.close()

    return render_template("admin/tables.html", tables=[dict(t) for t in tables])

@app.route("/admin/menu")
@admin_required
def admin_menu():
    menu_with_availability = db.get_menu_with_availability(menu_card)
    return render_template("admin/menu.html", menu=menu_card, menu_availability=menu_with_availability)

@app.route("/admin/analytics")
@admin_required
def admin_analytics():
    all_orders = db.get_orders()

    # Calculate analytics
    completed_orders = [o for o in all_orders if o.get("status") == "completed"]
    total_revenue = sum(o.get("total", 0) for o in completed_orders)

    # Daily stats for last 7 days
    daily_stats = []
    today = datetime.now()

    for i in range(6, -1, -1):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        day_orders = [o for o in all_orders if o.get("created_at", "").startswith(date)]
        day_revenue = sum(o.get("total", 0) for o in day_orders if o.get("status") == "completed")

        daily_stats.append({
            "date": date,
            "orders": len(day_orders),
            "revenue": day_revenue
        })

    # Top selling items
    item_sales = {}
    for order in completed_orders:
        items = parse_order_items(order.get("items", ""))
        for item in items:
            item_sales[item["name"]] = item_sales.get(item["name"], 0) + item["quantity"]

    top_items = sorted(item_sales.items(), key=lambda x: x[1], reverse=True)[:10]

    analytics_data = {
        "total_revenue": total_revenue,
        "total_orders": len(all_orders),
        "completed_orders": len(completed_orders),
        "avg_order_value": total_revenue // len(completed_orders) if completed_orders else 0,
        "daily_stats": daily_stats,
        "top_items": top_items
    }

    return render_template("admin/analytics.html", analytics=analytics_data)

@app.route("/admin/settings")
@admin_required
def admin_settings():
    user = db.get_user(session.get("user"))
    all_users = db.get_all_users()
    return render_template("admin/settings.html", user=user, all_users=all_users, admin_code_configured=bool(ADMIN_CODE))
    return render_template("admin/settings.html", user=user, all_users=all_users, admin_code_configured=bool(os.environ.get("ADMIN_CODE")))

# =========================
# ADMIN API ENDPOINTS - PART 3/3
# =========================
@app.route("/api/admin/search-orders")
@admin_required
def admin_search_orders():
    query = request.args.get("q", "").strip()

    conn = db.db_connection()
    cur = conn.cursor()

    if query:
        cur.execute("""
            SELECT o.*, u.username, u.name as user_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id LIKE ? OR 
                  o.guest_name LIKE ? OR 
                  u.username LIKE ? OR
                  u.name LIKE ? OR
                  o.table_id LIKE ?
            ORDER BY o.created_at DESC
            LIMIT 50
        """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
    else:
        cur.execute("""
            SELECT o.*, u.username, u.name as user_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 50
        """)

    orders = cur.fetchall()
    conn.close()

    return jsonify([dict(order) for order in orders])


@app.route("/admin/orders/<int:order_id>/force-complete", methods=["POST"])
@admin_required
def admin_force_complete(order_id):
    data = request.json
    reason = data.get("reason", "")

    user = db.get_user(session.get("user"))
    if not user:
        return jsonify({"error": "Admin not found"}), 404

    success = db.force_complete_order(order_id, user["id"], reason)

    if success:
        order = db.get_order_by_id(order_id)
        if order and order.get("user_id"):
            msg = f"Order #{order_id} marked as completed by admin"
            db.create_notification(order_id, order['user_id'],
                                 order.get('table_id'), msg, "admin_action")

        return jsonify({
            "success": True,
            "order_id": order_id,
            "action": "force_complete",
            "message": "Order force completed"
        })

    return jsonify({"error": "Failed to force complete order"}), 500

@app.route("/admin/orders/<int:order_id>/force-cancel", methods=["POST"])
@admin_required
def admin_force_cancel(order_id):
    data = request.json
    reason = data.get("reason", "")

    user = db.get_user(session.get("user"))
    if not user:
        return jsonify({"error": "Admin not found"}), 404

    success = db.force_cancel_order(order_id, user["id"], reason)

    if success:
        order = db.get_order_by_id(order_id)
        if order and order.get("user_id"):
            msg = f"Order #{order_id} cancelled by admin. Reason: {reason}"
            db.create_notification(order_id, order['user_id'],
                                 order.get('table_id'), msg, "admin_action")

        return jsonify({
            "success": True,
            "order_id": order_id,
            "action": "force_cancel",
            "message": "Order force cancelled"
        })

    return jsonify({"error": "Failed to force cancel order"}), 500

@app.route("/admin/orders/<int:order_id>/mark-paid", methods=["POST"])
@admin_required
def admin_mark_paid(order_id):
    data = request.json
    payment_method = data.get("payment_method", "cash")
    reason = data.get("reason", "")

    user = db.get_user(session.get("user"))
    if not user:
        return jsonify({"error": "Admin not found"}), 404

    success = db.mark_as_paid(order_id, user["id"], payment_method, reason)

    if success:
        order = db.get_order_by_id(order_id)
        if order and order.get("user_id"):
            msg = f"Order #{order_id} marked as paid ({payment_method})"
            db.create_notification(order_id, order['user_id'],
                                 order.get('table_id'), msg, "payment")

        return jsonify({
            "success": True,
            "order_id": order_id,
            "action": "mark_paid",
            "payment_method": payment_method,
            "message": "Order marked as paid"
        })

    return jsonify({"error": "Failed to mark order as paid"}), 500

@app.route("/admin/orders/<int:order_id>/lock", methods=["POST"])
@admin_required
def admin_lock_order(order_id):
    data = request.json
    lock_reason = data.get("reason", "admin_locked")
    can_edit = data.get("can_edit", 0)
    can_cancel = data.get("can_cancel", 0)

    user = db.get_user(session.get("user"))
    if not user:
        return jsonify({"error": "Admin not found"}), 404

    success = db.create_order_lock(order_id, lock_reason, user["username"], can_edit, can_cancel)

    if success:
        return jsonify({
            "success": True,
            "order_id": order_id,
            "locked": True,
            "lock_reason": lock_reason,
            "can_edit": bool(can_edit),
            "can_cancel": bool(can_cancel)
        })

    return jsonify({"error": "Failed to lock order"}), 500

@app.route("/admin/orders/<int:order_id>/unlock", methods=["POST"])
@admin_required
def admin_unlock_order(order_id):
    conn = db.db_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM order_locks WHERE order_id = ?", (order_id,))

        cur.execute("""
            UPDATE orders 
            SET locked = 0, lock_reason = NULL 
            WHERE id = ?
        """, (order_id,))

        conn.commit()

        return jsonify({
            "success": True,
            "order_id": order_id,
            "locked": False,
            "message": "Order unlocked"
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# =========================
# TABLE MANAGEMENT API
# =========================
@app.route("/admin/tables/setup", methods=["POST"])
@admin_required
def setup_tables():
    count = int(request.json.get("count", 0))
    if count <= 0:
        return jsonify({"error": "Invalid count"}), 400

    conn = db.db_connection()
    cur = conn.cursor()

    cur.execute("UPDATE tables_config SET is_active = 0")

    for i in range(1, count + 1):
        table_no = f"T{i}"

        cur.execute("""
            INSERT INTO tables_config (table_number, table_name, is_active)
            VALUES (?, ?, 1)
            ON CONFLICT(table_number)
            DO UPDATE SET is_active = 1
        """, (table_no, f"Table {i}"))

    conn.commit()
    conn.close()

    qr_generator.generate_all_tables(count)
    qr_generator.generate_qr_html_preview()

    return jsonify({"success": True, "tables": count})

@app.route("/admin/tables/generate", methods=["POST"])
@admin_required
def generate_tables():
    data = request.json
    count = int(data.get("count", 0))

    if count <= 0:
        return jsonify({"error": "Invalid table count"}), 400

    qr_generator.generate_all_tables(num_tables=count)
    qr_generator.generate_qr_html_preview()

    return jsonify({"success": True, "tables": count})

@app.route("/admin/tables/<table_no>/deactivate", methods=["POST"])
@admin_required
def deactivate_table(table_no):
    conn = db.db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE tables_config
        SET is_active = 0
        WHERE table_number = ?
    """, (table_no,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/admin/tables/<table_no>/regen-qr", methods=["POST"])
@admin_required
def regen_single_qr(table_no):
    qr_generator.generate_table_qr(table_no)
    return jsonify({"success": True})

@app.route("/admin/tables/add", methods=["POST"])
@admin_required
def add_new_tables():
    """Add new tables to existing ones (incremental)"""
    try:
        count = int(request.json.get("count", 0))

        if count <= 0 or count > 50:
            return jsonify({"error": "Please enter a number between 1 and 50"}), 400

        conn = db.db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT table_number FROM tables_config 
            WHERE table_number LIKE 'T%' 
            ORDER BY id DESC 
            LIMIT 1
        """)
        last_table = cur.fetchone()

        if last_table:
            last_num = int(last_table["table_number"][1:])
            start_num = last_num + 1
        else:
            start_num = 1

        new_tables = []

        for i in range(count):
            table_no = f"T{start_num + i}"
            table_name = f"Table {start_num + i}"

            cur.execute("SELECT * FROM tables_config WHERE table_number = ?", (table_no,))
            if cur.fetchone():
                continue

            cur.execute("""
                INSERT INTO tables_config (table_number, table_name, is_active)
                VALUES (?, ?, 1)
            """, (table_no, table_name))

            qr_generator.generate_table_qr(table_no)
            new_tables.append(table_no)

        conn.commit()
        conn.close()

        qr_generator.generate_qr_html_preview()

        return jsonify({
            "success": True,
            "added": len(new_tables),
            "tables": new_tables,
            "message": f"Successfully added {len(new_tables)} new tables"
        })
    except Exception as e:
        print(f"Error adding tables: {e}")
        return jsonify({"error": str(e)}), 500

# =========================
# MENU MANAGEMENT API
# =========================
@app.route("/admin/menu/add", methods=["POST"])
@admin_required
def admin_menu_add():
    try:
        data = request.get_json()
        category = data.get("category")
        item_name = data.get("item_name")
        price = data.get("price")

        if not category or not item_name or not price:
            return jsonify({"error": "Invalid data"}), 400

        if category not in menu_card:
            menu_card[category] = {}
        menu_card[category][item_name] = price

        return jsonify({"success": True, "message": "Item added successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/menu/edit", methods=["POST"])
@admin_required
def admin_menu_edit():
    try:
        data = request.get_json()
        category = data.get("category")
        item_name = data.get("item_name")
        new_price = data.get("price")

        if not category or not item_name or not new_price:
            return jsonify({"error": "Invalid data"}), 400

        # Update in the menu_card dictionary
        if category in menu_card and item_name in menu_card[category]:
            menu_card[category][item_name] = int(new_price)
            return jsonify({"success": True, "message": "Item updated successfully"})
        else:
            return jsonify({"error": "Item not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#ADD Images

UPLOAD_FOLDER = 'static/menu_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/admin/menu/upload-image", methods=["POST"])
@admin_required
def upload_menu_image():
    try:
        item_name = request.form.get('item_name')

        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{item_name.replace(' ', '_')}.{file.filename.rsplit('.', 1)[1].lower()}")
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                image_url = f"/static/menu_images/{filename}"

        # Handle URL upload
        elif request.form.get('image_url'):
            image_url = request.form.get('image_url')
        else:
            return jsonify({"error": "No image provided"}), 400

        # Save to JSON file
        try:
            with open('menu_images.json', 'r') as f:
                images = json.load(f)
        except:
            images = {}

        images[item_name] = image_url

        with open('menu_images.json', 'w') as f:
            json.dump(images, f, indent=2)

        return jsonify({"success": True, "image_url": image_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/menu-images")
def get_menu_images():
    try:
        with open('menu_images.json', 'r') as f:
            images = json.load(f)
        return jsonify(images)
    except:
        return jsonify({})


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'})

    data = request.get_json()
    status = data.get('status')

    if status not in ['pending', 'preparing', 'ready', 'completed', 'cancelled']:
        return jsonify({'success': False, 'error': 'Invalid status'})

    try:
        # Update status in database
        conn = db.db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))

        # If status is 'preparing', lock the order
        if status == 'preparing':
            cur.execute("""
                INSERT OR IGNORE INTO order_locks (order_id, lock_reason, locked_by)
                VALUES (?, ?, ?)
            """, (order_id, "kitchen_started", "system"))

            cur.execute("UPDATE orders SET locked = 1 WHERE id = ?", (order_id,))

        cur.execute("SELECT user_id, table_id FROM orders WHERE id = ?", (order_id,))
        order_row = cur.fetchone()

        conn.commit()
        conn.close()

        if order_row and order_row[0]:
            status_message_map = {
                'preparing': f"Order #{order_id} is now being prepared 👨‍🍳",
                'ready': f"Order #{order_id} is ready for pickup ✅",
                'completed': f"Order #{order_id} has been completed 🎉",
                'cancelled': f"Order #{order_id} was cancelled",
                'pending': f"Order #{order_id} status changed to pending"
            }
            db.create_notification(order_id, order_row[0], order_row[1], status_message_map.get(status, f"Order #{order_id} status updated"), "admin_action")

        return jsonify({'success': True, 'status': status})
    except Exception as e:
        print(f"Error updating status: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin/menu/toggle", methods=["POST"])
@admin_required
def admin_menu_toggle():
    try:
        data = request.get_json()
        item_name = data.get("item_name")
        category = data.get("category")

        if not item_name:
            return jsonify({"error": "Invalid data"}), 400

        found_category = None
        for cat, items in menu_card.items():
            if item_name in items:
                found_category = cat
                break

        if not found_category:
            return jsonify({"error": "Item not found in menu"}), 404

        new_status = db.toggle_item_availability_in_db(item_name, found_category)

        if new_status is not None:
            return jsonify({
                "success": True,
                "message": "Availability toggled",
                "category": found_category,
                "is_available": new_status
            })
        else:
            return jsonify({"error": "Failed to toggle availability"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# API ENDPOINTS
# =========================
@app.route("/api/menu")
def menu_api():
    return jsonify(db.get_menu_with_availability(menu_card))

@app.route("/api/my-orders")
def my_orders_api():
    if "user" not in session:
        return jsonify([]), 401

    user = db.get_user(session.get("user"))
    if not user:
        return jsonify([])

    orders = db.order_join_user(user["id"])
    return jsonify(orders)

@app.route("/api/notifications")
def get_notifications():
    if not login_required_check():
        return jsonify({"error": "Authentication required"}), 401

    user = db.get_user(session.get("user", ""))
    if not user:
        return jsonify({"error": "User not found"}), 404

    notifications = db.get_user_notifications(user["id"], limit=20)

    return jsonify({
        "success": True,
        "notifications": notifications,
        "unread_count": len([n for n in notifications if not n.get("is_read")])
    })

@app.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read_api(notification_id):
    if not login_required_check():
        return jsonify({"error": "Authentication required"}), 401

    db.mark_notification_read(notification_id)

    return jsonify({
        "success": True,
        "notification_id": notification_id
    })

# =========================
# OFFLINE SUPPORT
# =========================
@app.route("/api/cart/save", methods=["POST"])
def save_cart_api():
    if not login_required_check():
        return jsonify({"error": "Authentication required"}), 401

    data = request.json
    cart_data = data.get("cart", {})

    for item in cart_data.keys():
        if not item_exists(item):
            return jsonify({"error": f"Invalid item: {item}"}), 400

    session["cart"] = cart_data
    session["cart_last_updated"] = datetime.now().isoformat()
    session["cart_saved_offline"] = True

    return jsonify({
        "success": True,
        "saved_at": session["cart_last_updated"],
        "item_count": len(cart_data),
        "total": calculate_cart_total(cart_data)
    })

@app.route("/api/cart/recover", methods=["GET"])
def recover_cart_api():
    if not login_required_check():
        return jsonify({"error": "Authentication required"}), 401

    cart = get_cart()
    last_updated = session.get("cart_last_updated")

    return jsonify({
        "success": True,
        "cart": cart,
        "last_updated": last_updated,
        "total": calculate_cart_total(cart),
        "recovered": bool(cart)
    })

# =========================
# ORDER STATUS & LIVE UPDATES
# =========================
@app.route("/api/order/<int:order_id>/status")
def get_order_status(order_id):
    if not login_required_check():
        return jsonify({"error": "Authentication required"}), 401

    order = db.get_order_by_id(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    # Authorization check
    user = db.get_user(session.get("user", ""))
    if user and order.get("user_id") != user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    lock = db.check_order_lock(order_id)

    return jsonify({
        "order_id": order_id,
        "status": order.get("status", "pending"),
        "locked": order.get("locked", 0) == 1,
        "lock_reason": order.get("lock_reason"),
        "can_edit": db.can_edit_order(order_id),
        "placed_at": order.get("placed_at"),
        "estimated_ready": None,
        "notifications": []
    })

@app.route("/api/cleanup-sessions", methods=["POST"])
def cleanup_sessions():
    """Clean up expired table sessions"""
    cleaned = db.cleanup_expired_sessions()
    return jsonify({
        "success": True,
        "cleaned": cleaned,
        "message": f"Cleaned {cleaned} expired sessions"
    })

# =========================
# MAINTENANCE TASKS (FIXED VERSION)
# =========================
@app.before_request
def before_request():
    # Clean up expired sessions periodically (every 10th request)
    if random.random() < 0.1:  # 10% chance
        db.cleanup_expired_sessions()

    # Check for orders that need auto-locking - FIXED VERSION
    # Use the can_edit_order function logic instead of direct SQL
    try:
        conn = db.db_connection()
        cur = conn.cursor()

        # Get orders that are not locked and placed recently (within edit window)
        # In your original code, the edit window is 15 minutes
        time_limit = datetime.now() - timedelta(minutes=EDIT_WINDOW_MINUTES)

        cur.execute("""
            SELECT id, created_at FROM orders 
            WHERE locked = 0 
            AND status NOT IN ('completed', 'cancelled')
        """)

        orders = cur.fetchall()
        conn.close()

        for order in orders:
            order_id = order['id']
            created_at_str = order['created_at']

            # Parse the created_at timestamp
            try:
                # Handle different datetime formats
                if isinstance(created_at_str, str):
                    if 'T' in created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    else:
                        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                else:
                    created_at = created_at_str

                # Check if edit window has expired
                if created_at < time_limit:
                    # Auto-lock the order
                    db.create_order_lock(order_id, "edit_window_expired", "system", 0, 0)
                    print(f"Auto-locked order {order_id} - edit window expired")

            except Exception as e:
                print(f"Error processing order {order_id}: {e}")
                continue

    except Exception as e:
        print(f"Error in before_request maintenance: {e}")

@app.route('/admin/tax-settings', methods=['GET', 'POST'])
def tax_settings():
    if not session.get('is_admin'):
        return redirect('/')

    if request.method == 'POST':
        settings = {
            'gst_enabled': 1 if request.form.get('gst_enabled') == 'on' else 0,
            'gst_rate': float(request.form.get('gst_rate', 5.0)),
            'gst_number': request.form.get('gst_number', ''),
            'service_charge_enabled': 1 if request.form.get('service_charge_enabled') == 'on' else 0,
            'service_charge_rate': float(request.form.get('service_charge_rate', 10.0)),
            'packaging_charge_enabled': 1 if request.form.get('packaging_charge_enabled') == 'on' else 0,
            'packaging_charge': float(request.form.get('packaging_charge', 0.0)),
            'delivery_charge_enabled': 1 if request.form.get('delivery_charge_enabled') == 'on' else 0,
            'delivery_charge': float(request.form.get('delivery_charge', 0.0))
        }

        db.update_tax_settings(settings)
        return redirect('/admin/tax-settings?success=1')

    settings = db.get_tax_settings()
    return render_template('admin/tax_settings.html', settings=settings)

# =========================
# LEGAL PAGES
# =========================
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

# =========================
# ERROR HANDLERS
# =========================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized"}), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Forbidden"}), 403




# =========================
# APPLICATION STARTUP
# =========================
if __name__ == "__main__":
    print("=" * 50)
    print("🏪 MY CAFE - Starting Application")
    print("=" * 50)
    print("📊 Initializing database...")
    db.init_db()
    print("✅ Database ready!")
    port = int(os.environ.get("PORT", 5000))
    print(f"🔥 Server starting on port {port}")
    print("=" * 50)
    app.run(debug=False, port=port, host='0.0.0.0')

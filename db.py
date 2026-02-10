# File: db.py (UPDATED VERSION - PART 1)
import sqlite3
from datetime import datetime, timedelta
import uuid

DATABASE_NAME = "order.db"

def db_connection():
    """Create a database connection with Row factory"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# =====================
# NEW: ORDER LOCK FUNCTIONS
# =====================

def create_order_lock(order_id, lock_reason="kitchen_started", locked_by="system", can_edit=0, can_cancel=0):
    """Lock an order to prevent edits"""
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO order_locks (order_id, lock_reason, locked_by, can_edit, can_cancel)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                locked_at = CURRENT_TIMESTAMP,
                lock_reason = ?,
                locked_by = ?,
                can_edit = ?,
                can_cancel = ?
        """, (order_id, lock_reason, locked_by, can_edit, can_cancel,
              lock_reason, locked_by, can_edit, can_cancel))
        
        # Update orders table
        cur.execute("""
            UPDATE orders 
            SET locked = 1, lock_reason = ?
            WHERE id = ?
        """, (lock_reason, order_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error creating order lock: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def check_order_lock(order_id):
    """Check if order is locked and get lock details"""
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM order_locks 
        WHERE order_id = ?
    """, (order_id,))
    
    lock = cur.fetchone()
    conn.close()
    
    if lock:
        return dict(lock)
    return None

def can_edit_order(order_id):
    """Check if order can still be edited (within time window)"""
    conn = db_connection()
    cur = conn.cursor()
    
    # Get order placed time
    cur.execute("""
        SELECT placed_at, edit_until, locked 
        FROM orders 
        WHERE id = ?
    """, (order_id,))
    
    order = cur.fetchone()
    conn.close()
    
    if not order:
        return False
    
    # Check if locked
    if order['locked'] == 1:
        return False
    
    # Check edit window (15 minutes by default)
    if order['edit_until']:
        edit_until = datetime.strptime(order['edit_until'], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > edit_until:
            return False
    
    return True

# =====================
# NEW: BILL FUNCTIONS
# =====================

def generate_bill(order_id):
    """Generate bill with tax and service charge"""
    conn = db_connection()
    cur = conn.cursor()
    
    # Get order details
    cur.execute("""
        SELECT id, total, items FROM orders WHERE id = ?
    """, (order_id,))
    
    order = cur.fetchone()
    if not order:
        return None
    
    subtotal = float(order['total'])
    tax_rate = 5.0  # 5% GST
    service_charge_rate = 10.0  # 10% service charge
    
    tax_amount = (subtotal * tax_rate) / 100
    service_charge_amount = (subtotal * service_charge_rate) / 100
    grand_total = subtotal + tax_amount + service_charge_amount
    
    # Generate unique bill number
    bill_number = f"BILL-{order_id}-{datetime.now().strftime('%Y%m%d')}"
    
    try:
        cur.execute("""
            INSERT INTO bill_details 
            (order_id, subtotal, tax_rate, tax_amount, service_charge_rate, 
             service_charge_amount, grand_total, bill_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, subtotal, tax_rate, tax_amount, service_charge_rate,
              service_charge_amount, grand_total, bill_number))
        
        # Mark order as billed
        cur.execute("""
            UPDATE orders SET bill_generated = 1 WHERE id = ?
        """, (order_id,))
        
        conn.commit()
        
        return {
            "bill_number": bill_number,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": round(tax_amount, 2),
            "service_charge_rate": service_charge_rate,
            "service_charge_amount": round(service_charge_amount, 2),
            "grand_total": round(grand_total, 2),
            "items": order['items']
        }
    except Exception as e:
        print(f"❌ Error generating bill: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_bill(order_id):
    """Get bill details for order"""
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM bill_details WHERE order_id = ?
    """, (order_id,))
    
    bill = cur.fetchone()
    conn.close()
    
    if bill:
        return dict(bill)
    return None

# =====================
# NEW: FORCE ACTIONS
# =====================

def record_force_action(order_id, admin_id, action, reason=""):
    """Record admin force action"""
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO force_actions (order_id, admin_id, action, reason)
            VALUES (?, ?, ?, ?)
        """, (order_id, admin_id, action, reason))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error recording force action: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def force_complete_order(order_id, admin_id, reason=""):
    """Force complete an order"""
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Update order status
        cur.execute("""
            UPDATE orders SET status = 'completed' WHERE id = ?
        """, (order_id,))
        
        # Record action
        record_force_action(order_id, admin_id, "force_complete", reason)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error force completing order: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def force_cancel_order(order_id, admin_id, reason=""):
    """Force cancel an order"""
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Update order status
        cur.execute("""
            UPDATE orders SET status = 'cancelled' WHERE id = ?
        """, (order_id,))
        
        # Record action
        record_force_action(order_id, admin_id, "force_cancel", reason)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error force cancelling order: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def mark_as_paid(order_id, admin_id, payment_method="cash", reason=""):
    """Mark order as paid"""
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        # Update order
        cur.execute("""
            UPDATE orders 
            SET payment_method = ?, status = 'completed' 
            WHERE id = ?
        """, (payment_method, order_id))
        
        # Record action
        record_force_action(order_id, admin_id, "mark_paid", 
                          f"{payment_method}: {reason}")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error marking as paid: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# =====================
# NEW: NOTIFICATION FUNCTIONS
# =====================

def create_notification(order_id, user_id, table_id, message, notification_type):
    """Create a notification"""
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO notifications 
            (order_id, user_id, table_id, message, type)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, user_id, table_id, message, notification_type))
        
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"❌ Error creating notification: {e}")
        return None
    finally:
        conn.close()

def get_user_notifications(user_id, limit=10):
    """Get notifications for a user"""
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, limit))
    
    notifications = cur.fetchall()
    conn.close()
    
    return [dict(notif) for notif in notifications]

def mark_notification_read(notification_id):
    """Mark notification as read"""
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE notifications SET is_read = 1 WHERE id = ?
    """, (notification_id,))
    
    conn.commit()
    conn.close()

# =====================
# NEW: TABLE SESSION FUNCTIONS
# =====================

def create_table_session_with_expiry(table_id, session_token, guest_name=None, expiry_hours=2):
    """Create table session with expiry"""
    conn = db_connection()
    cur = conn.cursor()
    
    expiry = (datetime.now() + timedelta(hours=expiry_hours)).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cur.execute("""
            INSERT INTO table_sessions 
            (table_id, session_token, guest_name, expires_at, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (table_id, session_token, guest_name, expiry))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error creating table session: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def validate_table_session(table_id, session_token):
    """Validate if table session is still active"""
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM table_sessions 
        WHERE table_id = ? 
        AND session_token = ? 
        AND is_active = 1
        AND expires_at > CURRENT_TIMESTAMP
    """, (table_id, session_token))
    
    session = cur.fetchone()
    conn.close()
    
    return session is not None

def cleanup_expired_sessions():
    """Clean up expired table sessions"""
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE table_sessions 
        SET is_active = 0 
        WHERE expires_at <= CURRENT_TIMESTAMP
        AND is_active = 1
    """)
    
    rows_affected = cur.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected

# =====================
# UPDATED ORDER SAVE FUNCTION
# =====================

def save_order_with_features(user_id, items, total, cafe_name="MY CAFE", 
                           table_id=None, session_token=None, guest_name=None):
    """Save order with all new features"""
    conn = db_connection()  # <-- CORRECT: Uses the proper connection function
    cursor = conn.cursor()

    try:
        placed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        edit_until = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO orders 
            (user_id, items, total, cafe_name, status, created_at, 
             placed_at, edit_until, table_id, session_token, guest_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            items,
            total,
            cafe_name,
            'pending',
            placed_at,
            placed_at,
            edit_until,
            table_id,
            session_token,
            guest_name
        ))
        
        order_id = cursor.lastrowid

        if order_id is None:
            # Fallback: get the last inserted ID
            cursor.execute("SELECT last_insert_rowid()")
            order_id = cursor.fetchone()[0]
        
        # Create notification
        notification_msg = f"New order #{order_id} placed from {table_id or 'Online'}"
        create_notification(order_id, user_id, table_id, notification_msg, "order_placed")
        
        conn.commit()
        print(f"✅ Order #{order_id} saved with features")
        return order_id
    except Exception as e:
        print(f"❌ Error saving order with features: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

# =====================
# EXISTING FUNCTIONS (keep them all)
# =====================

def init_db():
    """Initialize all database tables"""
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        email TEXT,
        phone TEXT,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Orders table (with new columns)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        cafe_name TEXT DEFAULT 'MY CAFE',
        items TEXT,
        total INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        table_id TEXT,
        session_token TEXT,
        placed_at TIMESTAMP,
        locked INTEGER DEFAULT 0,
        payment_method TEXT DEFAULT 'pending',
        guest_name TEXT,
        edit_until TIMESTAMP,
        lock_reason TEXT,
        bill_generated INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Item availability table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS item_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE NOT NULL,
        category TEXT,
        is_available INTEGER DEFAULT 1,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # New tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_locks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER UNIQUE,
        locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        lock_reason TEXT,
        can_edit INTEGER DEFAULT 0,
        can_cancel INTEGER DEFAULT 0,
        locked_by TEXT,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bill_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER UNIQUE,
        subtotal REAL,
        tax_rate REAL DEFAULT 5.0,
        tax_amount REAL,
        service_charge_rate REAL DEFAULT 10.0,
        service_charge_amount REAL,
        discount REAL DEFAULT 0.0,
        grand_total REAL,
        bill_number TEXT UNIQUE,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS force_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        admin_id INTEGER,
        action TEXT,
        reason TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(admin_id) REFERENCES users(id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS table_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id TEXT NOT NULL,
        session_token TEXT UNIQUE NOT NULL,
        guest_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP DEFAULT (datetime('now', '+2 hours')),
        is_active INTEGER DEFAULT 1
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        user_id INTEGER,
        table_id TEXT,
        message TEXT,
        type TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tables_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_number TEXT UNIQUE NOT NULL,
        table_name TEXT,
        qr_code TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Add this to init_db() function
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tax_settings (
        id INTEGER PRIMARY KEY DEFAULT 1,
        gst_enabled INTEGER DEFAULT 1,
        gst_rate REAL DEFAULT 5.0,
        gst_number TEXT DEFAULT 'GSTIN: 29ABCDE1234F1Z5',
        service_charge_enabled INTEGER DEFAULT 1,
        service_charge_rate REAL DEFAULT 10.0,
        packaging_charge_enabled INTEGER DEFAULT 0,
        packaging_charge REAL DEFAULT 0.0,
        delivery_charge_enabled INTEGER DEFAULT 0,
        delivery_charge REAL DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT one_row CHECK (id = 1)
    )
    """)

# Insert default settings if not exists
    cur.execute("""
        INSERT OR IGNORE INTO tax_settings (id) VALUES (1)
    """)

    conn.commit()
    conn.close()
    
    # Initialize sample tables
    init_tables()
    print("✅ Database initialized successfully with all features")

# File: db.py (CONTINUED - PART 2)
# =====================
# EXISTING USER FUNCTIONS (unchanged)
# =====================

def user_exists(username):
    """Check if a username already exists"""
    conn = db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def create_user(username, hashed_password, name, email, phone):
    """Create a new user"""
    conn = db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (username, password, name, email, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            hashed_password,
            name,
            email,
            phone,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        print(f"✅ User '{username}' created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_user(username):
    """Get user by username"""
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return dict(user)
    return None


def get_user_by_id(user_id):
    """Get user by ID"""
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return dict(user)
    return None


def get_all_users():
    """Get all users"""
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, name, email, phone, is_admin, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    return [dict(user) for user in users]


def is_user_admin(username):
    """Check if user is admin"""
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] == 1:
        return True
    return False


def make_user_admin(username):
    """Make a user an admin"""
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    print(f"✅ {username} is now an admin")

# =====================
# EXISTING ORDER FUNCTIONS (updated)
# =====================

def save_order(user_id, items, total, cafe_name="MY CAFE"):
    """Save a new order (legacy function for backward compatibility)"""
    return save_order_with_features(user_id, items, total, cafe_name)


def get_orders(user_id=None):
    """Get orders (all or for specific user)"""
    conn = db_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute("""
            SELECT * FROM orders 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")

    orders = cursor.fetchall()
    conn.close()
    return [dict(order) for order in orders]


def order_join_user(user_id):
    """Get orders with user information"""
    conn = db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            orders.id,
            orders.cafe_name,
            orders.items,
            orders.total,
            orders.status,
            orders.created_at,
            orders.table_id,
            orders.locked,
            orders.payment_method,
            orders.guest_name,
            orders.edit_until,
            users.username,
            users.name
        FROM orders
        JOIN users ON orders.user_id = users.id
        WHERE users.id = ?
        ORDER BY orders.created_at DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_order_status(order_id, status):
    """Update order status"""
    conn = db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ?
        """, (status, order_id))

        # Create notification
        order = get_order_by_id(order_id)
        if order and order.get('user_id'):
            msg = f"Order #{order_id} status changed to {status}"
            create_notification(order_id, order['user_id'],
                              order.get('table_id'), msg, "status_update")

        conn.commit()
        print(f"✅ Order {order_id} status updated to {status}")
        return True
    except Exception as e:
        print(f"❌ Error updating order status: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_order_by_id(order_id):
    """Get order by ID"""
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()

    if order:
        return dict(order)
    return None

# =====================
# ITEM AVAILABILITY FUNCTIONS
# =====================

def get_item_availability(item_name):
    """Get availability status of an item"""
    conn = db_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_available FROM item_availability WHERE item_name = ?", (item_name,))
    result = cur.fetchone()
    conn.close()

    # Default to available (1) if not in database
    return result[0] if result else 1


def set_item_availability(item_name, category, is_available):
    """Set availability status of an item"""
    conn = db_connection()
    cur = conn.cursor()

    try:
        # Check if item exists
        cur.execute("SELECT 1 FROM item_availability WHERE item_name = ?", (item_name,))
        exists = cur.fetchone() is not None

        if exists:
            # Update existing
            cur.execute("""
                UPDATE item_availability 
                SET is_available = ?, category = ?, last_updated = CURRENT_TIMESTAMP
                WHERE item_name = ?
            """, (1 if is_available else 0, category, item_name))
        else:
            # Insert new
            cur.execute("""
                INSERT INTO item_availability (item_name, category, is_available)
                VALUES (?, ?, ?)
            """, (item_name, category, 1 if is_available else 0))

        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error setting availability: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def toggle_item_availability_in_db(item_name, category=None):
    """
    Toggle item availability in database
    Returns the NEW status after toggling (1 for available, 0 for unavailable)
    """
    conn = db_connection()
    cur = conn.cursor()

    try:
        # Get current status
        cur.execute("SELECT is_available, category FROM item_availability WHERE item_name = ?", (item_name,))
        result = cur.fetchone()

        if result:
            current_status = result[0]
            new_status = 0 if current_status == 1 else 1

            cur.execute("""
                UPDATE item_availability 
                SET is_available = ?, last_updated = CURRENT_TIMESTAMP
                WHERE item_name = ?
            """, (new_status, item_name))
        else:
            # Item not in database, insert as unavailable (0)
            if not category:
                category = "Unknown"

            new_status = 0
            cur.execute("""
                INSERT INTO item_availability (item_name, category, is_available)
                VALUES (?, ?, ?)
            """, (item_name, category, new_status))

        conn.commit()
        print(f"✅ Toggled {item_name} to {'available' if new_status == 1 else 'unavailable'}")
        return new_status
    except Exception as e:
        print(f"❌ Error toggling availability: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_all_item_availabilities():
    """Get availability status for all items"""
    conn = db_connection()
    cur = conn.cursor()
    cur.execute("SELECT item_name, is_available FROM item_availability")
    rows = cur.fetchall()
    conn.close()

    availabilities = {}
    for row in rows:
        availabilities[row[0]] = row[1]
    return availabilities


def get_menu_with_availability(menu_card):
    """Get menu with availability status from database"""
    # Get all availabilities from database
    conn = db_connection()
    cur = conn.cursor()
    cur.execute("SELECT item_name, is_available FROM item_availability")
    db_availabilities = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()

    # Build menu structure with availability
    menu_with_availability = {}
    for category, items in menu_card.items():
        menu_with_availability[category] = {}
        for item_name, price in items.items():
            is_available = db_availabilities.get(item_name, 1)  # Default to available
            menu_with_availability[category][item_name] = {
                "price": price,
                "is_available": is_available
            }

    return menu_with_availability

# =====================
# TABLE MANAGEMENT FUNCTIONS
# =====================

def get_table(table_no):
    """Get table information"""
    conn = db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tables_config WHERE table_number = ?", (table_no,))
    table = cur.fetchone()
    conn.close()

    if table:
        return dict(table)
    return None


def create_table_session(table_no, token):
    """Create a new table session (legacy - use create_table_session_with_expiry instead)"""
    return create_table_session_with_expiry(table_no, token)


def init_tables():
    """Initialize tables_config table if it doesn't exist"""
    conn = db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tables_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number TEXT UNIQUE NOT NULL,
            table_name TEXT,
            qr_code TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS table_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id TEXT NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            guest_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP DEFAULT (datetime('now', '+2 hours')),
            is_active INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Table management tables initialized")

# =====================
# NEW: OFFLINE SAFETY FUNCTIONS
# =====================

def get_pending_orders_for_user(user_id):
    """Get pending orders that might need sync"""
    conn = db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM orders 
        WHERE user_id = ? 
        AND status IN ('pending', 'preparing')
        ORDER BY created_at DESC
    """, (user_id,))

    orders = cur.fetchall()
    conn.close()

    return [dict(order) for order in orders]

def save_offline_cart(user_id, cart_data):
    """Save cart data for offline recovery"""
    # This could be implemented with localStorage on frontend
    # For now, we'll store in session
    pass

# Add these to db.py
def get_tax_settings():
    """Get current tax and charge settings"""
    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tax_settings WHERE id = 1")
    settings = cur.fetchone()
    conn.close()

    if settings:
        return dict(settings)

    # Return defaults if not found
    return {
        "gst_enabled": 1,
        "gst_rate": 5.0,
        "gst_number": "GSTIN: 29ABCDE1234F1Z5",
        "service_charge_enabled": 1,
        "service_charge_rate": 10.0,
        "packaging_charge_enabled": 0,
        "packaging_charge": 0.0,
        "delivery_charge_enabled": 0,
        "delivery_charge": 0.0
    }

def update_tax_settings(settings_dict):
    """Update tax and charge settings"""
    from datetime import datetime

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE tax_settings SET
                gst_enabled = ?,
                gst_rate = ?,
                gst_number = ?,
                service_charge_enabled = ?,
                service_charge_rate = ?,
                packaging_charge_enabled = ?,
                packaging_charge = ?,
                delivery_charge_enabled = ?,
                delivery_charge = ?,
                updated_at = ?
            WHERE id = 1
        """, (
            settings_dict.get('gst_enabled', 1),
            settings_dict.get('gst_rate', 5.0),
            settings_dict.get('gst_number', 'GSTIN: 29ABCDE1234F1Z5'),
            settings_dict.get('service_charge_enabled', 1),
            settings_dict.get('service_charge_rate', 10.0),
            settings_dict.get('packaging_charge_enabled', 0),
            settings_dict.get('packaging_charge', 0.0),
            settings_dict.get('delivery_charge_enabled', 0),
            settings_dict.get('delivery_charge', 0.0),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating tax settings: {e}")
        conn.rollback()
        conn.close()
        return False

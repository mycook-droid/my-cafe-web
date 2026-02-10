#!/usr/bin/env python3
"""
Database Migration - Add Final Features
Run this ONCE to add new tables and columns
"""

import sqlite3
from datetime import datetime

DATABASE_NAME = "order.db"

def migrate_database():
    print("=" * 60)
    print("🔧 MY CAFE - Database Migration")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()

    try:
        # 1. Add columns to orders table
        print("\n1️⃣ Adding new columns to orders table...")

        columns_to_add = [
            ("table_id", "TEXT"),
            ("session_token", "TEXT"),
            ("placed_at", "TIMESTAMP"),
            ("locked", "INTEGER DEFAULT 0"),
            ("payment_method", "TEXT DEFAULT 'pending'"),
            ("guest_name", "TEXT")
        ]

        for col_name, col_type in columns_to_add:
            try:
                cur.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
                print(f"  ✅ Added column: {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"  ⏭️  Column {col_name} already exists")
                else:
                    raise

        # 2. Create table_sessions table
        print("\n2️⃣ Creating table_sessions table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS table_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id TEXT NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            guest_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
        """)
        print("  ✅ table_sessions created")

        # 3. Create order_locks table
        print("\n3️⃣ Creating order_locks table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS order_locks (
            order_id INTEGER PRIMARY KEY,
            locked_at TIMESTAMP,
            lock_reason TEXT,
            can_edit INTEGER DEFAULT 0,
            can_cancel INTEGER DEFAULT 0,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
        """)
        print("  ✅ order_locks created")

        # 4. Create force_actions table
        print("\n4️⃣ Creating force_actions table...")
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
        print("  ✅ force_actions created")

        # 5. Create bill_details table
        print("\n5️⃣ Creating bill_details table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bill_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER UNIQUE,
            subtotal REAL,
            tax_rate REAL DEFAULT 5.0,
            tax_amount REAL,
            service_charge_rate REAL DEFAULT 0.0,
            service_charge_amount REAL,
            grand_total REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
        """)
        print("  ✅ bill_details created")

        # 6. Create tables_config table (for QR system)
        print("\n6️⃣ Creating tables_config table...")
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
        print("  ✅ tables_config created")

        # 7. Add sample tables
        print("\n7️⃣ Adding sample tables...")
        sample_tables = [
            ("T1", "Table 1"),
            ("T2", "Table 2"),
            ("T3", "Table 3"),
            ("T4", "Table 4"),
            ("T5", "Table 5"),
            ("T6", "Table 6"),
            ("T7", "Table 7"),
            ("T8", "Table 8"),
            ("T9", "Table 9"),
            ("T10", "Table 10")
        ]

        for table_num, table_name in sample_tables:
            try:
                cur.execute("""
                    INSERT INTO tables_config (table_number, table_name)
                    VALUES (?, ?)
                """, (table_num, table_name))
                print(f"  ✅ Added {table_name}")
            except sqlite3.IntegrityError:
                print(f"  ⏭️  {table_name} already exists")

        conn.commit()

        # Verify
        print("\n" + "=" * 60)
        print("✅ MIGRATION SUCCESSFUL!")
        print("=" * 60)

        # Show table count
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cur.fetchall()
        print(f"\n📊 Total tables in database: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")

        # Show sample data
        print("\n📋 Sample Tables:")
        cur.execute("SELECT table_number, table_name FROM tables_config LIMIT 5")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("🎉 Database is ready for new features!")
    print("=" * 60)


if __name__ == "__main__":
    migrate_database()

#!/usr/bin/env python3
"""
QR Code Generator for Table Sessions
Generates QR codes that link directly to menu with table_id
"""

import qrcode
import os
from pathlib import Path

def generate_table_qr(table_id, base_url="http://localhost:5000"):
    """
    Generate QR code for a table

    Args:
        table_id: Table identifier (e.g., "T1", "T2")
        base_url: Base URL of your cafe app

    Returns:
        Path to saved QR code image
    """
    # Create QR code
    qr_url = f"{base_url}/table/{table_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(qr_url)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Save
    output_dir = Path("static/qr_codes")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"table_{table_id}.png"
    img.save(output_path)

    print(f"✅ Generated QR for {table_id}: {output_path}")
    print(f"   URL: {qr_url}")

    return str(output_path)

def generate_all_tables(num_tables=10, base_url="http://localhost:5000"):
    """Generate QR codes for all tables"""
    print("=" * 60)
    print("📷 Generating QR Codes for Tables")
    print("=" * 60)

    qr_paths = []
    for i in range(1, num_tables + 1):
        table_id = f"T{i}"
        path = generate_table_qr(table_id, base_url)
        qr_paths.append(path)

    print("\n" + "=" * 60)
    print(f"✅ Generated {len(qr_paths)} QR codes!")
    print("=" * 60)
    print("\n📁 QR codes saved in: static/qr_codes/")
    print("\n💡 TIP: Print these and place on tables")
    print("   Customers scan → Direct to menu with table ID")

    return qr_paths

def generate_qr_html_preview(num_tables=None):
    """Generate HTML page to preview all QR codes"""
    # If num_tables not provided, count active tables from database
    if num_tables is None:
        try:
            import db
            conn = db.db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tables_config WHERE is_active = 1")
            num_tables = cur.fetchone()[0]
            conn.close()
        except:
            num_tables = 10  # Default fallback

    html = """
<!DOCTYPE html>
<html>
<head>
    <title>MY CAFE - Table QR Codes</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            background: #f5f5f5;
        }
        h1 {
            text-align: center;
            color: #E17055;
        }
        .qr-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }
        .qr-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }
        .qr-card img {
            max-width: 200px;
            width: 100%;
        }
        .print-btn {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            padding: 1rem 2rem;
            background: #E17055;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        @media print {
            .print-btn { display: none; }
            .qr-card { page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <h1>🍽️ MY CAFE - Table QR Codes</h1>
    <div class="qr-grid">
"""

    # Get all active tables from database
    try:
        import db
        conn = db.db_connection()
        cur = conn.cursor()
        cur.execute("SELECT table_number, table_name FROM tables_config WHERE is_active = 1 ORDER BY table_number")
        tables = cur.fetchall()
        conn.close()

        for table in tables:
            table_no = table[0]
            table_name = table[1]
            html += f"""
        <div class="qr-card">
            <h3>{table_name}</h3>
            <img src="/static/qr_codes/table_{table_no}.png">
            <p>Scan to order from {table_name}</p>
        </div>
"""
    except:
        # Fallback to generating for T1 to T{num_tables}
        for i in range(1, num_tables + 1):
            html += f"""
        <div class="qr-card">
            <h3>Table {i}</h3>
            <img src="/static/qr_codes/table_T{i}.png">
            <p>Scan to order from Table {i}</p>
        </div>
"""

    html += """
    </div>
    <button class="print-btn" onclick="window.print()">🖨️ Print</button>
</body>
</html>
"""

    output_path = Path("static/qr_codes/preview.html")
    output_path.write_text(html)
    print(f"📄 Preview ready: {output_path}")
    return output_path


if __name__ == "__main__":
    # Generate QR codes
    TABLE_COUNT = 26
    generate_all_tables(num_tables=TABLE_COUNT, base_url="http://localhost:5000")

    # Generate preview page
    generate_qr_html_preview(num_tables=TABLE_COUNT)


    print("\n" + "=" * 60)
    print("📋 INSTRUCTIONS:")
    print("=" * 60)
    print("1. Run: python qr_generator.py")
    print("2. Open: http://localhost:5000/static/qr_codes/preview.html")
    print("3. Print QR codes")
    print("4. Place on tables")
    print("5. Customers scan → order directly!")

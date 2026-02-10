# 🍽️ MY CAFE - Smart Restaurant QR Ordering System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-3-green?style=for-the-badge&logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**A complete, production-ready restaurant management system with QR code table ordering, real-time kitchen display, and comprehensive admin dashboard.**

[🚀 Live Demo](#) • [📖 Documentation](#installation) • [🐛 Report Bug](#) • [✨ Request Feature](#)

</div>

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🎯 What Makes This Different?](#-what-makes-this-different)
- [🛠️ Tech Stack](#️-tech-stack)
- [📦 Installation](#-installation)
- [🚀 Quick Start](#-quick-start)
- [📱 Usage](#-usage)
- [🌐 Deployment](#-deployment)
- [📸 Screenshots](#-screenshots)
- [🔧 Configuration](#-configuration)
- [🤝 Contributing](#-contributing)
- [👨‍💻 Developer](#-developer)
- [📄 License](#-license)

---

## ✨ Features

### 👤 **Customer Experience**
- 📱 **QR Code Ordering** - Scan table QR, browse menu, order instantly
- 🛒 **Smart Shopping Cart** - Real-time updates, easy add/remove
- ⏱️ **15-Min Edit Window** - Modify orders after placement
- 📄 **Digital Bill** - Automated GST + Service Charge calculation
- 📊 **Order History** - Track all past orders
- 🔔 **Status Updates** - Real-time order status notifications
- 🌓 **Dark Mode** - Eye-friendly night theme
- 📱 **Mobile First** - Optimized for phones and tablets

### 👨‍🍳 **Kitchen Management**
- 🖥️ **Live Kitchen Display** - Real-time order queue
- ⚡ **One-Click Updates** - Mark orders as preparing/ready/completed
- 🔄 **Auto-Refresh** - Updates every 10 seconds
- 🎯 **Status Filters** - View pending, preparing, or ready orders
- 📢 **Visual Alerts** - Pulsing animations for new orders

### 🔐 **Admin Dashboard**
- 📊 **Analytics** - Revenue, orders, top items (7-day graphs)
- 🍕 **Menu Management** - Add/edit items, toggle availability
- 🪑 **Table Management** - Generate QR codes for any number of tables
- 💰 **Tax Settings** - Configure GST, service charge, packaging fees
- 👥 **User Management** - View all registered customers
- 🔧 **Force Actions** - Override order status when needed
- 📈 **Performance Metrics** - Average order value, daily trends

---

## 🎯 What Makes This Different?

Unlike traditional food ordering apps like Zomato/Swiggy:

| Feature | MY CAFE | Traditional Apps |
|---------|---------|------------------|
| **Order Method** | QR scan at restaurant table | Home delivery focus |
| **Target** | Dine-in customers | Delivery customers |
| **Payment** | Pay at counter after dining | Online payment required |
| **Speed** | Instant order to kitchen | Delivery delays |
| **Cost** | No delivery fee | High commission + delivery |
| **Experience** | Self-service at table | Wait for waiter |

**Perfect for:** Cafes, restaurants, food courts, canteens

---

## 🛠️ Tech Stack

<table>
<tr>
<td valign="top" width="50%">

### Backend
- **Framework:** Flask 3.0 (Python)
- **Database:** SQLite3
- **Security:** Werkzeug password hashing
- **Sessions:** Flask-Session
- **QR Codes:** python-qrcode
- **Server:** Gunicorn (production)

</td>
<td valign="top" width="50%">

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Modern animations, glassmorphism
- **JavaScript** - Vanilla JS (no jQuery)
- **Charts:** Chart.js for analytics
- **Icons:** Font Awesome 6
- **Fonts:** Inter + Playfair Display

</td>
</tr>
</table>

---

## 📦 Installation

### Prerequisites

```bash
# Check Python version (3.8+ required)
python3 --version

# Check pip
pip3 --version
```

### Step 1: Clone Repository

```bash
# Option A: Clone from GitHub
git clone https://github.com/YOUR_USERNAME/my-cafe.git
cd my-cafe

# Option B: Download ZIP and extract
# Navigate to extracted folder
cd my-cafe-main
```

### Step 2: Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install all packages
pip install -r requirements.txt
```

**Or install manually:**
```bash
pip install Flask==3.0.0
pip install Werkzeug==3.0.1
pip install qrcode==7.4.2
pip install Pillow==10.1.0
pip install gunicorn==21.2.0
```

### Step 3: Database Setup

```bash
# Initialize database
python migrate.py

# Generate QR codes for tables
python qr_generator.py
```

### Step 4: Run Application

```bash
# Development mode (with auto-reload)
python app.py

# Production mode
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**🎉 Success!** Open browser to: **http://localhost:5000**

---

## 🚀 Quick Start

### First Time Setup (3 minutes)

```bash
# 1. Navigate to project
cd my-cafe

# 2. Activate venv
source venv/bin/activate

# 3. Run migrations
python migrate.py

# 4. Generate QR codes
python qr_generator.py

# 5. Start server
python app.py
```

### Create Admin Account

1. Open: http://localhost:5000/signup
2. Create account with username/password
3. Go to: http://localhost:5000/become-admin
4. Enter admin code: **`MYCAFE2024`**
5. Access admin dashboard: http://localhost:5000/admin

---

## 📱 Usage

### For Customers

1. **📱 Scan QR Code** on restaurant table
2. **📋 Browse Menu** - View all categories
3. **🛒 Add to Cart** - Tap + to add items
4. **✅ Place Order** - Tap cart icon → "Place Order"
5. **👀 Track Status** - View in "Your Orders"
6. **💳 Pay at Counter** - Show bill when ready

### For Staff (Kitchen)

1. Login as admin
2. Go to **Kitchen Display**: `/admin/orders`
3. View incoming orders in real-time
4. Update status:
   - **Pending** → Click "Start Preparing"
   - **Preparing** → Click "Mark as Ready"
   - **Ready** → Click "Complete Order"

### For Admin

1. **Dashboard**: `/admin` - Overview statistics
2. **Menu**: `/admin/menu` - Add/edit/toggle items
3. **Tables**: `/admin/tables` - Generate more QR codes
4. **Analytics**: `/admin/analytics` - Revenue charts
5. **Settings**: `/admin/settings` - User management

---

## 🌐 Deployment

### Option 1: Render.com (Free, Recommended)

```bash
# 1. Push code to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/my-cafe.git
git push -u origin main

# 2. Go to render.com and sign up with GitHub
# 3. Create New Web Service
# 4. Connect your repository
# 5. Configure:
#    - Environment: Python
#    - Build Command: pip install -r requirements.txt
#    - Start Command: gunicorn app:app
# 6. Deploy! (takes 5-10 minutes)
```

**Automatic deployment** with `render.yaml` already included!

### Option 2: Docker

```bash
# Build image
docker build -t mycafe:latest .

# Run container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3: VPS (DigitalOcean/AWS)

```bash
# SSH into server
ssh user@your-server-ip

# Clone repository
git clone https://github.com/YOUR_USERNAME/my-cafe.git
cd my-cafe

# Install dependencies
pip3 install -r requirements.txt

# Run with systemd (persistent)
sudo cp mycafe.service /etc/systemd/system/
sudo systemctl enable mycafe
sudo systemctl start mycafe
```

---

## 📸 Screenshots

### Customer Flow
<table>
<tr>
<td><img src="screenshots/qr-scanner.png" alt="QR Scanner"/><br><b>1. QR Scanner</b></td>
<td><img src="screenshots/menu.png" alt="Menu"/><br><b>2. Menu Browsing</b></td>
<td><img src="screenshots/cart.png" alt="Cart"/><br><b>3. Shopping Cart</b></td>
</tr>
<tr>
<td><img src="screenshots/order-status.png" alt="Order Status"/><br><b>4. Order Tracking</b></td>
<td><img src="screenshots/bill.png" alt="Bill"/><br><b>5. Digital Bill</b></td>
<td><img src="screenshots/dark-mode.png" alt="Dark Mode"/><br><b>6. Dark Mode</b></td>
</tr>
</table>

### Admin Dashboard
<table>
<tr>
<td><img src="screenshots/admin-dashboard.png" alt="Dashboard"/><br><b>Dashboard</b></td>
<td><img src="screenshots/kitchen-display.png" alt="Kitchen"/><br><b>Kitchen Display</b></td>
</tr>
<tr>
<td><img src="screenshots/menu-management.png" alt="Menu"/><br><b>Menu Management</b></td>
<td><img src="screenshots/analytics.png" alt="Analytics"/><br><b>Analytics</b></td>
</tr>
</table>

> **Note:** Add screenshots to `screenshots/` folder after deployment

---

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```env
# App Config
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=production
DEBUG=False

# Admin
ADMIN_CODE=MYCAFE2024

# Database
DATABASE_NAME=order.db

# Server
PORT=5000
HOST=0.0.0.0
```

### Menu Configuration

Edit in `app.py`:

```python
menu_card = {
    "Pizza": {
        "Margherita": 199,
        "Farmhouse": 249,
        # Add your items...
    },
    "Burger": {
        "Veg Burger": 70,
        # Add more...
    }
}
```

### Tax Settings

Configure via Admin Panel:
1. Go to `/admin/tax-settings`
2. Set GST rate (default 5%)
3. Set service charge (default 10%)
4. Enable/disable packaging/delivery charges

---

## 📁 Project Structure

```
my-cafe/
├── 📄 app.py                    # Main Flask application
├── 📄 db.py                     # Database operations
├── 📄 qr_generator.py           # QR code generator
├── 📄 migrate.py                # Database migrations
├── 📄 requirements.txt          # Python dependencies
├── 📄 Dockerfile                # Docker configuration
├── 📄 docker-compose.yml        # Docker compose config
├── 📄 render.yaml               # Render deployment config
├── 📄 .gitignore                # Git ignore rules
│
├── 📁 templates/                # HTML templates
│   ├── base.html               # Base template with navbar
│   ├── home.html               # Landing page
│   ├── qr_scanner.html         # QR scanner intermediate page
│   ├── index.html              # Menu browsing page
│   ├── login.html              # User login
│   ├── signup.html             # User registration
│   ├── orders.html             # Order history
│   ├── bill.html               # Bill display
│   ├── about.html              # About page
│   └── admin/                  # Admin templates
│       ├── dashboard.html      # Admin overview
│       ├── kitchen.html        # Kitchen display
│       ├── menu.html           # Menu management
│       ├── analytics.html      # Charts & stats
│       └── settings.html       # Admin settings
│
├── 📁 static/                   # Static assets
│   ├── style.css               # Main stylesheet
│   ├── auth.css                # Login/signup styles
│   ├── admin.css               # Admin panel styles
│   ├── icons/                  # Icons & images
│   │   └── Cart.png
│   ├── menu_images/            # Menu item images
│   └── qr_codes/               # Generated QR codes
│       ├── preview.html        # QR preview page
│       ├── table_T1.png
│       ├── table_T2.png
│       └── ...
│
├── 📁 screenshots/              # App screenshots (for README)
├── 📄 menu_images.json          # Menu image mappings
└── 📄 order.db                  # SQLite database (auto-created)
```

---

## 🔒 Security Best Practices

### Production Checklist

- [ ] Change `SECRET_KEY` in app.py
- [ ] Change `ADMIN_CODE` from default
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS (SSL/TLS certificate)
- [ ] Set up database backups
- [ ] Use strong admin passwords
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Regular security updates

### Secure Deployment

```python
# In app.py - Production settings
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

---

## 🐛 Troubleshooting

### Common Issues

**Q: Database errors on first run?**
```bash
# Solution: Run migrations
python migrate.py
```

**Q: QR codes not generating?**
```bash
# Solution: Install dependencies
pip install qrcode Pillow
python qr_generator.py
```

**Q: Port 5000 already in use?**
```bash
# Solution: Change port in app.py
app.run(port=5001)  # Use different port
```

**Q: Can't access admin panel?**
```bash
# Solution: Become admin
# 1. Create account at /signup
# 2. Go to /become-admin
# 3. Enter code: MYCAFE2024
```

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** changes (`git commit -m 'Add AmazingFeature'`)
4. **Push** to branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/my-cafe.git
cd my-cafe

# Create branch
git checkout -b feature/my-new-feature

# Make changes and test
python app.py

# Commit and push
git add .
git commit -m "Add my new feature"
git push origin feature/my-new-feature
```

---

## 👨‍💻 Developer

<div align="center">

### **Zishan Ali**

[![Portfolio](https://img.shields.io/badge/Portfolio-Visit-orange?style=for-the-badge)](https://mycook-droid.github.io/Zishan_droid/)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=for-the-badge&logo=github)](https://github.com/mycook-droid)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/zishanali)

**Full-Stack Developer | Python Enthusiast | Open Source Contributor**

</div>

---

## ⭐ Show Your Support

If you found this project helpful, please consider:

- ⭐ **Star** this repository
- 🍴 **Fork** for your own use
- 📣 **Share** with others
- 🐛 **Report** bugs
- 💡 **Suggest** features

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 Zishan Ali

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 🙏 Acknowledgments

- **Flask Team** - Amazing Python framework
- **Chart.js** - Beautiful charts for analytics
- **Font Awesome** - Icon library
- **Unsplash** - Food images
- **GitHub Community** - Inspiration and support

---

## 📞 Support & Contact

- 📧 **Email:** zishanali.dev@gmail.com
- 💬 **GitHub Issues:** [Report a bug](https://github.com/mycook-droid/my-cafe/issues)
- 📱 **WhatsApp:** [Contact Developer](https://wa.me/YOUR_NUMBER)

---

<div align="center">

### Made with ❤️ by Zishan Ali

**Version 1.0.0** • **Last Updated:** February 2026

[⬆ Back to Top](#-my-cafe---smart-restaurant-qr-ordering-system)

</div>

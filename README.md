# SmartPrint – Campus Xerox & Self-Service Print Queue Management System

SmartPrint is an end-to-end self-service campus Xerox and document printing management web application designed for colleges, universities, and student printing centres. It eliminates long lines at the campus photocopy counter by providing document uploads, instant price calculation, queue token generation, live queue tracking, and an operator console for print shop staff.

---

## 🌟 Key Features

1. **Self-Service Student Portal**:
   - Upload PDF and Word documents (`.pdf`, `.doc`, `.docx`).
   - Automatic page count extraction using `pypdf`.
   - Flexible print options: B&W or Colour, Single-sided or Duplex, custom page ranges (e.g. `1-3, 5, 7-10`), copies, and paper sizes (A4, A3, Letter).
   - Instant real-time price estimation and breakdown.
   - Unique pickup tokens (e.g., `TK-8421`) and printable digital receipt vouchers with QR codes.

2. **Live Public Queue Display**:
   - Real-time queue board (`/queue`) designed for wall-mounted displays and student mobile viewing.
   - Shows active print jobs, sequential token numbers, order status, and dynamic wait-time countdown.
   - Privacy protection: student roll numbers and names are securely masked on the public display.
   - Auto-refreshes seamlessly via JSON polling API.

3. **Admin / Operator Console**:
   - Manage print jobs across lifecycle stages: `Queued` → `Processing` → `Ready for Pickup` → `Completed`.
   - One-click printer dispatch and print job cancellation.
   - Search orders by Pickup Token, Order Number, or Student Roll Number.
   - Download uploaded original documents directly for physical printing.
   - Campus pricing & hardware management settings panel (`/admin/settings`).

4. **Hardware & Spooler Modes**:
   - **Simulation Mode (`simulation`)**: Zero-hardware demo and testing mode that simulates printing workflows.
   - **CUPS Integration (`cups`)**: Common UNIX Printing System integration via IPP / network queue.
   - **Windows Spooler Mode (`windows_spooler`)**: Integration with local Windows printers.

5. **Dual Database Architecture**:
   - Primary: **MySQL / MariaDB** (via PyMySQL and SQLAlchemy) for production campus servers.
   - Auto-Fallback: **SQLite** (`smartprint.db`) for immediate zero-config local development and demonstrations.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (Python 3.12 or 3.14 recommended)
- Windows / macOS / Linux

### Option 1: One-Click Launch (Windows)
Double-click `run.bat` or run in terminal:
```bat
.\run.bat
```
This automatically sets up the virtual environment, installs dependencies, seeds the database, and starts the server.

### Option 2: Manual Setup

1. **Create and activate a virtual environment**:
   ```bash
   py -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize and seed database**:
   ```bash
   python seed_data.py
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open in browser**:
   Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## 🔑 Demo Login Credentials

| Role | Identifier / Email | Password | Access Details |
| :--- | :--- | :--- | :--- |
| **Administrator / Operator** | `admin@smartprint.campus` | `admin123` | Operator dashboard, queue control, pricing settings |
| **Demo Student** | `CS2026-084` or `rahul.cse@college.edu` | `student123` | Document upload, order tracking, receipts |
| **Demo Student 2** | `EC2026-042` | `student123` | ECE Student demo account |

*(Students can also create new accounts via the Registration page).*

---

## 🧪 Automated Testing

A full workflow test suite is included in `test_workflow.py`. To run tests against the running server:
```bash
python test_workflow.py
```
This tests:
- Public endpoints (`/`, `/queue`, `/pricing`)
- Student authentication and dashboard
- Price calculation API
- Document upload and order placement
- Administrator authentication, console, and settings

---

## 📁 Project Structure

```
xeroxx/
├── app.py                  # Main Flask application and HTTP route handlers
├── config.py               # Configuration management and environment variables
├── database.py             # SQLAlchemy models, initialization, and SQLite fallback
├── printer_service.py      # Print backend drivers (Simulation, CUPS, Windows Spooler)
├── utils.py                # PDF page counting, price computation, QR generator
├── seed_data.py            # Sample accounts, settings, and demo print jobs
├── test_workflow.py        # Automated end-to-end integration test suite
├── schema.sql              # Raw SQL database schema
├── requirements.txt        # Python package dependencies
├── run.bat                 # Windows one-click start script
├── .env                    # Environment variables
├── static/
│   ├── css/                # Styling (style.css, dashboard.css, queue.css)
│   └── js/                 # Client scripts (main.js, order.js, queue.js, admin.js)
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── pricing.html
│   ├── queue.html
│   ├── student_dashboard.html
│   ├── new_order.html
│   ├── order_detail.html
│   ├── order_success.html
│   ├── admin_dashboard.html
│   ├── admin_settings.html
│   └── receipt_template.html
└── uploads/
    └── documents/          # Secure storage directory for uploaded files
```

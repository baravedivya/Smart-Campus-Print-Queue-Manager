import os
import logging
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    roll_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False)  # 'student', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    orders = db.relationship('PrintOrder', backref='student', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'roll_number': self.roll_number,
            'phone': self.phone,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }


class PrintOrder(db.Model):
    __tablename__ = 'print_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Document info
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size_bytes = db.Column(db.BigInteger, nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    total_doc_pages = db.Column(db.Integer, default=1, nullable=False)
    
    # Print preferences
    page_selection_type = db.Column(db.String(20), default='all')  # 'all', 'custom'
    page_range_text = db.Column(db.String(100), default='All')
    selected_pages_count = db.Column(db.Integer, default=1, nullable=False)
    copies = db.Column(db.Integer, default=1, nullable=False)
    print_type = db.Column(db.String(20), default='bw', nullable=False)  # 'bw', 'color'
    print_sides = db.Column(db.String(20), default='single', nullable=False)  # 'single', 'duplex'
    paper_size = db.Column(db.String(20), default='A4', nullable=False)  # 'A4', 'A3', 'Letter'
    orientation = db.Column(db.String(20), default='portrait', nullable=False)  # 'portrait', 'landscape'
    total_printed_pages = db.Column(db.Integer, default=1, nullable=False)  # selected_pages * copies
    
    # Financials
    unit_price = db.Column(db.Numeric(10, 2), default=2.00, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), default=2.00, nullable=False)
    payment_method = db.Column(db.String(50), default='demo_upi', nullable=False)
    payment_status = db.Column(db.String(50), default='paid', nullable=False)  # 'paid', 'pay_on_counter', 'pending'
    payment_ref = db.Column(db.String(100), nullable=True)
    
    # Queue & Lifecycle
    # Statuses: 'queued', 'processing', 'ready', 'completed', 'cancelled'
    status = db.Column(db.String(50), default='queued', nullable=False, index=True)
    queue_position = db.Column(db.Integer, default=0)
    estimated_wait_mins = db.Column(db.Integer, default=5)
    pickup_token = db.Column(db.String(20), unique=True, nullable=False, index=True)
    special_instructions = db.Column(db.Text, nullable=True)
    
    # Hardware/Printer spooler integration
    printer_mode = db.Column(db.String(50), default='simulation')  # 'simulation', 'cups', 'windows_spooler'
    printer_job_id = db.Column(db.String(100), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'student_name': self.student.name if self.student else 'Unknown',
            'roll_number': self.student.roll_number if self.student else 'N/A',
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size_formatted': f"{self.file_size_bytes / (1024 * 1024):.2f} MB" if self.file_size_bytes >= 1024*1024 else f"{self.file_size_bytes / 1024:.1f} KB",
            'total_doc_pages': self.total_doc_pages,
            'page_selection_type': self.page_selection_type,
            'page_range_text': self.page_range_text,
            'selected_pages_count': self.selected_pages_count,
            'copies': self.copies,
            'print_type': self.print_type,
            'print_sides': self.print_sides,
            'paper_size': self.paper_size,
            'orientation': self.orientation,
            'total_printed_pages': self.total_printed_pages,
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'status': self.status,
            'queue_position': self.queue_position,
            'estimated_wait_mins': self.estimated_wait_mins,
            'pickup_token': self.pickup_token,
            'printer_mode': self.printer_mode,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M') if self.completed_at else None,
        }


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_setting(key, default=None):
    setting = SystemSetting.query.filter_by(setting_key=key).first()
    if setting:
        return setting.setting_value
    return default


def set_setting(key, value, description=None):
    setting = SystemSetting.query.filter_by(setting_key=key).first()
    if setting:
        setting.setting_value = str(value)
        if description:
            setting.description = description
    else:
        setting = SystemSetting(setting_key=key, setting_value=str(value), description=description)
        db.session.add(setting)
    db.session.commit()
    return setting.setting_value


def initialize_database(app):
    """
    Connects to MySQL or falls back gracefully to SQLite.
    Initializes schema tables and default system settings & accounts.
    """
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    is_mysql = 'mysql' in db_uri.lower()
    
    try:
        # Test connection
        engine = sqlalchemy.create_engine(db_uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Database connection verified successfully: {'MySQL' if is_mysql else 'SQLite'}")
    except Exception as e:
        logger.warning(f"Primary database connection failed ({e}). Switching to SQLite fallback...")
        sqlite_uri = f"sqlite:///{app.config['SQLITE_PATH']}"
        app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
        app.config['DATABASE_BACKEND'] = 'sqlite'
    else:
        app.config['DATABASE_BACKEND'] = 'mysql' if is_mysql else 'sqlite'
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        seed_defaults(app)


def seed_defaults(app):
    """Seeds default pricing, settings, and demo admin account."""
    default_settings = [
        ('price_bw_per_page', str(app.config.get('PRICE_BW_PER_PAGE', 2.0)), 'Black and White print price per page in INR'),
        ('price_color_per_page', str(app.config.get('PRICE_COLOR_PER_PAGE', 5.0)), 'Colour print price per page in INR'),
        ('price_duplex_page', str(app.config.get('PRICE_DUPLEX_PAGE', 2.0)), 'Duplex print per page rate in INR'),
        ('printer_mode', app.config.get('PRINTER_MODE', 'simulation'), 'Current print backend (simulation, cups, windows_spooler)'),
        ('cups_server_host', app.config.get('CUPS_SERVER_HOST', 'localhost'), 'CUPS server host address'),
        ('cups_server_port', str(app.config.get('CUPS_SERVER_PORT', 631)), 'CUPS server port number'),
        ('printer_name', app.config.get('PRINTER_NAME', 'Campus_Xerox_Main'), 'Active printer or print queue identifier'),
        ('shop_open_status', 'open', 'Status of campus Xerox counter (open/closed)'),
        ('avg_seconds_per_page', '12', 'Average printing speed per page in seconds for wait time estimation'),
        ('campus_name', app.config.get('CAMPUS_NAME', 'Central College Campus Xerox'), 'Campus and Xerox Shop name'),
        ('max_upload_size_mb', '15', 'Maximum allowed document upload size in megabytes')
    ]
    
    for key, val, desc in default_settings:
        if not SystemSetting.query.filter_by(setting_key=key).first():
            setting = SystemSetting(setting_key=key, setting_value=val, description=desc)
            db.session.add(setting)
            
    # Seed default Admin account if not existing
    admin_user = User.query.filter_by(email='admin@smartprint.campus').first()
    if not admin_user:
        admin_user = User(
            name='Campus Xerox Admin / Operator',
            email='admin@smartprint.campus',
            roll_number='STAFF-001',
            phone='9876543210',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        logger.info("Created default Administrator account: admin@smartprint.campus / admin123")

    # Seed sample student account for testing
    student_user = User.query.filter_by(email='rahul.cse@college.edu').first()
    if not student_user:
        student_user = User(
            name='Rahul Sharma',
            email='rahul.cse@college.edu',
            roll_number='CS2026-084',
            phone='9823456789',
            role='student'
        )
        student_user.set_password('student123')
        db.session.add(student_user)
        logger.info("Created demo Student account: CS2026-084 / student123")
        
    db.session.commit()

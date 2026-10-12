import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartprint-campus-secret-key-2026-98dfb841')
    
    # Secure document storage outside static
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'uploads' / 'documents'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE_MB', 15)) * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
    
    # MySQL Database Settings
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3307))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'smartprint_db')
    
    # SQLite fallback
    SQLITE_PATH = str(BASE_DIR / 'smartprint.db')
    
    # Construct primary MySQL URI
    # Format: mysql+pymysql://user:password@host:port/dbname?charset=utf8mb4
    pwd_part = f":{MYSQL_PASSWORD}" if MYSQL_PASSWORD else ""
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}{pwd_part}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True
    }
    
    # Printer Configuration
    PRINTER_MODE = os.environ.get('PRINTER_MODE', 'simulation')  # 'simulation', 'cups', 'windows_spooler'
    CUPS_SERVER_HOST = os.environ.get('CUPS_SERVER_HOST', 'localhost')
    CUPS_SERVER_PORT = int(os.environ.get('CUPS_SERVER_PORT', 631))
    PRINTER_NAME = os.environ.get('PRINTER_NAME', 'Campus_Xerox_Main')
    
    # Pricing Defaults (INR ₹)
    PRICE_BW_PER_PAGE = float(os.environ.get('PRICE_BW_PER_PAGE', 2.0))
    PRICE_COLOR_PER_PAGE = float(os.environ.get('PRICE_COLOR_PER_PAGE', 5.0))
    PRICE_DUPLEX_PAGE = float(os.environ.get('PRICE_DUPLEX_PAGE', 2.0))
    
    # Campus Details
    CAMPUS_NAME = os.environ.get('CAMPUS_NAME', 'Central College Campus Xerox')
    SHOP_LOCATION = os.environ.get('SHOP_LOCATION', 'Ground Floor, Student Activity Centre (SAC)')
    SHOP_HOURS = os.environ.get('SHOP_HOURS', '8:30 AM - 6:30 PM (Mon-Sat)')

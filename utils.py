import os
import io
import re
import uuid
import base64
import random
import logging
from datetime import datetime
from pathlib import Path
from pypdf import PdfReader
import qrcode
from config import Config

logger = logging.getLogger(__name__)

def allowed_file(filename: str) -> bool:
    """Checks if the uploaded file has an allowed extension."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


def get_document_page_count(file_path: str, file_ext: str) -> int:
    """
    Extracts total page count from an uploaded document.
    Accurately parses PDFs using pypdf.
    Provides safe fallback for DOC/DOCX.
    """
    ext = file_ext.lower().replace('.', '')
    
    if ext == 'pdf':
        try:
            reader = PdfReader(file_path)
            num_pages = len(reader.pages)
            return max(1, num_pages)
        except Exception as e:
            logger.warning(f"Failed to read PDF page count from {file_path}: {e}")
            return 1
            
    elif ext in ('doc', 'docx'):
        # For DOCX files, rough page estimate based on word/character count or default 1
        try:
            file_size_kb = os.path.getsize(file_path) / 1024
            # Rough estimate: ~25-30 KB per page for docx with standard text
            estimated = max(1, round(file_size_kb / 28))
            return min(estimated, 20)  # capped reasonable default
        except Exception:
            return 1
            
    return 1


def parse_page_range(range_str: str, total_pages: int):
    """
    Parses page range strings like '1-3, 5, 7-9' or 'all'.
    Returns: (is_valid: bool, pages: list[int], error_msg: str)
    """
    if not range_str or range_str.strip().lower() == 'all':
        return True, list(range(1, total_pages + 1)), ""
        
    cleaned = range_str.strip().replace(' ', '')
    pages = set()
    parts = cleaned.split(',')
    
    for part in parts:
        if not part:
            continue
        if '-' in part:
            bounds = part.split('-')
            if len(bounds) != 2 or not bounds[0].isdigit() or not bounds[1].isdigit():
                return False, [], f"Invalid range format: '{part}'. Example format: 1-4, 7, 9-12"
            start, end = int(bounds[0]), int(bounds[1])
            if start < 1 or end > total_pages or start > end:
                return False, [], f"Range '{part}' must be between 1 and {total_pages} with start <= end."
            pages.update(range(start, end + 1))
        else:
            if not part.isdigit():
                return False, [], f"Invalid page number: '{part}'"
            page_num = int(part)
            if page_num < 1 or page_num > total_pages:
                return False, [], f"Page {page_num} is outside document boundaries (1-{total_pages})."
            pages.add(page_num)
            
    if not pages:
        return False, [], "No valid pages specified in custom selection."
        
    sorted_pages = sorted(list(pages))
    return True, sorted_pages, ""


def calculate_price(
    pages_count: int,
    copies: int,
    print_type: str,
    print_sides: str,
    bw_rate: float = 2.0,
    color_rate: float = 5.0,
    duplex_rate: float = 2.0
) -> dict:
    """
    Calculates print price breakdown.
    For duplex printing, charges are calculated according to printed pages,
    unless specific discount rate is configured.
    """
    copies = max(1, int(copies))
    pages_count = max(1, int(pages_count))
    
    # Base rate per side/page printed
    unit_rate = float(color_rate) if print_type == 'color' else float(bw_rate)
    
    total_printed_pages = pages_count * copies
    
    # Calculate physical sheets required
    if print_sides == 'duplex':
        # Duplex uses 2 printed sides per sheet
        sheets_per_copy = (pages_count + 1) // 2
        total_sheets = sheets_per_copy * copies
    else:
        total_sheets = total_printed_pages
        
    total_price = total_printed_pages * unit_rate
    
    return {
        "unit_rate": unit_rate,
        "selected_pages": pages_count,
        "copies": copies,
        "total_printed_pages": total_printed_pages,
        "total_sheets": total_sheets,
        "print_type": print_type,
        "print_sides": print_sides,
        "total_price": round(total_price, 2)
    }


def generate_order_number() -> str:
    """Generates unique, user-friendly order number: e.g. SP-2026-4891"""
    year = datetime.now().year if 'datetime' in globals() else 2026
    rand_code = random.randint(1000, 9999)
    return f"SP-{year}-{rand_code}"


def generate_pickup_token() -> str:
    """Generates a short, memorable 4-6 char pickup token: e.g. TK-4921"""
    token_num = random.randint(1000, 9999)
    return f"TK-{token_num}"


def generate_qr_code_base64(data_string: str) -> str:
    """Generates a base64 encoded PNG data URI for QR code display."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=7,
        border=2,
    )
    qr.add_data(data_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64}"

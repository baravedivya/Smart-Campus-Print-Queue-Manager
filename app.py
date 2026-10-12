import os
import time
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_file, abort
)
from werkzeug.utils import secure_filename

from config import Config
from database import (
    db, initialize_database, User, PrintOrder, SystemSetting,
    get_setting, set_setting
)
import utils
import printer_service

app = Flask(__name__)
app.config.from_object(Config)

# Ensure document upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database (MySQL primary, SQLite auto-fallback)
initialize_database(app)


# -------------------------------------------------------------
# Authentication & Authorization Helpers
# -------------------------------------------------------------
def get_current_user():
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Admin authentication required.', 'warning')
            return redirect(url_for('login', next=request.url))
        user = get_current_user()
        if not user or user.role != 'admin':
            flash('Access restricted to Xerox Shop Administrators.', 'danger')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global_data():
    current_user = get_current_user()
    bw_rate = float(get_setting('price_bw_per_page', Config.PRICE_BW_PER_PAGE))
    color_rate = float(get_setting('price_color_per_page', Config.PRICE_COLOR_PER_PAGE))
    shop_status = get_setting('shop_open_status', 'open')
    printer_mode = get_setting('printer_mode', Config.PRINTER_MODE)
    
    # Active queue counter
    active_count = PrintOrder.query.filter(PrintOrder.status.in_(['queued', 'processing'])).count()
    
    return {
        'current_user': current_user,
        'bw_rate': bw_rate,
        'color_rate': color_rate,
        'shop_status': shop_status,
        'printer_mode': printer_mode,
        'active_queue_count': active_count,
        'campus_name': get_setting('campus_name', Config.CAMPUS_NAME),
        'now_year': datetime.now().year
    }


# -------------------------------------------------------------
# Public & Landing Routes
# -------------------------------------------------------------
@app.route('/')
def index():
    """SmartPrint Homepage with Hero, Live Queue snapshot, and service highlights."""
    recent_queue = (
        PrintOrder.query.filter(PrintOrder.status.in_(['processing', 'queued']))
        .order_by(PrintOrder.created_at.asc())
        .limit(6)
        .all()
    )
    
    stats = {
        'active_jobs': PrintOrder.query.filter(PrintOrder.status.in_(['queued', 'processing'])).count(),
        'completed_today': PrintOrder.query.filter(
            PrintOrder.status == 'completed',
            PrintOrder.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).count(),
        'est_wait_time': calculate_estimated_wait_time()
    }
    return render_template('index.html', recent_queue=recent_queue, stats=stats)


@app.route('/queue')
def public_queue():
    """Live public display of current campus printing queue."""
    active_orders = (
        PrintOrder.query.filter(PrintOrder.status.in_(['processing', 'queued', 'ready']))
        .order_by(
            db.case(
                (PrintOrder.status == 'processing', 1),
                (PrintOrder.status == 'ready', 2),
                (PrintOrder.status == 'queued', 3),
                else_=4
            ),
            PrintOrder.created_at.asc()
        )
        .all()
    )
    return render_template('queue.html', orders=active_orders)


@app.route('/pricing')
def pricing():
    """Displays transparent campus xerox pricing tiers."""
    bw_rate = float(get_setting('price_bw_per_page', Config.PRICE_BW_PER_PAGE))
    color_rate = float(get_setting('price_color_per_page', Config.PRICE_COLOR_PER_PAGE))
    duplex_rate = float(get_setting('price_duplex_page', Config.PRICE_DUPLEX_PAGE))
    return render_template('pricing.html', bw_rate=bw_rate, color_rate=color_rate, duplex_rate=duplex_rate)


# -------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        roll_number = request.form.get('roll_number', '').strip().upper()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not roll_number or not password:
            flash('Please fill in all mandatory fields.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(roll_number=roll_number).first():
            flash('An account with this roll number already exists.', 'danger')
            return render_template('register.html')

        new_user = User(
            name=name,
            email=email,
            roll_number=roll_number,
            phone=phone,
            role='student'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in to place print orders.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user = get_current_user()
        if user and user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()  # email or roll number
        password = request.form.get('password', '')

        user = User.query.filter(
            (User.email == identifier.lower()) | (User.roll_number == identifier.upper())
        ).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            flash(f'Welcome back, {user.name}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
                
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email/roll number or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


# -------------------------------------------------------------
# Student Portal Routes
# -------------------------------------------------------------
@app.route('/dashboard')
@login_required
def student_dashboard():
    user = get_current_user()
    
    # Active orders (queued, processing, ready)
    active_orders = (
        PrintOrder.query.filter_by(user_id=user.id)
        .filter(PrintOrder.status.in_(['queued', 'processing', 'ready']))
        .order_by(PrintOrder.created_at.desc())
        .all()
    )
    
    # Completed/Past orders
    past_orders = (
        PrintOrder.query.filter_by(user_id=user.id)
        .filter(PrintOrder.status.in_(['completed', 'cancelled']))
        .order_by(PrintOrder.created_at.desc())
        .limit(10)
        .all()
    )
    
    # Re-calculate live queue positions for active orders
    update_live_queue_positions()
    
    return render_template(
        'student_dashboard.html',
        user=user,
        active_orders=active_orders,
        past_orders=past_orders
    )


@app.route('/order/new', methods=['GET', 'POST'])
@login_required
def new_order():
    user = get_current_user()
    bw_rate = float(get_setting('price_bw_per_page', Config.PRICE_BW_PER_PAGE))
    color_rate = float(get_setting('price_color_per_page', Config.PRICE_COLOR_PER_PAGE))
    duplex_rate = float(get_setting('price_duplex_page', Config.PRICE_DUPLEX_PAGE))
    max_size_mb = int(get_setting('max_upload_size_mb', 15))

    if request.method == 'POST':
        # 1. Validate File
        if 'document' not in request.files:
            flash('No document file was selected.', 'danger')
            return redirect(request.url)
            
        file = request.files['document']
        if file.filename == '':
            flash('No document file was selected.', 'danger')
            return redirect(request.url)

        if not utils.allowed_file(file.filename):
            flash('Invalid file format. Only PDF, DOC, and DOCX files are allowed.', 'danger')
            return redirect(request.url)

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > max_size_mb * 1024 * 1024:
            flash(f'File size exceeds the {max_size_mb} MB limit.', 'danger')
            return redirect(request.url)

        # Securely save file with unique prefix
        original_name = secure_filename(file.filename)
        file_ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else 'pdf'
        timestamp_prefix = datetime.now().strftime('%Y%m%d_%H%M%S')
        stored_filename = f"{timestamp_prefix}_{user.id}_{original_name}"
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(saved_path)

        # 2. Extract Document Page Count
        total_pages = utils.get_document_page_count(saved_path, file_ext)

        # 3. Parse Print Preferences
        page_selection = request.form.get('page_selection', 'all')
        custom_range = request.form.get('page_range_text', '').strip()
        
        if page_selection == 'custom':
            is_valid, pages, err = utils.parse_page_range(custom_range, total_pages)
            if not is_valid:
                flash(f'Page Range Error: {err}', 'danger')
                try:
                    os.remove(saved_path)
                except OSError:
                    pass
                return redirect(request.url)
            selected_pages_count = len(pages)
            page_range_display = custom_range
        else:
            selected_pages_count = total_pages
            page_range_display = f"All ({total_pages} pages)"

        try:
            copies = int(request.form.get('copies', 1))
            copies = max(1, min(copies, 99))
        except ValueError:
            copies = 1

        print_type = request.form.get('print_type', 'bw')  # 'bw' or 'color'
        print_sides = request.form.get('print_sides', 'single')  # 'single' or 'duplex'
        paper_size = request.form.get('paper_size', 'A4')
        orientation = request.form.get('orientation', 'portrait')
        payment_method = request.form.get('payment_method', 'demo_upi')
        special_instructions = request.form.get('special_instructions', '').strip()

        # 4. Calculate Price Breakdown
        price_quote = utils.calculate_price(
            pages_count=selected_pages_count,
            copies=copies,
            print_type=print_type,
            print_sides=print_sides,
            bw_rate=bw_rate,
            color_rate=color_rate,
            duplex_rate=duplex_rate
        )

        # 5. Generate Order identifiers
        order_number = utils.generate_order_number()
        pickup_token = utils.generate_pickup_token()
        
        # Calculate initial queue position
        active_jobs_count = PrintOrder.query.filter(PrintOrder.status.in_(['queued', 'processing'])).count()
        queue_pos = active_jobs_count + 1
        est_wait = max(3, queue_pos * 3)  # estimated 3 mins per job ahead

        # Determine payment status
        payment_status = 'paid' if payment_method in ['demo_upi', 'student_wallet'] else 'pay_on_counter'
        payment_ref = f"TXN-{int(time.time())}-{pickup_token}"

        # 6. Save Print Order
        order = PrintOrder(
            order_number=order_number,
            user_id=user.id,
            original_filename=original_name,
            stored_filename=stored_filename,
            file_path=saved_path,
            file_size_bytes=file_size,
            file_type=file_ext.upper(),
            total_doc_pages=total_pages,
            page_selection_type=page_selection,
            page_range_text=page_range_display,
            selected_pages_count=selected_pages_count,
            copies=copies,
            print_type=print_type,
            print_sides=print_sides,
            paper_size=paper_size,
            orientation=orientation,
            total_printed_pages=price_quote['total_printed_pages'],
            unit_price=price_quote['unit_rate'],
            total_price=price_quote['total_price'],
            payment_method=payment_method,
            payment_status=payment_status,
            payment_ref=payment_ref,
            status='queued',
            queue_position=queue_pos,
            estimated_wait_mins=est_wait,
            pickup_token=pickup_token,
            special_instructions=special_instructions,
            printer_mode=get_setting('printer_mode', Config.PRINTER_MODE)
        )
        db.session.add(order)
        db.session.commit()

        flash(f'Print Order {order.order_number} submitted to queue successfully!', 'success')
        return redirect(url_for('order_success', order_id=order.id))

    return render_template(
        'new_order.html',
        bw_rate=bw_rate,
        color_rate=color_rate,
        duplex_rate=duplex_rate,
        max_size_mb=max_size_mb
    )


@app.route('/order/<int:order_id>/success')
@login_required
def order_success(order_id):
    user = get_current_user()
    order = db.session.get(PrintOrder, order_id)
    if not order or (order.user_id != user.id and not user.is_admin):
        flash('Order not found.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    qr_data = utils.generate_qr_code_base64(f"SMARTPRINT:{order.order_number}:{order.pickup_token}")
    update_live_queue_positions()
    
    return render_template('order_success.html', order=order, qr_data=qr_data)


@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    user = get_current_user()
    order = db.session.get(PrintOrder, order_id)
    if not order or (order.user_id != user.id and not user.is_admin):
        flash('Order not found.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    qr_data = utils.generate_qr_code_base64(f"SMARTPRINT:{order.order_number}:{order.pickup_token}")
    update_live_queue_positions()
    
    return render_template('order_detail.html', order=order, qr_data=qr_data)


@app.route('/order/<int:order_id>/receipt')
@login_required
def order_receipt(order_id):
    user = get_current_user()
    order = db.session.get(PrintOrder, order_id)
    if not order or (order.user_id != user.id and not user.is_admin):
        abort(403)
        
    qr_data = utils.generate_qr_code_base64(f"SMARTPRINT:{order.order_number}:{order.pickup_token}")
    return render_template('receipt_template.html', order=order, qr_data=qr_data)


@app.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    user = get_current_user()
    order = db.session.get(PrintOrder, order_id)
    if not order or (order.user_id != user.id and not user.is_admin):
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    if order.status not in ['queued']:
        flash('This order is already being processed or completed and cannot be cancelled.', 'warning')
        return redirect(url_for('order_detail', order_id=order.id))
        
    order.status = 'cancelled'
    db.session.commit()
    update_live_queue_positions()
    
    flash(f'Order {order.order_number} has been cancelled.', 'info')
    return redirect(url_for('student_dashboard'))


# -------------------------------------------------------------
# Secure Document Serving (Never exposed via public URL)
# -------------------------------------------------------------
@app.route('/documents/<int:order_id>/view')
@login_required
def view_document(order_id):
    user = get_current_user()
    order = db.session.get(PrintOrder, order_id)
    if not order:
        abort(404)
        
    # Only order owner or shop admin can view the document
    if order.user_id != user.id and not user.is_admin:
        abort(403)
        
    if not os.path.exists(order.file_path):
        abort(404)
        
    mimetype = 'application/pdf' if order.file_type.lower() == 'pdf' else 'application/octet-stream'
    return send_file(
        order.file_path,
        mimetype=mimetype,
        as_attachment=False,
        download_name=order.original_filename
    )


# -------------------------------------------------------------
# Admin / Operator Master Portal
# -------------------------------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    # Update queue positions
    update_live_queue_positions()
    
    # Filter parameter
    status_filter = request.args.get('status', 'active')
    search_query = request.args.get('q', '').strip()
    
    query = PrintOrder.query
    
    if search_query:
        query = query.join(User).filter(
            (PrintOrder.order_number.ilike(f"%{search_query}%")) |
            (PrintOrder.pickup_token.ilike(f"%{search_query}%")) |
            (User.roll_number.ilike(f"%{search_query}%")) |
            (User.name.ilike(f"%{search_query}%"))
        )
    elif status_filter == 'active':
        query = query.filter(PrintOrder.status.in_(['queued', 'processing', 'ready']))
    elif status_filter != 'all':
        query = query.filter(PrintOrder.status == status_filter)
        
    orders = query.order_by(
        db.case(
            (PrintOrder.status == 'processing', 1),
            (PrintOrder.status == 'ready', 2),
            (PrintOrder.status == 'queued', 3),
            else_=4
        ),
        PrintOrder.created_at.asc()
    ).all()
    
    # Operator Summary KPIs
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    stats = {
        'total_active': PrintOrder.query.filter(PrintOrder.status.in_(['queued', 'processing', 'ready'])).count(),
        'in_processing': PrintOrder.query.filter_by(status='processing').count(),
        'waiting_queued': PrintOrder.query.filter_by(status='queued').count(),
        'ready_pickup': PrintOrder.query.filter_by(status='ready').count(),
        'completed_today': PrintOrder.query.filter(
            PrintOrder.status == 'completed',
            PrintOrder.created_at >= today_start
        ).count(),
        'pages_printed_today': int(db.session.query(db.func.sum(PrintOrder.total_printed_pages)).filter(
            PrintOrder.status == 'completed',
            PrintOrder.created_at >= today_start
        ).scalar() or 0),
        'revenue_today': float(db.session.query(db.func.sum(PrintOrder.total_price)).filter(
            PrintOrder.status == 'completed',
            PrintOrder.created_at >= today_start
        ).scalar() or 0.0)
    }
    
    # Printer hardware diagnostics
    mode = get_setting('printer_mode', Config.PRINTER_MODE)
    service = printer_service.get_printer_service(mode)
    printer_info = service.get_status()
    
    return render_template(
        'admin_dashboard.html',
        orders=orders,
        stats=stats,
        printer_info=printer_info,
        status_filter=status_filter,
        search_query=search_query
    )


@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    order = db.session.get(PrintOrder, order_id)
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    new_status = request.form.get('new_status')
    if new_status not in ['queued', 'processing', 'ready', 'completed', 'cancelled']:
        flash('Invalid status supplied.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    order.status = new_status
    if new_status == 'completed':
        order.completed_at = datetime.utcnow()
        if order.payment_status != 'paid':
            order.payment_status = 'paid'  # Cash collected on pickup
            
    elif new_status == 'processing':
        # Submit to printer backend
        mode = get_setting('printer_mode', Config.PRINTER_MODE)
        service = printer_service.get_printer_service(mode)
        job_result = service.submit_job(order)
        order.printer_job_id = job_result.get('job_id')
        flash(f"Order #{order.order_number}: {job_result.get('message')}", 'info')
        
    db.session.commit()
    update_live_queue_positions()
    
    flash(f"Order #{order.order_number} status updated to '{new_status.upper()}'.", 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        set_setting('price_bw_per_page', request.form.get('price_bw_per_page', 2.0))
        set_setting('price_color_per_page', request.form.get('price_color_per_page', 5.0))
        set_setting('price_duplex_page', request.form.get('price_duplex_page', 2.0))
        set_setting('printer_mode', request.form.get('printer_mode', 'simulation'))
        set_setting('cups_server_host', request.form.get('cups_server_host', 'localhost'))
        set_setting('cups_server_port', request.form.get('cups_server_port', 631))
        set_setting('printer_name', request.form.get('printer_name', 'Campus_Xerox_Main'))
        set_setting('shop_open_status', request.form.get('shop_open_status', 'open'))
        set_setting('max_upload_size_mb', request.form.get('max_upload_size_mb', 15))
        
        flash('System and pricing configurations updated successfully.', 'success')
        return redirect(url_for('admin_settings'))

    mode = get_setting('printer_mode', Config.PRINTER_MODE)
    service = printer_service.get_printer_service(mode)
    printer_info = service.get_status()

    settings_dict = {
        'price_bw_per_page': get_setting('price_bw_per_page', 2.0),
        'price_color_per_page': get_setting('price_color_per_page', 5.0),
        'price_duplex_page': get_setting('price_duplex_page', 2.0),
        'printer_mode': mode,
        'cups_server_host': get_setting('cups_server_host', 'localhost'),
        'cups_server_port': get_setting('cups_server_port', 631),
        'printer_name': get_setting('printer_name', 'Campus_Xerox_Main'),
        'shop_open_status': get_setting('shop_open_status', 'open'),
        'max_upload_size_mb': get_setting('max_upload_size_mb', 15)
    }

    return render_template('admin_settings.html', settings=settings_dict, printer_info=printer_info)


# -------------------------------------------------------------
# REST API Endpoints (AJAX Real-Time Functionality)
# -------------------------------------------------------------
@app.route('/api/inspect-document', methods=['POST'])
@login_required
def api_inspect_document():
    """Extracts page count and validates file before final order submission."""
    if 'document' not in request.files:
        return jsonify({'success': False, 'error': 'No document uploaded'}), 400
        
    file = request.files['document']
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400
        
    if not utils.allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Unsupported file format'}), 400
        
    original_name = secure_filename(file.filename)
    file_ext = original_name.rsplit('.', 1)[1].lower()
    
    # Save to temp location in uploads
    temp_name = f"temp_{int(time.time())}_{original_name}"
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_name)
    file.save(temp_path)
    
    try:
        pages = utils.get_document_page_count(temp_path, file_ext)
        file_size = os.path.getsize(temp_path)
    finally:
        # Cleanup temporary file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
            
    return jsonify({
        'success': True,
        'filename': original_name,
        'file_ext': file_ext.upper(),
        'total_pages': pages,
        'file_size_bytes': file_size,
        'file_size_formatted': f"{file_size / (1024*1024):.2f} MB" if file_size >= 1024*1024 else f"{file_size / 1024:.1f} KB"
    })


@app.route('/api/calculate-price', methods=['POST'])
def api_calculate_price():
    data = request.get_json() or {}
    pages = int(data.get('pages', 1))
    copies = int(data.get('copies', 1))
    print_type = data.get('print_type', 'bw')
    print_sides = data.get('print_sides', 'single')
    
    bw_rate = float(get_setting('price_bw_per_page', Config.PRICE_BW_PER_PAGE))
    color_rate = float(get_setting('price_color_per_page', Config.PRICE_COLOR_PER_PAGE))
    duplex_rate = float(get_setting('price_duplex_page', Config.PRICE_DUPLEX_PAGE))
    
    breakdown = utils.calculate_price(
        pages_count=pages,
        copies=copies,
        print_type=print_type,
        print_sides=print_sides,
        bw_rate=bw_rate,
        color_rate=color_rate,
        duplex_rate=duplex_rate
    )
    return jsonify({'success': True, 'quote': breakdown})


@app.route('/api/queue-status')
def api_queue_status():
    """Live queue telemetry endpoint for auto-refreshing public queue board."""
    update_live_queue_positions()
    active_orders = (
        PrintOrder.query.filter(PrintOrder.status.in_(['processing', 'ready', 'queued']))
        .order_by(
            db.case(
                (PrintOrder.status == 'processing', 1),
                (PrintOrder.status == 'ready', 2),
                (PrintOrder.status == 'queued', 3),
                else_=4
            ),
            PrintOrder.created_at.asc()
        )
        .all()
    )
    
    # Mask student name for public privacy
    def format_public_order(o):
        return {
            'order_number': o.order_number,
            'pickup_token': o.pickup_token,
            'student_masked': o.student.name.split()[0] + " " + (o.student.roll_number[-4:] if len(o.student.roll_number) >= 4 else "***"),
            'pages': o.selected_pages_count,
            'copies': o.copies,
            'print_type': o.print_type.upper(),
            'status': o.status,
            'queue_position': o.queue_position,
            'estimated_wait_mins': o.estimated_wait_mins,
            'created_at': o.created_at.strftime('%H:%M')
        }
        
    return jsonify({
        'success': True,
        'count': len(active_orders),
        'orders': [format_public_order(o) for o in active_orders],
        'est_wait_time': calculate_estimated_wait_time()
    })


@app.route('/api/order/<int:order_id>/status')
@login_required
def api_order_status(order_id):
    user = get_current_user()
    order = db.session.get(PrintOrder, order_id)
    if not order or (order.user_id != user.id and not user.is_admin):
        return jsonify({'success': False, 'error': 'Not found'}), 404
        
    update_live_queue_positions()
    return jsonify({
        'success': True,
        'status': order.status,
        'queue_position': order.queue_position,
        'estimated_wait_mins': order.estimated_wait_mins
    })


# -------------------------------------------------------------
# Internal Helpers
# -------------------------------------------------------------
def update_live_queue_positions():
    """Recalculates sequential queue numbers and estimated wait times."""
    queued_jobs = (
        PrintOrder.query.filter(PrintOrder.status.in_(['processing', 'queued']))
        .order_by(
            db.case((PrintOrder.status == 'processing', 1), else_=2),
            PrintOrder.created_at.asc()
        )
        .all()
    )
    
    cumulative_pages = 0
    pos = 1
    for job in queued_jobs:
        if job.status == 'processing':
            job.queue_position = 0  # In progress
            job.estimated_wait_mins = 1
        else:
            job.queue_position = pos
            # ~20 seconds per copy/page in queue
            job.estimated_wait_mins = max(2, round(float(cumulative_pages) * 0.3) + (pos * 2))
            pos += 1
        cumulative_pages += int(job.total_printed_pages or 0)
        
    db.session.commit()


def calculate_estimated_wait_time():
    """Calculates general waiting time for prospective orders."""
    active_pages = db.session.query(db.func.sum(PrintOrder.total_printed_pages)).filter(
        PrintOrder.status.in_(['queued', 'processing'])
    ).scalar() or 0
    return max(3, round(float(active_pages) * 0.3))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

import os
from datetime import datetime, timedelta
from app import app
from database import db, User, PrintOrder, set_setting
import utils

def seed():
    with app.app_context():
        # Ensure dummy test PDF exists in uploads/documents
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        demo_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'sample_lab_manual.pdf')
        
        # Create a tiny valid PDF file if not exists
        if not os.path.exists(demo_pdf_path):
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(demo_pdf_path)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(100, 750, "SmartPrint Campus Xerox - Sample Document")
            c.setFont("Helvetica", 12)
            c.drawString(100, 720, "This is a test document automatically generated for demo verification.")
            c.drawString(100, 700, "Campus Self-Service Printing Queue System.")
            c.showPage()
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, 750, "Page 2 - Laboratory Report & Diagrams")
            c.drawString(100, 720, "Experiments and test parameters...")
            c.showPage()
            c.save()

        # Find or create demo students
        student1 = User.query.filter_by(roll_number='CS2026-084').first()
        if not student1:
            student1 = User(
                name='Rahul Sharma',
                email='rahul.cse@college.edu',
                roll_number='CS2026-084',
                phone='9823456789',
                role='student'
            )
            student1.set_password('student123')
            db.session.add(student1)
            db.session.commit()

        student2 = User.query.filter_by(roll_number='EC2026-042').first()
        if not student2:
            student2 = User(
                name='Ananya Iyer',
                email='ananya.ece@college.edu',
                roll_number='EC2026-042',
                phone='9811223344',
                role='student'
            )
            student2.set_password('student123')
            db.session.add(student2)
            db.session.commit()

        student3 = User.query.filter_by(roll_number='ME2026-115').first()
        if not student3:
            student3 = User(
                name='Vikram Singh',
                email='vikram.mech@college.edu',
                roll_number='ME2026-115',
                phone='9899887766',
                role='student'
            )
            student3.set_password('student123')
            db.session.add(student3)
            db.session.commit()

        # Check existing orders
        if PrintOrder.query.count() == 0:
            demo_orders = [
                {
                    "order_number": "SP-2026-101",
                    "user_id": student1.id,
                    "original_filename": "OS_Lab_Assignment_4.pdf",
                    "stored_filename": "sample_lab_manual.pdf",
                    "file_path": demo_pdf_path,
                    "file_size_bytes": 145000,
                    "file_type": "PDF",
                    "total_doc_pages": 8,
                    "selected_pages_count": 8,
                    "copies": 1,
                    "print_type": "bw",
                    "print_sides": "duplex",
                    "paper_size": "A4",
                    "orientation": "portrait",
                    "total_printed_pages": 8,
                    "unit_price": 2.00,
                    "total_price": 16.00,
                    "payment_method": "demo_upi",
                    "payment_status": "paid",
                    "payment_ref": "UPI-DEMO-991201",
                    "status": "processing",
                    "queue_position": 0,
                    "estimated_wait_mins": 1,
                    "pickup_token": "TK-8421",
                    "special_instructions": "Please staple on top-left corner",
                    "created_at": datetime.utcnow() - timedelta(minutes=15)
                },
                {
                    "order_number": "SP-2026-102",
                    "user_id": student2.id,
                    "original_filename": "VLSI_Design_Project_Presentation.pdf",
                    "stored_filename": "sample_lab_manual.pdf",
                    "file_path": demo_pdf_path,
                    "file_size_bytes": 284000,
                    "file_type": "PDF",
                    "total_doc_pages": 12,
                    "selected_pages_count": 12,
                    "copies": 2,
                    "print_type": "color",
                    "print_sides": "single",
                    "paper_size": "A4",
                    "orientation": "landscape",
                    "total_printed_pages": 24,
                    "unit_price": 5.00,
                    "total_price": 120.00,
                    "payment_method": "demo_upi",
                    "payment_status": "paid",
                    "payment_ref": "UPI-DEMO-991202",
                    "status": "ready",
                    "queue_position": 0,
                    "estimated_wait_mins": 0,
                    "pickup_token": "TK-3190",
                    "special_instructions": "Glossy paper if available",
                    "created_at": datetime.utcnow() - timedelta(minutes=30)
                },
                {
                    "order_number": "SP-2026-103",
                    "user_id": student3.id,
                    "original_filename": "Resume_Campus_Placements.pdf",
                    "stored_filename": "sample_lab_manual.pdf",
                    "file_path": demo_pdf_path,
                    "file_size_bytes": 98000,
                    "file_type": "PDF",
                    "total_doc_pages": 2,
                    "selected_pages_count": 2,
                    "copies": 5,
                    "print_type": "bw",
                    "print_sides": "single",
                    "paper_size": "A4",
                    "orientation": "portrait",
                    "total_printed_pages": 10,
                    "unit_price": 2.00,
                    "total_price": 20.00,
                    "payment_method": "cash_counter",
                    "payment_status": "pay_on_counter",
                    "payment_ref": "CASH-SAC-003",
                    "status": "queued",
                    "queue_position": 1,
                    "estimated_wait_mins": 4,
                    "pickup_token": "TK-6725",
                    "special_instructions": "Need urgently before 1 PM interview",
                    "created_at": datetime.utcnow() - timedelta(minutes=5)
                }
            ]

            for item in demo_orders:
                order = PrintOrder(**item)
                db.session.add(order)
            db.session.commit()
            print("Successfully seeded 3 demo print orders across active queue states!")
        else:
            print("Print orders already exist. Skipping seed.")

if __name__ == '__main__':
    seed()

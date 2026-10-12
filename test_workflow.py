import requests
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    s = requests.Session()
    print("=== 1. Testing Public Routes ===")
    r = s.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Home failed: {r.status_code}"
    print("[PASS] Home Page: 200 OK")

    r = s.get(f"{BASE_URL}/queue")
    assert r.status_code == 200
    print("[PASS] Public Queue Board: 200 OK")

    r = s.get(f"{BASE_URL}/pricing")
    assert r.status_code == 200
    print("[PASS] Pricing Page: 200 OK")

    r = s.get(f"{BASE_URL}/api/queue-status")
    assert r.status_code == 200
    data = r.json()
    assert data['success'] is True
    print(f"[PASS] API Queue Status: {data['count']} active jobs returned")

    print("\n=== 2. Testing Student Login & Dashboard ===")
    login_data = {
        'identifier': 'CS2026-084',
        'password': 'student123'
    }
    r = s.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
    assert r.status_code == 200
    assert "Rahul" in r.text
    print("[PASS] Student Login successful (Rahul Sharma)")

    r = s.get(f"{BASE_URL}/dashboard")
    assert r.status_code == 200
    assert "Student Portal" in r.text
    print("[PASS] Student Dashboard: 200 OK")

    print("\n=== 3. Testing Price Calculation API ===")
    quote_payload = {
        'pages': 15,
        'copies': 2,
        'print_type': 'bw',
        'print_sides': 'duplex'
    }
    r = s.post(f"{BASE_URL}/api/calculate-price", json=quote_payload)
    assert r.status_code == 200
    q = r.json()['quote']
    print(f"[PASS] Price Quote for 15 pages x 2 copies B&W: Total ₹{q['total_price']}, Sheets: {q['total_sheets']}")

    print("\n=== 4. Testing Document Upload & New Order Placement ===")
    # Create test document
    test_pdf = "test_doc_upload.pdf"
    with open(test_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n193\n%%EOF")

    with open(test_pdf, "rb") as f:
        order_payload = {
            'page_selection': 'all',
            'copies': 2,
            'print_type': 'color',
            'print_sides': 'duplex',
            'paper_size': 'A4',
            'orientation': 'portrait',
            'payment_method': 'demo_upi',
            'special_instructions': 'Test order automated verification'
        }
        files = {'document': (test_pdf, f, 'application/pdf')}
        r = s.post(f"{BASE_URL}/order/new", data=order_payload, files=files, allow_redirects=True)
        assert r.status_code == 200
        assert "Your Print Job is Queued" in r.text
        print("[PASS] Order Placed Successfully & Redirected to Confirmation!")

    if os.path.exists(test_pdf):
        os.remove(test_pdf)

    print("\n=== 5. Testing Admin / Operator Console ===")
    admin_session = requests.Session()
    r = admin_session.post(f"{BASE_URL}/login", data={'identifier': 'admin@smartprint.campus', 'password': 'admin123'}, allow_redirects=True)
    assert r.status_code == 200
    assert "Operator Console" in r.text or "Campus Print Queue Manager" in r.text
    print("[PASS] Admin Login successful")

    r = admin_session.get(f"{BASE_URL}/admin")
    assert r.status_code == 200
    assert "Active Queue" in r.text
    print("[PASS] Admin Dashboard: 200 OK")

    r = admin_session.get(f"{BASE_URL}/admin/settings")
    assert r.status_code == 200
    assert "Campus Xerox & Pricing Settings" in r.text
    print("[PASS] Admin Settings: 200 OK")

    print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY! SmartPrint system is fully functional.")

if __name__ == '__main__':
    run_tests()

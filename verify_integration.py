import requests
import sys

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5174"
USERNAME = "admin"
PASSWORD = "admin"

def test_backend():
    print(f"Testing Backend at {BACKEND_URL}...")
    
    # 1. Login
    login_url = f"{BACKEND_URL}/api/login/"
    try:
        response = requests.post(login_url, json={'username': USERNAME, 'password': PASSWORD})
        if response.status_code == 200:
            token = response.json().get('token')
            print(f"[OK] Login Successful. Token: {token[:10]}...")
        else:
            print(f"[FAIL] Login Failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[FAIL] Backend connection failed: {e}")
        return False

    # 2. Fetch Products
    products_url = f"{BACKEND_URL}/api/products/"
    headers = {'Authorization': f'Token {token}'}
    try:
        response = requests.get(products_url, headers=headers)
        if response.status_code == 200:
            print(f"[OK] Fetch Products Successful. Count: {len(response.json())}")
            return True
        else:
            print(f"[FAIL] Fetch Products Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Product fetch failed: {e}")
        return False

def test_frontend():
    print(f"Testing Frontend at {FRONTEND_URL}...")
    try:
        response = requests.get(FRONTEND_URL)
        if response.status_code == 200:
            print("[OK] Frontend is serving HTML.")
            return True
        else:
            print(f"[FAIL] Frontend returned {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Frontend connection failed: {e}")
        return False

if __name__ == "__main__":
    b_ok = test_backend()
    f_ok = test_frontend()
    
    if b_ok and f_ok:
        print("\n[SUCCESS] SYSTEM VERIFIED: ALL GREEN")
    else:
        print("\n[WARNING] SYSTEM ISSUES DETECTED")

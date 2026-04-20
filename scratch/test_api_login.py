import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_login():
    url = f"{BASE_URL}/admin/login"
    payload = {
        "email": "adminlogin6631@gmail.com",
        "password": "admin123"
    }
    try:
        print(f"POST {url} with {json.dumps(payload)}")
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()

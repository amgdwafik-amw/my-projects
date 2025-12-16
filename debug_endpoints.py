import os
import django
import sys
from django.conf import settings

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oms_backend.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from core.views import CustomerViewSet, UserViewSet, OrderViewSet
from django.contrib.auth import get_user_model

def debug_apis():
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(username='admin', role='ADMIN', defaults={'email':'admin@example.com'})
    
    factory = APIRequestFactory()
    
    # 1. Test Customers
    print("--- Testing Customers Endpoint ---")
    try:
        view = CustomerViewSet.as_view({'get': 'list'})
        request = factory.get('/api/customers/')
        request.user = admin_user
        response = view(request)
        print(f"Status: {response.status_code}")
        print(f"Data Count: {len(response.data) if isinstance(response.data, list) else 'Not a list'}")
        if response.status_code >= 400:
            print(f"Error: {response.data}")
    except Exception as e:
        print(f"Customer Endpoint Crashed: {e}")

    # 2. Test Users
    print("\n--- Testing Users Endpoint ---")
    try:
        view = UserViewSet.as_view({'get': 'list'})
        request = factory.get('/api/users/')
        request.user = admin_user
        response = view(request)
        print(f"Status: {response.status_code}")
        print(f"Data Count: {len(response.data) if isinstance(response.data, list) else 'Not a list'}")
        if response.status_code >= 400:
            print(f"Error: {response.data}")
    except Exception as e:
        print(f"User Endpoint Crashed: {e}")

    # 3. Test Orders (Again)
    print("\n--- Testing Orders Endpoint ---")
    try:
        view = OrderViewSet.as_view({'get': 'list'})
        request = factory.get('/api/orders/')
        request.user = admin_user
        response = view(request)
        print(f"Status: {response.status_code}")
        print(f"Data Count: {len(response.data) if isinstance(response.data, list) else 'Not a list'}")
    except Exception as e:
        print(f"Order Endpoint Crashed: {e}")

if __name__ == '__main__':
    debug_apis()

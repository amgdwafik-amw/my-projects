import os
import django
from django.conf import settings
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oms_backend.settings')
django.setup()

from core.models import Order, User
from rest_framework.test import APIRequestFactory
from core.views import OrderViewSet
from django.contrib.auth import get_user_model

def test_filters():
    User = get_user_model()
    # Ensure we have a user
    admin, _ = User.objects.get_or_create(username='admin', role='ADMIN', defaults={'email':'admin@example.com'})
    
    factory = APIRequestFactory()
    view = OrderViewSet.as_view({'get': 'list'})

    print("Testing Filter: Status=DRAFT")
    request = factory.get('/api/orders/', {'status': 'DRAFT'})
    request.user = admin
    response = view(request)
    print(f"Status: {response.status_code}, Count: {len(response.data)}")

    print("\nTesting Filter: Status=INVALID_STATUS")
    request = factory.get('/api/orders/', {'status': 'INVALID_STATUS'})
    request.user = admin
    response = view(request)
    # Should get empty list or error depending on strictness, usually empty list
    print(f"Status: {response.status_code}, Count: {len(response.data) if isinstance(response.data, list) else response.data}")

if __name__ == '__main__':
    try:
        test_filters()
        print("\nVerification Script Completed Successfully.")
    except Exception as e:
        print(f"\nVerification Script Failed: {e}")

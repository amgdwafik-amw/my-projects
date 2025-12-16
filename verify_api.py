import os
import django
from decimal import Decimal

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oms_backend.settings')
django.setup()

from core.models import User, Product, Order, OrderItem, Discount
from rest_framework.test import APIRequestFactory, force_authenticate
from core.views import ProductViewSet, OrderViewSet
from core.serializers import ProductSerializer

def run_verification():
    print("--- Starting Verification ---")
    
    # 1. Setup Data
    print("\n1. Setting up Test Data...")
    
    # Users
    admin, _ = User.objects.get_or_create(username='admin', role=User.Role.ADMIN)
    sales_rep, _ = User.objects.get_or_create(username='sales', role=User.Role.SALES_REP)
    warehouse, _ = User.objects.get_or_create(username='warehouse', role=User.Role.WAREHOUSE)
    
    # Product
    product, _ = Product.objects.get_or_create(
        sku='TEST-001',
        defaults={
            'name': 'Test Part',
            'stock_quantity': 10,
            'cost_price': Decimal('50.00'),
            'selling_price': Decimal('100.00')
        }
    )
    # Reset stock for test
    product.stock_quantity = 10
    product.save()
    
    print(f"Product created: {product.sku} (Stock: {product.stock_quantity})")

    # 2. Test Cost Price Visibility
    print("\n2. Testing Cost Price Visibility...")
    factory = APIRequestFactory()
    
    # Admin Request
    request = factory.get('/api/products/')
    request.user = admin
    serializer = ProductSerializer(product, context={'request': request})
    if 'cost_price' in serializer.data:
        print("PASS: Admin sees cost_price")
    else:
        print("FAIL: Admin cannot see cost_price")

    # Sales Rep Request
    request = factory.get('/api/products/')
    request.user = sales_rep
    serializer = ProductSerializer(product, context={'request': request})
    if 'cost_price' not in serializer.data:
        print("PASS: Sales Rep cannot see cost_price")
    else:
        print("FAIL: Sales Rep can see cost_price!")

    # 3. Test Order Creation & Permissions
    print("\n3. Testing Order Creation...")
    view = OrderViewSet.as_view({'post': 'create'})
    
    # Create Order Payload
    payload = {
        "customer_name": "Test Client",
        "items": [
            {"product": product.id, "quantity": 2}
        ]
    }
    
    request = factory.post('/api/orders/', payload, format='json')
    force_authenticate(request, user=sales_rep)
    response = view(request)
    
    if response.status_code == 201:
        print("PASS: Order created successfully")
        order_id = response.data['id']
        order = Order.objects.get(id=order_id)
        print(f"Order Status: {order.status}") # Should be PENDING_APPROVAL
    else:
        print(f"FAIL: Order creation failed: {response.data}")
        return

    # 4. Test Stock Logic (Creation doesn't deduct yet in current logic, verify?)
    # Logic in view: "create" calls serializer.save(). Serializer validation checks stock.
    # View perform_create does nothing extra for deduction yet.
    # But wait, my view implementation logic for status_update mentions logic.
    # Let's see if plain create does anything.
    product.refresh_from_db()
    print(f"Stock after order (Should be 10 if deduction is on transition, or 8 if immediate): {product.stock_quantity}")
    
    # 5. Test State Transition (Admin Approve)
    print("\n5. Testing Admin Approval...")
    view_status = OrderViewSet.as_view({'post': 'status_update'})
    request = factory.post(f'/api/orders/{order.id}/status_update/', {'status': 'APPROVED'}, format='json')
    force_authenticate(request, user=admin)
    response = view_status(request, pk=order.id)
    
    if response.status_code == 200:
        print("PASS: Order Approved")
    else:
        print(f"FAIL: Approval failed: {response.data}")

    # 6. Test Unauthorized Transition
    print("\n6. Testing Unauthorized Transition (Sales Rep trying to Pack)...")
    request = factory.post(f'/api/orders/{order.id}/status_update/', {'status': 'PACKED'}, format='json')
    force_authenticate(request, user=sales_rep) # Sales rep cannot pack usually?
    # Logic: "PACKED" -> Warehouse/Admin.
    # My logic: "if new_status == Order.Status.PACKED: ... pass" 
    # But I missed the Role Check for PACKED in the view code block!
    # Let's see if it fails or defaults to allowed.
    # My view code: allowed_transitions key exists.
    # Role checks: only explicit check was for APPROVED. 
    # So this might Pass (False Positive) -> Meaning I need to fix the code.
    response = view_status(request, pk=order.id)
    if response.status_code == 200:
        print("WARNING: Sales Rep was able to PACK order (Role check missing?)")
    else:
        print("PASS: Sales Rep blocked from Packing")

if __name__ == "__main__":
    run_verification()

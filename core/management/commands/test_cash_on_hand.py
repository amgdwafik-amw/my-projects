from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Order, Product, Customer
from rest_framework.test import APIRequestFactory, force_authenticate
from core.views import DashboardStatsViewSet, UserViewSet
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Verify Cash on Hand Logic'

    def handle(self, *args, **kwargs):
        self.stdout.write("Setting up test data...")
        
        # Cleanup
        Order.objects.filter(created_by__username__in=['test_rep']).delete()
        User.objects.filter(username__in=['test_rep']).delete()
        
        # Setup
        rep = User.objects.create_user(username='test_rep', password='password', role=User.Role.SALES_REP, email='rep@test.com')
        customer, _ = Customer.objects.get_or_create(name='Test Customer')
        
        # Create orders in different statuses
        # 1. Delivered (Should count as Cash on Hand) - 100.00
        Order.objects.create(customer=customer, created_by=rep, total_amount=Decimal('100.00'), status=Order.Status.DELIVERED)
        
        # 2. Delivered (Should count as Cash on Hand) - 50.50
        Order.objects.create(customer=customer, created_by=rep, total_amount=Decimal('50.50'), status=Order.Status.DELIVERED)
        
        # 3. Settled (Should NOT count) - 200.00
        Order.objects.create(customer=customer, created_by=rep, total_amount=Decimal('200.00'), status=Order.Status.SETTLED)
        
        # 4. Draft (Should NOT count) - 10.00
        Order.objects.create(customer=customer, created_by=rep, total_amount=Decimal('10.00'), status=Order.Status.DRAFT)
        
        factory = APIRequestFactory()

        # ==========================================
        # TEST 1: Dashboard Stats (Sales Rep View)
        # ==========================================
        self.stdout.write("Test 1: Dashboard Stats (Cash on Hand)... ", ending='')
        view = DashboardStatsViewSet.as_view({'get': 'list'})
        req = factory.get('/api/dashboard-stats/')
        force_authenticate(req, user=rep)
        res = view(req)
        
        print(f"DEBUG: Response keys: {res.data.keys()}")
        print(f"DEBUG: Response data: {res.data}")
        
        expected_cash = Decimal('150.50')
        actual_cash = res.data.get('cash_on_hand')
        
        if actual_cash == expected_cash:
             self.stdout.write(self.style.SUCCESS(f"PASS ({actual_cash})"))
        else:
             self.stdout.write(self.style.ERROR(f"FAIL (Expected {expected_cash}, Got {actual_cash})"))

        # ==========================================
        # TEST 2: User List (Admin View)
        # ==========================================
        self.stdout.write("Test 2: User List Annotation... ", ending='')
        admin = User.objects.filter(role=User.Role.ADMIN).first()
        if not admin:
             admin = User.objects.create_user(username='admin_check', role=User.Role.ADMIN)
             
        view = UserViewSet.as_view({'get': 'list'})
        req = factory.get('/api/users/')
        force_authenticate(req, user=admin)
        res = view(req)
        
        # Find test_rep in response
        rep_data = next((u for u in res.data if u['username'] == 'test_rep'), None)
        
        if rep_data:
            user_cash = Decimal(str(rep_data.get('cash_on_hand', 0)))
            if user_cash == expected_cash:
                self.stdout.write(self.style.SUCCESS(f"PASS ({user_cash})"))
            else:
                self.stdout.write(self.style.ERROR(f"FAIL (Expected {expected_cash}, Got {user_cash})"))
        else:
             self.stdout.write(self.style.ERROR("FAIL (test_rep not found in list)"))

        # Cleanup
        # Order.objects.filter(created_by=rep).delete()
        # rep.delete()

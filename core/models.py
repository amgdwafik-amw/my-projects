from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        SALES_REP = 'SALES_REP', 'Sales Rep'
        WAREHOUSE = 'WAREHOUSE', 'Warehouse'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SALES_REP)

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost Price (Hidden from Sales)")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Category(models.TextChoices):
        SPARE_PART = 'SPARE_PART', 'Spare Part'
        ACCESSORIES = 'ACCESSORIES', 'Accessories'
        OTHERS = 'OTHERS', 'Others'

    category = models.CharField(max_length=50, choices=Category.choices, default=Category.OTHERS)
    image = models.ImageField(upload_to='products/', blank=True, null=True)



    def __str__(self):
        return f"{self.sku} - {self.name}"

class Customer(models.Model):
    class City(models.TextChoices):
        ALEXANDRIA = 'Alexandria', 'Alexandria'
        ASWAN = 'Aswan', 'Aswan'
        ASYUT = 'Asyut', 'Asyut'
        BEHEIRA = 'Beheira', 'Beheira'
        BENI_SUEF = 'Beni Suef', 'Beni Suef'
        CAIRO = 'Cairo', 'Cairo'
        DAKAHLIA = 'Dakahlia', 'Dakahlia'
        DAMIETTA = 'Damietta', 'Damietta'
        FAIYUM = 'Faiyum', 'Faiyum'
        GHARBOIA = 'Gharbia', 'Gharbia'
        GIZA = 'Giza', 'Giza'
        ISMAILIA = 'Ismailia', 'Ismailia'
        KAFR_EL_SHEIKH = 'Kafr El Sheikh', 'Kafr El Sheikh'
        LUXOR = 'Luxor', 'Luxor'
        MATRUH = 'Matruh', 'Matruh'
        MINYA = 'Minya', 'Minya'
        MONUFIA = 'Monufia', 'Monufia'
        NEW_VALLEY = 'New Valley', 'New Valley'
        NORTH_SINAI = 'North Sinai', 'North Sinai'
        PORT_SAID = 'Port Said', 'Port Said'
        QALYUBIA = 'Qalyubia', 'Qalyubia'
        QENA = 'Qena', 'Qena'
        RED_SEA = 'Red Sea', 'Red Sea'
        SHARQIA = 'Sharqia', 'Sharqia'
        SOHAG = 'Sohag', 'Sohag'
        SOUTH_SINAI = 'South Sinai', 'South Sinai'
        SUEZ = 'Suez', 'Suez'

    name = models.CharField(max_length=255)
    city = models.CharField(max_length=50, choices=City.choices, blank=True, null=True)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return self.name

class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        PACKED = 'PACKED', 'Packed'
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', 'Out for Delivery'
        DELIVERED = 'DELIVERED', 'Delivered'
        REJECTED = 'REJECTED', 'Rejected'
        SETTLED = 'SETTLED', 'Settled'

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders', null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Global Order Discount %")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name if self.customer else 'Unknown'}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()


    def __str__(self):
        return f"{self.order.id} - {self.product.sku} (x{self.quantity})"

class Invoice(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    invoice_data = models.JSONField()

    def __str__(self):
        return f"Invoice {self.invoice_number}"

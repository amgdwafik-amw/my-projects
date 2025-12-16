from rest_framework import serializers
from .models import User, Product, Order, OrderItem, Customer, Invoice
from django.db import transaction
from decimal import Decimal

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'password', 'cash_on_hand']
        
    cash_on_hand = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user



class CustomerSerializer(serializers.ModelSerializer):
    total_purchases = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'name', 'address', 'phone_number', 'city', 'total_purchases']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'description', 'stock_quantity', 'locked_stock', 'selling_price', 'cost_price', 'category', 'image']
        
    locked_stock = serializers.IntegerField(read_only=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Check if request exists and user is Sales Rep
        request = self.context.get('request')
        # If no request (internal), show everything. If Sales Rep, hide.
        if request and request.user.role == User.Role.SALES_REP:
            representation.pop('cost_price', None)
        return representation

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_sku', 'quantity']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    customer_email = serializers.CharField(source='customer.email', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    customer_address = serializers.CharField(source='customer.address', read_only=True)
    customer_city = serializers.CharField(source='customer.city', read_only=True)

    created_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'customer_name', 'customer_email', 'customer_phone', 'customer_address', 'customer_city', 'status', 'total_amount', 'discount_percentage', 'created_by', 'created_by_username', 'created_by_name', 'created_at', 'updated_at', 'items']
        read_only_fields = ['status', 'total_amount']

    def get_created_by_name(self, obj):
        if obj.created_by:
            full_name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
            return full_name if full_name else obj.created_by.username
        return "Unknown"

    def validate_created_by(self, value):
        request = self.context.get('request')
        if request and request.user.role != User.Role.ADMIN:
            if value != request.user:
                 raise serializers.ValidationError("You cannot set the order owner to another user.")
        return value

    def validate(self, attrs):
        items_data = attrs.get('items')
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Calculate total amount and basic validation
        subtotal = 0
        
        # Atomic transaction to ensure order and items are created together
        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            
            for item_data in items_data:
                product = item_data['product']
                quantity = item_data['quantity']
                
                # Check Stock
                if product.stock_quantity < quantity:
                     raise serializers.ValidationError(f"Insufficient stock for {product.name}. Available: {product.stock_quantity}")

                # Calculate Line Price
                price = product.selling_price
                line_total = (price * quantity)
                subtotal += line_total

                # Deduct Stock if status reserves it (PENDING_APPROVAL or valid active status)
                if order.status not in [Order.Status.DRAFT, Order.Status.REJECTED]:
                     product.stock_quantity -= quantity
                     product.save()

                OrderItem.objects.create(order=order, **item_data)
            
            # Apply Global Discount
            discount_multiplier = 1 - (order.discount_percentage / 100)
            order.total_amount = subtotal * discount_multiplier
            order.save()
            
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        
        with transaction.atomic():
            # Update Order fields
            instance = super().update(instance, validated_data)
            
            # Update Items if provided
            if items_data is not None:
                # Basic strategy: Delete all existing and recreate (simplest for MVP)
                # Ideally, we would diff and update/create/delete
                
                # Check status: if reserving stock, we need to handle stock reversal/re-deduction
                # But typically edits are allowed in DRAFT, where stock isn't deducted.
                # If editing in PENDING/APPROVED (Admin), we must handle stock.
                
                # 1. Restore Stock for removed items if they were reserved
                is_reserved = instance.status not in [Order.Status.DRAFT, Order.Status.REJECTED]
                
                if is_reserved:
                    for old_item in instance.items.all():
                        old_item.product.stock_quantity += old_item.quantity
                        old_item.product.save()

                # 2. Delete old items
                instance.items.all().delete()
                
                # 3. Create new items
                subtotal = 0
                for item_data in items_data:
                    product = item_data['product']
                    quantity = item_data['quantity']
                    
                    if product.stock_quantity < quantity:
                         raise serializers.ValidationError(f"Insufficient stock for {product.name}. Available: {product.stock_quantity}")

                    price = product.selling_price
                    
                    line_total = (price * quantity)
                    subtotal += line_total
                    
                    if is_reserved:
                         product.stock_quantity -= quantity
                         product.save()

                    OrderItem.objects.create(order=instance, **item_data)
                
                # Recalculate Total with updated discount (if instance changed it) or existing one
                discount_multiplier = 1 - (instance.discount_percentage / 100)
                instance.total_amount = subtotal * discount_multiplier
                instance.save()

        return instance

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'created_at', 'invoice_data']

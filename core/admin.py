from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, Order, OrderItem, Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'address')
    search_fields = ('name', 'phone_number')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Role Info', {'fields': ('role',)}),
    )



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'stock_quantity', 'selling_price')
    search_fields = ('sku', 'name')
    # inlines = [DiscountInline] removed as Discount model is deleted

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'total_amount', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    inlines = [OrderItemInline]
    readonly_fields = ('created_by', 'total_amount')



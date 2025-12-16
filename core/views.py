from rest_framework import viewsets, permissions, status, filters
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import User, Product, Order, OrderItem, Customer, Invoice
from .serializers import ProductSerializer, OrderSerializer, UserSerializer, CustomerSerializer, InvoiceSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    
    def get_queryset(self):
        from django.db.models import Sum, Q, Value, DecimalField
        from django.db.models.functions import Coalesce
        
        return Customer.objects.annotate(
            total_purchases=Coalesce(
                Sum('orders__total_amount', filter=Q(orders__status__in=['DELIVERED', 'SETTLED'])),
                Value(0),
                output_field=DecimalField()
            )
        )
    serializer_class = CustomerSerializer
    permission_classes = []

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone_number', 'address']
    filterset_fields = ['name', 'phone_number', 'city']



class UserFilter(django_filters.FilterSet):
    has_cash_on_hand = django_filters.BooleanFilter(method='filter_cash_on_hand')
    role = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = User
        fields = ['role', 'username', 'email']

    def filter_cash_on_hand(self, queryset, name, value):
        if value is True:
            return queryset.filter(cash_on_hand__gt=0)
        elif value is False:
            return queryset.filter(cash_on_hand=0)
        return queryset

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def get_queryset(self):
        from django.db.models import Sum, Q, Value, DecimalField
        from django.db.models.functions import Coalesce
        
        return User.objects.annotate(
            cash_on_hand=Coalesce(
                Sum('orders__total_amount', filter=Q(orders__status='DELIVERED')),
                Value(0),
                output_field=DecimalField()
            )
        )



from django.db.models import Sum, Q, Value
from django.db.models.functions import Coalesce



class ProductFilter(django_filters.FilterSet):
    has_locked_items = django_filters.BooleanFilter(method='filter_locked_items')

    class Meta:
        model = Product
        fields = ['sku', 'name', 'stock_quantity']

    def filter_locked_items(self, queryset, name, value):
        if value is True:
            return queryset.filter(locked_stock__gt=0)
        elif value is False:
            return queryset.filter(locked_stock=0)
        return queryset

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # Permission: Authenticated users can view. Only Admin/Warehouse can edit (simplified for MVP)
    # For now, let's allow read for all authenticated, write for Admin only ideally
    
    def get_queryset(self):
        return Product.objects.annotate(
            locked_stock=Coalesce(
                Sum('orderitem__quantity', 
                    filter=Q(orderitem__order__status__in=[Order.Status.PENDING_APPROVAL, Order.Status.APPROVED])
                ), 
                0
            )
        )

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()] # Or custom permission

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'description']
    filterset_class = ProductFilter

class OrderFilter(django_filters.FilterSet):
    created_at = django_filters.DateFromToRangeFilter()
    status = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Order
        fields = ['customer', 'status', 'created_by', 'created_at']

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OrderFilter

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN or user.role == User.Role.WAREHOUSE:
            return Order.objects.all().order_by('-created_at')
        return Order.objects.filter(created_by=user).order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        # Default to PENDING_APPROVAL, but allow DRAFT if explicitly requested
        status_input = self.request.data.get('status')
        if status_input == Order.Status.DRAFT:
            save_kwargs = {'status': Order.Status.DRAFT}
        else:
            save_kwargs = {'status': Order.Status.PENDING_APPROVAL}
        
        # Determine owner
        if user.role == User.Role.ADMIN:
             # Admin can set created_by; if not provided, default to self
             if 'created_by' not in serializer.validated_data:
                 save_kwargs['created_by'] = user
        else:
             # Non-admin: force owner to self
             save_kwargs['created_by'] = user

        serializer.save(**save_kwargs)

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance # The order being updated
        
        if user.role == User.Role.SALES_REP:
            if instance.status != Order.Status.DRAFT:
                 raise serializers.ValidationError({"error": "Sales Reps can only edit Draft orders."})
        
        serializer.save()

    @action(detail=True, methods=['post'])
    def status_update(self, request, pk=None):
        """
        Handle State Transitions.
        Admin can facilitate any transition (Next/Prev).
        Stock Logic:
        - HOLDING States (Stock Deducted): PENDING_APPROVAL, APPROVED, PACKED, OUT_FOR_DELIVERY, DELIVERED, SETTLED
        - FREE States (Stock Available): DRAFT, REJECTED
        Transitions between HOLDING and FREE trigger stock updates.
        """
        order = self.get_object()
        new_status = request.data.get('status')
        user = request.user
        
        if not new_status:
            return Response({"error": "Status is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate Status Exists
        if new_status not in Order.Status.values:
             return Response({"error": f"Invalid status: {new_status}"}, status=status.HTTP_400_BAD_REQUEST)

        # Permission Logic
        # Admin can do anything.
        # Others might have restrictions, but for this request "admin should have access..." allows broad admin rights.
        # We'll enforce basic role checks for non-admins if needed, but assuming mostly Admin/System usage for status moves in this context.
        if user.role != User.Role.ADMIN:
             # Sales Rep Transition Rules
             if user.role == User.Role.SALES_REP:
                 allowed_transitions = {
                     Order.Status.DRAFT: [Order.Status.PENDING_APPROVAL],
                     Order.Status.PENDING_APPROVAL: [Order.Status.DRAFT],
                     Order.Status.PACKED: [Order.Status.OUT_FOR_DELIVERY],
                     Order.Status.OUT_FOR_DELIVERY: [Order.Status.DELIVERED],
                 }
                 
                 allowed_targets = allowed_transitions.get(order.status, [])
                 if new_status not in allowed_targets:
                      return Response({"error": f"Sales Rep cannot transition from {order.status} to {new_status}"}, status=status.HTTP_403_FORBIDDEN)
             
             # Warehouse Transition Rules (Generic, can be refined later if needed)
             elif user.role == User.Role.WAREHOUSE:
                  # Warehouse mainly moves Approved -> Packed
                  if order.status == Order.Status.APPROVED and new_status == Order.Status.PACKED:
                      pass
                  else:
                      return Response({"error": "Warehouse can only pack approved orders (MVP Rule)"}, status=status.HTTP_403_FORBIDDEN)
             
             else:
                  # Fallback for other roles?
                  pass

        old_status = order.status
        
        # Define State Categories
        HOLDING_STATES = [
            Order.Status.PENDING_APPROVAL, 
            Order.Status.APPROVED, 
            Order.Status.PACKED, 
            Order.Status.OUT_FOR_DELIVERY, 
            Order.Status.DELIVERED, 
            Order.Status.SETTLED
        ]
        FREE_STATES = [Order.Status.DRAFT, Order.Status.REJECTED]

        with transaction.atomic():
            # Logic: FREE -> HOLDING (Deduct)
            if old_status in FREE_STATES and new_status in HOLDING_STATES:
                for item in order.items.select_related('product').all():
                    # Check stock first
                    if item.product.stock_quantity < item.quantity:
                         raise serializers.ValidationError(f"Insufficient stock for {item.product.name}. Available: {item.product.stock_quantity}")
                    item.product.stock_quantity -= item.quantity
                    item.product.save()
            
            # Logic: HOLDING -> FREE (Restore)
            elif old_status in HOLDING_STATES and new_status in FREE_STATES:
                for item in order.items.select_related('product').all():
                    item.product.stock_quantity += item.quantity
                    item.product.save()
            
            # Logic: HOLDING -> HOLDING (No stock change)
            # Logic: FREE -> FREE (No stock change)

            order.status = new_status
            order.save()


        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def generate_invoice(self, request, pk=None):
        order = self.get_object()
        
        if order.status != Order.Status.APPROVED:
             return Response({"error": "Order must be APPROVED to generate invoice"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check against last invoice
        last_invoice = order.invoices.order_by('-created_at').first()
        if last_invoice and order.updated_at <= last_invoice.created_at:
             return Response(InvoiceSerializer(last_invoice).data)

        # Calculate totals
        subtotal = sum(item.product.selling_price * item.quantity for item in order.items.all())
        discount_amount = subtotal * (order.discount_percentage / 100)
        total = subtotal - discount_amount
        
        current_data = {
            'order_id': order.id,
            'customer_name': order.customer.name if order.customer else "Guest",
            'customer_phone': order.customer.phone_number if order.customer else "",
            'customer_address': order.customer.address if order.customer else "",
            'sales_rep': order.created_by.get_full_name() or order.created_by.username,
            'issued_at': timezone.now().isoformat(),
            'items': [
                {
                    'sku': item.product.sku,
                    'category': item.product.category,
                    'quantity': item.quantity,
                    'unit_price': str(item.product.selling_price),
                    'total': str(item.product.selling_price * item.quantity)
                }
                for item in order.items.select_related('product').all()
            ],
            'subtotal': str(subtotal),
            'discount_percentage': str(order.discount_percentage),
            'discount_amount': str(discount_amount),
            'total': str(total),
            'currency': 'EGP'
        }
        
        # Generate New
        count = order.invoices.count() + 1
        inv_num = f"INV-{order.id}-{count:02d}"
        
        invoice = Invoice.objects.create(
            order=order,
            invoice_number=inv_num,
            invoice_data=current_data
        )
        return Response(InvoiceSerializer(invoice).data)
    
    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        order = self.get_object()
        invoices = order.invoices.all().order_by('-created_at')
        return Response(InvoiceSerializer(invoices, many=True).data)

class DashboardStatsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user = request.user
        
        # Base Query for Revenue
        revenue_qs = Order.objects.filter(status=Order.Status.SETTLED)
        pending_qs = Order.objects.filter(status=Order.Status.PENDING_APPROVAL)
        
        # Filter for Sales Rep
        if user.role == User.Role.SALES_REP:
            revenue_qs = revenue_qs.filter(created_by=user)
            pending_qs = pending_qs.filter(created_by=user)

        # Cash on Hand: Orders that are DELIVERED but not yet SETTLED
        # Logic: Status=DELIVERED is the state before SETTLED.
        cash_qs = Order.objects.filter(status=Order.Status.DELIVERED)
        if user.role == User.Role.SALES_REP:
            cash_qs = cash_qs.filter(created_by=user)

        total_revenue = revenue_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        pending_orders = pending_qs.count()
        cash_on_hand = cash_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        low_stock_count = Product.objects.filter(stock_quantity__lt=10).count()
        
        return Response({
            'total_revenue': total_revenue,
            'pending_orders': pending_orders,
            'low_stock_items': low_stock_count,
            'cash_on_hand': cash_on_hand
        })

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username,
            'role': user.role,
            'firstName': user.first_name,
            'lastName': user.last_name
        })

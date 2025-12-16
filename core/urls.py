from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, OrderViewSet, UserViewSet, CustomerViewSet, DashboardStatsViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'users', UserViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'dashboard-stats', DashboardStatsViewSet, basename='dashboard-stats')


urlpatterns = [
    path('', include(router.urls)),
]

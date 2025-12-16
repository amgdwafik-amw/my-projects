from django.contrib import admin
from django.urls import path, include
from core.views import CustomAuthToken
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/login/', CustomAuthToken.as_view(), name='api_token_auth'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

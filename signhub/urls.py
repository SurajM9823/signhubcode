from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('clients.urls')),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
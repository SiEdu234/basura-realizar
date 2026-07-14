from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from study.views import admin_dashboard
from study import views as study_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/register/', study_views.register_user, name='register'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('study/', include('study.urls')),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('pages/<slug:slug>/', study_views.view_custom_page, name='custom_page'),
    path('', study_views.dashboard, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

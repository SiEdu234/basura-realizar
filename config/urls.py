from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.template.exceptions import TemplateDoesNotExist
from django.http import Http404
from study.views import admin_dashboard, landing_page
from study import views as study_views
from django.conf import settings
from django.conf.urls.static import static

def render_template(request, template_name):
    try:
        return render(request, template_name)
    except TemplateDoesNotExist:
        raise Http404("Template does not exist")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/register/', study_views.register_user, name='register'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('study/', include('study.urls')),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('', landing_page, name='home'),
    path('<path:template_name>', render_template, name='render_template'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

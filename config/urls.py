from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.template.exceptions import TemplateDoesNotExist
from django.http import Http404

def home(request):
    return render(request, 'index.html')

def render_template(request, template_name):
    try:
        return render(request, template_name)
    except TemplateDoesNotExist:
        raise Http404("Template does not exist")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('<path:template_name>', render_template, name='render_template'),
]

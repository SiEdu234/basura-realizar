from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.utils.text import slugify
import json
import io
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from study.models import Subject, File, UserProfile, QuizSession, ActivityLog, CustomPage, Flashcard, FailedQuestion
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.views import View
from django.utils.decorators import method_decorator

from .utils import _log, _get_client_ip


def dashboard(request):
    """
    Vista principal del dashboard para profesores y estudiantes.
    - Profesores (Staff): Ven todos los cuadernos (propios y públicos) para gestionarlos.
    - Estudiantes: Ven solo los cuadernos que el profesor ha marcado como públicos y sus cuadernos asignados.
    """
    if request.user.is_authenticated:
        UserProfile.objects.get_or_create(user=request.user)
        
        if request.user.is_staff:
            # Los administradores pueden ver todos los cuadernos ordenados por creación
            subjects = Subject.objects.all().select_related('owner').order_by('-created_at')
        else:
            # Los estudiantes ven los públicos y los que les pertenecen
            subjects = Subject.objects.filter(
                Q(owner=request.user) | Q(is_public=True)
            ).select_related('owner').order_by('-created_at')
    else:
        subjects = Subject.objects.filter(
            Q(owner__isnull=True) | Q(is_public=True)
        ).select_related('owner').order_by('-created_at')

    # Published custom pages for nav
    nav_pages = CustomPage.objects.filter(is_published=True, show_in_nav=True).order_by('title')
    return render(request, 'study/dashboard.html', {'subjects': subjects, 'nav_pages': nav_pages})



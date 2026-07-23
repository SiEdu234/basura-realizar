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




@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('study:dashboard')

    total_subjects = Subject.objects.filter(owner__isnull=True).count()
    student_subjects = Subject.objects.filter(owner__isnull=False).count()
    public_notebooks = Subject.objects.filter(owner__isnull=False, is_public=True).count()
    total_files = File.objects.count()
    total_users = User.objects.count()
    total_sessions = QuizSession.objects.count()

    total_questions = 0
    subjects_data = []
    files_count_data = []

    for subject in Subject.objects.filter(owner__isnull=True):
        subjects_data.append(subject.name)
        files_count_data.append(subject.files.count())

    for f in File.objects.all():
        if isinstance(f.data, list):
            total_questions += len(f.data)
        elif isinstance(f.data, dict) and 'questions' in f.data:
            total_questions += len(f.data['questions'])

    # Recent activity
    recent_activity = ActivityLog.objects.select_related('user').order_by('-created_at')[:15]

    # Top students by sessions
    top_students = User.objects.filter(is_staff=False).annotate(
        session_count=Count('quiz_sessions')
    ).order_by('-session_count')[:5]

    # Recent sessions
    recent_sessions = QuizSession.objects.select_related('user', 'subject').order_by('-started_at')[:8]

    # Private notebooks for admin review
    private_notebooks = Subject.objects.filter(owner__isnull=False, is_public=False).order_by('-created_at')[:10]
    private_notebooks_count = Subject.objects.filter(owner__isnull=False, is_public=False).count()

    # Top students by score in test mode
    top_scores = QuizSession.objects.filter(mode='test', completed_at__isnull=False).order_by('-correct_answers')[:4]

    context = {
        'total_subjects': total_subjects,
        'student_subjects': student_subjects,
        'public_notebooks': public_notebooks,
        'private_notebooks_count': private_notebooks_count,
        'total_files': total_files,
        'total_users': total_users,
        'total_sessions': total_sessions,
        'total_questions': total_questions,
        'subjects_labels': json.dumps(subjects_data),
        'files_data': json.dumps(files_count_data),
        'recent_activity': recent_activity,
        'top_students': top_students,
        'top_scores': top_scores,
        'recent_sessions': recent_sessions,
        'private_notebooks': private_notebooks,
    }
    return render(request, 'home.html', context)



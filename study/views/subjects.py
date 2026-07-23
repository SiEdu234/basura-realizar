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


@login_required
def create_subject(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            if request.user.is_staff:
                Subject.objects.create(name=name, owner=None)
            else:
                Subject.objects.create(name=name, owner=request.user)
            _log(request, 'create_subject', f'Creó: {name}')
            messages.success(request, 'Cuaderno creado exitosamente.')
    return redirect('study:dashboard')


@login_required
def edit_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if not request.user.is_staff and subject.owner != request.user:
        return redirect('study:dashboard')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            subject.name = name
            subject.save()
            messages.success(request, 'Materia actualizada.')
    return redirect('study:dashboard')


@login_required
def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if not request.user.is_staff and subject.owner != request.user:
        return redirect('study:dashboard')
    if request.method == 'POST':
        _log(request, 'delete_subject', f'Eliminó: {subject.name}')
        subject.delete()
        messages.success(request, 'Materia eliminada.')
    return redirect('study:dashboard')


@login_required
def make_subject_public(request, subject_id):
    """Allow a student to make their private notebook public."""
    subject = get_object_or_404(Subject, id=subject_id)
    if subject.owner != request.user:
        messages.error(request, 'No tienes permisos para esta acción.')
        return redirect('study:dashboard')
    if request.method == 'POST':
        action = request.POST.get('action', 'public')
        if action == 'public':
            subject.is_public = True
            subject.save()
            _log(request, 'make_public', f'{request.user.username} hizo público: {subject.name}')
            messages.success(request, f'"{subject.name}" ahora es público. Otros usuarios pueden verlo.')
        else:
            subject.is_public = False
            subject.save()
            messages.success(request, f'"{subject.name}" es privado nuevamente.')
    return redirect('study:dashboard')


def subject_detail(request, subject_id):
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        if request.user.is_authenticated:
            if not request.user.is_staff:
                if subject.owner is not None and subject.owner != request.user and not subject.is_public:
                    return redirect('study:dashboard')
        else:
            if subject.owner is not None and not subject.is_public:
                return redirect('study:dashboard')

        files = subject.files.all().order_by('-created_at')
        failed_count = 0
        if request.user.is_authenticated:
            failed_count = FailedQuestion.objects.filter(user=request.user, subject=subject).count()

        return render(request, 'study/subject_detail.html', {
            'subject': subject, 
            'files': files,
            'failed_count': failed_count
        })
    except Exception as e:
        return render(request, 'study/error.html', {'error_message': str(e)})




@csrf_exempt
@login_required
def upload_file(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if not request.user.is_staff and subject.owner != request.user:
        return JsonResponse({'success': False, 'error': 'No tienes permisos para este cuaderno'})
    if request.method == 'POST':
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            try:
                content = uploaded_file.read().decode('utf-8')
                data = json.loads(content)
                File.objects.create(
                    subject=subject,
                    name=uploaded_file.name,
                    data=data,
                    uploaded_by=request.user,
                )
                _log(request, 'upload_file', f'Subió: {uploaded_file.name} a {subject.name}')
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def delete_file(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    subject_id = file_obj.subject.id
    if not request.user.is_staff and file_obj.subject.owner != request.user:
        return redirect('study:subject_detail', subject_id=subject_id)
    if request.method == 'POST':
        _log(request, 'delete_file', f'Eliminó archivo: {file_obj.name}')
        file_obj.delete()
        messages.success(request, 'Archivo eliminado.')
    return redirect('study:subject_detail', subject_id=subject_id)



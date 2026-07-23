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
def manage_users(request):
    if not request.user.is_staff:
        return redirect('study:dashboard')

    users = User.objects.select_related('profile').annotate(
        subject_count=Count('subjects'),
        session_count=Count('quiz_sessions'),
    ).order_by('-date_joined')

    context = {
        'users': users,
        'total_users': users.count(),
        'staff_count': users.filter(is_staff=True).count(),
        'active_count': users.filter(is_active=True).count(),
    }
    return render(request, 'study/manage_users.html', context)


@login_required
def toggle_user_status(request, user_id):
    if not request.user.is_staff:
        return redirect('study:dashboard')
    if request.method == 'POST':
        target = get_object_or_404(User, id=user_id)
        if target == request.user:
            messages.error(request, 'No puedes modificar tu propia cuenta.')
            return redirect('study:manage_users')
        action = request.POST.get('action')
        if action == 'toggle_active':
            target.is_active = not target.is_active
            target.save()
            status = 'activado' if target.is_active else 'desactivado'
            messages.success(request, f'Usuario {target.username} {status}.')
        elif action == 'toggle_staff':
            target.is_staff = not target.is_staff
            target.save()
            role = 'administrador' if target.is_staff else 'estudiante'
            messages.success(request, f'{target.username} ahora es {role}.')
        elif action == 'delete':
            username = target.username
            target.delete()
            messages.success(request, f'Usuario {username} eliminado.')
            return redirect('study:manage_users')
    return redirect('study:manage_users')


@login_required
def reset_user_password(request, user_id):
    if not request.user.is_staff:
        return redirect('study:dashboard')
    if request.method == 'POST':
        target = get_object_or_404(User, id=user_id)
        new_password = request.POST.get('new_password')
        if new_password and len(new_password) >= 6:
            target.set_password(new_password)
            target.save()
            messages.success(request, f'Contraseña de {target.username} actualizada.')
        else:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
    return redirect('study:manage_users')



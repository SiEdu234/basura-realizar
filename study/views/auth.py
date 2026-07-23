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


def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            _log(request, 'register', f'Nuevo usuario: {user.username}')
            messages.success(request, '¡Registro exitoso! Bienvenido al sistema.')
            return redirect('study:dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile_view(request):
    from django.contrib.auth import update_session_auth_hash
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        # Handing profile image
        avatar_file = request.FILES.get('avatar')
        if avatar_file:
            ext = avatar_file.name.split('.')[-1].lower()
            avatar_file.name = f'avatar_{request.user.id}.{ext}'
            profile.avatar = avatar_file
            profile.save()
        
        # Handling user info
        first_name = request.POST.get('first_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if first_name is not None:
            request.user.first_name = first_name
        if email is not None:
            request.user.email = email
            
        if password:
            if len(password) < 6:
                messages.error(request, 'La nueva contraseña debe tener al menos 6 caracteres.')
            else:
                request.user.set_password(password)
                update_session_auth_hash(request, request.user) # Keep user logged in
                from study.emails import send_password_changed_alert
                send_password_changed_alert(request.user)
                
        request.user.save()
        messages.success(request, '¡Perfil actualizado exitosamente!')
        return redirect('study:profile_view')
        
    sessions = QuizSession.objects.filter(user=request.user).order_by('-started_at')[:10]
    return render(request, 'study/profile.html', {'profile': profile, 'sessions': sessions})



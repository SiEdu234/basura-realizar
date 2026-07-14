from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseServerError
import json
from .models import Subject, File, UserProfile
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q

def landing_page(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        else:
            return redirect('study:dashboard')
    return render(request, 'landing.html')

def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Ensure UserProfile exists
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, '¡Registro exitoso! Bienvenido al sistema.')
            return redirect('study:dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_view(request):
    # Ensure user has a profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            profile.save()
            messages.success(request, '¡Foto de perfil actualizada exitosamente!')
            return redirect('study:profile_view')
            
    return render(request, 'study/profile.html', {'profile': profile})

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('study:dashboard')

    total_subjects = Subject.objects.filter(owner__isnull=True).count()
    student_subjects = Subject.objects.filter(owner__isnull=False).count()
    total_files = File.objects.count()
    total_users = User.objects.count()
    
    total_questions = 0
    subjects_data = []
    files_count_data = []
    
    # We'll plot public subjects
    for subject in Subject.objects.filter(owner__isnull=True):
        subjects_data.append(subject.name)
        files_count_data.append(subject.files.count())
        
    for f in File.objects.all():
        if isinstance(f.data, list):
            total_questions += len(f.data)
        elif isinstance(f.data, dict) and 'questions' in f.data:
            total_questions += len(f.data['questions'])
            
    context = {
        'total_subjects': total_subjects,
        'student_subjects': student_subjects,
        'total_files': total_files,
        'total_users': total_users,
        'total_questions': total_questions,
        'subjects_labels': json.dumps(subjects_data),
        'files_data': json.dumps(files_count_data),
    }
    return render(request, 'home.html', context)

@login_required
def dashboard(request):
    # Ensure profile exists
    UserProfile.objects.get_or_create(user=request.user)
    
    if request.user.is_staff:
        # Admins see all subjects
        subjects = Subject.objects.all().order_by('-created_at')
    else:
        # Students see global subjects (owner=None) OR their own private subjects
        subjects = Subject.objects.filter(Q(owner__isnull=True) | Q(owner=request.user)).order_by('-created_at')
        
    return render(request, 'study/dashboard.html', {'subjects': subjects})

@login_required
def create_subject(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            if request.user.is_staff:
                # Global subject
                Subject.objects.create(name=name, owner=None)
            else:
                # Private notebook
                Subject.objects.create(name=name, owner=request.user)
            messages.success(request, 'Cuaderno creado exitosamente.')
    return redirect('study:dashboard')

@login_required
def edit_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Check permissions
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
    
    # Admins can delete anything, students can only delete their own
    if not request.user.is_staff and subject.owner != request.user:
        return redirect('study:dashboard')
        
    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Materia eliminada.')
    return redirect('study:dashboard')

@login_required
def subject_detail(request, subject_id):
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Security check: if student, can only view global or own
        if not request.user.is_staff:
            if subject.owner is not None and subject.owner != request.user:
                return redirect('study:dashboard')
                
        files = subject.files.all().order_by('-created_at')
        return render(request, 'study/subject_detail.html', {'subject': subject, 'files': files})
    except Exception as e:
        return render(request, 'study/error.html', {'error_message': str(e)})

@csrf_exempt
@login_required
def upload_file(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Students can only upload to their own subjects
    if not request.user.is_staff and subject.owner != request.user:
        return JsonResponse({'success': False, 'error': 'No tienes permisos para este cuaderno'})
        
    if request.method == 'POST':
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            try:
                content = uploaded_file.read().decode('utf-8')
                data = json.loads(content)
                File.objects.create(subject=subject, name=uploaded_file.name, data=data)
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
        file_obj.delete()
        messages.success(request, 'Archivo eliminado.')
    return redirect('study:subject_detail', subject_id=subject_id)

@login_required
def quiz_runner(request, subject_id):
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        
        if not request.user.is_staff:
            if subject.owner is not None and subject.owner != request.user:
                return redirect('study:dashboard')
                
        file_ids = request.GET.get('files', '')
        mode = request.GET.get('mode', 'test')
        count = request.GET.get('count', 'all')
        
        selected_files = []
        if file_ids:
            id_list = file_ids.split(',')
            selected_files = File.objects.filter(id__in=id_list)
        else:
            selected_files = subject.files.all()
            
        files_data = [{'data': f.data} for f in selected_files]
                
        context = {
            'subject': subject,
            'files_data': files_data,
            'session_mode': mode,
            'session_count': count
        }
        return render(request, 'study/quiz_runner.html', context)
    except Exception as e:
        return render(request, 'study/error.html', {'error_message': str(e)})

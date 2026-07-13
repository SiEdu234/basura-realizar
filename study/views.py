from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseServerError
import json
from .models import Subject, File
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages

def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '¡Registro exitoso! Bienvenido al sistema.')
            return redirect('study:dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('study:dashboard')

    total_subjects = Subject.objects.count()
    total_files = File.objects.count()
    total_users = User.objects.count()
    
    total_questions = 0
    # Collect data for charts
    subjects_data = []
    files_count_data = []
    
    for subject in Subject.objects.all():
        subjects_data.append(subject.name)
        files_count_data.append(subject.files.count())
        
    for f in File.objects.all():
        if isinstance(f.data, list):
            total_questions += len(f.data)
        elif isinstance(f.data, dict) and 'questions' in f.data:
            total_questions += len(f.data['questions'])
            
    context = {
        'total_subjects': total_subjects,
        'total_files': total_files,
        'total_users': total_users,
        'total_questions': total_questions,
        'subjects_labels': json.dumps(subjects_data),
        'files_data': json.dumps(files_count_data),
    }
    return render(request, 'home.html', context)

@login_required
def dashboard(request):
    subjects = Subject.objects.all().order_by('-created_at')
    return render(request, 'study/dashboard.html', {'subjects': subjects})

@login_required
def create_subject(request):
    if not request.user.is_staff:
        return redirect('study:dashboard')

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Subject.objects.create(name=name)
            messages.success(request, 'Materia creada exitosamente.')
    return redirect('study:dashboard')

@login_required
def edit_subject(request, subject_id):
    if not request.user.is_staff:
        return redirect('study:dashboard')
        
    subject = get_object_or_404(Subject, id=subject_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            subject.name = name
            subject.save()
            messages.success(request, 'Materia actualizada.')
    return redirect('study:dashboard')

@login_required
def delete_subject(request, subject_id):
    if not request.user.is_staff:
        return redirect('study:dashboard')
        
    subject = get_object_or_404(Subject, id=subject_id)
    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Materia eliminada.')
    return redirect('study:dashboard')

@login_required
def subject_detail(request, subject_id):
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        files = subject.files.all().order_by('-created_at')
        return render(request, 'study/subject_detail.html', {'subject': subject, 'files': files})
    except Exception as e:
        return render(request, 'study/error.html', {'error_message': str(e)})

@csrf_exempt
@login_required
def upload_file(request, subject_id):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No tienes permisos de administrador'})
        
    subject = get_object_or_404(Subject, id=subject_id)
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
    if not request.user.is_staff:
        return redirect('study:dashboard')
        
    file_obj = get_object_or_404(File, id=file_id)
    subject_id = file_obj.subject.id
    if request.method == 'POST':
        file_obj.delete()
        messages.success(request, 'Archivo eliminado.')
    return redirect('study:subject_detail', subject_id=subject_id)

@login_required
def quiz_runner(request, subject_id):
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        # Passed via query parameters ?files=id1,id2
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

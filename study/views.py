import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Subject, File
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.models import User

def admin_dashboard(request):
    total_subjects = Subject.objects.count()
    total_files = File.objects.count()
    total_users = User.objects.count()
    
    total_questions = 0
    for f in File.objects.all():
        if isinstance(f.data, list):
            total_questions += len(f.data)
        elif isinstance(f.data, dict) and 'questions' in f.data:
            total_questions += len(f.data['questions'])
            
    context = {
        'total_subjects': total_subjects,
        'total_files': total_files,
        'total_users': total_users,
        'total_questions': total_questions
    }
    return render(request, 'home.html', context)

def dashboard(request):
    subjects = Subject.objects.all().order_by('-created_at')
    return render(request, 'study/dashboard.html', {'subjects': subjects})

def create_subject(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Subject.objects.create(name=name)
    return redirect('study:dashboard')

def subject_detail(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    files = subject.files.all().order_by('-created_at')
    return render(request, 'study/subject_detail.html', {'subject': subject, 'files': files})

@csrf_exempt
def upload_file(request, subject_id):
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

def quiz_runner(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    # Passed via query parameters ?files=id1,id2
    file_ids = request.GET.get('files', '')
    if file_ids:
        file_ids_list = file_ids.split(',')
        files = subject.files.filter(id__in=file_ids_list)
    else:
        files = subject.files.all()
    
    # We pass the data directly to the template so JS can use it
    files_data = []
    for f in files:
        files_data.append({'name': f.name, 'data': f.data})
        
    context = {
        'subject': subject,
        'files_data': files_data,
        'session_count': request.GET.get('count', 'all'),
        'session_mode': request.GET.get('mode', 'test'),
    }
    return render(request, 'study/quiz_runner.html', context)

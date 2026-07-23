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


def quiz_runner(request, subject_id):
    """
    Controlador principal para ejecutar un cuestionario (Quiz).
    Soporta varios modos: 'test' (normal) y 'refuerzo' (solo preguntas falladas).
    """
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Validación de permisos: Los cuadernos privados solo los ve el dueño o el staff
        if request.user.is_authenticated:
            if not request.user.is_staff:
                if subject.owner is not None and subject.owner != request.user and not subject.is_public:
                    return redirect('study:dashboard')
        else:
            if subject.owner is not None and not subject.is_public:
                return redirect('study:dashboard')

        # Parámetros de la URL
        file_ids = request.GET.get('files', '')
        mode = request.GET.get('mode', 'test')
        count = request.GET.get('count', 'all')

        if mode == 'refuerzo' and request.user.is_authenticated:
            # Modo Refuerzo: Carga exclusivamente preguntas previamente falladas por el usuario
            failed_qs = FailedQuestion.objects.filter(user=request.user, subject=subject)
            questions = [fq.question_data for fq in failed_qs]
            files_data = [{
                'id': 'refuerzo',
                'name': 'Refuerzo de Preguntas Fallidas',
                'data': {'questions': questions}
            }]
        else:
            # Modo Normal: Carga los archivos seleccionados o todos los del cuaderno
            selected_files = []
            if file_ids:
                id_list = file_ids.split(',')
                selected_files = File.objects.filter(id__in=id_list)
            else:
                selected_files = subject.files.all()
            files_data = [{'id': str(f.id), 'name': f.name, 'data': f.data} for f in selected_files]

        # Crear registro de sesión para seguimiento de estadísticas (si está logueado)
        session = None
        if request.user.is_authenticated:
            session = QuizSession.objects.create(
                user=request.user,
                subject=subject,
                mode=mode,
            )
            _log(request, 'start_quiz', f'Inició sesión en {subject.name} modo {mode}')

        context = {
            'subject': subject,
            'files_data': files_data,
            'session_mode': mode,
            'session_count': count,
            'session_id': str(session.id) if session else '',
        }
        return render(request, 'study/quiz_runner.html', context)
    except Exception as e:
        return render(request, 'study/error.html', {'error_message': str(e)})


@csrf_exempt
@login_required
def save_quiz_result(request):
    """AJAX endpoint to save quiz results."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            correct = data.get('correct', 0)
            total = data.get('total', 0)
            duration = data.get('duration', 0)
            failed_questions = data.get('failed_questions', [])
            passed_questions = data.get('passed_questions', [])

            if session_id:
                try:
                    session = QuizSession.objects.get(id=session_id, user=request.user)
                    session.correct_answers = correct
                    session.total_questions = total
                    session.duration_seconds = duration
                    session.completed_at = timezone.now()
                    session.save()
                    _log(request, 'complete_quiz', f'Completó sesión: {correct}/{total} correctas')
                    
                    # Update FailedQuestions tracking
                    for q in passed_questions:
                        q_text = q.get('text', '')
                        if q_text:
                            FailedQuestion.objects.filter(user=request.user, subject=session.subject, question_text=q_text).delete()
                            
                    for q in failed_questions:
                        q_text = q.get('text', '')
                        if q_text:
                            FailedQuestion.objects.update_or_create(
                                user=request.user,
                                subject=session.subject,
                                question_text=q_text,
                                defaults={'question_data': q}
                            )

                    return JsonResponse({'success': True, 'score': session.score_percent})
                except QuizSession.DoesNotExist:
                    pass
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})



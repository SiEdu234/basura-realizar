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
def flashcards_list(request, subject_id):
    """
    Muestra la lista de tarjetas de memoria de un cuaderno.
    Permite el acceso si el usuario es el dueño, es administrador, o si el cuaderno es público.
    Las tarjetas se ordenan por su próxima fecha de revisión.
    """
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Validar permisos: Solo dueños, staff o cuadernos públicos pueden acceder
    if not request.user.is_staff and subject.owner != request.user and not subject.is_public:
        return redirect('study:dashboard')
        
    # Obtener todas las tarjetas ordenadas por el algoritmo de repetición espaciada
    cards = Flashcard.objects.filter(subject=subject).order_by('next_review', 'created_at')
    return render(request, 'study/flashcards.html', {'subject': subject, 'cards': cards})


@csrf_exempt
@login_required
def flashcard_create(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if not request.user.is_staff and subject.owner != request.user:
        return JsonResponse({'success': False, 'error': 'Sin permisos'})
    if request.method == 'POST':
        try:
            front = request.POST.get('front', '').strip()
            back = request.POST.get('back', '').strip()
            if front and back:
                Flashcard.objects.create(
                    subject=subject,
                    owner=request.user,
                    front=front,
                    back=back,
                )
                messages.success(request, 'Tarjeta creada exitosamente.')
            else:
                messages.error(request, 'Ambos campos son obligatorios.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        return redirect('study:flashcards_list', subject_id=subject.id)
    return redirect('study:flashcards_list', subject_id=subject.id)


@csrf_exempt
@login_required
def flashcards_import(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if not request.user.is_staff and subject.owner != request.user:
        messages.error(request, 'Sin permisos para importar.')
        return redirect('study:flashcards_list', subject_id=subject.id)
        
    if request.method == 'POST':
        json_data = request.POST.get('json_data', '').strip()
        try:
            data = json.loads(json_data)
            cards_list = data.get('cards', [])
            if not cards_list:
                raise ValueError("El JSON no contiene el arreglo 'cards'.")
                
            for c in cards_list:
                diff_val = c.get('difficulty', 0)
                if isinstance(diff_val, str):
                    if diff_val.lower() == 'easy': diff_val = 1
                    elif diff_val.lower() == 'medium': diff_val = 2
                    elif diff_val.lower() == 'hard': diff_val = 3
                    else: diff_val = 1
                    
                Flashcard.objects.create(
                    subject=subject,
                    owner=request.user,
                    front=c.get('front', ''),
                    back=c.get('back', ''),
                    difficulty=diff_val
                )
            messages.success(request, f'Se importaron {len(cards_list)} tarjetas exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al importar: {str(e)}')
            
    return redirect('study:flashcards_list', subject_id=subject.id)


@csrf_exempt
@login_required
def flashcard_review(request, card_id):
    card = get_object_or_404(Flashcard, id=card_id)
    if not request.user.is_staff and card.subject.owner != request.user and not card.subject.is_public:
        return JsonResponse({'success': False, 'error': 'Sin permisos'})
        
    if request.method == 'POST':
        # Solo actualizamos el progreso si es el dueño
        if card.owner == request.user:
            try:
                data = json.loads(request.body)
                rating = data.get('rating', 2) # 1: fácil, 2: medio, 3: difícil
                
                if rating == 1:
                    card.difficulty = max(1, card.difficulty - 1)
                    card.next_review = timezone.now() + timedelta(days=2)
                elif rating == 3:
                    card.difficulty = min(3, card.difficulty + 1)
                    card.next_review = timezone.now() + timedelta(minutes=10)
                else:
                    card.next_review = timezone.now() + timedelta(days=1)
                    
                card.save()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        else:
            # Para estudiantes en cuaderno público, no guardamos su progreso en la tarjeta del profe
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def delete_flashcard(request, card_id):
    card = get_object_or_404(Flashcard, id=card_id, owner=request.user)
    subject_id = card.subject.id
    if request.method == 'POST':
        card.delete()
        messages.success(request, 'Tarjeta eliminada.')
    return redirect('study:flashcards_list', subject_id=subject_id)



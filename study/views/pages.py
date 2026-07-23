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
def manage_pages(request):
    if not request.user.is_staff:
        return redirect('study:dashboard')
    pages = CustomPage.objects.select_related('created_by').order_by('-created_at')
    return render(request, 'study/manage_pages.html', {'pages': pages})


@login_required
def create_page(request):
    if not request.user.is_staff:
        return redirect('study:dashboard')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        page_type = request.POST.get('page_type', 'custom')
        meta_desc = request.POST.get('meta_description', '').strip()
        is_published = request.POST.get('is_published') == 'on'
        show_in_nav = request.POST.get('show_in_nav') == 'on'

        if title:
            base_slug = slugify(title)
            slug = base_slug
            counter = 1
            while CustomPage.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            page = CustomPage.objects.create(
                title=title,
                slug=slug,
                page_type=page_type,
                content=content,
                meta_description=meta_desc,
                is_published=is_published,
                show_in_nav=show_in_nav,
                created_by=request.user,
            )
            messages.success(request, f'Página "{title}" creada. URL: /pages/{slug}/')
            return redirect('study:manage_pages')
        else:
            messages.error(request, 'El título es obligatorio.')
    return render(request, 'study/page_editor.html', {'page': None, 'action': 'create'})


@login_required
def edit_page(request, page_id):
    if not request.user.is_staff:
        return redirect('study:dashboard')
    page = get_object_or_404(CustomPage, id=page_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        page_type = request.POST.get('page_type', 'custom')
        meta_desc = request.POST.get('meta_description', '').strip()
        is_published = request.POST.get('is_published') == 'on'
        show_in_nav = request.POST.get('show_in_nav') == 'on'

        if title:
            page.title = title
            page.content = content
            page.page_type = page_type
            page.meta_description = meta_desc
            page.is_published = is_published
            page.show_in_nav = show_in_nav
            page.save()
            messages.success(request, f'Página "{title}" actualizada.')
            return redirect('study:manage_pages')
    return render(request, 'study/page_editor.html', {'page': page, 'action': 'edit'})


@login_required
def delete_page(request, page_id):
    if not request.user.is_staff:
        return redirect('study:dashboard')
    page = get_object_or_404(CustomPage, id=page_id)
    if request.method == 'POST':
        title = page.title
        page.delete()
        messages.success(request, f'Página "{title}" eliminada.')
    return redirect('study:manage_pages')


def view_custom_page(request, slug):
    """Render a custom page for all users."""
    page = get_object_or_404(CustomPage, slug=slug, is_published=True)
    page.views_count += 1
    page.save(update_fields=['views_count'])
    nav_pages = CustomPage.objects.filter(is_published=True, show_in_nav=True).order_by('title')
    return render(request, 'study/custom_page_view.html', {'page': page, 'nav_pages': nav_pages})



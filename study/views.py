from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.utils.text import slugify
import json
import io
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from .models import Subject, File, UserProfile, QuizSession, ActivityLog, CustomPage, Flashcard
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.views import View
from django.utils.decorators import method_decorator

# ─── PDF ────────────────────────────────────────────────────────────────────
def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def _log(request, action, description=''):
    try:
        ActivityLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=action,
            description=description,
            ip_address=_get_client_ip(request),
        )
    except Exception:
        pass

# ─── AUTH ────────────────────────────────────────────────────────────────────

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
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        avatar_file = request.FILES.get('avatar')
        if avatar_file:
            ext = avatar_file.name.split('.')[-1].lower()
            avatar_file.name = f'avatar_{request.user.id}.{ext}'
            profile.avatar = avatar_file
            profile.save()
            messages.success(request, '¡Foto de perfil actualizada exitosamente!')
            return redirect('study:profile_view')
    sessions = QuizSession.objects.filter(user=request.user).order_by('-started_at')[:10]
    return render(request, 'study/profile.html', {'profile': profile, 'sessions': sessions})


# ─── ADMIN DASHBOARD ─────────────────────────────────────────────────────────

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
    private_notebooks = Subject.objects.filter(owner__isnull=False).select_related('owner').order_by('-created_at')[:10]

    context = {
        'total_subjects': total_subjects,
        'student_subjects': student_subjects,
        'public_notebooks': public_notebooks,
        'total_files': total_files,
        'total_users': total_users,
        'total_sessions': total_sessions,
        'total_questions': total_questions,
        'subjects_labels': json.dumps(subjects_data),
        'files_data': json.dumps(files_count_data),
        'recent_activity': recent_activity,
        'top_students': top_students,
        'recent_sessions': recent_sessions,
        'private_notebooks': private_notebooks,
    }
    return render(request, 'home.html', context)


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

def dashboard(request):
    if request.user.is_authenticated:
        UserProfile.objects.get_or_create(user=request.user)
        if request.user.is_staff:
            subjects = Subject.objects.all().select_related('owner').order_by('-created_at')
        else:
            subjects = Subject.objects.filter(
                Q(owner__isnull=True) | Q(owner=request.user) | Q(is_public=True)
            ).select_related('owner').order_by('-created_at')
    else:
        subjects = Subject.objects.filter(
            Q(owner__isnull=True) | Q(is_public=True)
        ).select_related('owner').order_by('-created_at')

    # Published custom pages for nav
    nav_pages = CustomPage.objects.filter(is_published=True, show_in_nav=True).order_by('title')
    return render(request, 'study/dashboard.html', {'subjects': subjects, 'nav_pages': nav_pages})


# ─── SUBJECTS ────────────────────────────────────────────────────────────────

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
        return render(request, 'study/subject_detail.html', {'subject': subject, 'files': files})
    except Exception as e:
        return render(request, 'study/error.html', {'error_message': str(e)})


# ─── FILES ───────────────────────────────────────────────────────────────────

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


# ─── QUESTION BANK ───────────────────────────────────────────────────────────

@login_required
def question_bank(request):
    """Full question bank view, separated by JSON files."""
    if not request.user.is_staff:
        return redirect('study:dashboard')

    files = File.objects.select_related('subject', 'uploaded_by').order_by('subject__name', 'name')
    bank = []
    total_q = 0

    for f in files:
        questions = []
        if isinstance(f.data, list):
            questions = f.data
        elif isinstance(f.data, dict) and 'questions' in f.data:
            questions = f.data['questions']

        total_q += len(questions)
        bank.append({
            'file': f,
            'questions': questions,
            'count': len(questions),
        })

    context = {
        'bank': bank,
        'total_questions': total_q,
        'total_files': len(bank),
    }
    return render(request, 'study/question_bank.html', context)


# ─── QUIZ / SESSION ───────────────────────────────────────────────────────────

def quiz_runner(request, subject_id):
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        if request.user.is_authenticated:
            if not request.user.is_staff:
                if subject.owner is not None and subject.owner != request.user and not subject.is_public:
                    return redirect('study:dashboard')
        else:
            if subject.owner is not None and not subject.is_public:
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

        files_data = [{'id': str(f.id), 'name': f.name, 'data': f.data} for f in selected_files]

        # Create a session record
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

            if session_id:
                try:
                    session = QuizSession.objects.get(id=session_id, user=request.user)
                    session.correct_answers = correct
                    session.total_questions = total
                    session.duration_seconds = duration
                    session.completed_at = timezone.now()
                    session.save()
                    _log(request, 'complete_quiz', f'Completó sesión: {correct}/{total} correctas')
                    return JsonResponse({'success': True, 'score': session.score_percent})
                except QuizSession.DoesNotExist:
                    pass
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


# ─── USER MANAGEMENT ─────────────────────────────────────────────────────────

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


# ─── PDF REPORTS ─────────────────────────────────────────────────────────────

@login_required
def generate_report_pdf(request):
    if not request.user.is_staff:
        return redirect('study:dashboard')

    try:
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, inch
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable,
                                         KeepTogether, PageBreak)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        # ── Data collection ──
        total_users = User.objects.count()
        staff_count = User.objects.filter(is_staff=True).count()
        student_count = total_users - staff_count
        active_users = User.objects.filter(is_active=True).count()

        total_subjects = Subject.objects.filter(owner__isnull=True).count()
        student_subjects = Subject.objects.filter(owner__isnull=False).count()
        public_notebooks = Subject.objects.filter(owner__isnull=False, is_public=True).count()
        total_files = File.objects.count()
        total_sessions = QuizSession.objects.count()
        completed_sessions = QuizSession.objects.filter(completed_at__isnull=False).count()

        total_questions = 0
        for f in File.objects.all():
            if isinstance(f.data, list):
                total_questions += len(f.data)
            elif isinstance(f.data, dict) and 'questions' in f.data:
                total_questions += len(f.data['questions'])

        avg_score_qs = QuizSession.objects.filter(
            completed_at__isnull=False, total_questions__gt=0
        )
        avg_score = 0
        if avg_score_qs.exists():
            scores = [s.score_percent for s in avg_score_qs]
            avg_score = round(sum(scores) / len(scores), 1)

        recent_sessions = QuizSession.objects.select_related('user', 'subject').filter(
            completed_at__isnull=False
        ).order_by('-started_at')[:20]

        recent_users = User.objects.order_by('-date_joined')[:15]
        subjects_list = Subject.objects.select_related('owner').annotate(
            file_count=Count('files'),
            session_count=Count('quiz_sessions'),
        ).order_by('-created_at')[:20]

        activity_logs = ActivityLog.objects.select_related('user').order_by('-created_at')[:30]

        # ── PDF setup ──
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        PRIMARY = colors.HexColor('#3c8dbc')
        DARK = colors.HexColor('#222d32')
        SUCCESS = colors.HexColor('#00a65a')
        WARNING = colors.HexColor('#f39c12')
        DANGER = colors.HexColor('#dd4b39')
        LIGHT_BG = colors.HexColor('#f4f6f9')
        MID_GRAY = colors.HexColor('#aaaaaa')

        title_style = ParagraphStyle('Title', parent=styles['Title'],
            fontSize=22, textColor=DARK, spaceAfter=4, alignment=TA_CENTER,
            fontName='Helvetica-Bold')
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
            fontSize=11, textColor=MID_GRAY, spaceAfter=20, alignment=TA_CENTER)
        h2_style = ParagraphStyle('H2', parent=styles['Heading2'],
            fontSize=14, textColor=PRIMARY, spaceBefore=16, spaceAfter=8,
            fontName='Helvetica-Bold', borderPadding=(0, 0, 4, 0))
        h3_style = ParagraphStyle('H3', parent=styles['Heading3'],
            fontSize=11, textColor=DARK, spaceBefore=10, spaceAfter=6,
            fontName='Helvetica-Bold')
        body_style = ParagraphStyle('Body', parent=styles['Normal'],
            fontSize=9, textColor=colors.HexColor('#444444'), leading=13)
        small_style = ParagraphStyle('Small', parent=styles['Normal'],
            fontSize=8, textColor=MID_GRAY)
        cell_style = ParagraphStyle('Cell', parent=styles['Normal'],
            fontSize=8, leading=11)

        def section_table_style(header_color=PRIMARY):
            return TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), header_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ])

        story = []
        now = datetime.now()

        # ── COVER ──
        story.append(Spacer(1, 1.5*cm))
        story.append(Paragraph("📊 REPORTE GENERAL DEL SISTEMA", title_style))
        story.append(Paragraph("Study Admin — Panel de Administración", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=10))
        story.append(Paragraph(
            f"Generado el: <b>{now.strftime('%d de %B de %Y a las %H:%M')}</b> &nbsp;|&nbsp; "
            f"Por: <b>{request.user.get_full_name() or request.user.username}</b>",
            ParagraphStyle('Meta', parent=styles['Normal'], fontSize=9,
                           textColor=MID_GRAY, alignment=TA_CENTER, spaceAfter=20)
        ))
        story.append(Spacer(1, 0.5*cm))

        # ── KPI BOXES ──
        story.append(Paragraph("Resumen Ejecutivo", h2_style))
        kpi_data = [
            ['USUARIOS', 'MATERIAS PÚBLICAS', 'CUADERNOS', 'ARCHIVOS', 'PREGUNTAS', 'SESIONES'],
            [str(total_users), str(total_subjects), str(student_subjects),
             str(total_files), str(total_questions), str(total_sessions)],
        ]
        kpi_table = Table(kpi_data, colWidths=[2.7*cm]*6)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 1), (-1, 1), PRIMARY),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.white),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 18),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROUNDEDCORNERS', [5, 5, 5, 5]),
            ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 0.4*cm))

        # Secondary KPIs
        kpi2_data = [
            ['Administradores', 'Estudiantes', 'Usuarios Activos',
             'Cuadernos Públicos', 'Sesiones Completadas', 'Puntaje Promedio'],
            [str(staff_count), str(student_count), str(active_users),
             str(public_notebooks), str(completed_sessions), f'{avg_score}%'],
        ]
        kpi2_table = Table(kpi2_data, colWidths=[2.7*cm]*6)
        kpi2_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#555555')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 1), (-1, 1), SUCCESS),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.white),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, SUCCESS),
        ]))
        story.append(kpi2_table)
        story.append(Spacer(1, 0.8*cm))

        # ── USERS TABLE ──
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dddddd')))
        story.append(Paragraph("Registro de Usuarios", h2_style))
        user_rows = [['#', 'Usuario', 'Correo', 'Rol', 'Activo', 'Fecha de Registro']]
        for i, u in enumerate(recent_users, 1):
            role = 'Admin' if u.is_staff else 'Estudiante'
            active = '✓' if u.is_active else '✗'
            user_rows.append([
                str(i),
                u.username,
                u.email or '—',
                role,
                active,
                u.date_joined.strftime('%d/%m/%Y'),
            ])
        user_table = Table(user_rows, colWidths=[0.8*cm, 3.5*cm, 5*cm, 2.2*cm, 1.5*cm, 3*cm])
        user_table.setStyle(section_table_style())
        story.append(user_table)

        # ── SUBJECTS TABLE ──
        story.append(Spacer(1, 0.6*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dddddd')))
        story.append(Paragraph("Materias y Cuadernos", h2_style))
        subj_rows = [['Nombre', 'Propietario', 'Tipo', 'Archivos', 'Sesiones', 'Creado']]
        for s in subjects_list:
            tipo = 'Materia Pública' if s.owner is None else ('Público' if s.is_public else 'Privado')
            owner_name = s.owner.username if s.owner else 'Sistema'
            subj_rows.append([
                s.name,
                owner_name,
                tipo,
                str(s.file_count),
                str(s.session_count),
                s.created_at.strftime('%d/%m/%Y'),
            ])
        subj_table = Table(subj_rows, colWidths=[4.5*cm, 3*cm, 2.5*cm, 1.8*cm, 1.8*cm, 2.4*cm])
        subj_table.setStyle(section_table_style(SUCCESS))
        story.append(subj_table)

        # ── SESSIONS TABLE ──
        if recent_sessions:
            story.append(PageBreak())
            story.append(Paragraph("Sesiones de Estudio Completadas", h2_style))
            sess_rows = [['Usuario', 'Materia', 'Modo', 'Correctas', 'Total', 'Puntaje', 'Fecha']]
            for s in recent_sessions:
                sess_rows.append([
                    s.user.username,
                    s.subject.name if s.subject else '—',
                    s.get_mode_display(),
                    str(s.correct_answers),
                    str(s.total_questions),
                    f'{s.score_percent}%',
                    s.started_at.strftime('%d/%m/%Y %H:%M'),
                ])
            sess_table = Table(sess_rows, colWidths=[2.5*cm, 3.5*cm, 2*cm, 2*cm, 1.5*cm, 1.8*cm, 2.7*cm])
            sess_table.setStyle(section_table_style(WARNING))
            story.append(sess_table)

        # ── ACTIVITY LOG ──
        if activity_logs:
            story.append(Spacer(1, 0.6*cm))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dddddd')))
            story.append(Paragraph("Registro de Actividad Reciente", h2_style))
            log_rows = [['Fecha', 'Usuario', 'Acción', 'Descripción', 'IP']]
            for log in activity_logs:
                log_rows.append([
                    log.created_at.strftime('%d/%m %H:%M'),
                    log.user.username if log.user else 'Anónimo',
                    log.get_action_display(),
                    (log.description[:40] + '...') if len(log.description) > 40 else log.description,
                    log.ip_address or '—',
                ])
            log_table = Table(log_rows, colWidths=[2.2*cm, 2.5*cm, 3*cm, 5*cm, 2.3*cm])
            log_table.setStyle(section_table_style(DANGER))
            story.append(log_table)

        # ── FOOTER note ──
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY))
        story.append(Paragraph(
            f"Reporte generado automáticamente por Study Admin v1.0 | "
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} | Confidencial",
            small_style
        ))

        doc.build(story)
        buffer.seek(0)
        filename = f"reporte_study_{now.strftime('%Y%m%d_%H%M')}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ImportError:
        messages.error(request, 'ReportLab no está instalado. Ejecuta: pip install reportlab')
        return redirect('admin_dashboard')
    except Exception as e:
        messages.error(request, f'Error al generar PDF: {str(e)}')
        return redirect('admin_dashboard')


# ─── CUSTOM PAGES ────────────────────────────────────────────────────────────

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
    nav_pages = CustomPage.objects.filter(is_published=True, show_in_nav=True).order_by('title')
    return render(request, 'study/custom_page_view.html', {'page': page, 'nav_pages': nav_pages})


# ─── FLASHCARDS ──────────────────────────────────────────────────────────────

@login_required
def flashcards_list(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if not request.user.is_staff and subject.owner != request.user and not subject.is_public:
        return redirect('study:dashboard')
    cards = Flashcard.objects.filter(subject=subject, owner=request.user).order_by('next_review', 'created_at')
    return render(request, 'study/flashcards.html', {'subject': subject, 'cards': cards})


@csrf_exempt
@login_required
def flashcard_create(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if not request.user.is_staff and subject.owner != request.user:
        return JsonResponse({'success': False, 'error': 'Sin permisos'})
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            card = Flashcard.objects.create(
                subject=subject,
                owner=request.user,
                front=data.get('front', '').strip(),
                back=data.get('back', '').strip(),
            )
            return JsonResponse({'success': True, 'id': str(card.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


@csrf_exempt
@login_required
def flashcard_review(request, card_id):
    card = get_object_or_404(Flashcard, id=card_id, owner=request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            difficulty = int(data.get('difficulty', 1))
            card.difficulty = difficulty
            card.last_reviewed = timezone.now()
            card.review_count += 1
            # Simple spaced repetition: next review in N days based on difficulty
            days_map = {0: 1, 1: 3, 2: 7, 3: 14}
            card.next_review = timezone.now() + timedelta(days=days_map.get(difficulty, 1))
            card.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


@login_required
def delete_flashcard(request, card_id):
    card = get_object_or_404(Flashcard, id=card_id, owner=request.user)
    subject_id = card.subject.id
    if request.method == 'POST':
        card.delete()
        messages.success(request, 'Tarjeta eliminada.')
    return redirect('study:flashcards_list', subject_id=subject_id)


# ─── MISC ─────────────────────────────────────────────────────────────────────

def format_guide(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('study:dashboard')
    return render(request, 'study/format_guide.html')

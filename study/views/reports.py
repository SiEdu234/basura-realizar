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

        # ── PÁGINAS DINÁMICAS ──
        pages = CustomPage.objects.all().order_by('-views_count')
        if pages:
            story.append(Spacer(1, 0.6*cm))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dddddd')))
            story.append(Paragraph("Rendimiento de Páginas Dinámicas", h2_style))
            page_rows = [['Título', 'Slug', 'Tipo', 'Estado', 'Vistas']]
            for p in pages:
                page_rows.append([
                    p.title[:25],
                    f"/{p.slug}/",
                    p.get_page_type_display(),
                    'Publicada' if p.is_published else 'Borrador',
                    str(p.views_count)
                ])
            page_table = Table(page_rows, colWidths=[4*cm, 3.5*cm, 3*cm, 2.5*cm, 2*cm])
            page_table.setStyle(section_table_style(SUCCESS))
            story.append(page_table)

        # ── PREGUNTAS FALLIDAS (REFUERZO) ──
        failed_stats = FailedQuestion.objects.values('user__username', 'subject__name').annotate(
            count=Count('id')
        ).order_by('-count')
        if failed_stats:
            story.append(Spacer(1, 0.6*cm))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dddddd')))
            story.append(Paragraph("Estado de Refuerzo por Usuario/Materia", h2_style))
            fail_rows = [['Usuario', 'Materia', 'Preguntas por Repasar']]
            for f in failed_stats:
                fail_rows.append([
                    f['user__username'],
                    f['subject__name'],
                    str(f['count'])
                ])
            fail_table = Table(fail_rows, colWidths=[4.5*cm, 5.5*cm, 5*cm])
            fail_table.setStyle(section_table_style(WARNING))
            story.append(fail_table)

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



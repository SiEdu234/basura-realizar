from django.urls import path
from . import views

app_name = 'study'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile_view'),

    # Subjects
    path('subject/create/', views.create_subject, name='create_subject'),
    path('subject/<uuid:subject_id>/edit/', views.edit_subject, name='edit_subject'),
    path('subject/<uuid:subject_id>/delete/', views.delete_subject, name='delete_subject'),
    path('subject/<uuid:subject_id>/make-public/', views.make_subject_public, name='make_subject_public'),
    path('subject/<uuid:subject_id>/', views.subject_detail, name='subject_detail'),
    path('subject/<uuid:subject_id>/upload/', views.upload_file, name='upload_file'),

    # Files
    path('file/<uuid:file_id>/delete/', views.delete_file, name='delete_file'),

    # Quiz / Sessions
    path('quiz/<uuid:subject_id>/', views.quiz_runner, name='quiz_runner'),
    path('quiz/save-result/', views.save_quiz_result, name='save_quiz_result'),

    # Question Bank (admin)
    path('question-bank/', views.question_bank, name='question_bank'),

    # User Management (admin)
    path('users/', views.manage_users, name='manage_users'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/reset-password/', views.reset_user_password, name='reset_user_password'),

    # PDF Reports (admin)
    path('reports/pdf/', views.generate_report_pdf, name='generate_report_pdf'),

    # Custom Pages (admin)
    path('pages/', views.manage_pages, name='manage_pages'),
    path('pages/create/', views.create_page, name='create_page'),
    path('pages/<uuid:page_id>/edit/', views.edit_page, name='edit_page'),
    path('pages/<uuid:page_id>/delete/', views.delete_page, name='delete_page'),

    # Flashcards
    path('subject/<uuid:subject_id>/flashcards/', views.flashcards_list, name='flashcards_list'),
    path('subject/<uuid:subject_id>/flashcards/create/', views.flashcard_create, name='flashcard_create'),
    path('flashcard/<uuid:card_id>/review/', views.flashcard_review, name='flashcard_review'),
    path('flashcard/<uuid:card_id>/delete/', views.delete_flashcard, name='delete_flashcard'),

    # Format Guide
    path('format-guide/', views.format_guide, name='format_guide'),
]

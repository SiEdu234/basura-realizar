from django.urls import path
from . import views

app_name = 'study'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('subject/create/', views.create_subject, name='create_subject'),
    path('subject/<uuid:subject_id>/edit/', views.edit_subject, name='edit_subject'),
    path('subject/<uuid:subject_id>/delete/', views.delete_subject, name='delete_subject'),
    path('subject/<uuid:subject_id>/', views.subject_detail, name='subject_detail'),
    path('subject/<uuid:subject_id>/upload/', views.upload_file, name='upload_file'),
    path('file/<uuid:file_id>/delete/', views.delete_file, name='delete_file'),
    path('quiz/<uuid:subject_id>/', views.quiz_runner, name='quiz_runner'),
]

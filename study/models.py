import uuid
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return self.user.username


class Subject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='subjects')
    is_public = models.BooleanField(default=False)  # Students can make their notebooks public
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_private_notebook(self):
        """Returns True if this is a student's private notebook."""
        return self.owner is not None and not self.is_public

    @property
    def is_admin_subject(self):
        """Returns True if this is an admin-created public subject."""
        return self.owner is None


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='files')
    name = models.CharField(max_length=255)
    data = models.JSONField()
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_files')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class QuizSession(models.Model):
    """Tracks quiz/study sessions by users."""
    MODE_CHOICES = [
        ('test', 'Práctica'),
        ('study', 'Repaso'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_sessions')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='quiz_sessions')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='test')
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    duration_seconds = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.subject} - {self.started_at.date()}"

    @property
    def score_percent(self):
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100, 1)


class ActivityLog(models.Model):
    """General activity log for admin reporting."""
    ACTION_CHOICES = [
        ('login', 'Inicio de sesión'),
        ('logout', 'Cierre de sesión'),
        ('register', 'Registro'),
        ('create_subject', 'Crear materia/cuaderno'),
        ('delete_subject', 'Eliminar materia/cuaderno'),
        ('upload_file', 'Subir archivo'),
        ('delete_file', 'Eliminar archivo'),
        ('start_quiz', 'Iniciar sesión de estudio'),
        ('complete_quiz', 'Completar sesión de estudio'),
        ('make_public', 'Hacer cuaderno público'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"


class CustomPage(models.Model):
    """Admin-created custom pages displayed to users."""
    PAGE_TYPE_CHOICES = [
        ('view', 'Vista basada en plantilla'),
        ('class', 'Vista basada en clase'),
        ('custom', 'Página personalizada'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES, default='custom')
    content = models.TextField(blank=True, help_text='HTML/Text content of the page')
    meta_description = models.CharField(max_length=500, blank=True)
    is_published = models.BooleanField(default=False)
    show_in_nav = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='custom_pages')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Flashcard(models.Model):
    """Memory/flash cards for future support."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='flashcards')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
    front = models.TextField(help_text='Front side of the card (question/term)')
    back = models.TextField(help_text='Back side of the card (answer/definition)')
    difficulty = models.IntegerField(default=0, help_text='0=New, 1=Easy, 2=Medium, 3=Hard')
    last_reviewed = models.DateTimeField(null=True, blank=True)
    next_review = models.DateTimeField(null=True, blank=True)
    review_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['next_review', 'created_at']

    def __str__(self):
        return f"{self.owner.username} - {self.front[:50]}"

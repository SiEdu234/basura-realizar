from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@receiver(user_logged_in)
def send_login_alert(sender, request, user, **kwargs):
    if user.email:
        subject = 'Nuevo inicio de sesión en Study App'
        
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        html_message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
            <h2 style="color: #007bff; text-align: center;">Study App</h2>
            <p>Hola <strong>{user.username}</strong>,</p>
            <p>Se ha detectado un nuevo inicio de sesión en tu cuenta.</p>
            <ul>
                <li><strong>Dirección IP:</strong> {ip}</li>
                <li><strong>Fecha y Hora:</strong> {request.META.get('HTTP_DATE', 'Reciente')}</li>
            </ul>
            <p>Si no fuiste tú, por favor cambia tu contraseña inmediatamente.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 12px; color: #888; text-align: center;">Este es un mensaje automático, por favor no respondas.</p>
        </div>
        """
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception:
            pass

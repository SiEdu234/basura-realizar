from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags

def send_password_changed_alert(user):
    if not user.email:
        return
        
    subject = 'Alerta de Seguridad: Contraseña cambiada'
    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
        <h2 style="color: #007bff; text-align: center;">Study App</h2>
        <p>Hola <strong>{user.username}</strong>,</p>
        <p>Te escribimos para avisarte que la contraseña de tu cuenta ha sido modificada recientemente.</p>
        <p>Si fuiste tú, puedes ignorar este mensaje de forma segura.</p>
        <p style="color: red;"><strong>Si NO fuiste tú, por favor contáctanos de inmediato y restablece tu contraseña.</strong></p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #888; text-align: center;">Este es un mensaje automático de seguridad, no es necesario que respondas.</p>
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

from .models import CustomPage


def nav_pages(request):
    """Inject published nav pages into every template context."""
    try:
        pages = CustomPage.objects.filter(is_published=True, show_in_nav=True).order_by('title')
    except Exception:
        pages = []
    return {'nav_pages': pages}

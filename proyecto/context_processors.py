# proyecto/context_processors.py
from django.conf import settings

def global_settings(request):
    return {
        'SHOW_PRICES': getattr(settings, 'SHOW_PRICES', True),
        'SHOW_PRICES_CLIENTES': getattr(settings, 'SHOW_PRICES_CLIENTES', True),
    }
from django.shortcuts import render
from app1.models import Orden

def solicitudes_ordenes(request):
    # Ejemplo básico: mostrar todas las órdenes
    ordenes = Orden.objects.all().order_by('-creado')
    return render(request, 'solicitudes_cotizacion.html', {'solicitudes': [{'orden': o, 'items': list(o.items.all()), 'subtotal': float(o.total)} for o in ordenes], 'SHOW_PRICES': True})

from .models import Cliente, Orden, OrdenItem, Product


def crear_cliente(nombre, correo, telefono=''):
    nombre = (nombre or '').strip().upper()  # Normalizar a mayúsculas
    correo = (correo or '').strip().lower()  # Normalizar correo a minúsculas
    telefono = (telefono or '').strip()
    
    if not nombre or not correo:
        raise ValueError("Nombre y correo son obligatorios")
    
    # 1. Primero buscar por correo (prioridad máxima) - búsqueda insensible a mayúsculas
    cliente_existente = Cliente.objects.filter(correo__iexact=correo).first()
    if cliente_existente:
        # Si el correo existe, devolver el cliente existente (ignorando diferencias en nombre)
        return cliente_existente
    
    # 2. Si no existe por correo, crear uno nuevo
    cliente = Cliente.objects.create(
        nombre=nombre, 
        correo=correo, 
        telefono=telefono
    )
    return cliente

def crear_orden_desde_carrito(cliente, items, mensaje=''):
    """
    items: iterable de dicts {'product_id': int, 'cantidad': int}
    Crea la orden y items asociados. Devuelve la instancia Orden.
    """
    if not items:
        raise ValueError("No hay items en la orden")
    from datetime import datetime
    import pytz
    # Asignar hora local de Venezuela
    venezuela_tz = pytz.timezone('America/Caracas')
    ahora = datetime.now(venezuela_tz).replace(tzinfo=None)
    orden = Orden.objects.create(cliente=cliente, mensaje=(mensaje or '').strip(), creado=ahora)
    total = 0
    for it in items:
        pid = int(it.get('product_id'))
        cantidad = int(it.get('cantidad') or 1)
        try:
            prod = Product.objects.get(id=pid)
        except Product.DoesNotExist:
            continue
        precio = prod.precio
        OrdenItem.objects.create(
            orden=orden,
            producto=prod,
            cantidad=cantidad,
            precio_unitario=precio
        )
        total += precio * cantidad
    orden.total = total
    orden.save()
    return orden

# Compatibilidad con el nombre antiguo
crear_cotizacion_desde_carrito = crear_orden_desde_carrito

from .models import Cliente, Orden, OrdenItem, Product, Category
from decimal import Decimal


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

def crear_orden_desde_carrito(cliente, items, mensaje='', codigo_afiliado='', descuento_afiliado=0):
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
    orden = Orden.objects.create(
        cliente=cliente,
        mensaje=(mensaje or '').strip(),
        creado=ahora,
        codigo_afiliado=(codigo_afiliado or '').strip(),
        descuento_afiliado=Decimal(str(descuento_afiliado or 0))
    )
    total = Decimal('0')
    for it in items:
        pid = int(it.get('product_id'))
        cantidad = int(it.get('cantidad') or 1)
        try:
            prod = Product.objects.get(id=pid)
        except Product.DoesNotExist:
            continue
        # Usar el precio enviado si está presente (multiprecio), si no, el del producto
        precio = Decimal(str(it.get('precio', prod.precio)))
        OrdenItem.objects.create(
            orden=orden,
            producto=prod,
            cantidad=cantidad,
            precio_unitario=precio
        )
        total += precio * cantidad

    descuento_val = Decimal(str(descuento_afiliado or 0))
    if descuento_val > 0:
        descuento_monto = (total * descuento_val) / Decimal('100')
        total -= descuento_monto

    orden.total = total.quantize(Decimal('0.01'))
    orden.save()
    return orden

def crear_categoria(nombre, padre_id=None, icono_img=None):
    nombre = (nombre or '').strip()
    if not nombre:
        raise ValueError('El nombre de la categoría es obligatorio')
    padre = None
    if padre_id:
        try:
            padre = Category.objects.get(id=padre_id)
        except Category.DoesNotExist:
            padre = None
    cat = Category(nombre=nombre, padre=padre)
    if icono_img:
        cat.icono = icono_img
    cat.save()
    return cat

def editar_categoria(cat, nombre=None, padre_id=None, icono_img=None):
    if nombre:
        cat.nombre = nombre
    if padre_id is not None:
        if padre_id:
            try:
                cat.padre = Category.objects.get(id=padre_id)
            except Category.DoesNotExist:
                cat.padre = None
        else:
            cat.padre = None
    if icono_img is not None:
        cat.icono = icono_img
    cat.save()
    return cat
# Compatibilidad con el nombre antiguo
crear_cotizacion_desde_carrito = crear_orden_desde_carrito

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from .models import Category, Product
from . import crud
import random
from django.conf import settings
from urllib.parse import quote
from decimal import Decimal
from app2.models import AppConfig, Afiliado
from django.utils import timezone


def get_whatsapp_empresa():
    telefono_ventas = AppConfig.get_valor('WHATSAPP_EMPRESA')
    if not telefono_ventas:
        telefono_ventas = getattr(settings, 'WHATSAPP_EMPRESA', '')
    return (telefono_ventas or '').strip()


def get_whatsapp_url():
    telefono_ventas = get_whatsapp_empresa()
    if not telefono_ventas:
        return None

    # Normaliza el número a formato sin símbolos para wa.me
    cleaned = ''.join(ch for ch in telefono_ventas if ch.isdigit())
    if cleaned.startswith('0'):
        cleaned = '58' + cleaned.lstrip('0')

    return f'https://wa.me/{cleaned}'


def _get_cart_count(request):
    cart = request.session.get('orden', {}) or {}
    try:
        return sum(int(v) for v in cart.values())
    except Exception:
        return 0

from django.db.models import Sum

# Vista de inicio mejorada con productos más vendidos
def index(request):
    categoria_id = request.GET.get('categoria')
    categorias = Category.objects.all()
    
    # 1. Obtenemos los productos más vendidos (máximo 3, incluyendo agotados si son top)
    productos = Product.objects.filter(
        ordenitem__orden__es_venta=True
    ).annotate(
        total_vendido=Sum('ordenitem__cantidad')
    ).order_by('-total_vendido')[:3]

    # 2. Aplicamos el filtro de categoría si existe
    if categoria_id:
        try:
            productos = productos.filter(categorias__id=int(categoria_id))
        except (ValueError, TypeError):
            pass

    cart_count = _get_cart_count(request)
    whatsapp_url = get_whatsapp_url()
    whatsapp_number = get_whatsapp_empresa()
    
    return render(request, 'index.html', {
        'categorias': categorias,
        'productos': productos, 
        'categoria_id': categoria_id,
        'cart_count': cart_count,
        'whatsapp_url': whatsapp_url,
        'whatsapp_number': whatsapp_number,
    })

def tienda(request):
    categorias = Category.objects.prefetch_related('subcategorias').all()
    productos = Product.objects.prefetch_related('categorias').all()

    q = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    subcategoria_id = request.GET.get('subcategoria', '').strip()  # ← nuevo
    agotado_filter = request.GET.get('agotado', '').strip()

    # 1. Filtro por Texto
    if q:
        from django.db.models import Q
        productos = productos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))

    # 2. Filtro por Categoría / Subcategoría
    categoria_seleccionada = None  # ← nuevo
    if categoria_id:
        try:
            cid = int(categoria_id)
            categoria_seleccionada = Category.objects.prefetch_related('subcategorias').get(id=cid)  # ← nuevo

            if subcategoria_id:
                # Filtra solo por la subcategoría elegida
                productos = productos.filter(categorias__id=int(subcategoria_id))
            else:
                # Filtra por el padre + todas sus hijas
                ids_a_buscar = list(categoria_seleccionada.subcategorias.values_list('id', flat=True))
                ids_a_buscar.append(cid)
                productos = productos.filter(categorias__id__in=ids_a_buscar)

        except (ValueError, TypeError, Category.DoesNotExist):
            pass

    # 3. Filtro por Disponibilidad
    if agotado_filter == '1':
        productos = productos.filter(agotado=True)
    elif agotado_filter == '0':
        productos = productos.filter(agotado=False)

    productos = productos.distinct().order_by('-creado')

    cart_count = _get_cart_count(request)
    whatsapp_url = get_whatsapp_url()
    whatsapp_number = get_whatsapp_empresa()

    return render(request, 'tienda.html', {
        'categorias': categorias,
        'productos': productos,
        'q': q,
        'categoria_id': categoria_id,
        'subcategoria_id': subcategoria_id,        # ← nuevo
        'categoria_seleccionada': categoria_seleccionada,  # ← nuevo
        'agotado_filter': agotado_filter,
        'cart_count': cart_count,
        'whatsapp_url': whatsapp_url,
        'whatsapp_number': whatsapp_number,
    })

# Vista de detalle de producto
def productos(request, producto_id):
    producto = get_object_or_404(Product, id=producto_id)
    # Obtener imágenes del producto actual
    imagenes = list(producto.imagenes.order_by('orden'))
    if not imagenes and producto.imagen:
        imagenes = [producto.imagen]

    # Obtener productos sugeridos
    sugeridos = Product.objects.exclude(id=producto.id)
    first_cat = producto.categorias.first()
    if first_cat:
        sugeridos = sugeridos.filter(categorias=first_cat)
    sugeridos = list(sugeridos)
    random.shuffle(sugeridos)
    sugeridos = sugeridos[:4]

    cart_count = _get_cart_count(request)
    whatsapp_url = get_whatsapp_url()
    whatsapp_number = get_whatsapp_empresa()
    # Obtener precios por peso si aplica
    precios_por_peso = None
    if getattr(producto, 'por_peso', False):
        precios_por_peso = list(getattr(producto, 'precios_por_peso', []).all())

    return render(request, 'productos.html', {
        'producto': producto,
        'imagenes': imagenes,
        'sugeridos': sugeridos,
        'cart_count': cart_count,
        'whatsapp_url': whatsapp_url,
        'whatsapp_number': whatsapp_number,
        'precios_por_peso': precios_por_peso,
    })

# Nueva vista: añadir item al carrito de orden (session)
def orden_add(request):
    if request.method != 'POST':
        return redirect(request.META.get('HTTP_REFERER', reverse('tienda')))
    prod_id = request.POST.get('product_id')
    try:
        qty = int(request.POST.get('cantidad', '1'))
        if qty < 1:
            qty = 1
    except (ValueError, TypeError):
        qty = 1
    if not prod_id:
        messages.error(request, 'Producto inválido')
        return redirect(request.META.get('HTTP_REFERER', reverse('tienda')))

    cart = request.session.get('orden', {}) or {}
    cart = dict(cart)
    current = int(cart.get(str(prod_id), 0))
    current += qty
    cart[str(prod_id)] = current
    request.session['orden'] = cart
    request.session.modified = True
    messages.success(request, 'Producto agregado a la orden')
    return redirect(request.META.get('HTTP_REFERER', reverse('tienda')))

# Nueva vista: mostrar carrito de orden y enviar solicitud
def orden(request):
    cart = request.session.get('orden', {}) or {}
    product_ids = [int(k) for k in cart.keys() if k.isdigit()]
    productos = Product.objects.filter(id__in=product_ids)
    items = []
    subtotal = 0
    prod_map = {p.id: p for p in productos}
    
    # Reconstruimos los items
    for pid_str, qty in cart.items():
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        prod = prod_map.get(pid)
        if not prod:
            continue
        cantidad = int(qty)
        total = prod.precio * cantidad
        items.append({'product': prod, 'cantidad': cantidad, 'total': total})
        subtotal += total

    codigo_descuento = request.session.get('codigo_descuento', '') or ''
    afiliado_valido = None
    descuento_porcentaje = 0
    descuento_monto = 0
    total_con_descuento = subtotal
    codigo_error = ''

    if codigo_descuento:
        afiliado_valido = Afiliado.objects.filter(codigo__iexact=codigo_descuento, activo=True).first()
        if afiliado_valido:
            descuento_porcentaje = Decimal(str(afiliado_valido.descuento))
            descuento_monto = (subtotal * descuento_porcentaje / Decimal('100')).quantize(Decimal('0.01')) if subtotal else Decimal('0.00')
            total_con_descuento = (subtotal - descuento_monto).quantize(Decimal('0.01'))
        else:
            codigo_error = 'Código de descuento inválido o inactivo.'
            total_con_descuento = subtotal

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        correo = request.POST.get('correo', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        codigo_descuento = request.POST.get('codigo_descuento', '').strip().upper()
        request.session['codigo_descuento'] = codigo_descuento
        request.session.modified = True

        afiliado_valido = None
        descuento_porcentaje = Decimal('0.00')
        descuento_monto = Decimal('0.00')
        total_con_descuento = subtotal
        codigo_error = ''

        if codigo_descuento:
            afiliado_valido = Afiliado.objects.filter(codigo__iexact=codigo_descuento, activo=True).first()
            if afiliado_valido:
                descuento_porcentaje = Decimal(str(afiliado_valido.descuento))
                descuento_monto = (subtotal * descuento_porcentaje / Decimal('100')).quantize(Decimal('0.01')) if subtotal else Decimal('0.00')
                total_con_descuento = (subtotal - descuento_monto).quantize(Decimal('0.01'))
            else:
                codigo_error = 'Código de descuento inválido o inactivo.'

        if not nombre or not correo:
            messages.error(request, 'Nombre y correo son obligatorios para enviar la orden.')
            return render(request, 'orden.html', {
                'items': items,
                'subtotal': subtotal,
                'total_con_descuento': total_con_descuento,
                'descuento_porcentaje': descuento_porcentaje,
                'descuento_monto': descuento_monto,
                'codigo_descuento': codigo_descuento,
                'codigo_error': codigo_error,
                'cart_count': _get_cart_count(request),
                'whatsapp_url': get_whatsapp_url(),
                'whatsapp_number': get_whatsapp_empresa(),
            })

        if codigo_descuento and not afiliado_valido:
            messages.error(request, codigo_error)
            return render(request, 'orden.html', {
                'items': items,
                'subtotal': subtotal,
                'total_con_descuento': total_con_descuento,
                'descuento_porcentaje': descuento_porcentaje,
                'descuento_monto': descuento_monto,
                'codigo_descuento': codigo_descuento,
                'codigo_error': codigo_error,
                'cart_count': _get_cart_count(request),
                'whatsapp_url': get_whatsapp_url(),
                'whatsapp_number': get_whatsapp_empresa(),
            })

        try:
            # 1. Crear cliente y orden en BD
            cliente = crud.crear_cliente(nombre, correo, telefono)
            items_payload = [{'product_id': p['product'].id, 'cantidad': p['cantidad']} for p in items]
            orden = crud.crear_orden_desde_carrito(
                cliente,
                items_payload,
                mensaje=mensaje,
                codigo_afiliado=codigo_descuento,
                descuento_afiliado=descuento_porcentaje,
            )

            # 2. Montar mensaje de WhatsApp (cliente -> ventas)
            detalle_items = []
            total_orden = 0
            for it in items:
                p = it['product']
                c = it['cantidad']
                subtotal_item = float(p.precio) * c
                total_orden += subtotal_item
                detalle_items.append(f"{p.nombre} x{c} (${p.precio} c/u) = ${subtotal_item:.2f}")

            productos_str = "\n".join(detalle_items)
            fecha_actual = timezone.now()
            if timezone.is_naive(fecha_actual):
                fecha_actual = timezone.make_aware(fecha_actual)
            fecha_str = timezone.localtime(fecha_actual).strftime('%d/%m/%Y %H:%M')

            saludo = AppConfig.get_valor('WHATSAPP_SALUDO', 'Hola, buenos días. Me interesa solicitar una cotización.')
            total_mensaje = total_con_descuento if afiliado_valido else total_orden
            texto_orden = (
                f"📦 {saludo}\n\n"
                f"🆔 Orden #: {orden.id}\n"
                f"👤 Cliente: {nombre} ({correo})\n"
                f"📞 Teléfono: {telefono if telefono else 'N/A'}\n"
                f"📅 Fecha: {fecha_str}\n\n"
                f"🛒 Productos:\n{productos_str}\n\n"
                f"💵 Subtotal: ${total_orden:.2f}\n"
                + (f"🏷️ Código afiliado: {codigo_descuento} (-{descuento_porcentaje}% )\n" if afiliado_valido else "")
                + f"💰 Total: ${total_mensaje:.2f}\n\n"
                f"📝 Mensaje adicional: {mensaje if mensaje else '-'}\n\n"
                f"✅ ¡Gracias por tu pedido!"
            )

            telefono_ventas = AppConfig.get_valor('WHATSAPP_EMPRESA') or getattr(settings, 'WHATSAPP_EMPRESA', '')
            telefono_ventas = (telefono_ventas or '').strip()

            if not telefono_ventas:
                messages.warning(request, 'Orden creada pero no hay número de WhatsApp configurado para ventas.')
                request.session['orden'] = {}
                request.session.modified = True
                return render(request, 'cotizacion_success.html', {'cotizacion': orden, 'cart_count': 0})

            def _clean_phone(raw):
                cleaned = ''.join(ch for ch in raw if ch.isdigit())
                if cleaned.startswith('0'):
                    cleaned = '58' + cleaned.lstrip('0')
                return cleaned

            ventas_phone = _clean_phone(telefono_ventas)
            whatsapp_url = f"https://wa.me/{ventas_phone}?text={quote(texto_orden)}"

            request.session['orden'] = {}
            request.session.modified = True

            return render(request, 'orden_success.html', {
                'orden': orden,
                'whatsapp_url': whatsapp_url,
                'cart_count': 0,
            })

        except Exception as e:
            print(f"Error procesando orden/WhatsApp: {e}")
            messages.error(request, f'Error al crear la orden: {e}')
            return render(request, 'orden.html', {
                'items': items,
                'subtotal': subtotal,
                'total_con_descuento': total_con_descuento,
                'descuento_porcentaje': descuento_porcentaje,
                'descuento_monto': descuento_monto,
                'codigo_descuento': codigo_descuento,
                'codigo_error': codigo_error,
                'cart_count': _get_cart_count(request),
                'whatsapp_url': get_whatsapp_url(),
                'whatsapp_number': get_whatsapp_empresa(),
            })

    return render(request, 'orden.html', {
        'items': items,
        'subtotal': subtotal,
        'total_con_descuento': total_con_descuento,
        'descuento_porcentaje': descuento_porcentaje,
        'descuento_monto': descuento_monto,
        'codigo_descuento': codigo_descuento,
        'codigo_error': codigo_error,
        'cart_count': _get_cart_count(request),
        'whatsapp_url': get_whatsapp_url(),
        'whatsapp_number': get_whatsapp_empresa(),
    })


def validar_codigo_afiliado(request):
    codigo = (request.GET.get('codigo') or '').strip().upper()
    if not codigo:
        return JsonResponse({'valid': False, 'error': 'Ingresa un código de descuento.'})

    afiliado = Afiliado.objects.filter(codigo__iexact=codigo, activo=True).first()
    if not afiliado:
        return JsonResponse({'valid': False, 'error': 'Código inválido o inactivo.'})

    return JsonResponse({
        'valid': True,
        'codigo': afiliado.codigo,
        'descuento': float(afiliado.descuento),
    })


def guardar_contacto(request):
    if request.method == "POST":
        # 1. Obtener los datos del formulario (sin cambios)
        nombre = request.POST.get('nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        correo = request.POST.get('correo', '').strip()
        motivo_form = request.POST.get('motivo')
        mensaje = request.POST.get('mensaje', '').strip()

        # 2. Traducir el motivo a un texto legible (sin cambios)
        motivos_map = {
            'cotizacion_repuestos': 'Solicitar Cotización de Repuestos',
            'soporte_tecnico': 'Soporte Técnico / Mantenimiento',
            'alquiler_equipos': 'Información sobre Alquiler de Equipos',
            'info_general': 'Consulta General',
            'otro': 'Otro',
        }
        motivo_legible = motivos_map.get(motivo_form, 'No especificado')

        # --- INICIO LÓGICA DE ENVÍO DE CORREO (AJUSTADA) ---
        
        try:
            # 3. Preparar el contexto para la plantilla del correo
            email_context = {
                'nombre': nombre,
                'telefono': telefono,
                'correo': correo,
                'motivo_legible': motivo_legible,
                'mensaje': mensaje,
            }

            # 4. Renderizar SÓLO la plantilla HTML
            html_content = render_to_string('emails/nuevo_contacto.html', email_context)
            # 5. Crear la versión de texto plano automáticamente desde el HTML
            text_content = strip_tags(html_content)

            # 6. Configurar el correo usando EmailMultiAlternatives
            subject = f'Nuevo Contacto desde la Web: {motivo_legible}'
            
            msg = EmailMultiAlternatives(
                subject,                       # Asunto
                text_content,                  # Contenido en texto plano (body)
                settings.EMAIL_HOST_USER,      # De: (tu correo de notificaciones)
                [settings.CORREO_VENTAS]       # Para: (el correo de ventas)
            )
            
            # 7. Adjuntar la versión HTML
            msg.attach_alternative(html_content, "text/html")
            
            # 8. Enviar el correo
            msg.send()

            # --- FIN LÓGICA DE ENVÍO DE CORREO ---
            
            # 9. Mostrar mensaje de éxito al usuario
            messages.success(request, '¡Gracias por contactarnos! Hemos recibido tu mensaje y te responderemos pronto.')
        
        except Exception as e:
            # En caso de error, es útil registrarlo para depuración
            print(f"Error al enviar correo de contacto: {e}")
            messages.error(request, 'Hubo un error al enviar tu mensaje. Por favor, inténtalo de nuevo o contáctanos directamente.')

        # 10. Redirigir de vuelta al formulario en la página de inicio
        return redirect('/#contacto')

    # Si alguien intenta acceder a la URL por método GET, redirigir al inicio
    return redirect('/')
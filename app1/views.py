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
import json
import os
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings

def get_whatsapp_empresa():
    telefono_ventas = AppConfig.get_valor('WHATSAPP_EMPRESA')
    if not telefono_ventas:
        telefono_ventas = getattr(settings, 'WHATSAPP_EMPRESA', '')
    return (telefono_ventas or '').strip()


def get_whatsapp_url():
    telefono_ventas = get_whatsapp_empresa()
    if not telefono_ventas:
        return None
    cleaned = ''.join(ch for ch in telefono_ventas if ch.isdigit())
    if cleaned.startswith('0'):
        cleaned = '58' + cleaned.lstrip('0')
    return f'https://wa.me/{cleaned}'


def _get_cart_count(request):
    cart = request.session.get('orden', {}) or {}
    try:
        total = 0
        for v in cart.values():
            if isinstance(v, dict):
                total += int(v.get('cantidad', 0))
            else:
                total += int(v)
        return total
    except Exception:
        return 0


from django.db.models import Sum, Min


def index(request):
    categoria_id = request.GET.get('categoria')
    categorias = Category.objects.filter(padres__isnull=True)

    productos = Product.objects.filter(
        ordenitem__orden__es_venta=True
    ).annotate(
        total_vendido=Sum('ordenitem__cantidad')
    ).order_by('-total_vendido')[:3]

    if categoria_id:
        try:
            productos = productos.filter(categorias__id=int(categoria_id))
        except (ValueError, TypeError):
            pass

    cart_count = _get_cart_count(request)

    whatsapp_url = get_whatsapp_url()
    whatsapp_number = get_whatsapp_empresa()
    # Limpiar el número para WhatsApp (solo dígitos, sin espacios ni símbolos)
    whatsapp_number_clean = ''.join(ch for ch in whatsapp_number if ch.isdigit()) if whatsapp_number else ''

    return render(request, 'index.html', {
        'categorias': categorias,
        'productos': productos,
        'categoria_id': categoria_id,
        'cart_count': cart_count,
        'whatsapp_url': whatsapp_url,
        'whatsapp_number': whatsapp_number,
        'whatsapp_number_clean': whatsapp_number_clean,
    })


def cotizador(request):
    cart_count = _get_cart_count(request)
    whatsapp_url = get_whatsapp_url()
    whatsapp_number = get_whatsapp_empresa()
    whatsapp_number_clean = ''.join(ch for ch in whatsapp_number if ch.isdigit()) if whatsapp_number else ''
    return render(request, 'cotizador.html', {
        'cart_count': cart_count,
        'whatsapp_url': whatsapp_url,
        'whatsapp_number': whatsapp_number,
        'whatsapp_number_clean': whatsapp_number_clean,
    })


def tienda(request):
    categorias = Category.objects.prefetch_related('subcategorias').filter(padres__isnull=True)
    productos = Product.objects.prefetch_related('categorias').all()

    q = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    subcategoria_id = request.GET.get('subcategoria', '').strip()
    agotado_filter = request.GET.get('agotado', '').strip()

    if q:
        from django.db.models import Q
        productos = productos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))

    categoria_seleccionada = None
    if categoria_id:
        try:
            cid = int(categoria_id)
            categoria_seleccionada = Category.objects.prefetch_related('subcategorias').get(id=cid)
            if subcategoria_id:
                scid = int(subcategoria_id)
                # Verificar que la subcategoría es hija de la principal seleccionada
                subcat = categoria_seleccionada.subcategorias.filter(id=scid).first()
                if subcat:
                    # Solo productos que tengan la categoría principal y la subcategoría seleccionada
                    productos = productos.filter(categorias__id=cid).filter(categorias__id=scid)
                else:
                    productos = productos.none()  # No mostrar productos si la subcategoría no es hija de la principal
            else:
                # Solo productos que tengan la categoría principal seleccionada
                productos = productos.filter(categorias__id=cid)
        except (ValueError, TypeError, Category.DoesNotExist):
            pass

    if agotado_filter == '1':
        productos = productos.filter(agotado=True)
    elif agotado_filter == '0':
        productos = productos.filter(agotado=False)

    productos = productos.distinct().order_by('-creado').annotate(
        precio_minimo=Min('precios_por_peso__precio')
    )

    cart_count = _get_cart_count(request)
    whatsapp_url = get_whatsapp_url()
    whatsapp_number = get_whatsapp_empresa()

    return render(request, 'tienda.html', {
        'categorias': categorias,
        'productos': productos,
        'q': q,
        'categoria_id': categoria_id,
        'subcategoria_id': subcategoria_id,
        'categoria_seleccionada': categoria_seleccionada,
        'agotado_filter': agotado_filter,
        'cart_count': cart_count,
        'whatsapp_url': whatsapp_url,
        'whatsapp_number': whatsapp_number,
    })


def productos(request, producto_id):
    producto = get_object_or_404(Product, id=producto_id)
    imagenes = list(producto.imagenes.order_by('orden'))
    if not imagenes and producto.imagen:
        imagenes = [producto.imagen]

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


# ─── ORDEN ADD ────────────────────────────────────────────────────────────────
# Estructura del carrito en sesión:
#   Sin multiprecio → cart["42"] = 3            (entero = cantidad)
#   Con multiprecio → cart["42"] = {            (dict con detalle)
#       "cantidad": 2,
#       "precio": "765.00",
#       "peso": "1.80",
#       "precio_peso_id": "3",
#   }
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

    precio_seleccionado = request.POST.get('precio_seleccionado', '').strip()
    peso_seleccionado   = request.POST.get('peso_seleccionado', '').strip()
    precio_peso_id      = request.POST.get('precio_peso_id', '').strip()

    cart = dict(request.session.get('orden', {}) or {})
    key  = str(prod_id)

    if precio_seleccionado:
        # Producto con multiprecio
        existing = cart.get(key)
        if isinstance(existing, dict) and existing.get('precio_peso_id') == precio_peso_id:
            # Mismo peso seleccionado → acumular cantidad
            existing['cantidad'] = existing['cantidad'] + qty
            cart[key] = existing
        else:
            # Variante nueva o diferente → reemplazar
            cart[key] = {
                'cantidad':       qty,
                'precio':         precio_seleccionado,
                'peso':           peso_seleccionado,
                'precio_peso_id': precio_peso_id,
            }
    else:
        # Producto sin multiprecio → entero simple
        current = cart.get(key, 0)
        if isinstance(current, dict):
            current = current.get('cantidad', 0)
        cart[key] = int(current) + qty

    request.session['orden'] = cart
    request.session.modified = True
    messages.success(request, 'Producto agregado a la orden')
    return redirect(request.META.get('HTTP_REFERER', reverse('tienda')))


# ─── ORDEN (carrito + checkout) ───────────────────────────────────────────────
def orden(request):
    cart = request.session.get('orden', {}) or {}
    product_ids = [int(k) for k in cart.keys() if k.isdigit()]
    productos_qs = Product.objects.filter(id__in=product_ids)
    prod_map = {p.id: p for p in productos_qs}

    items    = []
    subtotal = Decimal('0.00')

    for pid_str, entry in cart.items():
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        prod = prod_map.get(pid)
        if not prod:
            continue

        if isinstance(entry, dict):
            cantidad = int(entry.get('cantidad', 1))
            try:
                precio_unit = Decimal(str(entry['precio']))
            except Exception:
                precio_unit = prod.precio
            peso       = entry.get('peso', '')
            item_total = precio_unit * cantidad
            items.append({
                'product':    prod,
                'cantidad':   cantidad,
                'precio_unit': precio_unit,
                'peso':        peso,
                'total':       item_total,
                'es_por_peso': True,
                'precio':      str(precio_unit),  # Para el payload a crud
            })
        else:
            cantidad    = int(entry)
            precio_unit = prod.precio
            item_total  = precio_unit * cantidad
            items.append({
                'product':    prod,
                'cantidad':   cantidad,
                'precio_unit': precio_unit,
                'peso':        '',
                'total':       item_total,
                'es_por_peso': False,
                'precio':      str(precio_unit),
            })

        subtotal += item_total

    codigo_descuento     = request.session.get('codigo_descuento', '') or ''
    afiliado_valido      = None
    descuento_porcentaje = Decimal('0.00')
    descuento_monto      = Decimal('0.00')
    total_con_descuento  = subtotal
    codigo_error         = ''

    if codigo_descuento:
        afiliado_valido = Afiliado.objects.filter(codigo__iexact=codigo_descuento, activo=True).first()
        if afiliado_valido:
            descuento_porcentaje = Decimal(str(afiliado_valido.descuento))
            descuento_monto      = (subtotal * descuento_porcentaje / Decimal('100')).quantize(Decimal('0.01'))
            total_con_descuento  = (subtotal - descuento_monto).quantize(Decimal('0.01'))
        else:
            codigo_error        = 'Código de descuento inválido o inactivo.'
            total_con_descuento = subtotal

    if request.method == 'POST':
        nombre           = request.POST.get('nombre', '').strip()
        correo           = request.POST.get('correo', '').strip()
        telefono         = request.POST.get('telefono', '').strip()
        mensaje          = request.POST.get('mensaje', '').strip()
        codigo_descuento = request.POST.get('codigo_descuento', '').strip().upper()
        request.session['codigo_descuento'] = codigo_descuento
        request.session.modified = True

        afiliado_valido      = None
        descuento_porcentaje = Decimal('0.00')
        descuento_monto      = Decimal('0.00')
        total_con_descuento  = subtotal
        codigo_error         = ''

        if codigo_descuento:
            afiliado_valido = Afiliado.objects.filter(codigo__iexact=codigo_descuento, activo=True).first()
            if afiliado_valido:
                descuento_porcentaje = Decimal(str(afiliado_valido.descuento))
                descuento_monto      = (subtotal * descuento_porcentaje / Decimal('100')).quantize(Decimal('0.01'))
                total_con_descuento  = (subtotal - descuento_monto).quantize(Decimal('0.01'))
            else:
                codigo_error = 'Código de descuento inválido o inactivo.'

        ctx_error = {
            'items': items, 'subtotal': subtotal,
            'total_con_descuento': total_con_descuento,
            'descuento_porcentaje': descuento_porcentaje,
            'descuento_monto': descuento_monto,
            'codigo_descuento': codigo_descuento,
            'codigo_error': codigo_error,
            'cart_count': _get_cart_count(request),
            'whatsapp_url': get_whatsapp_url(),
            'whatsapp_number': get_whatsapp_empresa(),
            'SHOW_PRICES_CLIENTES': True,
        }

        if not nombre or not correo:
            messages.error(request, 'Nombre y correo son obligatorios para enviar la orden.')
            return render(request, 'orden.html', ctx_error)

        if codigo_descuento and not afiliado_valido:
            messages.error(request, codigo_error)
            return render(request, 'orden.html', ctx_error)

        try:
            cliente = crud.crear_cliente(nombre, correo, telefono)
            items_payload = [
                {
                    'product_id': it['product'].id,
                    'cantidad': it['cantidad'],
                    'precio': it['precio'],
                }
                for it in items
            ]
            orden_obj = crud.crear_orden_desde_carrito(
                cliente,
                items_payload,
                mensaje=mensaje,
                codigo_afiliado=codigo_descuento,
                descuento_afiliado=descuento_porcentaje,
            )

            # ── Construir mensaje WhatsApp con precio real por peso ──
            detalle_lines = []
            for it in items:
                p   = it['product']
                c   = it['cantidad']
                pu  = float(it['precio_unit'])
                tot = float(it['total'])
                if it['es_por_peso']:
                    detalle_lines.append(
                        f"{p.nombre} — {it['peso']}g x{c} (${pu:.2f} c/u) = ${tot:.2f}"
                    )
                else:
                    detalle_lines.append(
                        f"{p.nombre} x{c} (${pu:.2f} c/u) = ${tot:.2f}"
                    )

            productos_str  = "\n".join(detalle_lines)
            total_whatsapp = float(total_con_descuento if afiliado_valido else subtotal)

            fecha_actual = timezone.now()
            if timezone.is_naive(fecha_actual):
                fecha_actual = timezone.make_aware(fecha_actual)
            fecha_str = timezone.localtime(fecha_actual).strftime('%d/%m/%Y %H:%M')

            saludo = AppConfig.get_valor('WHATSAPP_SALUDO', 'Hola, buenos días. Me interesa solicitar una cotización.')
            texto_orden = (
                f"📦 {saludo}\n\n"
                f"🆔 Orden #: {orden_obj.id}\n"
                f"👤 Cliente: {nombre} ({correo})\n"
                f"📞 Teléfono: {telefono if telefono else 'N/A'}\n"
                f"📅 Fecha: {fecha_str}\n\n"
                f"🛒 Productos:\n{productos_str}\n\n"
                f"💵 Subtotal: ${float(subtotal):.2f}\n"
                + (f"🏷️ Código afiliado: {codigo_descuento} (-{descuento_porcentaje}%)\n" if afiliado_valido else "")
                + f"💰 Total: ${total_whatsapp:.2f}\n\n"
                f"📝 Mensaje adicional: {mensaje if mensaje else '-'}\n\n"
                f"✅ ¡Gracias por tu pedido!"
            )

            telefono_ventas = AppConfig.get_valor('WHATSAPP_EMPRESA') or getattr(settings, 'WHATSAPP_EMPRESA', '')
            telefono_ventas = (telefono_ventas or '').strip()

            if not telefono_ventas:
                messages.warning(request, 'Orden creada pero no hay número de WhatsApp configurado para ventas.')
                request.session['orden'] = {}
                request.session.modified = True
                return render(request, 'cotizacion_success.html', {'cotizacion': orden_obj, 'cart_count': 0})

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
                'orden': orden_obj,
                'whatsapp_url': whatsapp_url,
                'cart_count': 0,
            })

        except Exception as e:
            print(f"Error procesando orden/WhatsApp: {e}")
            messages.error(request, f'Error al crear la orden: {e}')
            return render(request, 'orden.html', ctx_error)

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
        'SHOW_PRICES_CLIENTES': True,
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
        nombre      = request.POST.get('nombre', '').strip()
        telefono    = request.POST.get('telefono', '').strip()
        correo      = request.POST.get('correo', '').strip()
        motivo_form = request.POST.get('motivo')
        mensaje     = request.POST.get('mensaje', '').strip()

        motivos_map = {
            'cotizacion_repuestos': 'Solicitar Cotización de Repuestos',
            'soporte_tecnico':      'Soporte Técnico / Mantenimiento',
            'alquiler_equipos':     'Información sobre Alquiler de Equipos',
            'info_general':         'Consulta General',
            'otro':                 'Otro',
        }
        motivo_legible = motivos_map.get(motivo_form, 'No especificado')

        try:
            email_context = {
                'nombre': nombre, 'telefono': telefono,
                'correo': correo, 'motivo_legible': motivo_legible,
                'mensaje': mensaje,
            }
            html_content = render_to_string('emails/nuevo_contacto.html', email_context)
            text_content = strip_tags(html_content)

            subject = f'Nuevo Contacto desde la Web: {motivo_legible}'
            msg = EmailMultiAlternatives(
                subject, text_content,
                settings.EMAIL_HOST_USER, [settings.CORREO_VENTAS]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            messages.success(request, '¡Gracias por contactarnos! Hemos recibido tu mensaje y te responderemos pronto.')

        except Exception as e:
            print(f"Error al enviar correo de contacto: {e}")
            messages.error(request, 'Hubo un error al enviar tu mensaje. Por favor, inténtalo de nuevo o contáctanos directamente.')

        return redirect('/#contacto')

    return redirect('/')




# Cache del JSON en memoria para no leerlo en cada request
_RINGS_CACHE = None

def _load_rings(force_reload=False):
    global _RINGS_CACHE
    if _RINGS_CACHE is None or force_reload:
        json_path = os.path.join(settings.BASE_DIR, 'app1', 'data', 'nivoda_rings_v5.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _RINGS_CACHE = data['rings']
    return _RINGS_CACHE


# Mapeo de valores del frontend → valores del JSON scrapeado
SHAPE_MAP = {
    'round':     'ROUND',
    'oval':      'OVAL',
    'cushion':   'CUSHION',
    'princess':  'PRINCESS',
    'pear':      'PEAR',
    'emerald':   'EMERALD',
    'marquise':  'MARQUISE',
    'radiant':   'RADIANT',
}

STONE_MAP = {
    'lab':     'LABGROWN_DIAMOND',
    'natural': 'NATURAL_DIAMOND',
}

HEAD_MAP = {
    '4prong':    'FOUR_PRONGS',
    'basket':    'BASKET',
    'bezel':     'PEG_HEAD',
    'pave':      'PAVE',
    'halo':      'SINGLE_HALO',
    'doublehalo':'DOUBLE_HALO',
    'crown':     'CROWN',
    'flowerhalo':'FLOWER_HALO',
}

MOUNTING_MAP = {
    'single':  'SINGLE',
    'double':  'DOUBLE',
    'twisted': 'DOUBLE_TWIST',
    'knife':   'KNIFE_EDGE',
    'flat':    'SQUARE_EDGE',
    'tapered': 'TAPERED',
    'modern':  'CONTEMPORARY',
    'hidden':  'HIDDEN_HALO',
    'split':   'SPLIT',
}

SIDE_MAP = {
    'none':    'NONE',
    'upave':   'U_PAVE',
    'channel': 'CHANNEL',
    'prong':   'PRONG',
    'grain':   'BEAD',
    'pave':    'PAVE',
}

CARVING_MAP = {
    'smooth': 'PLAIN',
    'leaf':   'LEAF',
    'scroll': 'SCROLL',
}

QUALITY_MAP = {
    'kt10': 'KT_10',
    'kt14': 'KT_14',
    'kt18': 'KT_18',
}

PEEKABOO_MAP = {
    'none':     'NONE',
    'round':    'ROUND_DIAMOND',
    'princess': 'PRINCESS_DIAMOND',
}

HEADCOLOR_MAP = {
    'yellow': 'YELLOW_GOLD',
    'white':  'WHITE_GOLD',
    'rose':   'ROSE_GOLD',
}

MOUNTCOLOR_MAP = {
    'yellow': 'YELLOW_GOLD',
    'white':  'WHITE_GOLD',
    'rose':   'ROSE_GOLD',
}

@require_GET
def ring_config_api(request):
    """
    Endpoint que recibe la configuración del quoter y retorna
    el anillo correspondiente del JSON con sus imágenes y precio.
    Si la combinación no existe físicamente en el catálogo, retorna 404.
    """
    shape    = request.GET.get('shape', 'round')
    head     = request.GET.get('head', '4prong')
    band     = request.GET.get('band', 'single')
    side     = request.GET.get('side', 'none')
    peekaboo   = request.GET.get('peekaboo', 'none')
    metalcolor = request.GET.get('metalcolor', 'yellow')

    target_shape = SHAPE_MAP.get(shape, 'ROUND')
    target_head  = HEAD_MAP.get(head, 'FOUR_PRONGS')
    target_band  = MOUNTING_MAP.get(band, 'SINGLE')
    target_side  = SIDE_MAP.get(side, 'NONE')
    target_peek  = PEEKABOO_MAP.get(peekaboo, 'NONE')
    target_color = HEADCOLOR_MAP.get(metalcolor, 'YELLOW_GOLD')

    rings = _load_rings()

    # Buscar candidatos que coincidan en los 5 atributos visibles y el color
    candidates = [
        r for r in rings
        if (
            r['combination'].get('stone_shape') == target_shape and
            r['combination'].get('ring_head')   == target_head and
            r['combination'].get('mounting')    == target_band and
            r['combination'].get('side_setting')== target_side and
            r['combination'].get('peekaboo')    == target_peek and
            r['combination'].get('mounting_color', 'YELLOW_GOLD') == target_color
        )
    ]

    if not candidates:
        # Fallback de robustez: Si el color solicitado (ej. Oro Blanco) aún no ha sido
        # scrapeado para esta combinación, buscar ignorando el color para al menos
        # devolver la imagen y precio en otro metal (ej. Oro Amarillo) y que no se rompa la web.
        candidates = [
            r for r in rings
            if (
                r['combination'].get('stone_shape') == target_shape and
                r['combination'].get('ring_head')   == target_head and
                r['combination'].get('mounting')    == target_band and
                r['combination'].get('side_setting')== target_side and
                r['combination'].get('peekaboo')    == target_peek
            )
        ]

    if not candidates:
        return JsonResponse({'error': 'Combinación no disponible'}, status=404)

    # Seleccionar la mejor opción visual (priorizando tallado liso y color de cabeza)
    best_ring = None

    # 1. Priorizar que la cabeza sea del mismo color que la montura
    for r in candidates:
        c = r['combination']
        if (target_side != 'NONE' or c.get('ring_carving') == 'PLAIN') and c.get('head_color') == target_color:
            best_ring = r
            break

    # 2. Si no hay cabeza del mismo color, priorizar Oro Blanco (estándar para diamantes)
    if not best_ring:
        for r in candidates:
            c = r['combination']
            if (target_side != 'NONE' or c.get('ring_carving') == 'PLAIN') and c.get('head_color') == 'WHITE_GOLD':
                best_ring = r
                break

    # 3. Si tampoco hay, aceptar cualquiera con tallado liso
    if not best_ring:
        for r in candidates:
            c = r['combination']
            if target_side != 'NONE' or c.get('ring_carving') == 'PLAIN':
                best_ring = r
                break

    if not best_ring:
        best_ring = candidates[0]

    price_raw = best_ring.get('price_mount', '')
    try:
        price_num = float(price_raw.replace('$', '').replace(',', ''))
    except (ValueError, AttributeError):
        price_num = 0.0

    return JsonResponse({
        'sku':         best_ring['sku'],
        'title':       best_ring.get('title', ''),
        'images':      best_ring.get('images', []),
        'price_mount': price_raw,
        'price_num':   price_num,
        'combination': best_ring.get('combination', {}),
        'exact_match': True,
        'url':         best_ring.get('url', ''),
    })


@require_GET
def ring_options_api(request):
    """
    Dado el estado actual, devuelve qué valores son válidos para cada dimensión.
    Usado para deshabilitar botones que generarían 404 (Combinación no disponible).
    """
    shape    = request.GET.get('shape', 'round')
    head     = request.GET.get('head', '')
    band     = request.GET.get('band', '')
    side     = request.GET.get('side', '')
    peekaboo = request.GET.get('peekaboo', '')

    shape_val = SHAPE_MAP.get(shape, 'ROUND')
    rings     = _load_rings()

    pool = [r for r in rings if r['combination'].get('stone_shape') == shape_val]

    def valid_values(pool, field):
        return set(r['combination'].get(field) for r in pool if r['combination'].get(field) is not None)

    def pool_with(filters):
        result = pool
        for field, val in filters.items():
            if val:
                result = [r for r in result if r['combination'].get(field) == val]
        return result

    head_val     = HEAD_MAP.get(head, '')     if head     else ''
    band_val     = MOUNTING_MAP.get(band, '') if band     else ''
    side_val     = SIDE_MAP.get(side, '')     if side     else ''

    valid_heads = valid_values(pool, 'ring_head')

    p_head = pool_with({'ring_head': head_val}) if head_val else pool
    valid_mountings = valid_values(p_head, 'mounting')

    p_mount = pool_with({'ring_head': head_val, 'mounting': band_val}) if band_val else p_head
    valid_sides = valid_values(p_mount, 'side_setting')

    p_side = pool_with({'ring_head': head_val, 'mounting': band_val, 'side_setting': side_val}) if side_val else p_mount
    valid_peekaboos = valid_values(p_side, 'peekaboo')

    HEAD_REV     = {v: k for k, v in HEAD_MAP.items()}
    MOUNT_REV    = {v: k for k, v in MOUNTING_MAP.items()}
    SIDE_REV     = {v: k for k, v in SIDE_MAP.items()}
    PEEKABOO_REV = {v: k for k, v in PEEKABOO_MAP.items()}

    return JsonResponse({
        'valid_heads':     [HEAD_REV[v]     for v in valid_heads     if v in HEAD_REV],
        'valid_mountings': [MOUNT_REV[v]    for v in valid_mountings if v in MOUNT_REV],
        'valid_sides':     [SIDE_REV[v]     for v in valid_sides     if v in SIDE_REV],
        'valid_peekaboos': [PEEKABOO_REV[v] for v in valid_peekaboos if v in PEEKABOO_REV],
    })
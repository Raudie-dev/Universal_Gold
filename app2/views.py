import datetime

from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from urllib.parse import quote
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q, Count, Sum, Max, Avg, F
from datetime import timedelta
from django.utils import timezone
from .models import User_admin
from .crud import (
    crear_categoria,
    obtener_categorias,
    crear_producto,
    obtener_productos,
    eliminar_producto,
    eliminar_categoria,
    actualizar_producto,
    obtener_usuarios_admin, 
    crear_usuario_admin, 
    actualizar_usuario_admin, 
    eliminar_usuario_admin
)
from app1.models import Product, Orden, OrdenItem, Cliente, Category, ProductImage


def login(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        password = request.POST.get('password', '')

        try:
            user = User_admin.objects.get(nombre=nombre)
            if user.bloqueado:
                messages.error(request, 'Usuario bloqueado')
            elif user.password == password or check_password(password, user.password):
                request.session['user_admin_id'] = user.id
                return redirect('registro')
            else:
                messages.error(request, 'Contraseña incorrecta')
            return render(request, 'login.html')
        except User_admin.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
            return render(request, 'login.html')

    return render(request, 'login.html')


def registro(request):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return render(request, 'login.html')
    
    try:
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return render(request, 'login.html')

    # --- PROCESAMIENTO DE FORMULARIOS (POST) ---
    if request.method == 'POST':
        
        # 1. CREAR CATEGORÍA (Con soporte jerárquico)
        if 'crear_categoria' in request.POST:
            nombre_cat = request.POST.get('categoria_nombre', '').strip()
            
            # Capturamos el ID del padre del select
            padre_id = request.POST.get('categoria_padre')
            
            # Si el valor es vacío o string vacía, lo forzamos a None (Raíz)
            if not padre_id:
                padre_id = None
            
            if nombre_cat:
                try:
                    # Llamamos a la función corregida enviando el padre_id
                    crear_categoria(nombre_cat, padre_id)
                    messages.success(request, 'Categoría creada correctamente')
                except Exception as e:
                    messages.error(request, f'Error al crear la categoría: {e}')
            else:
                messages.error(request, 'El nombre de la categoría es obligatorio')
        
        if 'editar_categoria' in request.POST:
            cat_id = request.POST.get('editar_categoria_id')
            nuevo_nombre = request.POST.get('categoria_nombre', '').strip()
            nuevo_padre_id = request.POST.get('categoria_padre')

            if cat_id and nuevo_nombre:
                try:
                    categoria = Category.objects.get(id=cat_id)
                    
                    # Validación básica para evitar ciclos (una cat no puede ser padre de sí misma)
                    if nuevo_padre_id and int(nuevo_padre_id) == int(cat_id):
                        messages.error(request, 'Una categoría no puede ser su propio padre.')
                    else:
                        categoria.nombre = nuevo_nombre
                        
                        # Actualizar padre
                        if nuevo_padre_id:
                            categoria.padre_id = int(nuevo_padre_id)
                        else:
                            categoria.padre = None # Se vuelve categoría principal
                        
                        categoria.save()
                        messages.success(request, 'Categoría actualizada correctamente.')
                        
                except Category.DoesNotExist:
                    messages.error(request, 'La categoría no existe.')
                except Exception as e:
                    messages.error(request, f'Error al actualizar: {e}')
            else:
                messages.error(request, 'Datos incompletos para editar.')        

        # 2. CREAR PRODUCTO
        elif 'crear_producto' in request.POST:
            nombre = request.POST.get('nombre', '').strip()
            precio = request.POST.get('precio', '0')
            descripcion = request.POST.get('descripcion', '')
            
            # getlist obtiene todos los IDs seleccionados (Ctrl + Click)
            categoria_ids = request.POST.getlist('categoria_ids') or None
            
            imagenes = request.FILES.getlist('imagenes')
            
            if nombre:
                try:
                    crear_producto(nombre, precio, descripcion, categoria_ids, None, imagenes)
                    messages.success(request, 'Producto creado correctamente')
                except Exception as e:
                    messages.error(request, f'Error al crear el producto: {e}')
            else:
                messages.error(request, 'El nombre del producto es obligatorio')

        # 3. ELIMINAR PRODUCTO
        elif 'eliminar_producto' in request.POST:
            pid = request.POST.get('eliminar_producto')
            if pid:
                eliminar_producto(pid)
                messages.success(request, 'Producto eliminado')

        # 4. ELIMINAR CATEGORÍA
        elif 'eliminar_categoria' in request.POST:
            cid = request.POST.get('eliminar_categoria')
            if cid:
                eliminar_categoria(cid)
                messages.success(request, 'Categoría eliminada')

        # Patrón PRG (Post-Redirect-Get) para evitar reenvíos al refrescar
        return redirect(reverse('registro'))

    # --- MÉTODO GET (Renderizar página) ---
    
    # Asegúrate que 'obtener_categorias()' devuelva el queryset correctamente.
    # Si quieres optimizar la carga del árbol jerárquico (N+1 problem):
    # categorias = Category.objects.prefetch_related('subcategorias__subcategorias').all()
    categorias = obtener_categorias()
    productos = obtener_productos()
    
    return render(request, 'registro.html', {
        'productos': productos,
        'categorias': categorias,
    })

def control_productos(request):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    try:
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    if request.method == 'POST':
        
        # --- BLOQUE DE EDICIÓN CORREGIDO ---
        if 'editar_producto' in request.POST:
            producto_id = request.POST.get('editar_producto_id')
            
            try:
                # 1. Obtener el producto existente
                producto = Product.objects.get(id=producto_id)

                # 2. Asignar los nuevos valores desde el formulario
                producto.nombre = request.POST.get('nombre', '').strip()
                producto.descripcion = request.POST.get('descripcion', '')
                
                # 3. Convertir el precio a número
                try:
                    producto.precio = float(request.POST.get('precio', '0'))
                except (ValueError, TypeError):
                    messages.error(request, 'El precio ingresado no es un número válido.')
                    return redirect(reverse('control_productos'))

                # 4. Manejar el checkbox 'agotado'
                producto.agotado = 'agotado' in request.POST

                # 5. Manejar la imagen principal (solo si se sube una nueva)
                if 'imagen' in request.FILES:
                    producto.imagen = request.FILES['imagen']

                # 6. Guardar el objeto principal
                producto.save()

                # 7. actualizar categorías (ManyToMany)
                categoria_ids = request.POST.getlist('categoria_ids')
                producto.categorias.set(categoria_ids)

                # 8. Manejar imágenes
                eliminar_ids = request.POST.getlist('eliminar_imagenes')
                
                # Get existing images not deleted
                existing_images = producto.imagenes.exclude(id__in=eliminar_ids)
                
                # Update orden for existing images
                for img in existing_images:
                    orden_key = f'orden_{img.id}'
                    orden = request.POST.get(orden_key, '999')
                    try:
                        img.orden = int(orden)
                        img.save()
                    except ValueError:
                        pass
                
                # Set is_portada for the first in order (lowest orden)
                if existing_images.exists():
                    first_img = min(existing_images, key=lambda x: x.orden)
                    existing_images.update(is_portada=False)
                    first_img.is_portada = True
                    first_img.save()
                
                # Add new images
                imagenes_files = request.FILES.getlist('imagenes')
                if imagenes_files:
                    max_orden = existing_images.aggregate(models.Max('orden'))['orden__max'] or -1
                    for i, img_file in enumerate(imagenes_files):
                        orden = max_orden + 1 + i
                        is_portada = (orden == 0 and not existing_images.exists())
                        ProductImage.objects.create(product=producto, imagen=img_file, orden=orden, is_portada=is_portada, creado=timezone.now())
                
                # Delete marked images
                if eliminar_ids:
                    ProductImage.objects.filter(product=producto, id__in=eliminar_ids).delete()

                messages.success(request, f'Producto "{producto.nombre}" actualizado correctamente.')

            except Product.DoesNotExist:
                messages.error(request, 'El producto que intentas editar no existe.')
            except Exception as e:
                messages.error(request, f'Ocurrió un error inesperado al actualizar: {e}')

        # Toggle agotado (Tu código aquí ya es correcto)
        elif 'toggle_agotado' in request.POST:
            pid = request.POST.get('toggle_agotado')
            producto = get_object_or_404(Product, id=pid)
            producto.agotado = not producto.agotado
            producto.save()
            messages.success(request, f'Estado de "{producto.nombre}" actualizado.')

        # Delete product
        elif 'eliminar_producto' in request.POST:
            pid = request.POST.get('eliminar_producto')
            try:
                producto = Product.objects.get(id=pid)
                nombre_producto = producto.nombre

                # Eliminar imagen si existe
                if producto.imagen:
                    producto.imagen.delete(save=False)

                # Eliminar el producto
                producto.delete()
                messages.success(request, f'Producto "{nombre_producto}" eliminado.')
            except Product.DoesNotExist:
                 messages.error(request, 'Producto no encontrado.')

        # Siempre redirigir después de un POST exitoso
        return redirect(reverse('control_productos'))

    # --- Lógica GET para mostrar la página y filtros ---
    # Tu código para el método GET es correcto y no necesita cambios.
    categorias = obtener_categorias() # Asumo que esta función existe
    productos = obtener_productos() # Asumo que esta función existe

    q = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    agotado_filter = request.GET.get('agotado', '').strip()

    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
    if categoria_id:
        productos = productos.filter(categorias__id=categoria_id)
    if agotado_filter == '1':
        productos = productos.filter(agotado=True)
    elif agotado_filter == '0':
        productos = productos.filter(agotado=False)

    productos = productos.distinct().order_by('-creado')

    return render(request, 'control_productos.html', {
        'productos': productos,
        'categorias': categorias,
        'q': q,
        'categoria_id': categoria_id,
        'agotado_filter': agotado_filter,
    })
    
# Nueva vista: listar solicitudes de cotización
def solicitudes_ordenes(request):
    # --- 1. Autenticación (Código original) ---
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    try:
        User_admin.objects.get(id=user_id)
    except Exception:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    # --- 2. QuerySet Base ---
    # Obtenemos la consulta base optimizada
    ordenes_qs = Orden.objects.select_related('cliente').prefetch_related('items__producto').all().order_by('-creado')

    # --- 3. Lógica de Filtros ---
    
    # A) Filtro de Texto (Buscador)
    query = (request.GET.get('q') or '').strip()
    if query:
        q_filters = (
            Q(cliente__nombre__icontains=query) |
            Q(cliente__correo__icontains=query) |
            Q(cliente__telefono__icontains=query)
        )

        if query.isdigit():
            q_filters = q_filters | Q(id=int(query))
        else:
            # también permite buscar texto parcial en estado
            q_filters = q_filters | Q(estado__icontains=query)

        ordenes_qs = ordenes_qs.filter(q_filters)

    # B) Filtro de Estado
    estado = request.GET.get('estado')
    if estado:
        # Usamos iexact para ignorar mayúsculas/minúsculas (ej: 'Pendiente' == 'pendiente')
        ordenes_qs = ordenes_qs.filter(estado__iexact=estado)

    # --- 4. Procesamiento de Datos (Usando el total guardado) ---
    solicitudes = []
    
    # Iteramos solo sobre las ordenes que pasaron los filtros
    for c in ordenes_qs:
        solicitudes.append({
            'orden': c,
            'items': list(c.items.all()),
            'subtotal': float(c.total),
        })

    # --- 5. Renderizado ---
    context = {
        'solicitudes': solicitudes,
        'SHOW_PRICES': True, # Variable para controlar si se ven columnas de precios en el HTML
    }

    return render(request, 'solicitudes_cotizacion.html', context)


def clientes_registrados(request):
    # 1. Autenticación de administrador
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    try:
        User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    q = request.GET.get('q', '').strip()
    clientes = Cliente.objects.all().order_by('-creado')
    if q:
        clientes = clientes.filter(
            Q(nombre__icontains=q) | Q(correo__icontains=q) | Q(telefono__icontains=q)
        )

    return render(request, 'clientes.html', {
        'clientes': clientes,
        'q': q,
    })


def procesar_orden(request, orden_id):
    # 1. Verificar autenticación
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    # 2. Verificar que el usuario existe
    try:
        User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    # 3. Obtener la orden
    orden = get_object_or_404(Orden, id=orden_id)

    # 4. Actualizar estado a 'procesado' si está pendiente
    if orden.estado.lower() in ['pendiente', 'nuevo', 'en revisión']:
        orden.estado = 'procesado'
        orden.save()
        messages.success(request, f"Orden #{orden.id} marcada como PROCESADA.")
    else:
        messages.info(request, f"Orden #{orden.id} ya tiene estado '{orden.estado}'.")

    # 5. Retornar al listado de solicitudes (historial)
    return redirect('solicitudes_ordenes')


def marcar_orden_venta(request, orden_id):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    try:
        User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    orden = get_object_or_404(Orden, id=orden_id)
    orden.es_venta = True
    orden.estado = 'venta_confirmada'
    orden.fecha_venta = timezone.now()
    orden.save()

    messages.success(request, f"Orden #{orden.id} marcada como VENTA confirmada.")
    return redirect('solicitudes_ordenes')


def marcar_orden_no_venta(request, orden_id):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    try:
        User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    orden = get_object_or_404(Orden, id=orden_id)
    orden.es_venta = False
    orden.estado = 'no_vendido'
    orden.save()

    messages.success(request, f"Orden #{orden.id} marcada como NO venta.")
    return redirect('solicitudes_ordenes')


def configuracion_whatsapp(request):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    try:
        User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    from .crud import obtener_config, guardar_config
    whatsapp_empresa = obtener_config('WHATSAPP_EMPRESA', '')
    default_saludo = "Hola, buenos días. Me interesa solicitar una cotización."
    whatsapp_saludo = obtener_config('WHATSAPP_SALUDO', default_saludo)

    if request.method == 'POST':
        # Formulario del número de WhatsApp
        if 'guardar_numero' in request.POST:
            nuevo_numero = request.POST.get('whatsapp_empresa', '').strip()
            if not nuevo_numero:
                messages.error(request, 'El número de WhatsApp es obligatorio.')
            else:
                guardar_config('WHATSAPP_EMPRESA', nuevo_numero)
                messages.success(request, 'Número de WhatsApp actualizado.')
                whatsapp_empresa = nuevo_numero

        # Formulario del saludo de WhatsApp (único editable)
        elif 'guardar_saludo' in request.POST:
            nuevo_saludo = request.POST.get('whatsapp_saludo', '').strip()
            if nuevo_saludo:
                guardar_config('WHATSAPP_SALUDO', nuevo_saludo)
                messages.success(request, 'Saludo de WhatsApp actualizado.')
                whatsapp_saludo = nuevo_saludo
            else:
                guardar_config('WHATSAPP_SALUDO', default_saludo)
                messages.success(request, 'Saludo de WhatsApp restablecido al valor por defecto.')
                whatsapp_saludo = default_saludo

    return render(request, 'configuracion_whatsapp.html', {
        'whatsapp_empresa': whatsapp_empresa,
        'whatsapp_saludo': whatsapp_saludo,
    })


def gestion_usuarios(request):
    # 1. Verificación de Seguridad: Solo usuarios logueados
    user_id_sesion = request.session.get('user_admin_id')
    if not user_id_sesion:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    # 2. Procesamiento de Acciones (POST)
    if request.method == 'POST':
        
        # --- A. CREAR USUARIO ---
        if 'crear_usuario' in request.POST:
            nombre = request.POST.get('nombre', '').strip()
            password = request.POST.get('password', '')
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()

            try:
                crear_usuario_admin(nombre, password, email, telefono)
                messages.success(request, f'Administrador "{nombre}" creado con éxito.')
            except ValueError as e:
                # Captura errores de validación (nombre duplicado, email duplicado, etc.)
                messages.error(request, str(e))
            except Exception as e:
                # Captura cualquier otro error inesperado
                messages.error(request, f"Error inesperado al crear: {e}")

        # --- B. EDITAR USUARIO ---
        elif 'editar_usuario' in request.POST:
            uid = request.POST.get('usuario_id')
            nombre = request.POST.get('nombre', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            password = request.POST.get('password', '') 
            bloqueado = 'bloqueado' in request.POST

            # Seguridad: No permitir que el admin actual se bloquee a sí mismo
            if uid and int(uid) == user_id_sesion and bloqueado:
                messages.warning(request, "Operación cancelada: No puedes bloquear tu propia cuenta mientras estás en sesión.")
                bloqueado = False

            try:
                actualizar_usuario_admin(
                    uid, 
                    nombre=nombre, 
                    email=email, 
                    telefono=telefono, 
                    password=password, 
                    bloqueado=bloqueado
                )
                messages.success(request, f"Datos de '{nombre}' actualizados correctamente.")
            except ValueError as e:
                # Captura errores de validación en la edición (ej: intentar usar el email de otro admin)
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error al actualizar: {e}")

        # --- C. ELIMINAR USUARIO ---
        elif 'eliminar_usuario' in request.POST:
            uid = request.POST.get('eliminar_usuario')
            
            if uid and int(uid) == user_id_sesion:
                messages.error(request, "No puedes eliminar tu propia cuenta mientras la estás usando.")
            else:
                try:
                    eliminar_usuario_admin(uid)
                    messages.success(request, "Usuario eliminado permanentemente.")
                except Exception as e:
                    messages.error(request, f"No se pudo eliminar el usuario: {e}")

        # Redirección tras POST (Patrón PRG)
        return redirect('usuarios')

    # 3. Carga de datos para mostrar la página (GET)
    usuarios = obtener_usuarios_admin()
    
    return render(request, 'gestion_usuarios.html', {
        'usuarios': usuarios,
        'user_id_sesion': user_id_sesion 
    })


def dashboard(request):
    # 1. Verificación de autenticación
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    try:
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    # 2. Estadísticas generales
    hoy = timezone.now().date()
    fecha_inicio_mes = hoy.replace(day=1)
    fecha_fin_mes = hoy

    # Filtros de rango de fecha desde interfaz (GET)
    desde_str = request.GET.get('desde', '').strip()
    hasta_str = request.GET.get('hasta', '').strip()

    def parse_date(value):
        try:
            return timezone.datetime.strptime(value, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None

    fecha_desde = parse_date(desde_str) or fecha_inicio_mes
    fecha_hasta = parse_date(hasta_str) or fecha_fin_mes

    # Ajustar fecha_hasta para incluir todo el día
    fecha_hasta = fecha_hasta + timedelta(days=1)

    # Consultar ventas confirmadas dentro del rango de fechas
    ventas_confirmadas = Orden.objects.filter(es_venta=True, fecha_venta__range=[fecha_desde, fecha_hasta])
    total_ventas_confirmadas = ventas_confirmadas.aggregate(total=Sum('total'))['total'] or 0

    # Total de órdenes dentro del rango de fechas
    ordenes_rango = Orden.objects.filter(creado__date__range=[fecha_desde, fecha_hasta])
    total_ordenes_mes = ordenes_rango.count()

    # Calcular ingresos, ticket promedio y tasa de conversión
    ingresos_mes = total_ventas_confirmadas
    ticket_promedio = ingresos_mes / ventas_confirmadas.count() if ventas_confirmadas.count() > 0 else 0

    # Asegurarse de que total_ordenes_mes no sea cero antes de calcular la tasa de conversión
    if total_ordenes_mes > 0:
        tasa_conversion = (ventas_confirmadas.count() / total_ordenes_mes) * 100
    else:
        tasa_conversion = 0

    # Validar valores para evitar errores en el contexto
    ingresos_mes = round(ingresos_mes, 2)
    ticket_promedio = round(ticket_promedio, 2)
    tasa_conversion = round(tasa_conversion, 1)  # Ajustar a un decimal

    # Órdenes por estado dentro del rango de fechas
    ordenes_por_estado = ordenes_rango.values('estado').annotate(count=Count('id')).order_by('-count')

    total_productos = Product.objects.count()
    productos_agotados = Product.objects.filter(agotado=True).count()
    productos_disponibles = total_productos - productos_agotados

    porcentaje_agotados = (productos_agotados / total_productos * 100) if total_productos > 0 else 0
    porcentaje_disponibles = 100 - porcentaje_agotados

    clientes_recientes = Cliente.objects.annotate(
        ultima_orden=Max('ordenes__creado'),
        total_gastado=Sum('ordenes__total', filter=Q(ordenes__es_venta=True)),
        num_ordenes=Count('ordenes', filter=Q(ordenes__es_venta=True))
    ).order_by('-ultima_orden')[:5]

    productos_mas_vendidos = OrdenItem.objects.filter(orden__es_venta=True).values(
        producto__nombre=F('producto__nombre')
    ).annotate(total_vendido=Sum('cantidad')).order_by('-total_vendido')[:10]

    ultimos_12_meses = [
        {
            'mes': (hoy.replace(day=1) - timedelta(days=i * 30)).strftime('%b %Y'),
            'count': Orden.objects.filter(
                creado__year=(hoy - timedelta(days=i * 30)).year,
                creado__month=(hoy - timedelta(days=i * 30)).month
            ).count()
        }
        for i in range(12)
    ]

    context = {
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta - timedelta(days=1),  # Mostrar la fecha original en el contexto
        'total_ordenes_mes': total_ordenes_mes,
        'ingresos_mes': ingresos_mes,
        'ticket_promedio': ticket_promedio,
        'tasa_conversion': tasa_conversion,
        'total_productos': total_productos,
        'productos_agotados': productos_agotados,
        'productos_disponibles': productos_disponibles,
        'porcentaje_agotados': round(porcentaje_agotados, 1),
        'porcentaje_disponibles': round(porcentaje_disponibles, 1),
        'clientes_recientes': clientes_recientes,
        'productos_mas_vendidos': productos_mas_vendidos,
        'ordenes_por_estado': list(ordenes_por_estado),
        'ultimos_12_meses': ultimos_12_meses,
    }

    return render(request, 'dashboard.html', context)
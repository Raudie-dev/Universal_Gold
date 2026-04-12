import io
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from app1.models import Product, Category, ProductImage
from django.contrib.auth.hashers import make_password
from .models import User_admin, Afiliado # Importa el modelo
from django.utils import timezone
from PIL import Image as PilImage

def crear_categoria(nombre, padre_id=None):
    """
    Crea una categoría nueva o devuelve la existente.
    La unicidad se basa en el par (nombre, padre_id) para permitir
    mismos nombres en diferentes ramas del árbol.
    """
    nombre = (nombre or '').strip()
    if not nombre:
        return None
    
    # IMPORTANTE: Buscamos usando el nombre Y el padre_id.
    # get_or_create devuelve una tupla (objeto, creado_boolean)
    cat, created = Category.objects.get_or_create(
        nombre=nombre,
        padre_id=padre_id
    )
    
    return cat


def obtener_categorias():
    """
    Obtiene todas las categorías.
    Usamos 'prefetch_related' para cargar las subcategorías eficientemente
    y evitar lentitud en la plantilla HTML.
    """
    return Category.objects.prefetch_related('subcategorias').all().order_by('nombre')


def eliminar_categoria(cat_id):
    Category.objects.filter(id=cat_id).delete()


def generar_codigo_afiliado(nombre):
    base = ''.join(ch for ch in (nombre or '').upper() if ch.isalnum())[:8] or 'AFI'
    sufijo = '000'
    intento = 0
    while True:
        codigo = f"{base}{sufijo if intento == 0 else intento:03d}"
        if not Afiliado.objects.filter(codigo=codigo).exists():
            return codigo
        intento += 1


def obtener_afiliados():
    return Afiliado.objects.all()


def crear_afiliado(nombre, codigo=None, descuento=0, comision=0):
    nombre = (nombre or '').strip()
    if not nombre:
        raise ValueError('El nombre del afiliado es obligatorio.')

    descuento_val = 0
    try:
        descuento_val = float(descuento or 0)
    except (TypeError, ValueError):
        raise ValueError('El descuento debe ser un número válido.')

    if descuento_val < 0 or descuento_val > 100:
        raise ValueError('El descuento debe estar entre 0 y 100.')

    comision_val = 0
    try:
        comision_val = float(comision or 0)
    except (TypeError, ValueError):
        raise ValueError('La comisión debe ser un número válido.')

    if comision_val < 0 or comision_val > 100:
        raise ValueError('La comisión debe estar entre 0 y 100.')

    codigo = (codigo or '').strip().upper()
    if not codigo:
        codigo = generar_codigo_afiliado(nombre)

    if Afiliado.objects.filter(codigo__iexact=codigo).exists():
        raise ValueError(f'El código {codigo} ya está en uso.')

    return Afiliado.objects.create(
        nombre=nombre,
        codigo=codigo,
        descuento=descuento_val,
        comision=comision_val,
    )


def actualizar_afiliado(afiliado_id, **kwargs):
    try:
        afiliado = Afiliado.objects.get(id=afiliado_id)
    except Afiliado.DoesNotExist:
        raise ValueError('Afiliado no encontrado.')

    if 'nombre' in kwargs and kwargs['nombre'] is not None:
        afiliado.nombre = kwargs['nombre'].strip()
    if 'codigo' in kwargs and kwargs['codigo']:
        codigo = kwargs['codigo'].strip().upper()
        if Afiliado.objects.filter(codigo__iexact=codigo).exclude(id=afiliado_id).exists():
            raise ValueError(f'El código {codigo} ya está en uso por otro afiliado.')
        afiliado.codigo = codigo
    if 'descuento' in kwargs and kwargs['descuento'] is not None:
        try:
            descuento_val = float(kwargs['descuento'])
        except (TypeError, ValueError):
            raise ValueError('El descuento debe ser un porcentaje válido.')
        if descuento_val < 0 or descuento_val > 100:
            raise ValueError('El descuento debe estar entre 0 y 100.')
        afiliado.descuento = descuento_val
    if 'comision' in kwargs and kwargs['comision'] is not None:
        try:
            comision_val = float(kwargs['comision'])
        except (TypeError, ValueError):
            raise ValueError('La comisión debe ser un porcentaje válido.')
        if comision_val < 0 or comision_val > 100:
            raise ValueError('La comisión debe estar entre 0 y 100.')
        afiliado.comision = comision_val
    if 'activo' in kwargs:
        afiliado.activo = bool(kwargs['activo'])

    afiliado.save()
    return afiliado


def eliminar_afiliado(afiliado_id):
    Afiliado.objects.filter(id=afiliado_id).delete()


def convert_uploaded_image_to_webp(uploaded_file, quality=80):
    """Convierte una imagen subida a WebP y devuelve un ContentFile listo para guardar."""
    try:
        uploaded_file.seek(0)
        image = PilImage.open(uploaded_file)
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')

        output = io.BytesIO()
        image.save(output, format='WEBP', quality=quality, method=6)
        output.seek(0)

        base_name, _ = os.path.splitext(uploaded_file.name or 'imagen')
        webp_name = f"{base_name}.webp"
        return ContentFile(output.read(), name=webp_name)
    except Exception:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        return uploaded_file


def crear_producto(nombre, precio, descripcion='', categoria_ids=None, imagen=None, imagenes=None):
    """Crea un producto. `imagenes` es una lista de archivos ordenados."""
    nombre = (nombre or '').strip()
    if not nombre:
        raise ValueError('El nombre es obligatorio')
    try:
        precio_val = float(precio)
    except (TypeError, ValueError):
        precio_val = 0

    producto = Product.objects.create(
        nombre=nombre,
        precio=precio_val,
        descripcion=descripcion or '',
        creado=timezone.now()  # Set the current timestamp for 'creado'
    )

    # Asociar categorías si se entregaron ids
    if categoria_ids:
        ids = [int(x) for x in categoria_ids if x]
        cats = Category.objects.filter(id__in=ids)
        producto.categorias.set(cats)

    # Guardar imágenes (ahora ordenadas)
    if imagenes:
        for idx, img in enumerate(imagenes):
            webp_img = convert_uploaded_image_to_webp(img)
            ProductImage.objects.create(
                product=producto,
                imagen=webp_img,
                orden=idx,
                is_portada=(idx == 0),
                creado=timezone.now()
            )

    return producto


def obtener_productos():
    # Prefetch M2M categorias para optimizar la carga
    return Product.objects.prefetch_related('categorias').all()


def eliminar_producto(producto_id):
    Product.objects.filter(id=producto_id).delete()


def actualizar_producto(producto_id, **kwargs):
    """Actualizar campos permitidos de un producto."""
    try:
        p = Product.objects.get(id=producto_id)
    except ObjectDoesNotExist:
        return None

    for field in ('nombre', 'descripcion', 'precio', 'agotado'):
        if field in kwargs and kwargs[field] is not None:
            setattr(p, field, kwargs[field])

    # Soporte para actualizar categorias (lista de ids)
    if 'categoria_ids' in kwargs:
        cat_ids = kwargs.get('categoria_ids') or []
        ids = [int(x) for x in cat_ids if x]
        cats = Category.objects.filter(id__in=ids)
        p.categorias.set(cats)

    if 'imagen' in kwargs and kwargs['imagen'] is not None:
        p.imagen = convert_uploaded_image_to_webp(kwargs['imagen'])

    if 'imagenes' in kwargs and kwargs['imagenes']:
        # Agregar nuevas imágenes extras
        for img in kwargs['imagenes']:
            webp_img = convert_uploaded_image_to_webp(img)
            ProductImage.objects.create(product=p, imagen=webp_img, is_portada=False, creado=timezone.now())

    # Cambiar portada si se solicita
    if 'portada_imagen_id' in kwargs and kwargs['portada_imagen_id']:
        try:
            portada_id = int(kwargs['portada_imagen_id'])
            p.imagenes.update(is_portada=False)
            ProductImage.objects.filter(id=portada_id, product=p).update(is_portada=True)
        except (ValueError, TypeError):
            pass

    # Eliminar imágenes seleccionadas
    if 'eliminar_imagenes' in kwargs:
        eliminar_ids = [int(x) for x in (kwargs.get('eliminar_imagenes') or []) if x]
        ProductImage.objects.filter(product=p, id__in=eliminar_ids).delete()

    p.save()
    return p

def obtener_usuarios_admin():
    return User_admin.objects.all().order_by('nombre')

def crear_usuario_admin(nombre, password, email=None, telefono=None):
    nombre = nombre.strip()
    email = email.strip() if email else None
    
    if not nombre or not password:
        raise ValueError("El nombre y la contraseña son obligatorios.")

    # Validar si el nombre ya existe
    if User_admin.objects.filter(nombre=nombre).exists():
        raise ValueError(f"El nombre de usuario '{nombre}' ya está en uso.")

    # Validar si el email ya existe (si se proporcionó uno)
    if email and User_admin.objects.filter(email=email).exists():
        raise ValueError(f"El correo electrónico '{email}' ya está registrado por otro administrador.")

    return User_admin.objects.create(
        nombre=nombre,
        password=make_password(password),
        email=email,
        telefono=telefono
    )

def actualizar_usuario_admin(user_id, **kwargs):
    try:
        user = User_admin.objects.get(id=user_id)
        
        # Validar nombre duplicado (excluyendo al usuario actual)
        if 'nombre' in kwargs:
            nuevo_nombre = kwargs['nombre'].strip()
            if User_admin.objects.filter(nombre=nuevo_nombre).exclude(id=user_id).exists():
                raise ValueError(f"El nombre '{nuevo_nombre}' ya lo tiene otro usuario.")
            user.nombre = nuevo_nombre

        # Validar email duplicado (excluyendo al usuario actual)
        if 'email' in kwargs and kwargs['email']:
            nuevo_email = kwargs['email'].strip()
            if User_admin.objects.filter(email=nuevo_email).exclude(id=user_id).exists():
                raise ValueError(f"El correo '{nuevo_email}' ya está en uso por otro administrador.")
            user.email = nuevo_email

        if 'telefono' in kwargs:
            user.telefono = kwargs['telefono']
        if 'bloqueado' in kwargs:
            user.bloqueado = kwargs['bloqueado']
        if 'password' in kwargs and kwargs['password']:
            user.password = make_password(kwargs['password'])
            
        user.save()
        return user
    except User_admin.DoesNotExist:
        raise ValueError("El usuario no existe.")

def actualizar_usuario_admin(user_id, **kwargs):
    try:
        user = User_admin.objects.get(id=user_id)
        
        if 'nombre' in kwargs:
            user.nombre = kwargs['nombre'].strip()
        if 'email' in kwargs:
            user.email = kwargs['email']
        if 'telefono' in kwargs:
            user.telefono = kwargs['telefono']
        if 'bloqueado' in kwargs:
            user.bloqueado = kwargs['bloqueado']
        
        # Si se envía una nueva contraseña, se hashea
        if 'password' in kwargs and kwargs['password']:
            user.password = make_password(kwargs['password'])
            
        user.save()
        return user
    except User_admin.DoesNotExist:
        return None

def eliminar_usuario_admin(user_id):
    User_admin.objects.filter(id=user_id).delete()


def obtener_config(llave, default=None):
    from .models import AppConfig
    return AppConfig.get_valor(llave, default)


def guardar_config(llave, valor):
    from .models import AppConfig
    return AppConfig.set_valor(llave, valor)

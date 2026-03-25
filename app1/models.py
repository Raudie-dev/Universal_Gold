from django.db import models
from django.db import models

class Category(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    
    # --- CAMPO NUEVO PARA SUBCATEGORÍAS ---
    # 'self' indica relación con este mismo modelo.
    # null=True y blank=True permite que sea una categoría principal (sin padre).
    # related_name='subcategorias' es vital para el HTML que te pasé antes.
    padre = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        related_name='subcategorias', 
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        # Si tiene padre, muestra "Padre > Hijo", si no, solo el nombre.
        if self.padre:
            return f"{self.padre.nombre} > {self.nombre}"
        return self.nombre

class Product(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Permite múltiples categorías por producto
    categorias = models.ManyToManyField('Category', blank=True, related_name='productos') # Asegúrate que 'Category' coincida con tu modelo
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    creado = models.DateTimeField(null=True, blank=True)
    agotado = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

    @property
    def portada(self):
        portada_obj = self.imagenes.filter(is_portada=True).first()
        if portada_obj:
            return portada_obj.imagen
        if self.imagen:
            return self.imagen
        return None

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='productos/')
    is_portada = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=0)
    creado = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['orden', 'creado']

    def __str__(self):
        return f"Imagen #{self.id} para {self.product.nombre} {'(portada)' if self.is_portada else ''}"


class Cliente(models.Model):
    nombre = models.CharField(max_length=200)
    correo = models.EmailField()
    telefono = models.CharField(max_length=40, blank=True)
    creado = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f"{self.nombre} <{self.correo}>"

class Orden(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='ordenes')
    mensaje = models.TextField(blank=True)
    creado = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=30, default='pendiente')  # pendiente, procesado, finalizado, etc.
    es_venta = models.BooleanField(default=False)
    fecha_venta = models.DateTimeField(null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Nuevo campo para el monto total

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ['-creado']
        db_table = 'app1_cotizacion'  # Conserva tabla histórica de cotizaciones

    def __str__(self):
        return f"Orden #{self.id} - {self.cliente.nombre}"
    
class OrdenItem(models.Model):
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='cotizacion_id',
    )
    producto = models.ForeignKey(Product, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'app1_cotizacionitem'  # Conserva tabla histórica de cotizacionitems

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (orden #{self.orden_id})"


# Compatibilidad con referencia antigua
Cotizacion = Orden
CotizacionItem = OrdenItem

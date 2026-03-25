from django.db import models

class User_admin(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)
    bloqueado = models.BooleanField(default=False)
    email = models.EmailField(max_length=150, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.nombre


class AppConfig(models.Model):
    llave = models.CharField(max_length=100, unique=True)
    valor = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.llave}: {self.valor}"

    @staticmethod
    def get_valor(llave, default=None):
        try:
            return AppConfig.objects.get(llave=llave).valor
        except AppConfig.DoesNotExist:
            return default

    @staticmethod
    def set_valor(llave, valor):
        obj, _ = AppConfig.objects.update_or_create(llave=llave, defaults={'valor': valor})
        return obj


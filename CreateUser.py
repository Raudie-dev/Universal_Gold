import os
import django
from tkinter import *
from tkinter import messagebox
from django.contrib.auth.hashers import make_password

# =========================
# Configuración Django
# =========================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto.settings')
django.setup()

from app2.models import User_admin

# =========================
# Funciones
# =========================
def limpiar_campos():
    entry_nombre.delete(0, END)
    entry_password.delete(0, END)
    entry_email.delete(0, END)
    entry_telefono.delete(0, END)

def cargar_usuario():
    nombre = entry_nombre.get()

    if not nombre:
        messagebox.showerror("Error", "Ingrese un nombre de usuario")
        return

    try:
        user = User_admin.objects.get(nombre=nombre)
        entry_email.delete(0, END)
        entry_telefono.delete(0, END)

        entry_email.insert(0, user.email or "")
        entry_telefono.insert(0, user.telefono or "")

        messagebox.showinfo(
            "Usuario encontrado",
            "Usuario cargado. Puede modificar los datos."
        )

    except User_admin.DoesNotExist:
        messagebox.showinfo(
            "Nuevo usuario",
            "Usuario no existe. Se registrará uno nuevo."
        )
        limpiar_campos()
        entry_nombre.insert(0, nombre)

def guardar_usuario():
    nombre = entry_nombre.get()
    password = entry_password.get()
    email = entry_email.get()
    telefono = entry_telefono.get()

    if not nombre:
        messagebox.showerror("Error", "El nombre es obligatorio")
        return

    try:
        user = User_admin.objects.get(nombre=nombre)
        es_nuevo = False
    except User_admin.DoesNotExist:
        user = User_admin(nombre=nombre)
        es_nuevo = True

    # Validar email duplicado
    if email:
        qs = User_admin.objects.filter(email=email).exclude(nombre=nombre)
        if qs.exists():
            messagebox.showerror("Error", "El email ya está en uso")
            return

    # Actualizar datos
    user.email = email if email else None
    user.telefono = telefono if telefono else None

    if password:
        user.password = make_password(password)

    user.save()

    if es_nuevo:
        messagebox.showinfo("Éxito", "Usuario registrado correctamente")
    else:
        messagebox.showinfo("Éxito", "Usuario actualizado correctamente")

    limpiar_campos()

# =========================
# Interfaz Tkinter
# =========================
root = Tk()
root.title("Gestión de Usuarios Admin")
root.geometry("380x360")
root.resizable(False, False)

Label(root, text="Gestión de Usuarios", font=("Arial", 16)).pack(pady=10)

frame = Frame(root)
frame.pack(pady=10)

Label(frame, text="Nombre:").grid(row=0, column=0, sticky=E, pady=5)
entry_nombre = Entry(frame, width=25)
entry_nombre.grid(row=0, column=1, pady=5)

Button(frame, text="Buscar", command=cargar_usuario, width=10).grid(row=0, column=2, padx=5)

Label(frame, text="Contraseña:").grid(row=1, column=0, sticky=E, pady=5)
entry_password = Entry(frame, show="*", width=25)
entry_password.grid(row=1, column=1, pady=5)

Label(frame, text="Email:").grid(row=2, column=0, sticky=E, pady=5)
entry_email = Entry(frame, width=25)
entry_email.grid(row=2, column=1, pady=5)

Label(frame, text="Teléfono:").grid(row=3, column=0, sticky=E, pady=5)
entry_telefono = Entry(frame, width=25)
entry_telefono.grid(row=3, column=1, pady=5)

Label(
    root,
    text="* Dejar contraseña vacía para no modificarla",
    fg="gray"
).pack(pady=5)

Button(
    root,
    text="Guardar",
    command=guardar_usuario,
    width=15,
    bg="#4CAF50",
    fg="white"
).pack(pady=15)

root.mainloop()

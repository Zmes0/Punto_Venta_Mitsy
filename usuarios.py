"""
Diálogos para gestión de usuarios
"""
import tkinter as tk
from tkinter import messagebox
from config import COLORS, FONTS
from utils import get_resource_path
from database import db
from auth import session

class UsuarioDialog:
    def __init__(self, parent, user_id=None, callback=None):
        self.user_id = user_id
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Añadir Usuario" if not user_id else "Editar Usuario")
        self.dialog.geometry("500x550")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        try:
            self.dialog.iconbitmap(get_resource_path('icono.ico'))
        except:
            pass
        
        self.center_dialog()
        self.setup_ui()
        
        if user_id:
            self.load_usuario_data()
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 500
        height = 550
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Título
        titulo = "Añadir Nuevo Usuario" if not self.user_id else "Editar Usuario"
        tk.Label(main_frame, text=titulo, font=FONTS['subtitle'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=(0, 20))
        
        # Nombre de usuario
        tk.Label(main_frame, text="Nombre de Usuario:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        
        self.username_var = tk.StringVar()
        username_entry = tk.Entry(main_frame, textvariable=self.username_var, 
                                  font=FONTS['normal'])
        username_entry.pack(fill=tk.X, pady=(0, 15))
        username_entry.focus()
        
        # Nombre completo
        tk.Label(main_frame, text="Nombre Completo (opcional):", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        
        self.nombre_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=self.nombre_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 15))
        
        # Contraseña (solo si es nuevo usuario)
        if not self.user_id:
            tk.Label(main_frame, text="Contraseña:", font=FONTS['normal'],
                    bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
            
            self.password_var = tk.StringVar()
            tk.Entry(main_frame, textvariable=self.password_var, 
                    font=FONTS['normal'], show='●').pack(fill=tk.X, pady=(0, 15))
            
            tk.Label(main_frame, text="Confirmar Contraseña:", font=FONTS['normal'],
                    bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
            
            self.password_confirm_var = tk.StringVar()
            tk.Entry(main_frame, textvariable=self.password_confirm_var, 
                    font=FONTS['normal'], show='●').pack(fill=tk.X, pady=(0, 15))
        
        # Nivel de acceso
        tk.Label(main_frame, text="Nivel de Acceso:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        
        nivel_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        nivel_frame.pack(anchor='w', pady=(0, 20))
        
        self.nivel_var = tk.StringVar(value='empleado')
        
        tk.Radiobutton(nivel_frame, text="Administrador", variable=self.nivel_var,
                      value='admin', font=FONTS['normal'],
                      bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(nivel_frame, text="Empleado", variable=self.nivel_var,
                      value='empleado', font=FONTS['normal'],
                      bg=COLORS['bg_primary']).pack(side=tk.LEFT)
        
        # Botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Guardar", command=self.save_usuario,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def load_usuario_data(self):
        """Carga los datos del usuario a editar"""
        usuario = db.get_usuario(self.user_id)
        
        if not usuario:
            messagebox.showerror("Error", "Usuario no encontrado")
            self.dialog.destroy()
            return
        
        self.username_var.set(usuario['username'])
        self.nombre_var.set(usuario['nombre_completo'] or '')
        self.nivel_var.set(usuario['nivel'])
    
    def save_usuario(self):
        """Guarda el usuario"""
        username = self.username_var.get().strip()
        nombre = self.nombre_var.get().strip() or None
        nivel = self.nivel_var.get()
        
        # Validaciones
        if not username:
            messagebox.showerror("Error", "El nombre de usuario es obligatorio")
            return
        
        # Verificar si el username ya existe
        if db.username_exists(username, exclude_id=self.user_id):
            messagebox.showerror("Error", f"El nombre de usuario '{username}' ya existe")
            return
        
        if not self.user_id:
            # Nuevo usuario - validar contraseñas
            password = self.password_var.get()
            password_confirm = self.password_confirm_var.get()
            
            if not password:
                messagebox.showerror("Error", "La contraseña es obligatoria")
                return
            
            if password != password_confirm:
                messagebox.showerror("Error", "Las contraseñas no coinciden")
                return
            
            if len(password) < 4:
                messagebox.showerror("Error", "La contraseña debe tener al menos 4 caracteres")
                return
            
            try:
                # Crear usuario
                user_id = db.add_usuario(username, password, nombre, nivel)
                
                # Registrar en auditoría
                db.add_auditoria(session.get_current_user()['id'], 'user_create', 
                               f"Usuario creado: {username} ({nivel})")
                
                messagebox.showinfo("Éxito", "Usuario creado correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"Error al crear usuario: {str(e)}")
                return
        else:
            # Actualizar usuario existente
            try:
                db.update_usuario(self.user_id, 
                                username=username,
                                nombre_completo=nombre,
                                nivel=nivel)
                
                # Registrar en auditoría
                db.add_auditoria(session.get_current_user()['id'], 'user_update', 
                               f"Usuario actualizado: {username}")
                
                messagebox.showinfo("Éxito", "Usuario actualizado correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"Error al actualizar usuario: {str(e)}")
                return
        
        if self.callback:
            self.callback()
        
        self.dialog.destroy()


class CambiarPasswordDialog:
    def __init__(self, parent, user_id):
        self.user_id = user_id
        
        # Obtener datos del usuario
        self.usuario = db.get_usuario(user_id)
        if not self.usuario:
            messagebox.showerror("Error", "Usuario no encontrado")
            return
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Cambiar Contraseña")
        self.dialog.geometry("450x350")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        try:
            self.dialog.iconbitmap(get_resource_path('icono.ico'))
        except:
            pass
        
        self.center_dialog()
        self.setup_ui()
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 450
        height = 350
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Título
        tk.Label(main_frame, text="Cambiar Contraseña", font=FONTS['subtitle'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=(0, 10))
        
        tk.Label(main_frame, text=f"Usuario: {self.usuario['username']}", 
                font=FONTS['normal'], bg=COLORS['bg_primary'],
                fg=COLORS['text_secondary']).pack(pady=(0, 20))
        
        # Nueva contraseña
        tk.Label(main_frame, text="Nueva Contraseña:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        
        self.password_var = tk.StringVar()
        password_entry = tk.Entry(main_frame, textvariable=self.password_var, 
                                  font=FONTS['normal'], show='●')
        password_entry.pack(fill=tk.X, pady=(0, 15))
        password_entry.focus()
        
        # Confirmar contraseña
        tk.Label(main_frame, text="Confirmar Contraseña:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        
        self.password_confirm_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=self.password_confirm_var, 
                font=FONTS['normal'], show='●').pack(fill=tk.X, pady=(0, 20))
        
        # Botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Cambiar", command=self.change_password,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def change_password(self):
        """Cambia la contraseña del usuario"""
        password = self.password_var.get()
        password_confirm = self.password_confirm_var.get()
        
        # Validaciones
        if not password:
            messagebox.showerror("Error", "La contraseña es obligatoria")
            return
        
        if password != password_confirm:
            messagebox.showerror("Error", "Las contraseñas no coinciden")
            return
        
        if len(password) < 4:
            messagebox.showerror("Error", "La contraseña debe tener al menos 4 caracteres")
            return
        
        try:
            # Actualizar contraseña
            db.update_usuario(self.user_id, password=password)
            
            # Registrar en auditoría
            db.add_auditoria(session.get_current_user()['id'], 'password_change', 
                           f"Contraseña cambiada para: {self.usuario['username']}")
            
            messagebox.showinfo("Éxito", "Contraseña actualizada correctamente")
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar contraseña: {str(e)}")
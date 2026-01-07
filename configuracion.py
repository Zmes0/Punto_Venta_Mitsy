"""
Módulo de Configuración para Mitsy's POS
Requiere autenticación de administrador
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config import COLORS, FONTS, BUSINESS_INFO
from utils import get_resource_path
from database import db
from auth import session, AdminAuthDialog
import shutil
import os
from datetime import datetime

class ConfiguracionWindow:
    def __init__(self, parent, on_close=None):
        self.on_close_callback = on_close
        
        # Verificar que el usuario actual sea admin
        if not session.is_admin():
            messagebox.showerror("Acceso Denegado", 
                               "Esta sección requiere permisos de administrador")
            if on_close:
                on_close()
            return
        
        self.window = tk.Toplevel(parent)
        self.window.title("Configuración del Sistema - Mitsy's POS")
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.state('zoomed')
        self.window.minsize(900, 600)
        
        # Forzar al frente
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        try:
            self.window.iconbitmap(get_resource_path('icono.ico'))
        except:
            pass
        
        # Protocolo de cierre
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz con pestañas"""
        main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(main_frame, text="Configuración del Sistema", 
                              font=FONTS['title'], bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=(0, 20))
        
        # Notebook (pestañas)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Pestaña 1: Usuarios
        self.usuarios_frame = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(self.usuarios_frame, text="  Usuarios  ")
        self.setup_usuarios_tab()
        
        # Pestaña 2: Información del Negocio
        self.negocio_frame = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(self.negocio_frame, text="  Información del Negocio  ")
        self.setup_negocio_tab()
        
        # Pestaña 3: Base de Datos
        self.database_frame = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(self.database_frame, text="  Base de Datos  ")
        self.setup_database_tab()
        
        # Botón regresar
        tk.Button(main_frame, text="Regresar", command=self.close_window,
                 font=FONTS['button'], bg=COLORS['button_bg'],
                 fg=COLORS['text_primary'], relief=tk.RAISED,
                 borderwidth=2, padx=30, pady=10).pack()
    
    def setup_usuarios_tab(self):
        """Configura la pestaña de usuarios"""
        # Frame para el switch maestro
        switch_frame = tk.Frame(self.usuarios_frame, bg=COLORS['bg_secondary'],
                               relief=tk.RAISED, borderwidth=2)
        switch_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        tk.Label(switch_frame, text="Sistema de Autenticación:", 
                font=FONTS['heading'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=15, pady=15)
        
        self.auth_enabled_var = tk.BooleanVar(value=db.is_auth_enabled())
        self.auth_enabled_var.trace('w', self.toggle_auth_system)
        
        tk.Radiobutton(switch_frame, text="Activado", variable=self.auth_enabled_var,
                      value=True, font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(switch_frame, text="Desactivado", variable=self.auth_enabled_var,
                      value=False, font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=5)
        
        # Frame para timeout
        timeout_frame = tk.Frame(self.usuarios_frame, bg=COLORS['bg_secondary'],
                                relief=tk.RAISED, borderwidth=2)
        timeout_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(timeout_frame, text="Timeout de Sesión (minutos):", 
                font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=15, pady=15)
        
        self.timeout_var = tk.IntVar(value=int(db.get_config('session_timeout') or 30))
        timeout_spinbox = tk.Spinbox(timeout_frame, from_=15, to=120, increment=5,
                                     textvariable=self.timeout_var, font=FONTS['normal'],
                                     width=10, command=self.update_timeout)
        timeout_spinbox.pack(side=tk.LEFT, padx=10)
        
        # Tabla de usuarios
        table_frame = tk.Frame(self.usuarios_frame, bg=COLORS['bg_primary'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ('ID', 'Usuario', 'Nombre Completo', 'Nivel', 'Estado', 'Último Acceso')
        
        self.usuarios_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                         yscrollcommand=scrollbar.set, selectmode='browse')
        
        self.usuarios_tree.heading('ID', text='ID')
        self.usuarios_tree.heading('Usuario', text='Usuario')
        self.usuarios_tree.heading('Nombre Completo', text='Nombre Completo')
        self.usuarios_tree.heading('Nivel', text='Nivel')
        self.usuarios_tree.heading('Estado', text='Estado')
        self.usuarios_tree.heading('Último Acceso', text='Último Acceso')
        
        self.usuarios_tree.column('ID', width=50, anchor='center')
        self.usuarios_tree.column('Usuario', width=150)
        self.usuarios_tree.column('Nombre Completo', width=200)
        self.usuarios_tree.column('Nivel', width=100, anchor='center')
        self.usuarios_tree.column('Estado', width=100, anchor='center')
        self.usuarios_tree.column('Último Acceso', width=180, anchor='center')
        
        self.usuarios_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.usuarios_tree.yview)
        
        # Colores
        self.usuarios_tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.usuarios_tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        self.usuarios_tree.tag_configure('admin', background='#E3F2FD')
        self.usuarios_tree.tag_configure('inactivo', background='#FFEBEE')
        
        # Botones
        button_frame = tk.Frame(self.usuarios_frame, bg=COLORS['bg_primary'])
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Button(button_frame, text="Añadir Usuario", command=self.add_usuario,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Editar Usuario", command=self.edit_usuario,
                 font=FONTS['button'], bg=COLORS['button_bg'],
                 fg=COLORS['text_primary'], relief=tk.RAISED,
                 borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Cambiar Contraseña", command=self.change_password,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Desactivar Usuario", command=self.deactivate_usuario,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        # Cargar usuarios
        self.load_usuarios()
    
    def setup_negocio_tab(self):
        """Configura la pestaña de información del negocio"""
        # Próximamente
        tk.Label(self.negocio_frame, text="Próximamente: Configuración de información del negocio", 
                font=FONTS['heading'], bg=COLORS['bg_primary']).pack(pady=50)
    
    def setup_database_tab(self):
        """Configura la pestaña de base de datos"""
        # Próximamente
        tk.Label(self.database_frame, text="Próximamente: Gestión de base de datos", 
                font=FONTS['heading'], bg=COLORS['bg_primary']).pack(pady=50)
    
    def toggle_auth_system(self, *args):
        """Activa/desactiva el sistema de autenticación"""
        enabled = self.auth_enabled_var.get()
        db.toggle_auth_system(enabled)
        
        if enabled:
            messagebox.showinfo("Sistema de Autenticación", 
                              "Sistema de autenticación activado.\n\n"
                              "Los usuarios deberán iniciar sesión al abrir la aplicación.")
        else:
            messagebox.showinfo("Sistema de Autenticación", 
                              "Sistema de autenticación desactivado.\n\n"
                              "No se solicitará inicio de sesión al abrir la aplicación.")
        
        # Registrar en auditoría
        db.add_auditoria(session.get_current_user()['id'], 'config_auth', 
                       f"Sistema de autenticación {'activado' if enabled else 'desactivado'}")
    
    def update_timeout(self):
        """Actualiza el timeout de sesión"""
        timeout = self.timeout_var.get()
        db.set_config('session_timeout', str(timeout))
        session.set_timeout(timeout)
        
        db.add_auditoria(session.get_current_user()['id'], 'config_timeout', 
                       f"Timeout de sesión actualizado a {timeout} minutos")
    
    def load_usuarios(self):
        """Carga los usuarios en la tabla"""
        for item in self.usuarios_tree.get_children():
            self.usuarios_tree.delete(item)
        
        usuarios = db.get_usuarios()
        
        for idx, u in enumerate(usuarios):
            # Determinar tag
            if not u['activo']:
                tag = 'inactivo'
            elif u['nivel'] == 'admin':
                tag = 'admin'
            else:
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            values = (
                u['id'],
                u['username'],
                u['nombre_completo'] or '-',
                u['nivel'].capitalize(),
                'Activo' if u['activo'] else 'Inactivo',
                u['ultimo_acceso'] or 'Nunca'
            )
            
            self.usuarios_tree.insert('', tk.END, values=values, tags=(tag,))
    
    def add_usuario(self):
        """Abre diálogo para añadir usuario"""
        from usuarios import UsuarioDialog
        UsuarioDialog(self.window, callback=self.load_usuarios)
    
    def edit_usuario(self):
        """Edita el usuario seleccionado"""
        selection = self.usuarios_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un usuario para editar")
            return
        
        item = self.usuarios_tree.item(selection[0])
        user_id = item['values'][0]
        
        from usuarios import UsuarioDialog
        UsuarioDialog(self.window, user_id=user_id, callback=self.load_usuarios)
    
    def change_password(self):
        """Cambia la contraseña del usuario seleccionado"""
        selection = self.usuarios_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un usuario")
            return
        
        item = self.usuarios_tree.item(selection[0])
        user_id = item['values'][0]
        
        from usuarios import CambiarPasswordDialog
        CambiarPasswordDialog(self.window, user_id=user_id)
    
    def deactivate_usuario(self):
        """Desactiva el usuario seleccionado"""
        selection = self.usuarios_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un usuario")
            return
        
        item = self.usuarios_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        # No permitir desactivar al usuario actual
        if user_id == session.get_current_user()['id']:
            messagebox.showerror("Error", "No puedes desactivar tu propio usuario")
            return
        
        # No permitir desactivar a 'mitsy' si es el único admin
        if username == 'mitsy':
            # Contar admins activos
            db.cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE nivel = 'admin' AND activo = 1")
            count = db.cursor.fetchone()['count']
            
            if count <= 1:
                messagebox.showerror("Error", "No puedes desactivar el único administrador del sistema")
                return
        
        if messagebox.askyesno("Confirmar", f"¿Deseas desactivar al usuario '{username}'?"):
            db.delete_usuario(user_id)
            db.add_auditoria(session.get_current_user()['id'], 'user_deactivate', 
                           f"Usuario desactivado: {username}")
            
            messagebox.showinfo("Éxito", "Usuario desactivado correctamente")
            self.load_usuarios()
    
    def close_window(self):
        """Cierra la ventana"""
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()
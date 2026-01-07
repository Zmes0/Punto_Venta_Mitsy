"""
Sistema de Autenticación para Mitsy's POS - MEJORADO
"""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from config import COLORS, FONTS
from utils import get_resource_path

class SessionManager:
    """Gestor de sesiones de usuario"""
    def __init__(self):
        self.current_user = None
        self.last_activity = None
        self.timeout_minutes = 30
    
    def login(self, user_data):
        """Inicia sesión con un usuario"""
        self.current_user = user_data
        self.last_activity = datetime.now()
        
        from database import db
        db.cursor.execute('''
            UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?
        ''', (datetime.now().strftime('%d/%m/%Y %H:%M:%S'), user_data['id']))
        db.conn.commit()
        
        db.add_auditoria(user_data['id'], 'login', f"Inicio de sesión: {user_data['username']}")
        
        print(f"✓ Usuario '{user_data['username']}' ha iniciado sesión")
    
    def logout(self):
        """Cierra la sesión actual"""
        if self.current_user:
            username = self.current_user['username']
            user_id = self.current_user['id']
            
            from database import db
            db.add_auditoria(user_id, 'logout', f"Cierre de sesión: {username}")
            
            self.current_user = None
            self.last_activity = None
            print(f"✓ Usuario '{username}' ha cerrado sesión")
    
    def is_logged_in(self):
        """Verifica si hay una sesión activa"""
        if not self.current_user:
            return False
        
        if self.last_activity:
            elapsed = (datetime.now() - self.last_activity).total_seconds() / 60
            if elapsed > self.timeout_minutes:
                print(f"⏰ Sesión expirada por inactividad ({elapsed:.0f} min)")
                self.logout()
                return False
        
        return True
    
    def update_activity(self):
        """Actualiza la última actividad"""
        if self.current_user:
            self.last_activity = datetime.now()
    
    def get_current_user(self):
        """Obtiene el usuario actual"""
        return self.current_user
    
    def is_admin(self):
        """Verifica si el usuario actual es administrador"""
        return self.current_user and self.current_user['nivel'] == 'admin'
    
    def get_timeout(self):
        """Obtiene el timeout actual"""
        return self.timeout_minutes
    
    def set_timeout(self, minutes):
        """Establece el timeout de sesión"""
        self.timeout_minutes = minutes


session = SessionManager()


class LoginWindow:
    """Ventana de inicio de sesión - MEJORADA"""
    def __init__(self, parent, on_success=None):
        self.on_success = on_success
        self.show_password = False
        
        self.window = tk.Toplevel(parent)
        self.window.title("Iniciar Sesión - Mitsy's POS")
        self.window.geometry("450x500")
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.transient(parent)
        self.window.grab_set()
        self.window.resizable(False, False)
        
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        try:
            self.window.iconbitmap(get_resource_path('icono.ico'))
        except:
            pass
        
        self.center_window()
        self.setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def center_window(self):
        """Centra la ventana en la pantalla"""
        self.window.update_idletasks()
        width = 450
        height = 500
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        tk.Label(main_frame, text="Mitsy's POS", 
                font=('Segoe UI', 28, 'bold'),
                bg=COLORS['bg_primary'], fg=COLORS['accent']).pack(pady=(0, 10))
        
        tk.Label(main_frame, text="Sistema de Punto de Venta", 
                font=FONTS['normal'],
                bg=COLORS['bg_primary'], fg=COLORS['text_secondary']).pack(pady=(0, 40))
        
        # Usuario
        tk.Label(main_frame, text="Usuario:", font=FONTS['heading'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 5))
        
        self.username_var = tk.StringVar()
        username_entry = tk.Entry(main_frame, textvariable=self.username_var,
                                  font=('Segoe UI', 12), relief=tk.SOLID, borderwidth=1)
        username_entry.pack(fill=tk.X, pady=(0, 20), ipady=8)
        username_entry.focus()
        
        # Contraseña con botón de mostrar
        tk.Label(main_frame, text="Contraseña:", font=FONTS['heading'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 5))
        
        password_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        password_frame.pack(fill=tk.X, pady=(0, 30))
        
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(password_frame, textvariable=self.password_var,
                                  font=('Segoe UI', 12), show='●', relief=tk.SOLID, borderwidth=1)
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        
        # Botón mostrar/ocultar contraseña
        self.show_password_btn = tk.Button(password_frame, text="👁", 
                                           command=self.toggle_password,
                                           font=('Segoe UI', 12), width=3)
        self.show_password_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Bind Enter
        username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        self.password_entry.bind('<Return>', lambda e: self.do_login())
        
        # Botones
        login_btn = tk.Button(main_frame, text="Iniciar Sesión", command=self.do_login,
                             font=FONTS['button'], bg=COLORS['accent'], fg='white',
                             relief=tk.RAISED, borderwidth=2, cursor='hand2')
        login_btn.pack(fill=tk.X, pady=(0, 10), ipady=10)
        
        cancel_btn = tk.Button(main_frame, text="Cancelar", command=self.on_cancel,
                               font=FONTS['button'], bg=COLORS['button_bg'],
                               fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2)
        cancel_btn.pack(fill=tk.X, ipady=10)
    
    def toggle_password(self):
        """Muestra/oculta la contraseña"""
        self.show_password = not self.show_password
        if self.show_password:
            self.password_entry.config(show='')
            self.show_password_btn.config(text='🔒')
        else:
            self.password_entry.config(show='●')
            self.show_password_btn.config(text='👁')
    
    def do_login(self):
        """Realiza el inicio de sesión"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Por favor ingresa usuario y contraseña", parent=self.window)
            return
        
        from database import db
        user = db.authenticate_user(username, password)
        
        if user:
            if not user['activo']:
                messagebox.showerror("Error", "Este usuario está desactivado. Contacta al administrador.", parent=self.window)
                return
            
            session.login(user)
            
            timeout = db.get_config('session_timeout')
            if timeout:
                session.set_timeout(int(timeout))
            
            messagebox.showinfo("Bienvenido", f"Bienvenido, {user['nombre_completo'] or user['username']}", parent=self.window)
            
            self.window.destroy()
            
            if self.on_success:
                self.on_success()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos", parent=self.window)
            self.password_var.set("")
    
    def on_cancel(self):
        """Cancela el login"""
        if messagebox.askyesno("Cancelar", "¿Deseas cerrar la aplicación?", parent=self.window):
            self.window.destroy()
            import sys
            sys.exit(0)


class AdminAuthDialog:
    """Diálogo para autorización temporal de administrador - MEJORADO"""
    def __init__(self, parent, on_success=None, message="Esta acción requiere autorización de administrador"):
        self.on_success = on_success
        self.message = message
        self.show_password = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Autorización Requerida")
        self.dialog.geometry("450x550")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
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
        height = 550
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        tk.Label(main_frame, text="⚠", font=('Segoe UI', 48),
                bg=COLORS['bg_primary'], fg=COLORS['warning']).pack(pady=(0, 20))
        
        tk.Label(main_frame, text=self.message, 
                font=FONTS['normal'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary'], wraplength=350, justify='center').pack(pady=(0, 30))
        
        # Usuario Admin
        tk.Label(main_frame, text="Usuario Administrador:", font=FONTS['heading'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        
        self.username_var = tk.StringVar()
        username_entry = tk.Entry(main_frame, textvariable=self.username_var,
                                  font=FONTS['normal'])
        username_entry.pack(fill=tk.X, pady=(0, 15))
        username_entry.focus()
        
        # Contraseña con botón de mostrar
        tk.Label(main_frame, text="Contraseña:", font=FONTS['heading'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        
        password_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        password_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(password_frame, textvariable=self.password_var,
                                  font=FONTS['normal'], show='●')
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.show_password_btn = tk.Button(password_frame, text="👁", 
                                           command=self.toggle_password,
                                           font=FONTS['normal'], width=3)
        self.show_password_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Bind Enter
        username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        self.password_entry.bind('<Return>', lambda e: self.authorize())
        
        # Botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Autorizar", command=self.authorize,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def toggle_password(self):
        """Muestra/oculta la contraseña"""
        self.show_password = not self.show_password
        if self.show_password:
            self.password_entry.config(show='')
            self.show_password_btn.config(text='🔒')
        else:
            self.password_entry.config(show='●')
            self.show_password_btn.config(text='👁')
    
    def authorize(self):
        """Verifica las credenciales de administrador - CORREGIDO"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Por favor ingresa usuario y contraseña", parent=self.dialog)
            return
        
        from database import db
        user = db.authenticate_user(username, password)
        
        if user and user['nivel'] == 'admin' and user['activo']:
            messagebox.showinfo("Autorizado", "Autorización concedida", parent=self.dialog)
            
            db.add_auditoria(session.get_current_user()['id'], 'admin_auth', 
                           f"Autorización de admin por: {username}")
            
            self.dialog.destroy()
            
            # CORREGIDO: Llamar on_success SIN pasar admin_id
            if self.on_success:
                self.on_success()
        else:
            messagebox.showerror("Error", "Credenciales incorrectas o usuario sin permisos de administrador", parent=self.dialog)
            self.password_var.set("")
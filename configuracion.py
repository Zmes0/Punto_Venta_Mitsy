"""
Módulo de Configuración para Mitsy's POS - MEJORADO
"""
import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, FONTS
from utils import get_resource_path
from database import db
from auth import session

class ConfiguracionWindow:
    def __init__(self, parent, on_close=None):
        self.on_close_callback = on_close
        
        # La verificación de permisos de administrador se realiza en main.py (check_access)
        # antes de que esta ventana sea instanciada. Por lo tanto, no es necesario
        # repetir la verificación aquí.
        
        self.window = tk.Toplevel(parent)
        self.window.title("Configuración del Sistema - Mitsy's POS")
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.state('zoomed')
        self.window.minsize(900, 600)
        
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        try:
            self.window.iconbitmap(get_resource_path('icono.ico'))
        except:
            pass
        
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz con pestañas"""
        main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(main_frame, text="Configuración del Sistema", 
                              font=FONTS['title'], bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=(0, 20))
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.usuarios_frame = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(self.usuarios_frame, text="  Usuarios  ")
        self.setup_usuarios_tab()
        
        self.negocio_frame = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(self.negocio_frame, text="  Información del Negocio  ")
        self.setup_negocio_tab()
        
        self.database_frame = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(self.database_frame, text="  Base de Datos  ")
        self.setup_database_tab()
        
        tk.Button(main_frame, text="Regresar", command=self.close_window,
                 font=FONTS['button'], bg=COLORS['button_bg'],
                 fg=COLORS['text_primary'], relief=tk.RAISED,
                 borderwidth=2, padx=30, pady=10).pack()
    
    def setup_usuarios_tab(self):
        """Configura la pestaña de usuarios"""
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
        
        self.usuarios_tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.usuarios_tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        self.usuarios_tree.tag_configure('admin', background='#E3F2FD')
        self.usuarios_tree.tag_configure('inactivo', background='#FFEBEE')
        
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
        
        # NUEVO: Botón Activar/Desactivar
        tk.Button(button_frame, text="Activar/Desactivar", command=self.toggle_usuario,
                 font=FONTS['button'], bg=COLORS['warning'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        # NUEVO: Botón Eliminar Usuario
        tk.Button(button_frame, text="Eliminar Usuario", command=self.delete_usuario,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        self.load_usuarios()
    
    def setup_negocio_tab(self):
        """Configura la pestaña de información del negocio - ACTUALIZADO"""
        main_container = tk.Frame(self.negocio_frame, bg=COLORS['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        # Título
        tk.Label(main_container, text="Información del Negocio", 
                font=FONTS['subtitle'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=(0, 30))

        # Frame con scrollbar para todo el contenido
        canvas_frame = tk.Frame(main_container, bg=COLORS['bg_primary'])
        canvas_frame.pack(fill=tk.BOTH, expand=True)
    
        canvas = tk.Canvas(canvas_frame, bg=COLORS['bg_primary'], highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        content_scroll_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])
    
        content_scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
    
        canvas.create_window((0, 0), window=content_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
    
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        # Habilitar scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Frame principal con 2 columnas dentro del scroll
        content_frame = tk.Frame(content_scroll_frame, bg=COLORS['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        # COLUMNA IZQUIERDA
        left_column = tk.Frame(content_frame, bg=COLORS['bg_primary'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))

        # COLUMNA DERECHA
        right_column = tk.Frame(content_frame, bg=COLORS['bg_primary'])
        right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0))

        # Cargar datos actuales
        negocio_info = db.get_negocio_info()

        # ========== COLUMNA IZQUIERDA ==========

        # Nombre del Negocio
        tk.Label(left_column, text="Nombre del Negocio:", 
                font=FONTS['heading'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        self.name_var = tk.StringVar(value=negocio_info.get('name', '') if negocio_info else '')
        tk.Entry(left_column, textvariable=self.name_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 20))

        # Subtítulo
        tk.Label(left_column, text="Subtítulo:", 
                font=FONTS['heading'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        self.subtitle_var = tk.StringVar(value=negocio_info.get('subtitle', '') if negocio_info else '')
        tk.Entry(left_column, textvariable=self.subtitle_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 20))

        # Dirección
        tk.Label(left_column, text="Dirección:", 
                font=FONTS['heading'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        self.direccion_var = tk.StringVar(value=negocio_info.get('direccion', '') if negocio_info else '')
        tk.Entry(left_column, textvariable=self.direccion_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 20))

        # Ciudad
        tk.Label(left_column, text="Ciudad:", 
                font=FONTS['heading'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        self.ciudad_var = tk.StringVar(value=negocio_info.get('ciudad', '') if negocio_info else '')
        tk.Entry(left_column, textvariable=self.ciudad_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 20))

        # Teléfono
        tk.Label(left_column, text="Teléfono:", 
                font=FONTS['heading'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        self.telefono_var = tk.StringVar(value=negocio_info.get('telefono', '') if negocio_info else '')
        tk.Entry(left_column, textvariable=self.telefono_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 20))

        # ========== LÍNEAS EXTRA DEL HEADER ==========
        header_frame = tk.LabelFrame(left_column, text="Líneas Adicionales del Encabezado (Opcionales)", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2)
        header_frame.pack(fill=tk.X, pady=(0, 20), padx=5, ipady=10)

        tk.Label(header_frame, text="Se mostrarán debajo del teléfono:", 
                font=FONTS['small'], bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary']).pack(anchor='w', padx=10, pady=(5, 10))

        self.header_vars = []
        for i in range(1, 6):
            tk.Label(header_frame, text=f"Línea {i}:", 
                font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', padx=10, pady=(0, 5))
            var = tk.StringVar(value=negocio_info.get(f'header_linea{i}', '') if negocio_info else '')
            tk.Entry(header_frame, textvariable=var, 
                    font=FONTS['normal']).pack(fill=tk.X, padx=10, pady=(0, 10))
            self.header_vars.append(var)

        # ========== COLUMNA DERECHA ==========

        # ==== SECCIÓN DE LOGO ====
        logo_section = tk.LabelFrame(right_column, text="Logo del Negocio", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2)
        logo_section.pack(fill=tk.X, pady=(0, 20), padx=5, ipady=15)

        # Interruptor para mostrar/ocultar logo
        mostrar_logo_frame = tk.Frame(logo_section, bg=COLORS['bg_secondary'])
        mostrar_logo_frame.pack(pady=(10, 10), padx=10, fill=tk.X)

        tk.Label(mostrar_logo_frame, text="Mostrar logo en tickets:", 
                font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=(0, 10))

        self.mostrar_logo_var = tk.BooleanVar(value=negocio_info.get('mostrar_logo', 1) if negocio_info else 1)

        tk.Radiobutton(mostrar_logo_frame, text="Sí", variable=self.mostrar_logo_var,
                    value=True, font=FONTS['normal'],
                    bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mostrar_logo_frame, text="No", variable=self.mostrar_logo_var,
                    value=False, font=FONTS['normal'],
                    bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=5)

        # Preview del logo
        preview_frame = tk.Frame(logo_section, bg='white', relief=tk.SUNKEN, borderwidth=2)
        preview_frame.pack(pady=(10, 15), padx=10)

        self.logo_preview_label = tk.Label(preview_frame, text="Sin logo", 
                                        bg='white', fg='#999999',
                                        font=FONTS['small'], width=30, height=8)
        self.logo_preview_label.pack(padx=5, pady=5)

        # Cargar preview inicial
        self.logo_path_var = tk.StringVar(value=negocio_info.get('logo_path', 'images/logo_thermal.png') if negocio_info else 'images/logo_thermal.png')
        self.update_logo_preview()

        # Botón Preparar Logo
        tk.Button(logo_section, text="📁 Seleccionar y Preparar Logo", 
                command=self.preparar_logo_termico,
                font=FONTS['button'], bg=COLORS['accent'], fg='white',
                relief=tk.RAISED, borderwidth=2, padx=20, pady=12,
                cursor='hand2').pack(pady=(0, 10), padx=10)

        tk.Label(logo_section, text="Procesa tu imagen para impresora térmica (58mm)", 
                font=FONTS['small'], bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary']).pack(padx=10, pady=(0, 10))

        # Logo actual (ruta)
        tk.Label(logo_section, text="Ruta del archivo:", 
                font=FONTS['small'], bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary']).pack(anchor='w', padx=10, pady=(5, 2))
        tk.Entry(logo_section, textvariable=self.logo_path_var, 
                font=FONTS['small'], state='readonly',
                bg='#f0f0f0').pack(fill=tk.X, padx=10, pady=(0, 10))

        # Mensaje Final del Ticket
        mensaje_frame = tk.LabelFrame(right_column, text="Mensaje de Despedida", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2)
        mensaje_frame.pack(fill=tk.X, pady=(0, 20), padx=5, ipady=15)

        tk.Label(mensaje_frame, text="Cada campo es una línea en el ticket:", 
                font=FONTS['small'], bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary']).pack(anchor='w', padx=10, pady=(5, 10))

        # Dividir mensaje actual en líneas
        mensaje_actual = negocio_info.get('mensaje_final', '¡Gracias por su compra!\nVuelva pronto') if negocio_info else '¡Gracias por su compra!\nVuelva pronto'
        lineas = mensaje_actual.split('\n')

        # Línea 1
        tk.Label(mensaje_frame, text="Línea 1:", 
                font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', padx=10, pady=(0, 5))
        self.mensaje_linea1_var = tk.StringVar(value=lineas[0] if len(lineas) > 0 else '')
        tk.Entry(mensaje_frame, textvariable=self.mensaje_linea1_var, 
                font=FONTS['normal']).pack(fill=tk.X, padx=10, pady=(0, 15))

        # Línea 2
        tk.Label(mensaje_frame, text="Línea 2:", 
                font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', padx=10, pady=(0, 5))
        self.mensaje_linea2_var = tk.StringVar(value=lineas[1] if len(lineas) > 1 else '')
        tk.Entry(mensaje_frame, textvariable=self.mensaje_linea2_var, 
                font=FONTS['normal']).pack(fill=tk.X, padx=10, pady=(0, 15))

        # Línea 3 (opcional)
        tk.Label(mensaje_frame, text="Línea 3 (opcional):", 
                font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', padx=10, pady=(0, 5))
        self.mensaje_linea3_var = tk.StringVar(value=lineas[2] if len(lineas) > 2 else '')
        tk.Entry(mensaje_frame, textvariable=self.mensaje_linea3_var, 
                font=FONTS['normal']).pack(fill=tk.X, padx=10, pady=(0, 10))

        # ========== LÍNEAS EXTRA DEL FOOTER ==========
        footer_frame = tk.LabelFrame(right_column, text="Líneas Adicionales del Pie (Opcionales)", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2)
        footer_frame.pack(fill=tk.X, pady=(0, 20), padx=5, ipady=10)

        tk.Label(footer_frame, text="Se mostrarán después del mensaje de despedida:", 
                font=FONTS['small'], bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary']).pack(anchor='w', padx=10, pady=(5, 10))

        self.footer_vars = []
        for i in range(1, 6):
            tk.Label(footer_frame, text=f"Línea {i}:", 
                    font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', padx=10, pady=(0, 5))
            var = tk.StringVar(value=negocio_info.get(f'footer_linea{i}', '') if negocio_info else '')
            tk.Entry(footer_frame, textvariable=var, 
                    font=FONTS['normal']).pack(fill=tk.X, padx=10, pady=(0, 10))
            self.footer_vars.append(var)

        # Interruptor para mostrar total en letras
        total_letras_frame = tk.Frame(right_column, bg=COLORS['bg_secondary'], 
                                    relief=tk.RAISED, borderwidth=2)
        total_letras_frame.pack(fill=tk.X, pady=(0, 20), padx=5)

        tk.Label(total_letras_frame, text="Mostrar total en letras:", 
                font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=15, pady=15)

        self.mostrar_total_letras_var = tk.BooleanVar(value=negocio_info.get('mostrar_total_letras', 1) if negocio_info else 1)

        tk.Radiobutton(total_letras_frame, text="Sí", variable=self.mostrar_total_letras_var,
                    value=True, font=FONTS['normal'],
                    bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(total_letras_frame, text="No", variable=self.mostrar_total_letras_var,
                    value=False, font=FONTS['normal'],
                    bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=5)

        # ========== BOTÓN GUARDAR (CENTRADO ABAJO) ==========
        button_frame = tk.Frame(main_container, bg=COLORS['bg_primary'])
        button_frame.pack(pady=(20, 0))

        tk.Button(button_frame, text="💾 Guardar Cambios", 
                command=self.guardar_negocio_info,
                font=FONTS['button'], bg=COLORS['success'], fg='white',
                relief=tk.RAISED, borderwidth=2, padx=50, pady=15,
                cursor='hand2').pack()
    
    def setup_database_tab(self):
        """Configura la pestaña de base de datos"""
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
        
        # CORREGIDO: Verificar que hay un usuario activo antes de registrar auditoría
        current_user = session.get_current_user()
        if current_user:
            db.add_auditoria(current_user['id'], 'config_auth', 
                        f"Sistema de autenticación {'activado' if enabled else 'desactivado'}")
        
        db.add_auditoria(session.get_current_user()['id'], 'config_auth', 
                       f"Sistema de autenticación {'activado' if enabled else 'desactivado'}")
    
    def update_timeout(self):
        """Actualiza el timeout de sesión"""
        timeout = self.timeout_var.get()
        db.set_config('session_timeout', str(timeout))
        session.set_timeout(timeout)
        
        # CORREGIDO: Verificar que hay un usuario activo antes de registrar auditoría
        current_user = session.get_current_user()
        if current_user:
            db.add_auditoria(current_user['id'], 'config_timeout', 
                   f"Timeout de sesión actualizado a {timeout} minutos")
        
        db.add_auditoria(session.get_current_user()['id'], 'config_timeout', 
                       f"Timeout de sesión actualizado a {timeout} minutos")
    
    def load_usuarios(self):
        """Carga los usuarios en la tabla"""
        for item in self.usuarios_tree.get_children():
            self.usuarios_tree.delete(item)
        
        usuarios = db.get_usuarios()
        
        for idx, u in enumerate(usuarios):
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
        """Añade un nuevo usuario"""
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
    
    def toggle_usuario(self):
        """Activa/Desactiva el usuario seleccionado - NUEVO"""
        selection = self.usuarios_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un usuario")
            return
        
        item = self.usuarios_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        estado_actual = item['values'][4]
        
        # No permitir desactivar al usuario actual
        if user_id == session.get_current_user()['id']:
            messagebox.showerror("Error", "No puedes cambiar el estado de tu propio usuario")
            return
        
        # Si está activo, verificar que no sea el único admin
        if estado_actual == 'Activo' and username == 'mitsy':
            db.cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE nivel = 'admin' AND activo = 1")
            count = db.cursor.fetchone()['count']
            
            if count <= 1:
                messagebox.showerror("Error", "No puedes desactivar el único administrador del sistema")
                return
        
        # Toggle estado
        nuevo_estado = 0 if estado_actual == 'Activo' else 1
        accion = "desactivado" if nuevo_estado == 0 else "activado"
        
        if messagebox.askyesno("Confirmar", f"¿Deseas {accion.replace('do', 'r')} al usuario '{username}'?"):
            db.update_usuario(user_id, activo=nuevo_estado)
            db.add_auditoria(session.get_current_user()['id'], 'user_toggle', 
                           f"Usuario {accion}: {username}")
            
            messagebox.showinfo("Éxito", f"Usuario {accion} correctamente")
            self.load_usuarios()
    
    def delete_usuario(self):
        """Elimina permanentemente un usuario - NUEVO"""
        selection = self.usuarios_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un usuario")
            return
        
        item = self.usuarios_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        # No permitir eliminar al usuario actual
        if user_id == session.get_current_user()['id']:
            messagebox.showerror("Error", "No puedes eliminar tu propio usuario")
            return
        
        # No permitir eliminar a 'mitsy' si es el único admin
        if username == 'mitsy':
            db.cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE nivel = 'admin' AND activo = 1")
            count = db.cursor.fetchone()['count']
            
            if count <= 1:
                messagebox.showerror("Error", "No puedes eliminar el único administrador del sistema")
                return
        
        if messagebox.askyesno("Confirmar Eliminación", 
                              f"¿Estás seguro de ELIMINAR PERMANENTEMENTE al usuario '{username}'?\n\n"
                              "Esta acción NO se puede deshacer.\n\n"
                              "Si solo deseas desactivar temporalmente el usuario, usa el botón 'Activar/Desactivar'."):
            try:
                # Eliminar físicamente de la base de datos
                db.cursor.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
                db.conn.commit()
                
                db.add_auditoria(session.get_current_user()['id'], 'user_delete', 
                               f"Usuario eliminado permanentemente: {username}")
                
                messagebox.showinfo("Éxito", "Usuario eliminado permanentemente")
                self.load_usuarios()
            except Exception as e:
                messagebox.showerror("Error", f"Error al eliminar usuario: {str(e)}")
    
    def preparar_logo_termico(self):
        """Procesa una imagen para convertirla en logo apto para impresora térmica"""
        from tkinter import filedialog
        from PIL import Image
        import os
    
        # Abrir selector de archivo
        filename = filedialog.askopenfilename(
            title="Seleccionar imagen para procesar",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("Todos los archivos", "*.*")
            ]
        )
    
        if not filename:
            return
    
        try:
            # Configuración
            target_width = 300  # Ancho ideal para 58mm
            output_path = get_resource_path('images/logo_thermal.png')
        
            # Crear carpeta si no existe
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
            # 1. Abrir imagen
            img = Image.open(filename)
        
            # 2. Convertir a escala de grises
            img = img.convert('L')
        
            # 3. Redimensionar manteniendo proporciones
            width_percent = (target_width / float(img.size[0]))
            height_size = int((float(img.size[1]) * float(width_percent)))
            img = img.resize((target_width, height_size), Image.LANCZOS)
        
            # 4. Convertir a BLANCO Y NEGRO PURO
            img = img.point(lambda x: 0 if x < 128 else 255, '1')
        
            # 5. Guardar
            img.save(output_path)
        
            # Actualizar campo y preview
            self.logo_path_var.set('images/logo_thermal.png')
            self.update_logo_preview()
        
            messagebox.showinfo("Éxito", 
                            f"Logo procesado correctamente.\n\n"
                            f"Guardado en: {output_path}\n\n"
                            f"Recuerda hacer clic en 'Guardar Cambios' para aplicarlo.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al procesar la imagen: {str(e)}")

    def update_logo_preview(self):
        """Actualiza la previsualización del logo"""
        import os
        from PIL import Image
        try:
            from PIL import ImageTk
            logo_path = get_resource_path(self.logo_path_var.get())
        
            if os.path.exists(logo_path):
                
                # Cargar imagen
                img = Image.open(logo_path)
            
                # Redimensionar para preview (máximo 200x150)
                img.thumbnail((200, 150), Image.LANCZOS)
            
                # Convertir a PhotoImage
                photo = ImageTk.PhotoImage(img)
            
                # Actualizar label
                self.logo_preview_label.config(image=photo, text="")
                self.logo_preview_label.image = photo  # Mantener referencia
            else:
                self.logo_preview_label.config(image="", text="Logo no encontrado")
            
        except Exception as e:
            self.logo_preview_label.config(image="", text="Error al cargar logo")
            print(f"Error al cargar preview: {e}")
            
    
    
    def guardar_negocio_info(self):
        """Guarda la información del negocio"""
        try:
            # Construir mensaje final juntando las líneas
            mensaje_lineas = []
            if self.mensaje_linea1_var.get().strip():
                mensaje_lineas.append(self.mensaje_linea1_var.get().strip())
            if self.mensaje_linea2_var.get().strip():
                mensaje_lineas.append(self.mensaje_linea2_var.get().strip())
            if self.mensaje_linea3_var.get().strip():
                mensaje_lineas.append(self.mensaje_linea3_var.get().strip())
        
            mensaje_final = '\n'.join(mensaje_lineas)
        
            db.update_negocio_info(
                name=self.name_var.get().strip(),
                subtitle=self.subtitle_var.get().strip(),
                direccion=self.direccion_var.get().strip(),
                ciudad=self.ciudad_var.get().strip(),
                telefono=self.telefono_var.get().strip(),
                mensaje_final=mensaje_final,
                logo_path=self.logo_path_var.get().strip()
            )
        
            # Verificar que hay un usuario activo antes de registrar auditoría
            current_user = session.get_current_user()
            if current_user:
                db.add_auditoria(current_user['id'], 'config_negocio', 
                           'Información del negocio actualizada')
        
            messagebox.showinfo("Éxito", "Información del negocio actualizada correctamente.\n\n"
                            "Los cambios se aplicarán en los próximos tickets generados.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    
    def close_window(self):
        """Cierra la ventana"""
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()
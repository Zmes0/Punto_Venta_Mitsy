"""
Módulo de Configuración para Mitsy's POS - MEJORADO
"""
import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, FONTS
from utils import get_resource_path
from database import db
from auth import session, AdminAuthDialog

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
        
        self.audit_frame = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(self.audit_frame, text="  Auditoría  ")
        self.setup_audit_tab()
        
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
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Título
        tk.Label(main_container, text="Información del Negocio y Tickets", 
                font=FONTS['title'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=(0, 20))

        # Frame con scrollbar para todo el contenido
        canvas = tk.Canvas(main_container, bg=COLORS['bg_primary'], highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        content_scroll_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])
    
        canvas_window = canvas.create_window((0, 0), window=content_scroll_frame, anchor="nw")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        content_scroll_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
    
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        # Habilitar scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Frame principal con 2 columnas dentro del scroll
        content_frame = tk.Frame(content_scroll_frame, bg=COLORS['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        # Cargar datos actuales
        negocio_info = db.get_negocio_info()

        # --- COLUMNA IZQUIERDA ---
        left_column = tk.Frame(content_frame, bg=COLORS['bg_primary'])
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        # Datos Generales
        datos_frame = tk.LabelFrame(left_column, text="Datos Generales", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2,
                                    padx=15, pady=15)
        datos_frame.pack(fill=tk.X, expand=True)

        self.name_var = tk.StringVar(value=negocio_info.get('name', '') if negocio_info else '')
        self.subtitle_var = tk.StringVar(value=negocio_info.get('subtitle', '') if negocio_info else '')
        self.direccion_var = tk.StringVar(value=negocio_info.get('direccion', '') if negocio_info else '')
        self.ciudad_var = tk.StringVar(value=negocio_info.get('ciudad', '') if negocio_info else '')
        self.telefono_var = tk.StringVar(value=negocio_info.get('telefono', '') if negocio_info else '')

        fields = {
            "Nombre del Negocio:": self.name_var,
            "Subtítulo:": self.subtitle_var,
            "Dirección:": self.direccion_var,
            "Ciudad:": self.ciudad_var,
            "Teléfono:": self.telefono_var
        }
        for label, var in fields.items():
            tk.Label(datos_frame, text=label, font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', pady=(5, 2))
            tk.Entry(datos_frame, textvariable=var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))

        # Líneas Adicionales del Encabezado
        header_frame = tk.LabelFrame(left_column, text="Líneas Adicionales del Encabezado", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2,
                                    padx=15, pady=15)
        header_frame.pack(fill=tk.X, expand=True, pady=(20, 0))

        self.header_vars = []
        for i in range(1, 6):
            tk.Label(header_frame, text=f"Línea {i} (opcional):", font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', pady=(5, 2))
            var = tk.StringVar(value=negocio_info.get(f'header_linea{i}', '') if negocio_info else '')
            tk.Entry(header_frame, textvariable=var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
            self.header_vars.append(var)

        # --- COLUMNA DERECHA ---
        right_column = tk.Frame(content_frame, bg=COLORS['bg_primary'])
        right_column.grid(row=0, column=1, sticky="nsew", padx=(20, 0))

        # Logo del Ticket
        logo_section = tk.LabelFrame(right_column, text="Logo del Ticket", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2,
                                    padx=15, pady=15)
        logo_section.pack(fill=tk.X, expand=True)

        # Preview del logo
        preview_frame = tk.Frame(logo_section, bg='white', relief=tk.SUNKEN, borderwidth=2, width=220, height=170)
        preview_frame.pack(pady=(10, 15), anchor='center')
        preview_frame.pack_propagate(False)

        self.logo_preview_label = tk.Label(preview_frame, text="Sin logo", bg='white', fg='#999999', font=FONTS['small'])
        self.logo_preview_label.pack(expand=True)

        self.logo_path_var = tk.StringVar(value=negocio_info.get('logo_path', 'images/logo_thermal.png') if negocio_info else 'images/logo_thermal.png')
        self.update_logo_preview()

        tk.Button(logo_section, text="📁 Seleccionar y Preparar Logo", 
                command=self.preparar_logo_termico,
                font=FONTS['button'], bg=COLORS['accent'], fg='white',
                relief=tk.RAISED, borderwidth=2, cursor='hand2').pack(pady=(0, 10), fill=tk.X)

        self.mostrar_logo_var = tk.BooleanVar(value=negocio_info.get('mostrar_logo', 1) if negocio_info else 1)
        tk.Checkbutton(logo_section, text="Mostrar logo en tickets", variable=self.mostrar_logo_var,
                       font=FONTS['normal'], bg=COLORS['bg_secondary'], selectcolor=COLORS['bg_primary']).pack(anchor='center', pady=5)

        # Mensaje de Despedida y Pie de Página
        footer_section = tk.LabelFrame(right_column, text="Mensaje y Pie de Ticket", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2,
                                    padx=15, pady=15)
        footer_section.pack(fill=tk.X, expand=True, pady=(20, 0))

        mensaje_actual = negocio_info.get('mensaje_final', '¡Gracias por su compra!\nVuelva pronto') if negocio_info else '¡Gracias por su compra!\nVuelva pronto'
        lineas = mensaje_actual.split('\n')

        tk.Label(footer_section, text="Mensaje de Despedida (Línea 1):", font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', pady=(5, 2))
        self.mensaje_linea1_var = tk.StringVar(value=lineas[0] if len(lineas) > 0 else '')
        tk.Entry(footer_section, textvariable=self.mensaje_linea1_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))

        tk.Label(footer_section, text="Mensaje de Despedida (Línea 2):", font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', pady=(5, 2))
        self.mensaje_linea2_var = tk.StringVar(value=lineas[1] if len(lineas) > 1 else '')
        tk.Entry(footer_section, textvariable=self.mensaje_linea2_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))

        self.footer_vars = []
        for i in range(1, 6):
            tk.Label(footer_section, text=f"Línea Pie {i} (opcional):", font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(anchor='w', pady=(5, 2))
            var = tk.StringVar(value=negocio_info.get(f'footer_linea{i}', '') if negocio_info else '')
            tk.Entry(footer_section, textvariable=var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
            self.footer_vars.append(var)

        # Opciones Adicionales
        opciones_frame = tk.LabelFrame(right_column, text="Opciones Adicionales", 
                                    font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                    fg=COLORS['text_primary'], relief=tk.RAISED, borderwidth=2,
                                    padx=15, pady=15)
        opciones_frame.pack(fill=tk.X, expand=True, pady=(20, 0))

        self.mostrar_total_letras_var = tk.BooleanVar(value=negocio_info.get('mostrar_total_letras', 1) if negocio_info else 1)
        tk.Checkbutton(opciones_frame, text="Mostrar total en letras en ticket", variable=self.mostrar_total_letras_var,
                       font=FONTS['normal'], bg=COLORS['bg_secondary'], selectcolor=COLORS['bg_primary']).pack(anchor='w')

        # Botón Guardar
        button_frame = tk.Frame(content_scroll_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=(30, 10))

        tk.Button(button_frame, text="💾 Guardar Cambios", 
                command=self.guardar_negocio_info,
                font=FONTS['button'], bg=COLORS['success'], fg='white',
                relief=tk.RAISED, borderwidth=2, padx=50, pady=15,
                cursor='hand2').pack()
    
    def setup_database_tab(self):
        """Configura la pestaña de base de datos con un diseño más compacto y estético."""
        main_container = tk.Frame(self.database_frame, bg=COLORS['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(main_container, text="Opciones de Base de Datos", 
                font=FONTS['title'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=(0, 20))

        # Frame para contener las "tarjetas" de opciones en un grid
        options_grid_frame = tk.Frame(main_container, bg=COLORS['bg_primary'])
        options_grid_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Configurar columnas para el grid
        options_grid_frame.grid_columnconfigure(0, weight=1)
        options_grid_frame.grid_columnconfigure(1, weight=1)
        options_grid_frame.grid_rowconfigure(0, weight=1)
        options_grid_frame.grid_rowconfigure(1, weight=1)

        # --- Tarjeta de Copia de Seguridad ---
        self._create_db_option_card(
            parent=options_grid_frame,
            row=0, column=0,
            title="Copia de Seguridad",
            description="Crea una copia de la base de datos actual, selecciona una ubicación y guarda el archivo.",
            button_text="💾 Crear Copia de Seguridad",
            button_command=self.backup_database,
            button_color=COLORS['success']
        )

        # --- Tarjeta de Restaurar Checkpoint ---
        self._create_db_option_card(
            parent=options_grid_frame,
            row=0, column=1,
            title="Restaurar Checkpoint",
            description="Regresa la base de datos a un estado anterior (Se realiza un respaldo automáticamente al final de cada corte).",
            button_text="↩️ Restaurar Checkpoint",
            button_command=self.open_restore_checkpoint_dialog,
            button_color=COLORS['accent']
        )

        # --- Tarjeta de Reemplazar Base de Datos ---
        self._create_db_option_card(
            parent=options_grid_frame,
            row=1, column=0,
            title="Reemplazar Base de Datos",
            description="Sustituye la base de datos actual por un archivo .db seleccionado.",
            button_text="📂 Reemplazar Base de Datos",
            button_command=self.confirm_replace_database,
            button_color=COLORS['warning']
        )

        # --- Tarjeta de Borrar Base de Datos ---
        self._create_db_option_card(
            parent=options_grid_frame,
            row=1, column=1,
            title="Borrar Base de Datos",
            description="Elimina PERMANENTEMENTE todos los datos y reinicia el sistema.",
            button_text="🚨 Borrar Base de Datos Completa 🚨",
            button_command=self.confirm_delete_database,
            button_color=COLORS['danger']
        )

    def _create_db_option_card(self, parent, row, column, title, description, button_text, button_command, button_color):
        """Crea una tarjeta de opción para la pestaña de base de datos."""
        card_frame = tk.Frame(parent, bg=COLORS['bg_secondary'], relief=tk.RAISED, borderwidth=2)
        card_frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
        
        # Título de la tarjeta
        tk.Label(card_frame, text=title, font=FONTS['heading'], bg=COLORS['bg_secondary'],
                 fg=COLORS['text_primary']).pack(pady=(10, 5))
        
        # Descripción
        tk.Label(card_frame, text=description, font=FONTS['normal'], bg=COLORS['bg_secondary'],
                 fg=COLORS['text_primary'], wraplength=250, justify='center').pack(padx=10, pady=(0, 10))
        
        # Botón
        tk.Button(card_frame, text=button_text, command=button_command,
                 font=FONTS['button'], bg=button_color, fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=10,
                 cursor='hand2').pack(pady=(0, 15))
    
    def backup_database(self):
        """Crea una copia de seguridad de la base de datos en una ubicación seleccionada por el usuario."""
        from datetime import datetime
        from tkinter import filedialog

        try:
            # Sugerir un nombre de archivo para el backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f"mitsys_backup_{timestamp}.db"

            # Abrir diálogo para guardar archivo
            backup_path = filedialog.asksaveasfilename(
                title="Guardar copia de seguridad de la base de datos",
                initialfile=default_filename,
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                parent=self.window
            )

            if not backup_path:
                # El usuario canceló el diálogo
                return

            # Usar el método seguro de la clase Database
            db.backup_database_file(backup_path)

            messagebox.showinfo("Copia de Seguridad Exitosa",
                                f"La copia de seguridad se ha guardado correctamente en:\n{backup_path}",
                                parent=self.window)

            # Registrar en auditoría
            current_user = session.get_current_user()
            actor_id = current_user['id'] if current_user else None
            db.add_auditoria(actor_id, 'db_backup', f"Copia de seguridad creada en: {backup_path}")

        except Exception as e:
            messagebox.showerror("Error en Copia de Seguridad",
                                 f"Ocurrió un error al crear la copia de seguridad:\n{e}",
                                 parent=self.window)

    def confirm_replace_database(self):
        """Pide autorización de admin para reemplazar la base de datos."""
        AdminAuthDialog(self.window, on_success=self.perform_replace_database,
                        message="Se requiere autorización de administrador para REEMPLAZAR la base de datos.")

    def perform_replace_database(self):
        """Abre el explorador para seleccionar una BD y la reemplaza."""
        import os
        import shutil
        from tkinter import filedialog
        from utils import restart_application

        # Advertencia final
        if not messagebox.askyesno("Confirmación Final",
                                   "Estás a punto de REEMPLAZAR la base de datos actual.\n\n"
                                   "TODOS LOS DATOS ACTUALES SE PERDERÁN y serán sustituidos por los del archivo que selecciones.\n\n"
                                   "Esta acción NO se puede deshacer.\n\n"
                                   "¿Deseas continuar?",
                                   parent=self.window):
            return

        try:
            # Abrir diálogo para seleccionar archivo
            new_db_path = filedialog.askopenfilename(
                title="Seleccionar la nueva base de datos",
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                parent=self.window
            )

            if not new_db_path:
                return

            # Cerrar la conexión a la BD
            db.close()

            # Eliminar archivos WAL y SHM si existen para evitar corrupción
            wal_path = db.db_path + '-wal'
            shm_path = db.db_path + '-shm'
            if os.path.exists(wal_path):
                try: os.remove(wal_path)
                except: pass
            if os.path.exists(shm_path):
                try: os.remove(shm_path)
                except: pass

            # Reemplazar el archivo de la base de datos
            shutil.copy2(new_db_path, db.db_path)

            messagebox.showinfo("Base de Datos Reemplazada",
                                "La base de datos ha sido reemplazada exitosamente.\n\n"
                                "La aplicación se reiniciará para aplicar los cambios.",
                                parent=self.window)
            
            restart_application()

        except Exception as e:
            messagebox.showerror("Error al Reemplazar",
                                 f"Ocurrió un error al reemplazar la base de datos:\n{e}",
                                 parent=self.window)
            # Asegurarse de que la conexión se reabra si hay un error y no se reinicia
            if not db.conn:
                db.connect()

    def confirm_delete_database(self):
        """Pide confirmación y luego autorización de admin para borrar la base de datos."""
        if messagebox.askyesno("Confirmar Eliminación de Base de Datos",
                               "Estás a punto de eliminar PERMANENTEMENTE toda la información del sistema.\n\n"
                               "Esta acción NO se puede deshacer.\n\n"
                               "¿Estás ABSOLUTAMENTE seguro de que deseas continuar?",
                               parent=self.window):
            # Si el usuario confirma, pedir autorización de administrador
            AdminAuthDialog(self.window, on_success=self.perform_delete_database,
                            message="Se requiere autorización de administrador para ELIMINAR la base de datos completa.")

    def perform_delete_database(self):
        """Ejecuta la eliminación y recreación de la base de datos y reinicia la aplicación."""
        try:
            db.recreate_database()
            messagebox.showinfo("Base de Datos Eliminada",
                                "La base de datos ha sido eliminada y recreada exitosamente.\n\n"
                                "La aplicación se reiniciará para aplicar los cambios.",
                                parent=self.window)
            from utils import restart_application
            restart_application()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al intentar borrar y recrear la base de datos: {e}",
                                parent=self.window)
    
    def open_restore_checkpoint_dialog(self):
        """Abre el diálogo para restaurar un checkpoint."""
        RestoreCheckpointDialog(self.window)
    
    def toggle_auth_system(self, *args):
        """Activa/desactiva el sistema de autenticación con confirmación de admin."""
        enabled = self.auth_enabled_var.get()

        # Si se está intentando desactivar, se requiere autorización de admin
        if not enabled:
            # Desvincular temporalmente el trace para evitar recursión
            trace_id = self.auth_enabled_var.trace_info()[0][1]
            self.auth_enabled_var.trace_vdelete('w', trace_id)

            auth_successful = [False]

            def on_auth_success():
                auth_successful[0] = True

            # Crear y esperar al diálogo de autorización
            auth_dialog = AdminAuthDialog(self.window, on_success=on_auth_success, 
                                          message="Se requiere autorización de administrador para desactivar el sistema de autenticación.")
            self.window.wait_window(auth_dialog.dialog)

            # Después de que el diálogo se cierra, verificar si la auth fue exitosa
            if auth_successful[0]:
                db.toggle_auth_system(False)
                messagebox.showinfo("Sistema de Autenticación", 
                                  "Sistema de autenticación desactivado.\n\n" 
                                  "No se solicitará inicio de sesión al abrir la aplicación.")
                current_user = session.get_current_user()
                if current_user:
                    db.add_auditoria(current_user['id'], 'config_auth', 
                                'Sistema de autenticación desactivado')
            else:
                # Si la autenticación falla o se cancela, revertir el botón
                self.auth_enabled_var.set(True)

            # Volver a vincular el trace
            self.auth_enabled_var.trace('w', self.toggle_auth_system)

        else:  # Si se está activando, no se requiere auth extra
            db.toggle_auth_system(True)
            messagebox.showinfo("Sistema de Autenticación", 
                              "Sistema de autenticación activado.\n\n" 
                              "Los usuarios deberán iniciar sesión al abrir la aplicación.")
            current_user = session.get_current_user()
            if current_user:
                db.add_auditoria(current_user['id'], 'config_auth', 
                            'Sistema de autenticación activado')
    
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
        """Activa/Desactiva el usuario seleccionado - CORREGIDO"""
        selection = self.usuarios_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un usuario", parent=self.window)
            return
        
        item = self.usuarios_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        estado_actual = item['values'][4]
        
        # No permitir desactivar al usuario actual
        current_user = session.get_current_user()
        if current_user and user_id == current_user['id']:
            messagebox.showerror("Error", "No puedes cambiar el estado de tu propio usuario", parent=self.window)
            return
        
        # Si está activo, verificar que no sea el único admin
        if estado_actual == 'Activo':
            # Obtener el nivel del usuario a desactivar
            user_to_toggle = db.get_usuario(user_id)
            if user_to_toggle and user_to_toggle['nivel'] == 'admin':
                db.cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE nivel = 'admin' AND activo = 1")
                count = db.cursor.fetchone()['count']
                
                if count <= 1:
                    messagebox.showerror("Error", "No puedes desactivar el único administrador activo del sistema", parent=self.window)
                    return
        
        # Toggle estado
        nuevo_estado = 0 if estado_actual == 'Activo' else 1
        accion = "desactivado" if nuevo_estado == 0 else "activado"
        
        if messagebox.askyesno("Confirmar", f"¿Deseas {accion.replace('do', 'r')} al usuario '{username}'?", parent=self.window):
            db.update_usuario(user_id, activo=nuevo_estado)
            
            actor_id = current_user['id'] if current_user else None
            db.add_auditoria(actor_id, 'user_toggle', 
                           f"Usuario {accion}: {username} (ID: {user_id})")
            
            messagebox.showinfo("Éxito", f"Usuario {accion} correctamente", parent=self.window)
            self.load_usuarios()
    
    def delete_usuario(self):
        """Elimina permanentemente un usuario - CORREGIDO"""
        selection = self.usuarios_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un usuario", parent=self.window)
            return
        
        item = self.usuarios_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        # No permitir eliminar al usuario actual
        current_user = session.get_current_user()
        if current_user and user_id == current_user['id']:
            messagebox.showerror("Error", "No puedes eliminar tu propio usuario", parent=self.window)
            return
        
        # No permitir eliminar a 'mitsy' si es el único admin
        if username == 'mitsy':
            db.cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE nivel = 'admin' AND activo = 1")
            count = db.cursor.fetchone()['count']
            
            if count <= 1:
                messagebox.showerror("Error", "No puedes eliminar el único administrador del sistema", parent=self.window)
                return
        
        if messagebox.askyesno("Confirmar Eliminación", 
                              f"¿Estás seguro de ELIMINAR PERMANENTEMENTE al usuario '{username}'?\n\n"
                              "Esta acción NO se puede deshacer.\n\n"
                              "Si solo deseas desactivar temporalmente el usuario, usa el botón 'Activar/Desactivar'.",
                              parent=self.window):
            try:
                # Eliminar físicamente de la base de datos
                db.cursor.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
                db.conn.commit()
                
                actor_id = current_user['id'] if current_user else None
                db.add_auditoria(actor_id, 'user_delete', 
                               f"Usuario eliminado permanentemente: {username} (ID: {user_id})")
                
                messagebox.showinfo("Éxito", "Usuario eliminado permanentemente", parent=self.window)
                self.load_usuarios()
            except Exception as e:
                messagebox.showerror("Error", f"Error al eliminar usuario: {str(e)}", parent=self.window)
    
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
        
            mensaje_final = '\n'.join(mensaje_lineas)

            data_to_save = {
                'name': self.name_var.get().strip(),
                'subtitle': self.subtitle_var.get().strip(),
                'direccion': self.direccion_var.get().strip(),
                'ciudad': self.ciudad_var.get().strip(),
                'telefono': self.telefono_var.get().strip(),
                'mensaje_final': mensaje_final,
                'logo_path': self.logo_path_var.get().strip(),
                'mostrar_logo': 1 if self.mostrar_logo_var.get() else 0,
                'mostrar_total_letras': 1 if self.mostrar_total_letras_var.get() else 0
            }

            # Añadir líneas extra de header y footer
            for i, var in enumerate(self.header_vars, 1):
                data_to_save[f'header_linea{i}'] = var.get().strip()
            
            for i, var in enumerate(self.footer_vars, 1):
                data_to_save[f'footer_linea{i}'] = var.get().strip()

            db.update_negocio_info(**data_to_save)
        
            # Verificar que hay un usuario activo antes de registrar auditoría
            current_user = session.get_current_user()
            if current_user:
                db.add_auditoria(current_user['id'], 'config_negocio', 
                           'Información del negocio actualizada')
        
            messagebox.showinfo("Éxito", "Información del negocio actualizada correctamente.\n\n" 
                            "Los cambios se aplicarán en los próximos tickets generados.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    
    def setup_audit_tab(self):
        """Configura la pestaña de auditoría"""
        main_audit_frame = tk.Frame(self.audit_frame, bg=COLORS['bg_primary'])
        main_audit_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(main_audit_frame, text="Registro de Auditoría del Sistema", 
                 font=FONTS['subtitle'], bg=COLORS['bg_primary'],
                 fg=COLORS['text_primary']).pack(pady=(0, 20))

        controls_frame = tk.Frame(main_audit_frame, bg=COLORS['bg_primary'])
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(controls_frame, text="Recargar Registros", command=self.load_audit_logs,
                  font=FONTS['button'], bg=COLORS['button_bg'],
                  fg=COLORS['text_primary']).pack(side=tk.LEFT)

        table_frame = tk.Frame(main_audit_frame, bg=COLORS['bg_primary'])
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ('ID', 'Fecha', 'Usuario', 'Acción', 'Detalle')
        
        self.audit_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                       yscrollcommand=scrollbar.set, selectmode='browse')
        
        self.audit_tree.heading('ID', text='ID')
        self.audit_tree.heading('Fecha', text='Fecha y Hora')
        self.audit_tree.heading('Usuario', text='Usuario')
        self.audit_tree.heading('Acción', text='Acción')
        self.audit_tree.heading('Detalle', text='Detalle')
        
        self.audit_tree.column('ID', width=60, anchor='center')
        self.audit_tree.column('Fecha', width=180, anchor='center')
        self.audit_tree.column('Usuario', width=150)
        self.audit_tree.column('Acción', width=150)
        self.audit_tree.column('Detalle', width=400)
        
        self.audit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.audit_tree.yview)
        
        self.audit_tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.audit_tree.tag_configure('oddrow', background=COLORS['table_row_odd'])

        self.load_audit_logs()

    def load_audit_logs(self):
        """Carga los registros de auditoría en la tabla"""
        for item in self.audit_tree.get_children():
            self.audit_tree.delete(item)
        
        logs = db.get_auditoria(limit=200) 
        
        for idx, log in enumerate(logs):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            values = (
                log['id'],
                log['fecha'],
                log['username'],
                log['accion'],
                log['detalle'] or ''
            )
            
            self.audit_tree.insert('', tk.END, values=values, tags=(tag,))

    def close_window(self):
        """Cierra la ventana"""
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()

class RestoreCheckpointDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Restaurar Base de Datos desde Checkpoint")
        self.dialog.geometry("800x500")
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
        self.load_checkpoints()
    
    def center_dialog(self):
        self.dialog.update_idletasks()
        width = 800
        height = 500
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="Selecciona un Checkpoint para Restaurar", 
                font=FONTS['title'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=(0, 20))
        
        tk.Label(main_frame, text="¡ADVERTENCIA! Restaurar un checkpoint reemplazará la base de datos actual con la versión seleccionada. Se perderán todos los cambios posteriores al checkpoint.",
                font=FONTS['normal'], bg=COLORS['bg_primary'], fg=COLORS['danger'], wraplength=700, justify='center').pack(pady=(0, 10))
        
        table_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ('Nombre', 'Fecha', 'Hora', 'Corte')
        self.checkpoints_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                             yscrollcommand=scrollbar.set, selectmode='browse')
        
        self.checkpoints_tree.heading('Nombre', text='Nombre del Archivo')
        self.checkpoints_tree.heading('Fecha', text='Fecha')
        self.checkpoints_tree.heading('Hora', text='Hora')
        self.checkpoints_tree.heading('Corte', text='Corte #')
        
        self.checkpoints_tree.column('Nombre', width=300, anchor='w')
        self.checkpoints_tree.column('Fecha', width=100, anchor='center')
        self.checkpoints_tree.column('Hora', width=80, anchor='center')
        self.checkpoints_tree.column('Corte', width=80, anchor='center')
        
        self.checkpoints_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.checkpoints_tree.yview)
        
        self.checkpoints_tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.checkpoints_tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=(10, 0))
        
        tk.Button(button_frame, text="Restaurar Checkpoint", command=self.confirm_restore,
                 font=FONTS['button'], bg=COLORS['warning'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['button_bg'],
                 fg=COLORS['text_primary'], relief=tk.RAISED,
                 borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def load_checkpoints(self):
        """Carga los checkpoints disponibles en la tabla."""
        for item in self.checkpoints_tree.get_children():
            self.checkpoints_tree.delete(item)
        
        checkpoints = db.get_checkpoints()
        
        if not checkpoints:
            self.checkpoints_tree.insert('', tk.END, values=("No hay checkpoints disponibles", "", "", ""), tags=('oddrow',))
            return
        
        for idx, cp in enumerate(checkpoints):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            values = (cp['name'], cp['date'], cp['time'], cp['corte'])
            self.checkpoints_tree.insert('', tk.END, values=values, tags=(tag,), iid=cp['path']) # Usar path como iid
    
    def confirm_restore(self):
        """Pide confirmación y autorización para restaurar el checkpoint."""
        selected_item = self.checkpoints_tree.selection()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor selecciona un checkpoint para restaurar.", parent=self.dialog)
            return
        
        checkpoint_path = selected_item[0]
        checkpoint_name = self.checkpoints_tree.item(selected_item[0], 'values')[0]
        
        if messagebox.askyesno("Confirmar Restauración de Base de Datos",
                               f"Estás a punto de restaurar la base de datos a la versión:\n\n"
                               f"'{checkpoint_name}'\n\n"
                               "¡ADVERTENCIA! Se perderán todos los datos guardados después de este checkpoint.\n\n"
                               "¿Estás ABSOLUTAMENTE seguro de que deseas continuar?",
                               parent=self.dialog):
            # Si el usuario confirma, pedir autorización de administrador
            AdminAuthDialog(self.dialog, on_success=lambda: self.perform_restore(checkpoint_path),
                            message="Se requiere autorización de administrador para RESTAURAR la base de datos.")
    
    def perform_restore(self, checkpoint_path: str):
        """Ejecuta la restauración de la base de datos y reinicia la aplicación."""
        try:
            db.restore_checkpoint(checkpoint_path)
            messagebox.showinfo("Base de Datos Restaurada",
                                "La base de datos ha sido restaurada exitosamente.\n\n"
                                "La aplicación se reiniciará para aplicar los cambios.",
                                parent=self.dialog)
            from utils import restart_application
            restart_application()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al intentar restaurar la base de datos: {e}",
                                parent=self.dialog)
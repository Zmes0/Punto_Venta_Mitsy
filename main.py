"""
Aplicación principal de Mitsy's POS - CORREGIDO
"""
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
from config import COLORS, FONTS, WINDOW_CONFIG, DENOMINACIONES
from database import db
from utils import get_current_date, get_resource_path
from caja import open_cash_drawer
from auth import session

class MitsysPOS:
    def __init__(self):
        self.server_process = None
        self.root = tk.Tk()
        self.root.title("Mitsy's POS")
        try:
            self.root.iconbitmap(get_resource_path('icono.ico'))
        except Exception:
            pass
        self.root.geometry("600x700")
        self.root.configure(bg=COLORS['bg_primary'])
        
        # Centrar ventana principal
        self.center_window(self.root, 600, 700)
        
        # Mostrar splash screen
        self.show_splash()
        
        # Iniciar servidor Flask
        self.start_server()
        
        # Protocolo de cierre para asegurar que se mate el servidor
        self.root.protocol("WM_DELETE_WINDOW", self.salir)
        
        # Registrar limpieza para asegurar que el servidor muera al reiniciar
        import atexit
        atexit.register(self.cleanup_server)
    
    def center_window(self, window, width, height):
        """Centra una ventana en la pantalla"""
        window.update_idletasks()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    def show_splash(self):
        """Muestra la pantalla de bienvenida"""
        self.root.withdraw()
        
        self.splash = tk.Toplevel(self.root)
        self.splash.title("")
        self.splash.overrideredirect(True)
        self.splash.attributes('-topmost', True)
        self.splash.configure(bg=COLORS['bg_primary'])
        self.center_window(self.splash, 600, 400)
        
        frame = tk.Frame(self.splash, bg=COLORS['bg_primary'])
        frame.pack(expand=True)
        
        tk.Label(frame, text="Welcome to", font=('Segoe UI', 20),
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=(0, 10))
        
        tk.Label(frame, text="Mitsy's Point of Sale", font=('Segoe UI', 32, 'bold'),
                bg=COLORS['bg_primary'], fg=COLORS['accent']).pack(pady=(0, 20))
        
        tk.Label(frame, text="By Seb and Paola", font=('Segoe UI', 16),
                bg=COLORS['bg_primary'], fg=COLORS['text_secondary']).pack()
        
        self.splash.after(WINDOW_CONFIG['splash_duration'], self.close_splash)
    
    def close_splash(self):
        """Cierra el splash y continúa con el flujo"""
        try:
            self.splash.destroy()
        except:
            pass
    
        self.root.deiconify()
    
        if db.is_auth_enabled():
            from auth import LoginWindow
            LoginWindow(self.root, on_success=self.after_login)
        else:
            self.after_login()

    def after_login(self):
        """Continúa después del login"""
        self.check_dinero_caja()
    
    def check_dinero_caja(self):
        """Verifica si se debe ingresar dinero en caja"""
        corte_activo_id = db.get_corte_activo_id()
    
        if not corte_activo_id:
            self.show_dinero_caja_window()
        else:
            self.show_main_menu()
    
    def show_dinero_caja_window(self):
        """Muestra la ventana para ingresar dinero en caja"""
        DineroCajaWindow(self.root, callback=self.show_main_menu)
    
    def show_main_menu(self):
        """Muestra el menú principal"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
        self.root.deiconify()
    
        new_width = 450
        new_height = 700
        self.root.title("Mitsy's POS - Menú Principal")
    
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        self.root.focus_force()
    
        main_frame = tk.Frame(self.root, bg=COLORS['bg_primary'])
        main_frame.pack(expand=True, fill=tk.BOTH)
    
        center_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        center_frame.place(relx=0.5, rely=0.5, anchor='center')
    
        from auth import session
        if session.is_logged_in():
            user = session.get_current_user()
            user_text = f"Usuario: {user['username']}"
            tk.Label(center_frame, text=user_text, font=FONTS['small'],
                    bg=COLORS['bg_primary'], fg=COLORS['text_secondary']).pack(pady=(0, 10))
    
        tk.Label(center_frame, text="Sistema POS", font=FONTS['title'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=(0, 20))
    
        menu_options = [
            ("Punto de Venta", self.open_punto_venta, None),
            ("Productos", self.open_productos, 'admin'),
            ("Materia Prima", self.open_ingredientes, 'admin'),
            ("Recetas", self.open_recetas, 'admin'),
            ("Stock", self.open_stock, 'admin'),
            ("Historial de Ventas", self.open_historial, 'admin'),
            ("Cortes", self.open_cortes, 'admin'),
            ("Configuración", self.open_configuracion, 'admin'),
            ("Salir", self.salir, None)
        ]
    
        for text, command, required_level in menu_options:
            if text == "Salir":
                bg_color = COLORS['danger']
                fg_color = 'white'
            elif text == "Configuración":
                bg_color = COLORS['accent']
                fg_color = 'white'
            else:
                bg_color = COLORS['button_bg']
                fg_color = COLORS['text_primary']
        
            btn = tk.Button(center_frame, text=text, 
                        command=lambda c=command, r=required_level: self.check_access(c, r),
                        font=FONTS['button'], bg=bg_color, fg=fg_color,
                        relief=tk.RAISED, borderwidth=2, width=20, pady=8,
                        cursor='hand2')
            btn.pack(pady=6)
        
            if text not in ["Salir", "Configuración"]:
                btn.bind('<Enter>', lambda e, b=btn: b.config(bg=COLORS['button_hover']))
                btn.bind('<Leave>', lambda e, b=btn: b.config(bg=COLORS['button_bg']))
    
        self.center_window(self.root, new_width, new_height)
        self.root.minsize(400, 650)
    
    def check_access(self, command, required_level):
        """Verifica el acceso antes de ejecutar un comando - CORREGIDO"""
        from auth import session, AdminAuthDialog
        
        if getattr(self, '_processing_access', False):
            return
        self._processing_access = True
        self.root.after(1000, lambda: setattr(self, '_processing_access', False))

        if session.is_logged_in():
            session.update_activity()

        # Si no requiere nivel específico, ejecutar directamente
        if not required_level:
            command()
            return

        # Si el sistema de auth está desactivado, permitir acceso
        if not db.is_auth_enabled():
            command()
            return

        # Verificar sesión activa
        if not session.is_logged_in():
            from auth import LoginWindow
            LoginWindow(self.root, on_success=lambda: self.check_access(command, required_level))
            return

        # Si es admin, permitir acceso directo
        if session.is_admin():
            command()
            return

        # Si es empleado y requiere admin, solicitar autorización
        if required_level == 'admin':
            # NOTA: Este diálogo requiere que el usuario ingrese credenciales de un administrador
            # para poder continuar. Si solo ve un botón 'Aceptar', es probable que sea un mensaje
            # de error por credenciales incorrectas o incompletas.
            AdminAuthDialog(self.root, on_success=command,
                        message="Para acceder a esta sección, por favor ingrese las credenciales de un administrador.")
            return

        command()
        
    def open_punto_venta(self):
        """Abre el módulo de punto de venta"""
        corte_activo_id = db.get_corte_activo_id()

        if not corte_activo_id:
            messagebox.showerror("Error", 
                        "No hay ningún corte activo. Primero debes ingresar el dinero inicial en caja.")
            return
    
        self.root.withdraw()
        from punto_venta import PuntoVentaWindow
        PuntoVentaWindow(self.root, on_close=self.on_module_close)
    
    def open_productos(self):
        """Abre el módulo de productos"""
        self.root.withdraw()
        from productos import ProductosWindow
        ProductosWindow(self.root, on_close=self.on_module_close)
    
    def open_ingredientes(self):
        """Abre el módulo de ingredientes"""
        self.root.withdraw()
        from ingredientes import IngredientesWindow
        IngredientesWindow(self.root, on_close=self.on_module_close)
    
    def open_recetas(self):
        """Abre el módulo de recetas"""
        self.root.withdraw()
        from recetas import RecetasWindow
        RecetasWindow(self.root, on_close=self.on_module_close)
    
    def open_stock(self):
        """Abre el módulo de stock"""
        self.root.withdraw()
        from stock import StockWindow
        StockWindow(self.root, on_close=self.on_module_close)
    
    def open_historial(self):
        """Abre el módulo de historial de ventas - CORREGIDO"""
        self.root.withdraw()
        from historial_ventas import HistorialVentasWindow
        HistorialVentasWindow(self.root, on_close=self.on_module_close)
    
    def open_cortes(self):
        """Abre el módulo de cortes"""
        self.root.withdraw()
        from historial_cortes import CortesWindow
        CortesWindow(self.root, on_close=self.on_module_close)
    
    def open_configuracion(self):
        """Abre el módulo de configuración"""
        self.root.withdraw()
        from configuracion import ConfiguracionWindow
        
        # Controlador del servidor para la ventana de configuración
        server_controller = {
            'start': self.start_server,
            'stop': self.cleanup_server,
            'is_running': lambda: self.server_process is not None and self.server_process.poll() is None
        }
        
        ConfiguracionWindow(self.root, on_close=self.on_module_close, server_controller=server_controller)
    
    def on_module_close(self):
        """Callback cuando se cierra un módulo"""
        self.show_main_menu()
    
    def start_server(self):
        """Inicia el servidor Flask en un proceso separado"""
        try:
            if getattr(sys, 'frozen', False):
                # En modo ejecutable, nos llamamos a nosotros mismos con el argumento --server
                base_dir = os.path.dirname(sys.executable)
                cmd = [sys.executable, '--server']
            else:
                # En modo desarrollo, llamamos al script de python
                base_dir = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.join(base_dir, 'flask_app.py')
                cmd = [sys.executable, script_path]

            # Ocultar consola en Windows
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            self.server_process = subprocess.Popen(
                cmd,
                cwd=base_dir,
                startupinfo=startupinfo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            print(f"Servidor iniciado con PID: {self.server_process.pid}")
            
        except Exception as e:
            print(f"Error al iniciar servidor: {e}")

    def cleanup_server(self):
        """Detiene el servidor Flask de forma segura"""
        if self.server_process:
            try:
                if sys.platform == 'win32':
                    # Matar árbol de procesos en Windows
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.server_process.pid)],
                                    startupinfo=startupinfo,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL)
                else:
                    self.server_process.terminate()
                self.server_process = None # Evitar doble limpieza
            except Exception as e:
                print(f"Error al detener servidor: {e}")

    def salir(self):
        """Cierra el programa"""
        if messagebox.askyesno("Salir", "¿Estás seguro de que deseas salir del sistema?"):
            self.cleanup_server()
            self.root.quit()
            self.root.destroy()
            sys.exit(0)
    
    def run(self):
        """Ejecuta la aplicación"""
        self.root.mainloop()


class DineroCajaWindow:
    def __init__(self, parent, callback=None):
        self.callback = callback
        self.denominaciones_cantidad = {}
        
        self.window = tk.Toplevel(parent)
        self.window.title("Ingresa el dinero en caja")
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.transient(parent)
        self.window.grab_set()
        
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        try:
            self.window.iconbitmap(get_resource_path('icono.ico'))
        except Exception:
            # Si falla cargar el icono, continuamos sin él para no romper la app
            pass
        
        self.setup_ui()
        self.window.update_idletasks()
        width = 650
        height = 550
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.resizable(False, False)
        
        open_cash_drawer()
    
    def setup_ui(self):
        """Configura la interfaz"""
        main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        tk.Label(main_frame, text="Ingresa el dinero en caja", 
                font=FONTS['title'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=(0, 30))

        top_section_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        top_section_frame.pack(fill=tk.X)

        canvas = tk.Canvas(top_section_frame, bg=COLORS['bg_primary'],
                          highlightthickness=0, height=200)
        scrollbar = tk.Scrollbar(top_section_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        billetes_frame = tk.LabelFrame(scrollable_frame, text="Billetes", 
                                       font=FONTS['heading'],
                                       bg=COLORS['bg_secondary'],
                                       fg=COLORS['text_primary'],
                                       relief=tk.RAISED, borderwidth=2)
        billetes_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0, 20), padx=10)
        
        for denominacion in DENOMINACIONES['billetes']:
            self.create_denominacion_row(billetes_frame, denominacion, 'billete')
        
        monedas_frame = tk.LabelFrame(scrollable_frame, text="Monedas", 
                                      font=FONTS['heading'],
                                      bg=COLORS['bg_secondary'],
                                      fg=COLORS['text_primary'],
                                      relief=tk.RAISED, borderwidth=2)
        monedas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0, 20), padx=10)
        
        for denominacion in DENOMINACIONES['monedas']:
            self.create_denominacion_row(monedas_frame, denominacion, 'moneda')
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        bottom_section_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        bottom_section_frame.pack(fill=tk.X, pady=(10, 0))

        manual_entry_frame = tk.Frame(bottom_section_frame, bg=COLORS['bg_primary'])
        manual_entry_frame.pack(pady=(10, 5))
        
        tk.Label(manual_entry_frame, text="Ingresar total manualmente:", 
                 font=FONTS['normal'], bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.manual_total_var = tk.StringVar(value="0")
        manual_entry = tk.Entry(manual_entry_frame, textvariable=self.manual_total_var, 
                                font=FONTS['normal'], width=15, justify='center')
        manual_entry.pack(side=tk.LEFT)

        self.total_var = tk.StringVar(value="$0.00")
        total_frame = tk.Frame(bottom_section_frame, bg=COLORS['bg_primary'])
        total_frame.pack(pady=(10, 20))
        
        tk.Label(total_frame, text="Dinero en caja:", font=FONTS['heading'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(total_frame, textvariable=self.total_var, font=FONTS['heading'],
                bg=COLORS['bg_primary'], fg=COLORS['accent']).pack(side=tk.LEFT)
        
        tk.Button(bottom_section_frame, text="Aceptar", command=self.accept,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=40, pady=15,
                 cursor='hand2').pack(pady=20)
    
    def create_denominacion_row(self, parent, denominacion, tipo):
        """Crea una fila para ingresar cantidad de una denominación"""
        row_frame = tk.Frame(parent, bg=COLORS['bg_secondary'])
        row_frame.pack(fill=tk.X, padx=15, pady=5)
        
        from utils import format_currency
        tk.Label(row_frame, text=format_currency(denominacion), 
                font=FONTS['normal'], bg=COLORS['bg_secondary'],
                width=15, anchor='w').pack(side=tk.LEFT, padx=5)
        
        cantidad_var = tk.StringVar(value="0")
        cantidad_var.trace('w', lambda *args: self.calculate_total())
        
        entry = tk.Entry(row_frame, textvariable=cantidad_var, 
                        font=FONTS['normal'], width=10, justify='center')
        entry.pack(side=tk.LEFT, padx=5)
        
        key = f"{tipo}_{denominacion}"
        self.denominaciones_cantidad[key] = {
            'var': cantidad_var,
            'denominacion': denominacion,
            'tipo': tipo
        }
    
    def calculate_total(self):
        """Calcula el total de dinero ingresado"""
        total = 0
        
        try:
            manual_total = float(self.manual_total_var.get())
            if manual_total > 0:
                from utils import format_currency
                self.total_var.set(format_currency(manual_total))
                return
        except ValueError:
            pass

        for key, data in self.denominaciones_cantidad.items():
            try:
                cantidad = int(data['var'].get())
                if cantidad > 0:
                    total += cantidad * data['denominacion']
            except ValueError:
                pass
        
        from utils import format_currency
        self.total_var.set(format_currency(total))
    
    def accept(self):
        """Acepta y guarda el dinero en caja"""
        total = 0
        
        denominacion_total = 0
        for key, data in self.denominaciones_cantidad.items():
            try:
                cantidad = int(data['var'].get())
                if cantidad >= 0:
                    denominacion_total += cantidad * data['denominacion']
                else:
                    messagebox.showerror("Error", 
                                       "Las cantidades no pueden ser negativas")
                    return
            except ValueError:
                messagebox.showerror("Error", 
                                   "Todas las cantidades deben ser números enteros válidos")
                return

        try:
            manual_total = float(self.manual_total_var.get())
        except ValueError:
            manual_total = 0

        if denominacion_total == 0 and manual_total > 0:
            total = manual_total
        else:
            total = denominacion_total
        
        if total == 0:
            if not messagebox.askyesno("Confirmar", 
                                      "El total es $0.00. ¿Deseas continuar?"):
                return
        
        try:
            fecha = get_current_date()
            
            if total == manual_total and manual_total > 0:
                db.cursor.execute('''
                    INSERT INTO dinero_caja
                    (fecha, tipo, denominacion, cantidad, total, tipo_registro)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (fecha, 'manual', 0, 1, total, 'apertura'))
            else:
                for key, data in self.denominaciones_cantidad.items():
                    cantidad = int(data['var'].get())
                    if cantidad > 0:
                        db.cursor.execute('''
                            INSERT INTO dinero_caja 
                            (fecha, tipo, denominacion, cantidad, total, tipo_registro)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (fecha, data['tipo'], data['denominacion'], cantidad,
                              cantidad * data['denominacion'], 'apertura'))
            
            db.conn.commit()
            
            # Obtener usuario actual (si el sistema de auth está activo)
            usuario_id = None
            if db.is_auth_enabled() and session.is_logged_in():
                usuario_id = session.get_current_user()['id']

            corte_id = db.crear_nuevo_corte(total, usuario_id) 
            
            db.mark_dinero_ingresado()
            db.set_config('dinero_inicial_dia', str(total))
            
            from utils import format_currency
            
            db.cursor.execute('SELECT numero_corte FROM cortes WHERE id = ?', (corte_id,))
            result = db.cursor.fetchone()
            numero_corte = result['numero_corte'] if result else 'N/A'
            
            messagebox.showinfo("Éxito",
                              (f"Dinero en caja registrado: {format_currency(total)}\n\n"
                               f"Corte #{numero_corte} iniciado.\n")
                               )
            
            self.window.destroy()
            
            if self.callback:
                self.callback()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {e}")


if __name__ == "__main__":
    # Verificar si debemos ejecutar como servidor o como GUI
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        try:
            from flask_app import app, db
            # Configuración necesaria antes de correr
            db.limpiar_bloqueos_antiguos(minutos=0)
            print("Iniciando servidor de producción (Waitress)...")
            from waitress import serve
            serve(app, host='0.0.0.0', port=5000, threads=1)
        except Exception as e:
            print(f"Error fatal en servidor: {e}")
    else:
        app = MitsysPOS()
        app.run()
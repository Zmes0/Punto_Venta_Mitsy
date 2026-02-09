"""
Módulo de Punto de Venta para Mitsy's POS
"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
from config import COLORS, FONTS, MESAS
from utils import format_currency, parse_currency, get_resource_path
from database import db
from tickets import ticket_generator
import utils
from caja import open_cash_drawer
from auth import AuthDialog, session

class PuntoVentaWindow:
    def __init__(self, parent, on_close=None):
        self.on_close_callback = on_close
        
        self.window = tk.Toplevel(parent)
        self.window.title("Punto de Venta - Mitsy's POS")
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.minsize(800, 600)
        
        # Maximizar la ventana (pantalla completa en ventana)
        self.window.state('zoomed')
        
        # Forzar al frente
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        self.window.iconbitmap(get_resource_path('icono.ico'))
        
        # Protocolo de cierre
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        # MODIFICACIÓN: Cargar mesas desde la base de datos
        self.load_mesas()
        
        # ID para el proceso de actualización automática
        self.polling_id = None
        
        self.setup_ui()
        
        # Iniciar actualización automática
        self.start_polling()
    
    def load_mesas(self):
        """Carga la configuración de mesas desde la base de datos."""
        import json
        mesas_json = db.get_config('mesas_config')
        if mesas_json:
            try:
                self.mesas = json.loads(mesas_json)
            except json.JSONDecodeError:
                # Si hay un error en el JSON, cargar por defecto
                self.mesas = list(MESAS)
                self.save_mesas()
        else:
            # Si no existe la config, usar la de por defecto y guardarla
            self.mesas = list(MESAS)
            self.save_mesas()

    def save_mesas(self):
        """Guarda la configuración actual de mesas en la base de datos."""
        import json
        mesas_json = json.dumps(self.mesas)
        db.set_config('mesas_config', mesas_json)

    def setup_ui(self):
        """Configura la interfaz de usuario"""
        main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(main_frame, text="Punto de Venta", 
                              font=FONTS['title'], bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=(0, 20))
        
        # Frame para controles superiores
        controls_frame = tk.Frame(main_frame, bg=COLORS['bg_secondary'],
                                 relief=tk.RAISED, borderwidth=2)
        controls_frame.pack(fill=tk.X, pady=(0, 20), padx=10)
        
        # Interruptor de impresión automática
        print_frame = tk.Frame(controls_frame, bg=COLORS['bg_secondary'])
        print_frame.pack(side=tk.LEFT, padx=15, pady=10)
        
        tk.Label(print_frame, text="Imprimir tickets automáticamente:", 
                font=FONTS['normal'], bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.auto_print_var = tk.BooleanVar(value=db.get_auto_print())
        self.auto_print_var.trace('w', self.toggle_auto_print)
        
        tk.Radiobutton(print_frame, text="Sí", variable=self.auto_print_var,
                      value=True, font=FONTS['normal'],
                      bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(print_frame, text="No", variable=self.auto_print_var,
                      value=False, font=FONTS['normal'],
                      bg=COLORS['bg_secondary']).pack(side=tk.LEFT, padx=5)
        
        # Botón imprimir último ticket
        tk.Button(controls_frame, text="🖨 Imprimir Último Ticket", 
                 command=self.imprimir_ultimo_ticket,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=15, pady=8).pack(side=tk.RIGHT, padx=15, pady=10)
        
        # Frame para mesas
        mesas_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        mesas_frame.pack(expand=True)
        
        # Obtener mesas con ventas pendientes
        mesas_pendientes = db.get_mesas_con_ventas_pendientes()
        
        # MODIFICACIÓN: Determinar el número de columnas dinámicamente
        num_columns = 5 if len(self.mesas) >= 14 else 3
        
        # Obtener estados de todas las mesas
        estados_mesas = db.get_mesas_por_estado()

        # Guardar referencia a los botones
        self.mesa_buttons = {}

        # Bucle de creación de botones de mesas
        row = 0
        col = 0
        for idx, mesa in enumerate(self.mesas):
            # Obtener estado de la mesa
            estado = estados_mesas.get(mesa, 'libre')
    
            # Determinar color según estado
            if estado == 'libre':
                bg_color = COLORS['mesa_libre']
                fg_color = COLORS['text_primary']
            elif estado == 'ocupada_sin_pedido':
                bg_color = COLORS['mesa_ocupada']
                fg_color = COLORS['text_primary']
            elif estado == 'pedido_pendiente':
                bg_color = COLORS['mesa_pedido_pendiente']
                fg_color = 'white'
            elif estado == 'pedido_terminado':
                bg_color = COLORS['mesa_pedido_terminado']
                fg_color = 'white'
            else:
                bg_color = COLORS['button_bg']
                fg_color = COLORS['text_primary']
            
            # Sobrescribir color si tiene venta pendiente, pero dar prioridad a 'pedido_terminado'
            if mesa in mesas_pendientes and estado != 'pedido_terminado':
                bg_color = COLORS['warning']
                fg_color = 'white'

            btn = tk.Button(mesas_frame, text=mesa, 
                        command=lambda m=mesa: self.open_mesa(m),
                        font=FONTS['button'], bg=bg_color, fg=fg_color,
                        relief=tk.RAISED, borderwidth=3,
                        width=15, height=3, cursor='hand2')
            btn.grid(row=row, column=col, padx=15, pady=15)
    
            # Agregar menú contextual (click derecho)
            btn.bind('<Button-3>', lambda e, m=mesa: self.mostrar_menu_contextual(e, m))
    
            # Guardar referencia al botón
            self.mesa_buttons[mesa] = btn

            col += 1
            if col > num_columns - 1:
                col = 0
                row += 1
        
        # Frame de botones inferiores
        bottom_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        bottom_frame.pack(side=tk.BOTTOM, pady=(20, 0))
        
        # MODIFICACIÓN: Añadir nuevos botones y definir colores
        buttons = [
            ("Añadir Mesa", self.add_mesa, COLORS['success']),
            ("Eliminar Mesa", self.delete_mesa, COLORS['danger']),
            ("Retiro", self.hacer_retiro, COLORS['button_bg']),
            ("Finalizar Día", self.finalizar_dia, COLORS['accent']),
            ("Volver", self.close_window, COLORS['button_bg'])
        ]
        
        for text, command, color in buttons:
            fg = 'white' if color != COLORS['button_bg'] else COLORS['text_primary']
            
            btn = tk.Button(bottom_frame, text=text, command=command,
                          font=FONTS['button'], bg=color, fg=fg,
                          relief=tk.RAISED, borderwidth=2, padx=30, pady=10)
            btn.pack(side=tk.LEFT, padx=10)
    
    def start_polling(self):
        """Inicia el ciclo de actualización automática de mesas."""
        self.poll_updates()

    def poll_updates(self):
        """Consulta el estado de las mesas y actualiza la interfaz periódicamente."""
        if not self.window.winfo_exists():
            return

        try:
            # Obtener estados actualizados desde la base de datos
            estados_mesas = db.get_mesas_por_estado()
            mesas_pendientes = db.get_mesas_con_ventas_pendientes()
            
            # Actualizar colores de los botones de mesas
            for mesa, btn in self.mesa_buttons.items():
                estado = estados_mesas.get(mesa, 'libre')
                
                # Determinar colores según estado (lógica idéntica a setup_ui)
                if estado == 'libre':
                    bg_color = COLORS['mesa_libre']
                    fg_color = COLORS['text_primary']
                elif estado == 'ocupada_sin_pedido':
                    bg_color = COLORS['mesa_ocupada']
                    fg_color = COLORS['text_primary']
                elif estado == 'pedido_pendiente':
                    bg_color = COLORS['mesa_pedido_pendiente']
                    fg_color = 'white'
                elif estado == 'pedido_terminado':
                    bg_color = COLORS['mesa_pedido_terminado']
                    fg_color = 'white'
                else:
                    bg_color = COLORS['button_bg']
                    fg_color = COLORS['text_primary']
                
                # Prioridad a ventas pendientes locales si no es pedido terminado
                if mesa in mesas_pendientes and estado != 'pedido_terminado':
                    bg_color = COLORS['warning']
                    fg_color = 'white'
                
                # Aplicar cambios solo si es necesario para evitar parpadeo
                if btn.cget('bg') != bg_color or btn.cget('fg') != fg_color:
                    btn.config(bg=bg_color, fg=fg_color)
                    
        except Exception as e:
            print(f"Error en actualización automática: {e}")
        
        # Programar siguiente actualización en 3 segundos
        self.polling_id = self.window.after(3000, self.poll_updates)

    def toggle_auto_print(self, *args):
        """Activa/desactiva la impresión automática"""
        activo = self.auto_print_var.get()
        db.set_config('auto_print_tickets', '1' if activo else '0')
    
    def imprimir_ultimo_ticket(self):
        """Imprime el último ticket generado EN IMPRESORA TÉRMICA"""
        last_ticket = db.get_last_ticket_path()
    
        if not last_ticket or not os.path.exists(last_ticket):
            messagebox.showwarning("Sin Ticket", 
                              "No hay ningún ticket disponible para imprimir.")
            return
    
        try:
            # Cargar los datos de la última venta desde la base de datos
            # Obtener el número de venta del nombre del archivo
            import re
            match = re.search(r'ticket_(\d+)_', os.path.basename(last_ticket))
        
            if not match:
                messagebox.showerror("Error", "No se pudo identificar el número de ticket")
                return
        
            numero_venta = int(match.group(1))
        
            # Obtener datos de la venta desde la BD
            db.cursor.execute('''
            SELECT numero_venta, fecha, producto, cantidad, precio_unitario, 
                   total, metodo_pago, mesa, propina, recibido, cambio
            FROM ventas 
            WHERE numero_venta = ?
            ORDER BY id
        ''', (numero_venta,))
        
            ventas = [dict(row) for row in db.cursor.fetchall()]
        
            if not ventas:
                messagebox.showerror("Error", "No se encontraron datos de la venta")
                return
        
            # Reconstruir venta_data
            productos = []
            subtotal = 0
            propina = ventas[0]['propina'] if ventas[0]['propina'] else 0
            recibido = ventas[0]['recibido'] if ventas[0]['recibido'] else 0
            cambio = ventas[0]['cambio'] if ventas[0]['cambio'] else 0
        
            for venta in ventas:
                productos.append({
                    'nombre': venta['producto'],
                    'cantidad': venta['cantidad'],
                    'precio': venta['precio_unitario'],
                    'total': venta['total']
                })
                subtotal += venta['total']
        
            total = subtotal + propina
        
            venta_data = {
                'numero_venta': numero_venta,
                'fecha': ventas[0]['fecha'],
                'productos': productos,
                'subtotal': subtotal,
                'propina': propina,
                'total': total,
                'recibido': recibido,  # ✅ AHORA USA EL VALOR REAL
                'cambio': cambio,      # ✅ AHORA USA EL VALOR REAL
                'metodo_pago': ventas[0]['metodo_pago'],
                'mesa': ventas[0]['mesa']
            }
        
            # Imprimir en térmica
            if ticket_generator.print_thermal_ticket(venta_data):
                messagebox.showinfo("Éxito", "Ticket enviado a impresora térmica")
            else:
                messagebox.showerror("Error", "No se pudo imprimir el ticket en la impresora térmica")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al imprimir: {str(e)}")


    
    def open_mesa(self, mesa):
        """Abre la ventana de venta para una mesa"""
        if getattr(self, '_processing_mesa', False):
            return
        self._processing_mesa = True
        VentaMesaWindow(self.window, mesa, callback=self.refresh_mesas)
        self.window.after(1000, lambda: setattr(self, '_processing_mesa', False))
    
    def refresh_mesas(self):
        """Refresca la ventana para actualizar indicadores de mesas pendientes"""
        # Limpiar ventana
        for widget in self.window.winfo_children():
            widget.destroy()
        
        # Recrear UI
        self.setup_ui()
    
    def finalizar_dia(self):
        """Abre ventana para finalizar el día (corte de caja)"""
        if not messagebox.askyesno("Confirmar", "¿Estás seguro que deseas finalizar el día y realizar el corte de caja?"):
            return

        def open_finalizar_dia_window():
            FinalizarDiaWindow(self.window, callback=self.close_window)

        if db.is_auth_enabled():
            AuthDialog(
                self.window,
                on_success=open_finalizar_dia_window,
                allowed_roles=['admin', 'empleado'],
                message="Se requiere autorización para finalizar el día."
            )
        else:
            open_finalizar_dia_window()
    
    def close_window(self):
        """Cierra la ventana y vuelve al menú"""
        if self.polling_id:
            self.window.after_cancel(self.polling_id)
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()

    def add_mesa(self):
        """Añade una nueva mesa y refresca la UI"""
        # MODIFICACIÓN: Limitar el número de mesas a 24
        num_actual_mesas = len(self.mesas)
        if 'Para llevar' in self.mesas:
            num_actual_mesas -= 1
            
        if num_actual_mesas >= 24:
            messagebox.showinfo("Límite alcanzado", "No se pueden agregar más de 24 mesas.")
            return

        # Asumimos que 'Para llevar' siempre está y es el último
        if 'Para llevar' in self.mesas:
            para_llevar = self.mesas.pop()
            num_mesas = len(self.mesas)
            self.mesas.append(f"Mesa {num_mesas + 1}")
            self.mesas.append(para_llevar)
        else: # Si no hay 'Para llevar', solo añade
            num_mesas = len(self.mesas)
            self.mesas.append(f"Mesa {num_mesas + 1}")
        
        self.save_mesas() # Guardar cambios
        self.refresh_mesas()

    def delete_mesa(self):
        """Elimina la última mesa y refresca la UI"""
        if 'Para llevar' in self.mesas:
            para_llevar = self.mesas.pop()
            # Solo eliminar si hay más de una mesa (sin contar 'Para llevar')
            if len(self.mesas) > 1:
                self.mesas.pop()
            self.mesas.append(para_llevar)
        # Si 'Para llevar' no existe, solo eliminar si hay más de una mesa
        elif len(self.mesas) > 1:
            self.mesas.pop()

        self.save_mesas() # Guardar cambios
        self.refresh_mesas()

    def hacer_retiro(self):
        """Maneja el flujo para realizar un retiro de caja."""
        if not messagebox.askyesno("Confirmar Retiro", "¿Estás seguro que deseas registrar un retiro de caja?"):
            return

        from auth import session, AdminAuthDialog
        
        def open_retiro_dialog():
            RetiroDialog(self.window)

        # Si auth está desactivado, o si el usuario actual es admin, abrir directamente.
        if not db.is_auth_enabled() or session.is_admin():
            open_retiro_dialog()
        else:
            # Si es un empleado, pedir autorización de admin
            AdminAuthDialog(self.window, on_success=open_retiro_dialog,
                            message="Se requiere autorización de administrador para realizar un retiro.")
    
    def mostrar_menu_contextual(self, event, mesa):
        """Muestra menú contextual según el estado de la mesa"""
        estado = db.get_estado_mesa(mesa)
    
        # Crear menú contextual
        menu = tk.Menu(self.window, tearoff=0)
    
        if estado == 'libre':
            menu.add_command(label="Marcar como ocupada", 
                        command=lambda: self.cambiar_estado_mesa(mesa, 'ocupada_sin_pedido'))
        elif estado == 'ocupada_sin_pedido':
            menu.add_command(label="Marcar como libre", 
                        command=lambda: self.cambiar_estado_mesa(mesa, 'libre'))
        elif estado == 'pedido_pendiente':
            menu.add_command(label="Marcar pedido terminado", 
                        command=lambda: self.cambiar_estado_mesa(mesa, 'pedido_terminado'))
        elif estado == 'pedido_terminado':
            menu.add_command(label="Revertir a 'Pedido Pendiente'",
                        command=lambda: self.cambiar_estado_mesa(mesa, 'pedido_pendiente'))
            menu.add_separator()
            menu.add_command(label="Cancelar Venta y Liberar Mesa",
                        command=lambda: self.cancelar_venta_y_liberar_mesa(mesa))

        # No mostrar menú si no tiene opciones
        if menu.index('end') is None:
            return
    
        # Mostrar menú en la posición del click
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def cancelar_venta_y_liberar_mesa(self, mesa):
        """Cancela una venta pendiente, libera la mesa y refresca la UI."""
        if messagebox.askyesno("Confirmar Cancelación", 
                               f"¿Está seguro de que desea cancelar la venta de la mesa '{mesa}' y marcarla como libre?\n\nEsta acción no se puede deshacer.",
                               parent=self.window):
            db.delete_venta_pendiente(mesa)
            db.set_estado_mesa(mesa, 'libre')
            self.refresh_mesas()

    def cambiar_estado_mesa(self, mesa, nuevo_estado):
        """Cambia el estado de una mesa y actualiza el color del botón"""
        db.set_estado_mesa(mesa, nuevo_estado)
        self.actualizar_color_mesa(mesa, nuevo_estado)

    def actualizar_color_mesa(self, mesa, estado):
        """Actualiza el color del botón de la mesa según su estado"""
        if mesa not in self.mesa_buttons:
            return
    
        btn = self.mesa_buttons[mesa]
    
        if estado == 'libre':
            bg_color = COLORS['mesa_libre']
            fg_color = COLORS['text_primary']
        elif estado == 'ocupada_sin_pedido':
            bg_color = COLORS['mesa_ocupada']
            fg_color = COLORS['text_primary']
        elif estado == 'pedido_pendiente':
            bg_color = COLORS['mesa_pedido_pendiente']
            fg_color = 'white'
        elif estado == 'pedido_terminado':
            bg_color = COLORS['mesa_pedido_terminado']
            fg_color = 'white'
        else:
            bg_color = COLORS['button_bg']
            fg_color = COLORS['text_primary']
    
        btn.config(bg=bg_color, fg=fg_color)
           
class VentaMesaWindow:
    def __init__(self, parent, mesa, callback=None):
        self.mesa = mesa
        self.callback = callback
        self.productos_venta = []  # Lista de productos en la venta actual
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"{mesa} - Mitsy's POS")
        self.window.geometry("1000x700")
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.transient(parent)
        self.window.grab_set()
        self.window.focus_set()
        self.window.minsize(800, 600)
        
        # Forzar al frente
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        self.window.iconbitmap(get_resource_path('icono.ico'))
        
        # Protocolo de cierre
        self.window.protocol("WM_DELETE_WINDOW", self.minimizar_ventana)

        # Atajo de teclado para cobrar
        self.window.bind('<F2>', lambda event: self.cobrar_venta())
        self.window.bind('<Control-p>', lambda event: self.agregar_productos())
        
        # Atajo de teclado para minimizar
        self.window.bind('<Escape>', lambda event: self.minimizar_ventana())
        
        # Centrar ventana
        self.center_window()
        
        self.setup_ui()
        
        self.productos_venta = self.load_and_merge_products()
        
        self.update_table()

    def show_temporary_info(self, title, message, duration=3500):
        """Muestra un mensaje temporal que se cierra automáticamente"""
        popup = tk.Toplevel(self.window)
        popup.title(title)
        popup.configure(bg=COLORS['bg_primary'])
        popup.transient(self.window)
        
        # Contenido
        frame = tk.Frame(popup, bg=COLORS['bg_primary'], padx=30, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text=message, font=FONTS['normal'], 
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack()
        
        # Centrar
        popup.update_idletasks()
        width = popup.winfo_reqwidth()
        height = popup.winfo_reqheight()
        x = self.window.winfo_rootx() + (self.window.winfo_width() // 2) - (width // 2)
        y = self.window.winfo_rooty() + (self.window.winfo_height() // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")
        
        # Cerrar automáticamente
        popup.after(duration, popup.destroy)

    def load_and_merge_products(self):
        """Carga productos de ventas pendientes y de la web, y los fusiona."""
        import copy

        # Empezar con productos de una venta pendiente guardada
        productos_finales = []
        venta_pendiente = db.get_venta_pendiente(self.mesa)
        if venta_pendiente and 'productos' in venta_pendiente:
            # Usar deepcopy para evitar modificar accidentalmente un objeto cacheado o compartido
            productos_finales = copy.deepcopy(venta_pendiente['productos'])

        # Cargar y fusionar pedidos de la web
        try:
            productos_web = db.get_and_process_web_orders(self.mesa)
            
            if productos_web:
                # Usar un diccionario para búsqueda eficiente y segura
                existing_products = {prod['id']: prod for prod in productos_finales}

                for prod_data in productos_web:
                    if prod_data['id'] in existing_products:
                        # Si el producto ya existe, sumar la cantidad
                        existing_prod = existing_products[prod_data['id']]
                        existing_prod['cantidad'] += prod_data['cantidad']
                        existing_prod['total'] = existing_prod['cantidad'] * existing_prod['precio']
                    else:
                        # Si es un producto nuevo, añadirlo a la lista
                        total = prod_data['cantidad'] * prod_data['precio']
                        new_prod = {
                            'id': prod_data['id'],
                            'nombre': prod_data['nombre'],
                            'cantidad': prod_data['cantidad'],
                            'precio': prod_data['precio'],
                            'total': total
                        }
                        productos_finales.append(new_prod)
                
                # Si se agregaron productos, actualizar estado y notificar
                if productos_finales:
                    db.set_estado_mesa(self.mesa, 'pedido_pendiente')
                
        except Exception as e:
            self.window.after(100, lambda: messagebox.showerror("Error Web", f"No se pudieron cargar los pedidos web: {e}"))
        
        return productos_finales
    
    def center_window(self):
        """Centra la ventana en la pantalla"""
        self.window.update_idletasks()
        width = 1050
        height = 700
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(main_frame, text=self.mesa, 
                              font=FONTS['title'], bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=(0, 20))
        
        # Frame con scrollbar para la tabla
        table_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview (tabla)
        columns = ('No.', 'Producto', 'Cantidad', 'Precio Unit.', 'Total', 'Stock Est.')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar.set, selectmode='extended')
        utils.enable_drag_selection(self.tree)
        
        # Configurar columnas
        self.tree.heading('No.', text='No. Venta')
        self.tree.heading('Producto', text='Producto')
        self.tree.heading('Cantidad', text='Cantidad')
        self.tree.heading('Precio Unit.', text='Precio Unitario')
        self.tree.heading('Total', text='Total')
        self.tree.heading('Stock Est.', text='Stock Estimado')
        
        self.tree.column('No.', width=80, anchor='center')
        self.tree.column('Producto', width=200)
        self.tree.column('Cantidad', width=100, anchor='center')
        self.tree.column('Precio Unit.', width=120, anchor='e')
        self.tree.column('Total', width=120, anchor='e')
        self.tree.column('Stock Est.', width=120, anchor='center')
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Configurar colores y tags
        self.tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        self.tree.tag_configure('low_stock', background='#FFCCCC')
        
        # Permitir edición al hacer doble clic
        self.tree.bind('<Double-1>', self.edit_item)
        
        # Total de la venta
        total_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        total_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(total_frame, text="Total de la Venta:", font=FONTS['heading'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.total_var = tk.StringVar(value="$0.00")
        tk.Label(total_frame, textvariable=self.total_var, font=FONTS['heading'],
                bg=COLORS['bg_primary'], fg=COLORS['accent']).pack(side=tk.LEFT)
        
        # Frame de botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(fill=tk.X)
        
        buttons = [
            ("Agregar Productos", self.agregar_productos, COLORS['success']),
            ("Borrar Producto", self.borrar_producto, COLORS['danger']),
            ("Limpiar Venta", self.limpiar_venta, COLORS['warning']),
            ("Imprimir Cuenta", self.imprimir_cuenta, COLORS['button_bg']),
            ("Cobrar Venta (F2)", self.cobrar_venta, COLORS['accent']),
            ("Minimizar Ventana", self.minimizar_ventana, COLORS['button_bg'])
        ]
        
        for text, command, color in buttons:
            fg = 'white' if color != COLORS['button_bg'] else COLORS['text_primary']
            
            btn = tk.Button(button_frame, text=text, command=command,
                          font=FONTS['button'], bg=color, fg=fg,
                          relief=tk.RAISED, borderwidth=2, padx=15, pady=8)
            btn.pack(side=tk.LEFT, padx=5)
    
    def update_table(self):
        """Actualiza la tabla de productos"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Cargar productos
        total_venta = 0
        gestion_activa = db.is_gestion_stock_active()
        
        for idx, prod in enumerate(self.productos_venta):
            producto_db = db.get_producto(prod['id'])
            
            # Stock estimado
            if gestion_activa and producto_db and producto_db['gestion_stock']:
                stock_est = producto_db['stock_estimado']
                stock_min = producto_db.get('stock_minimo', 0)
                stock_text = f"{stock_est:.0f}"
                
                # Determinar tag por stock bajo
                if stock_est < stock_min:
                    tag = 'low_stock'
                else:
                    tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            else:
                stock_text = "N/A"
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            values = (
                idx + 1,
                prod['nombre'],
                f"{prod['cantidad']:.1f}",
                format_currency(prod['precio']),
                format_currency(prod['total']),
                stock_text
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
            total_venta += prod['total']
        
        # Actualizar total
        self.total_var.set(format_currency(total_venta))
    
    def agregar_productos(self):
        """Abre ventana para agregar productos"""
        if getattr(self, '_processing_add', False):
            return
        self._processing_add = True
        AgregarProductosWindow(self.window, callback=self.add_producto_to_venta)
        self.window.after(1000, lambda: setattr(self, '_processing_add', False))
    
    def add_producto_to_venta(self, producto_data):
        """Añade un producto a la venta"""
        # producto_data = {'id': 1, 'nombre': 'Tacos', 'precio': 15.00, 'cantidad': 2}
        
        # Verificar si el producto ya está en la venta
        producto_existente = None
        for prod in self.productos_venta:
            if prod['id'] == producto_data['id']:
                producto_existente = prod
                break
        
        if producto_existente:
            # Sumar cantidad
            producto_existente['cantidad'] += producto_data['cantidad']
            producto_existente['total'] = producto_existente['cantidad'] * producto_existente['precio']
        else:
            # Añadir nuevo
            total = producto_data['cantidad'] * producto_data['precio']
            self.productos_venta.append({
                'id': producto_data['id'],
                'nombre': producto_data['nombre'],
                'cantidad': producto_data['cantidad'],
                'precio': producto_data['precio'],
                'total': total
            })
        # Cambiar estado de la mesa a 'pedido_pendiente' al agregar productos
        db.set_estado_mesa(self.mesa, 'pedido_pendiente')
        self.update_table()
    
    def edit_item(self, event):
        """Permite editar un item al hacer doble clic"""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        
        if not row_id:
            return
        
        # Solo permitir editar cantidad y precio unitario
        col_index = int(column.replace('#', '')) - 1
        
        if col_index not in [2, 3]:  # Columnas Cantidad y Precio Unit.
            return
        
        # Obtener índice del producto
        values = self.tree.item(row_id)['values']
        producto_idx = int(values[0]) - 1
        
        if producto_idx >= len(self.productos_venta):
            return
        
        producto = self.productos_venta[producto_idx]
        
        # Crear diálogo de edición
        if col_index == 2:  # Cantidad
            EditarCantidadDialog(self.window, producto, self.update_table)
        elif col_index == 3:  # Precio
            EditarPrecioDialog(self.window, producto, self.update_table)
    
    def borrar_producto(self):
        """Elimina productos seleccionados"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona al menos un producto para borrar")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Estás seguro de borrar {len(selection)} producto(s)?"):
            return
        
        # Obtener índices a eliminar (de mayor a menor para no alterar índices)
        indices = []
        for item in selection:
            values = self.tree.item(item)['values']
            indices.append(int(values[0]) - 1)
        
        indices.sort(reverse=True)
        
        for idx in indices:
            if idx < len(self.productos_venta):
                del self.productos_venta[idx]
        
        self.update_table()
    
    def limpiar_venta(self):
        """Limpia toda la venta"""
        if not self.productos_venta:
            messagebox.showinfo("Información", "No hay productos en la venta")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                   "¿Estás seguro de limpiar toda la venta?"):
            return
        
        # Al limpiar productos, cambiar estado a libre
        db.set_estado_mesa(self.mesa, 'libre')
        self.productos_venta = []
        self.update_table()
    
    def cobrar_venta(self):
        """Abre ventana para cobrar la venta"""
        if getattr(self, '_processing_cobrar', False):
            return
        self._processing_cobrar = True
        if not self.productos_venta:
            messagebox.showwarning("Advertencia", "No hay productos en la venta")
            self._processing_cobrar = False
            return
        
        total = sum(p['total'] for p in self.productos_venta)
        
        CobrarVentaWindow(self.window, self.productos_venta, total, 
                         self.mesa, callback=self.on_venta_cobrada)
        self.window.after(1000, lambda: setattr(self, '_processing_cobrar', False))
    
    def on_venta_cobrada(self):
        """Callback cuando se cobra la venta exitosamente"""
        # Marcar pedidos de la mesa como cobrados
        db.marcar_pedidos_como_cobrados(self.mesa)
        
        # Limpiar venta
        self.productos_venta = []
        self.update_table()
        
        # Eliminar venta pendiente
        db.delete_venta_pendiente(self.mesa)
        
        # Cambiar estado de la mesa a 'libre' al cobrar
        db.set_estado_mesa(self.mesa, 'libre')
        
        # Cerrar ventana
        self.window.destroy()
        
        if self.callback:
            self.callback()
    
    def minimizar_ventana(self):
        """Minimiza la ventana y guarda la venta como pendiente"""
        if self.productos_venta:
            # Guardar venta pendiente
            total = sum(p['total'] for p in self.productos_venta)
            db.save_venta_pendiente(self.mesa, self.productos_venta, total)
        else:
            # Si no hay productos, eliminar venta pendiente
            db.delete_venta_pendiente(self.mesa)
            db.set_estado_mesa(self.mesa, 'libre')
            
        self.window.destroy()
        
        if self.callback:
            self.callback()

    def imprimir_cuenta(self):
        """Imprime una cuenta/pre-cuenta para la mesa actual."""
        if not self.productos_venta:
            messagebox.showwarning("Advertencia", "No hay productos en la venta para imprimir la cuenta.")
            return
        
        try:
            from tickets import ticket_generator
            if ticket_generator.print_bill_thermal(self.mesa, self.productos_venta):
                messagebox.showinfo("Éxito", "Cuenta enviada a impresora térmica.")
            else:
                messagebox.showerror("Error", "No se pudo imprimir la cuenta en la impresora térmica.")
        except Exception as e:
            messagebox.showerror("Error", f"Error al imprimir la cuenta: {str(e)}")

class AgregarProductosWindow:
    def __init__(self, parent, callback=None):
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.withdraw()
        self.dialog.title("Agregar Productos")
        self.dialog.geometry("1200x700")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.minsize(1000, 600)
        
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
        self.dialog.protocol("WM_DELETE_WINDOW", self.close_dialog)
        
        self.clasificaciones = []
        self.current_clasificacion_page = 0
        self.clasificaciones_per_page = 10
        self.selected_clasificacion_id = 'all'

        self.product_widgets = []
        self.selected_product_index = -1
        
        self.setup_ui()
        self.load_clasificaciones_and_productos()
        
        self.center_dialog()
        self.dialog.deiconify()
        self.search_entry.focus()

        # Key bindings for navigation
        self.dialog.bind('<Tab>', self.handle_tab_key)
        self.dialog.bind('<Return>', self.handle_enter_key)
        self.dialog.bind('<Escape>', lambda event: self.close_dialog())

    def center_dialog(self):
        self.dialog.update_idletasks()
        width = 1200
        height = 700
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        top_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        top_frame.pack(fill=tk.X, pady=(0, 15))

        self.clasificaciones_frame = tk.Frame(top_frame, bg=COLORS['bg_primary'])
        self.clasificaciones_frame.pack(side=tk.LEFT)

        self.pagination_frame = tk.Frame(top_frame, bg=COLORS['bg_primary'])
        self.pagination_frame.pack(side=tk.RIGHT)

        canvas_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg=COLORS['bg_primary'], highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS['bg_primary'])
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        
        bottom_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        bottom_frame.pack(fill=tk.X, pady=(20, 0))
        
        action_buttons_frame = tk.Frame(bottom_frame, bg=COLORS['bg_primary'])
        action_buttons_frame.pack(side=tk.LEFT)

        tk.Button(action_buttons_frame, text="Regresar (Esc)", command=self.close_dialog,
                 font=FONTS['button'], bg=COLORS['button_bg'],
                 fg=COLORS['text_primary'], relief=tk.RAISED,
                 borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_buttons_frame, text="Aceptar", command=self.close_dialog,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=5)

        search_frame = tk.Frame(bottom_frame, bg=COLORS['bg_primary'])
        search_frame.pack(side=tk.RIGHT)
        
        tk.Label(search_frame, text="Buscar:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.search_productos())
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               font=FONTS['normal'], width=40)
        self.search_entry.pack(side=tk.LEFT)

    def load_clasificaciones_and_productos(self):
        self.clasificaciones = db.get_clasificaciones_by_sales()
        self._update_clasificaciones_ui()
        self.load_productos()

    def _update_clasificaciones_ui(self):
        for widget in self.clasificaciones_frame.winfo_children():
            widget.destroy()
        for widget in self.pagination_frame.winfo_children():
            widget.destroy()

        is_selected = self.selected_clasificacion_id == 'all'
        all_btn = tk.Button(
            self.clasificaciones_frame, 
            text="Todos los productos",
            font=FONTS['button'],
            bg=COLORS['accent'] if is_selected else COLORS['button_bg'],
            fg='white' if is_selected else COLORS['text_primary'],
            relief=tk.RAISED,
            borderwidth=2,
            command=lambda: self.filter_by_clasificacion('all')
        )
        all_btn.pack(side=tk.LEFT, padx=5, pady=5)

        start_index = self.current_clasificacion_page * self.clasificaciones_per_page
        end_index = start_index + self.clasificaciones_per_page
        
        clasificaciones_to_show = self.clasificaciones[start_index:end_index]

        for clasificacion in clasificaciones_to_show:
            is_selected = self.selected_clasificacion_id == clasificacion['id']
            
            btn = tk.Button(
                self.clasificaciones_frame, 
                text=clasificacion['nombre'],
                font=FONTS['button'],
                bg=COLORS['accent'] if is_selected else COLORS['button_bg'],
                fg='white' if is_selected else COLORS['text_primary'],
                relief=tk.RAISED,
                borderwidth=2,
                command=lambda cid=clasificacion['id']: self.filter_by_clasificacion(cid)
            )
            btn.pack(side=tk.LEFT, padx=5, pady=5)

        num_pages = (len(self.clasificaciones) + self.clasificaciones_per_page - 1) // self.clasificaciones_per_page
        if num_pages > 1:
            tk.Button(self.pagination_frame, text="<", command=self.prev_page, font=FONTS['button']).pack(side=tk.LEFT)
            
            page_label = tk.Label(self.pagination_frame, text=f"{self.current_clasificacion_page + 1} / {num_pages}", font=FONTS['normal'], bg=COLORS['bg_primary'])
            page_label.pack(side=tk.LEFT, padx=5)

            tk.Button(self.pagination_frame, text=">", command=self.next_page, font=FONTS['button']).pack(side=tk.LEFT)

    def prev_page(self):
        if self.current_clasificacion_page > 0:
            self.current_clasificacion_page -= 1
            self._update_clasificaciones_ui()

    def next_page(self):
        num_pages = (len(self.clasificaciones) + self.clasificaciones_per_page - 1) // self.clasificaciones_per_page
        if self.current_clasificacion_page < num_pages - 1:
            self.current_clasificacion_page += 1
            self._update_clasificaciones_ui()

    def filter_by_clasificacion(self, clasificacion_id):
        self.selected_clasificacion_id = clasificacion_id
        self.search_var.set("")
        self.load_productos()
        self._update_clasificaciones_ui()

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
    
    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass
    
    def load_productos(self, search_query=None):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.product_widgets = []
        self.selected_product_index = -1

        productos = db.get_productos_by_sales_frequency(
            clasificacion_id=self.selected_clasificacion_id,
            query=search_query
        )
        
        row = 0
        col = 0
        for producto in productos:
            card = self.create_producto_card(producto, row, col)
            self.product_widgets.append((card, producto))
            col += 1
            if col > 6:
                col = 0
                row += 1
    
    def create_producto_card(self, producto, row, col):
        card = tk.Frame(self.scrollable_frame, bg=COLORS['bg_secondary'],
                       relief=tk.RAISED, borderwidth=2,
                       highlightthickness=3, highlightbackground=COLORS['bg_secondary'])
        card.grid(row=row, column=col, padx=12, pady=12, sticky='nsew')
        
        img_frame = tk.Frame(card, bg=COLORS['bg_secondary'], 
                            width=120, height=120)
        img_frame.pack(pady=8)
        img_frame.pack_propagate(False)
        
        try:
            if producto['imagen'] and os.path.exists(producto['imagen']):
                img = Image.open(producto['imagen'])
                img = img.resize((110, 110), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
            else:
                photo = self.create_placeholder_image()
            
            img_label = tk.Label(img_frame, image=photo, bg=COLORS['bg_secondary'])
            img_label.image = photo
            img_label.pack(expand=True)
        except:
            photo = self.create_placeholder_image()
            img_label = tk.Label(img_frame, image=photo, bg=COLORS['bg_secondary'])
            img_label.image = photo
            img_label.pack(expand=True)
        
        nombre = producto['nombre']
        if len(nombre) > 18:
            nombre = nombre[:18] + "..."
        
        tk.Label(card, text=nombre, font=FONTS['normal'],
                bg=COLORS['bg_secondary'], wraplength=130).pack(pady=(0, 5))
        
        tk.Label(card, text=format_currency(producto['precio_unitario']),
                font=FONTS['normal'], bg=COLORS['bg_secondary'],
                fg=COLORS['accent']).pack(pady=(0, 8))
        
        btn = tk.Button(card, text="Seleccionar", 
                       command=lambda p=producto: self.select_producto(p),
                       font=FONTS['button'], bg=COLORS['accent'], fg='white',
                       relief=tk.RAISED, borderwidth=2, cursor='hand2')
        btn.pack(pady=(0, 8), padx=8, fill=tk.X)
        
        card.bind('<Button-1>', lambda e, p=producto: self.select_producto(p))
        for child in card.winfo_children():
            if not isinstance(child, tk.Button):
                child.bind('<Button-1>', lambda e, p=producto: self.select_producto(p))
        
        return card

    def clear_product_selection(self):
        """Clears the visual selection from a product card."""
        if self.selected_product_index != -1 and self.selected_product_index < len(self.product_widgets):
            card, _ = self.product_widgets[self.selected_product_index]
            card.config(highlightbackground=COLORS['bg_secondary'], relief=tk.RAISED)
        self.selected_product_index = -1

    def handle_tab_key(self, event):
        """Handles Tab key press for product navigation."""
        if not self.product_widgets:
            self.search_entry.focus()
            return "break"

        # Un-highlight the previously selected card
        if self.selected_product_index != -1:
            card, _ = self.product_widgets[self.selected_product_index]
            card.config(highlightbackground=COLORS['bg_secondary'], relief=tk.RAISED)

        # Move to the next product, wrapping around if necessary
        self.selected_product_index += 1
        if self.selected_product_index >= len(self.product_widgets):
            self.selected_product_index = 0

        # Highlight the new selection
        card, _ = self.product_widgets[self.selected_product_index]
        card.config(highlightbackground=COLORS['accent'], relief=tk.SOLID)
        
        # Scroll the selected card into view
        self.canvas.after(50, self.scroll_to_widget, card)

        return "break"

    def scroll_to_widget(self, widget):
        """Scrolls the canvas to make the widget visible."""
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        
        content_height = bbox[3]
        widget_y = widget.winfo_y()
        
        if content_height > 0:
            self.canvas.yview_moveto(widget_y / content_height)

    def handle_enter_key(self, event):
        """Handles Enter key press to select a product."""
        if self.selected_product_index != -1:
            _, product_data = self.product_widgets[self.selected_product_index]
            self.select_producto(product_data)
        return "break"
    
    def create_placeholder_image(self):
        img = Image.new('RGB', (110, 110), color=COLORS['table_header'])
        
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        draw.rectangle([15, 15, 95, 95], outline='gray', width=2)
        draw.text((35, 45), "Sin", fill='gray')
        draw.text((25, 60), "Imagen", fill='gray')
        
        return ImageTk.PhotoImage(img)
    
    def search_productos(self, *args):
        query = self.search_var.get().strip()
        self.load_productos(search_query=query)
    
    def select_producto(self, producto):
        self.clear_product_selection()
        CantidadProductoDialog(self.dialog, producto, callback=self.on_cantidad_confirmed)
    
    def on_cantidad_confirmed(self, producto_data):
        if self.callback:
            self.callback(producto_data)
    
    def close_dialog(self):
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except:
            pass
        self.dialog.destroy()


class CantidadProductoDialog:
    def __init__(self, parent, producto, callback=None):
        self.producto = producto
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Ingresa la cantidad")
        self.dialog.geometry("650x600")  # MODIFICACIÓN: Nuevo tamaño
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.minsize(600, 600)
        

        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
        
        self.first_numpad_click = True
        
        self.setup_ui()
       
        # Centrar ventana
        self.center_dialog()
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 650  # MODIFICACIÓN: Ancho actualizado
        height = 600 # MODIFICACIÓN: Altura actualizada
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # --- INICIO DE MODIFICACIÓN ---
        # Frame superior para las dos columnas principales
        top_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        top_frame.pack(fill=tk.BOTH, expand=True)

        # Columna izquierda (Imagen y nombre)
        left_frame = tk.Frame(top_frame, bg=COLORS['bg_primary'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        tk.Label(left_frame, text=self.producto['nombre'], font=FONTS['subtitle'],
                 bg=COLORS['bg_primary'], wraplength=300).pack(pady=(10, 15))

        # Imagen del producto
        img_frame = tk.Frame(left_frame, bg=COLORS['bg_secondary'], relief=tk.SUNKEN, borderwidth=2)
        img_frame.pack(fill=tk.BOTH, expand=True)

        try:
            if self.producto['imagen'] and os.path.exists(self.producto['imagen']):
                img = Image.open(self.producto['imagen'])
            else:
                img = Image.open(get_resource_path('images/placeholder.png'))
            
            img = img.resize((250, 250), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            img_label = tk.Label(img_frame, image=photo, bg=COLORS['bg_secondary'])
            img_label.image = photo
            img_label.pack(expand=True, padx=10, pady=10)
        except Exception:
            tk.Label(img_frame, text="Imagen no disponible", font=FONTS['normal'], 
                     bg=COLORS['bg_secondary']).pack(expand=True)

        # Columna derecha (Teclado numérico)
        self.teclado_frame = tk.Frame(top_frame, bg=COLORS['bg_secondary'],
                                     relief=tk.RAISED, borderwidth=2)
        self.teclado_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.create_numpad()

        # Frame inferior para controles
        bottom_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        bottom_frame.pack(fill=tk.X, pady=(20, 0))

        # Campo de cantidad
        cantidad_frame = tk.Frame(bottom_frame, bg=COLORS['bg_primary'])
        cantidad_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)

        tk.Label(cantidad_frame, text="Cantidad:", font=FONTS['heading'],
                 bg=COLORS['bg_primary']).pack(pady=(0, 5))

        self.cantidad_var = tk.StringVar(value="1")
        self.cantidad_entry = tk.Entry(cantidad_frame, textvariable=self.cantidad_var, 
                                      font=('Segoe UI', 24, 'bold'), justify='center', width=10)
        self.cantidad_entry.pack(pady=(0, 10), ipady=10)
        self.cantidad_entry.focus()
        self.cantidad_entry.bind('<Button-1>', lambda e: self.cantidad_entry.select_range(0, tk.END))
        self.cantidad_entry.bind('<FocusIn>', lambda e: self.cantidad_entry.select_range(0, tk.END))
        self.cantidad_entry.bind('<Return>', lambda e: self.accept())

        # Botones de acción
        button_frame = tk.Frame(bottom_frame, bg=COLORS['bg_primary'])
        button_frame.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        tk.Button(button_frame, text="Aceptar", command=self.accept,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(pady=5)
        
        tk.Button(button_frame, text="Regresar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(pady=5)
        # --- FIN DE MODIFICACIÓN ---
    
    def create_numpad(self):
        """Crea el teclado numérico"""
        buttons = [
            ['7', '8', '9'],
            ['4', '5', '6'],
            ['1', '2', '3'],
            ['.', '0', 'X'] # MODIFICACIÓN: Se cambia '⌫' por 'X' para simetría.
        ]
        
        for row_idx, row in enumerate(buttons):
            self.teclado_frame.grid_rowconfigure(row_idx, weight=1)
            
            for col_idx, btn_text in enumerate(row):
                self.teclado_frame.grid_columnconfigure(col_idx, weight=1)

                if btn_text == 'X': # MODIFICACIÓN: Se actualiza la condición.
                    cmd = self.numpad_backspace
                else:
                    cmd = lambda t=btn_text: self.numpad_click(t)
                
                btn = tk.Button(self.teclado_frame, text=btn_text, command=cmd,
                              font=('Segoe UI', 22, 'bold'),
                              bg=COLORS['button_bg'], relief=tk.RAISED,
                              borderwidth=2, cursor='hand2')
                btn.grid(row=row_idx, column=col_idx, sticky='nsew', padx=5, pady=5)
    
    def numpad_click(self, digit):
        """Maneja el clic en el teclado numérico"""
        current = self.cantidad_var.get()
        if self.first_numpad_click:
            self.cantidad_var.set(digit)
            self.first_numpad_click = False
        else:
            self.cantidad_var.set(current + digit)
        self.cantidad_entry.icursor(tk.END)
        self.cantidad_entry.focus_set()
    
    def numpad_backspace(self):
        """Borra el último dígito"""
        current = self.cantidad_var.get()
        if len(current) > 0:
            self.cantidad_var.set(current[:-1])
        if self.cantidad_var.get() == "":
            self.cantidad_var.set("0")
        self.first_numpad_click = False
    
    def accept(self):
        """Acepta y retorna la cantidad"""
        try:
            cantidad = float(self.cantidad_var.get())
            
            if cantidad <= 0:
                messagebox.showerror("Error", "La cantidad debe ser mayor a 0")
                return
            
            producto_data = {
                'id': self.producto['id'],
                'nombre': self.producto['nombre'],
                'precio': self.producto['precio_unitario'],
                'cantidad': cantidad
            }
            
            if self.callback:
                self.callback(producto_data)
            
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número válido")
class EditarCantidadDialog:
    def __init__(self, parent, producto, callback=None):
        self.producto = producto
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Editar Cantidad")
        self.dialog.geometry("350x200")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        # Centrar ventana
        self.center_dialog()
        
        self.setup_ui()
        
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 350
        height = 200
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text=f"Producto: {self.producto['nombre']}", 
                font=FONTS['normal'], bg=COLORS['bg_primary']).pack(pady=10)
        
        tk.Label(main_frame, text="Nueva Cantidad:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        
        self.cantidad_var = tk.StringVar(value=str(self.producto['cantidad']))
        self.cantidad_entry = tk.Entry(main_frame, textvariable=self.cantidad_var, 
                                      font=FONTS['normal'])
        self.cantidad_entry.pack(fill=tk.X, pady=(0, 20))
        self.cantidad_entry.focus()
        
        # Seleccionar todo al hacer clic o al recibir foco
        self.cantidad_entry.bind('<Button-1>', lambda e: self.cantidad_entry.select_range(0, tk.END))
        self.cantidad_entry.bind('<FocusIn>', lambda e: self.cantidad_entry.select_range(0, tk.END))
        self.cantidad_entry.select_range(0, tk.END)
        
        self.cantidad_entry.bind('<Return>', lambda e: self.accept())
        
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack()
        
        tk.Button(button_frame, text="Aceptar", command=self.accept,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=8).pack(side=tk.LEFT, padx=5)
    
    def accept(self):
        """Acepta y actualiza la cantidad"""
        try:
            cantidad = float(self.cantidad_var.get())
            
            if cantidad <= 0:
                messagebox.showerror("Error", "La cantidad debe ser mayor a 0")
                return
            
            self.producto['cantidad'] = cantidad
            self.producto['total'] = cantidad * self.producto['precio']
            
            if self.callback:
                self.callback()
            
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número válido")


class EditarPrecioDialog:
    def __init__(self, parent, producto, callback=None):
        self.producto = producto
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Editar Precio")
        self.dialog.geometry("350x200")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        # Centrar ventana
        self.center_dialog()
        
        self.setup_ui()
        
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
    
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 350
        height = 200
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text=f"Producto: {self.producto['nombre']}", 
                font=FONTS['normal'], bg=COLORS['bg_primary']).pack(pady=10)
        
        tk.Label(main_frame, text="Nuevo Precio Unitario:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        
        self.precio_var = tk.StringVar(value=str(self.producto['precio']))
        self.precio_entry = tk.Entry(main_frame, textvariable=self.precio_var, 
                                     font=FONTS['normal'])
        self.precio_entry.pack(fill=tk.X, pady=(0, 20))
        self.precio_entry.focus()
        
        # Seleccionar todo al hacer clic o al recibir foco
        self.precio_entry.bind('<Button-1>', lambda e: self.precio_entry.select_range(0, tk.END))
        self.precio_entry.bind('<FocusIn>', lambda e: self.precio_entry.select_range(0, tk.END))
        self.precio_entry.select_range(0, tk.END)
        
        self.precio_entry.bind('<Return>', lambda e: self.accept())
        
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack()
        
        tk.Button(button_frame, text="Aceptar", command=self.accept,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=8).pack(side=tk.LEFT, padx=5)
    
    def accept(self):
        """Acepta y actualiza el precio"""
        try:
            precio = float(self.precio_var.get())
            
            if precio <= 0:
                messagebox.showerror("Error", "El precio debe ser mayor a 0")
                return
            
            self.producto['precio'] = precio
            self.producto['total'] = self.producto['cantidad'] * precio
            
            if self.callback:
                self.callback()
            
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("Error", "El precio debe ser un número válido")


class CobrarVentaWindow:
    def __init__(self, parent, productos, total, mesa, callback=None):
        self.productos = productos
        self.subtotal = total
        self.mesa = mesa
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Cobrar Venta")
        self.dialog.geometry("750x650")  # MODIFICACIÓN: Ancho fijo para incluir teclado
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))

        # Atajo de teclado para finalizar venta
        self.dialog.bind('<Return>', lambda event: self.finalizar_venta())
        self.dialog.bind('<Escape>', lambda event: self.dialog.destroy())
        
        # Centrar ventana
        self.center_dialog()
        
        self.setup_ui()
        
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 750 # MODIFICACIÓN: Ancho fijo
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # --- INICIO DE MODIFICACIÓN ---
        # Frame contenedor para las dos columnas
        content_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Columna izquierda para los controles de cobro
        left_frame = tk.Frame(content_frame, bg=COLORS['bg_primary'])
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Título
        tk.Label(left_frame, text="Cobrar Venta", font=FONTS['title'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=(0, 20))
        
        # Propina con botón de teclado
        propina_frame = tk.Frame(left_frame, bg=COLORS['bg_primary'])
        propina_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(propina_frame, text="Propina:", font=FONTS['heading'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT)
        
        self.propina_var = tk.StringVar(value="0")
        self.propina_var.trace('w', lambda *args: self.calculate_total())
        self.propina_entry = tk.Entry(propina_frame, textvariable=self.propina_var, 
                                      font=FONTS['normal'], width=15, justify='right')
        self.propina_entry.pack(side=tk.RIGHT)
        
        # Dinero recibido con botón de teclado
        recibido_frame = tk.Frame(left_frame, bg=COLORS['bg_primary'])
        recibido_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(recibido_frame, text="Dinero recibido:", font=FONTS['heading'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT)
        
        # Subtotal
        subtotal_frame = tk.Frame(left_frame, bg=COLORS['bg_primary'])
        subtotal_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(subtotal_frame, text="Subtotal:", font=FONTS['heading'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT)
        
        tk.Label(subtotal_frame, text=format_currency(self.subtotal), 
                font=FONTS['heading'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(side=tk.RIGHT)
        
        
        # Seleccionar todo al hacer clic
        self.propina_entry.bind('<Button-1>', lambda e: self.propina_entry.select_range(0, tk.END))
        
        # Total a pagar
        total_frame = tk.Frame(left_frame, bg=COLORS['bg_secondary'],
                              relief=tk.RAISED, borderwidth=1)
        total_frame.pack(fill=tk.X, pady=15, padx=12)
        total_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(total_frame, text="Total a pagar:", font=FONTS['subtitle'],
                bg=COLORS['bg_secondary']).grid(row=0, column=0, sticky='w', padx=10, pady=15)
        
        self.total_var = tk.StringVar(value=format_currency(self.subtotal))
        tk.Label(total_frame, textvariable=self.total_var, 
                font=('Segoe UI', 20, 'bold'), bg=COLORS['bg_secondary'],
                fg=COLORS['accent'], justify=tk.RIGHT).grid(row=0, column=1, sticky='e', padx=10, pady=12)
        
        
        self.recibido_var = tk.StringVar(value="0")
        self.recibido_entry = tk.Entry(recibido_frame, textvariable=self.recibido_var, 
                                       font=FONTS['normal'], width=15, justify='right')
        self.recibido_entry.pack(side=tk.RIGHT)
        self.recibido_var.trace('w', self.on_recibido_change)
        
        # Seleccionar todo y dar foco
        self.recibido_entry.focus()
        self.recibido_entry.select_range(0, tk.END)
        self.recibido_entry.bind('<Button-1>', lambda e: self.recibido_entry.select_range(0, tk.END))
        self.recibido_entry.bind('<FocusIn>', lambda e: self.recibido_entry.select_range(0, tk.END))
        
        # Columna derecha para teclado numérico
        self.teclado_frame = tk.Frame(content_frame, bg=COLORS['bg_secondary'],
                                     relief=tk.RAISED, borderwidth=2)
        # Se empaqueta para que esté siempre visible
        self.teclado_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))
        
        self.create_numpad()
        # --- FIN DE MODIFICACIÓN ---
        
        # Cambio
        cambio_frame = tk.Frame(left_frame, bg=COLORS['bg_primary'])
        cambio_frame.pack(fill=tk.X, pady=8)
        cambio_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(cambio_frame, text="Cambio:", font=FONTS['subtitle'],
                bg=COLORS['bg_primary']).grid(row=0, column=0, sticky='w')
        
        self.cambio_var = tk.StringVar(value="$0.00")
        tk.Label(cambio_frame, textvariable=self.cambio_var, 
                font=FONTS['subtitle'], bg=COLORS['bg_primary'],
                fg=COLORS['success'], justify=tk.RIGHT).grid(row=0, column=1, sticky='e')
        
        # Separador
        tk.Frame(left_frame, bg=COLORS['border'], height=2).pack(fill=tk.X, pady=15)
        
        # Método de pago
        tk.Label(left_frame, text="Método de pago:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=8)
        
        metodo_frame = tk.Frame(left_frame, bg=COLORS['bg_primary'])
        metodo_frame.pack(anchor='w')
        
        self.metodo_var = tk.StringVar(value='Efectivo')
        
        tk.Radiobutton(metodo_frame, text="Efectivo", variable=self.metodo_var,
                      value='Efectivo', font=FONTS['normal'],
                      bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(metodo_frame, text="Transferencia", variable=self.metodo_var,
                      value='Transferencia', font=FONTS['normal'],
                      bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(metodo_frame, text="Tarjeta", variable=self.metodo_var,
                      value='Tarjeta', font=FONTS['normal'],
                      bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=10)
        
        # Botones
        button_frame = tk.Frame(left_frame, bg=COLORS['bg_primary'])
        button_frame.pack(side=tk.BOTTOM, pady=(20, 0))
        
        tk.Button(button_frame, text="Finalizar Venta", command=self.finalizar_venta,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=12).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=12).pack(side=tk.LEFT, padx=10)
    
    def create_numpad(self):
        """Crea el teclado numérico"""
        buttons = [
            ['7', '8', '9'],
            ['4', '5', '6'],
            ['1', '2', '3'],
            ['.', '0', 'X']
        ]
        
        for row_idx, row in enumerate(buttons):
            self.teclado_frame.grid_rowconfigure(row_idx, weight=1)
            
            for col_idx, btn_text in enumerate(row):
                self.teclado_frame.grid_columnconfigure(col_idx, weight=1)

                if btn_text == 'X':
                    cmd = self.numpad_backspace
                else:
                    cmd = lambda t=btn_text: self.numpad_click(t)
                
                btn = tk.Button(self.teclado_frame, text=btn_text, command=cmd,
                              font=('Segoe UI', 20, 'bold'),
                              bg=COLORS['button_bg'], relief=tk.RAISED,
                              borderwidth=2, cursor='hand2')
                btn.grid(row=row_idx, column=col_idx, sticky='nsew', padx=5, pady=5)
    
    def numpad_click(self, digit):
        """Maneja el clic en el teclado numérico"""
        # Obtener el widget que tiene el foco
        focused = self.dialog.focus_get()
        
        if focused == self.recibido_entry:
            current = self.recibido_var.get()
            if current == "0":
                self.recibido_var.set(digit)
            else:
                self.recibido_var.set(current + digit)
        elif focused == self.propina_entry:
            current = self.propina_var.get()
            if current == "0":
                self.propina_var.set(digit)
            else:
                self.propina_var.set(current + digit)
    
    def on_recibido_change(self, *args):
        """Formatea el campo de recibido con comas y calcula cambio"""
        if getattr(self, '_updating_recibido', False):
            return

        value = self.recibido_var.get()
        if not value:
            self.calculate_cambio()
            return

        clean_value = value.replace(',', '')
        
        try:
            # Evitar formatear si hay múltiples puntos
            if clean_value.count('.') > 1:
                self.calculate_cambio()
                return
                
            # Separar parte entera y decimal
            if '.' in clean_value:
                parts = clean_value.split('.')
                integer_part = parts[0]
                decimal_part = parts[1]
                
                formatted_integer = "{:,}".format(int(integer_part)) if integer_part else "0"
                new_value = f"{formatted_integer}.{decimal_part}"
            else:
                new_value = "{:,}".format(int(clean_value)) if clean_value else ""
            
            if new_value != value:
                self._updating_recibido = True
                self.recibido_var.set(new_value)
                if hasattr(self, 'recibido_entry'):
                    self.recibido_entry.icursor(tk.END)
                self._updating_recibido = False
        except ValueError:
            pass
            
        self.calculate_cambio()

    def numpad_backspace(self):
        """Borra el último dígito"""
        focused = self.dialog.focus_get()
        
        if focused == self.recibido_entry:
            current = self.recibido_var.get()
            if len(current) > 0:
                self.recibido_var.set(current[:-1])
            if self.recibido_var.get() == "":
                self.recibido_var.set("0")
        elif focused == self.propina_entry:
            current = self.propina_var.get()
            if len(current) > 0:
                self.propina_var.set(current[:-1])
            if self.propina_var.get() == "":
                self.propina_var.set("0")
    
    def calculate_total(self):
        """Calcula el total con propina"""
        try:
            propina = float(self.propina_var.get()) if self.propina_var.get() else 0
            total = self.subtotal + propina
            self.total_var.set(format_currency(total))
            self.calculate_cambio()
        except ValueError:
            pass
    
    def calculate_cambio(self):
        """Calcula el cambio"""
        try:
            propina = float(self.propina_var.get()) if self.propina_var.get() else 0
            total = self.subtotal + propina
            recibido_str = self.recibido_var.get().replace(',', '')
            recibido = float(recibido_str) if recibido_str else 0
            cambio = recibido - total
            
            if cambio < 0:
                self.cambio_var.set(format_currency(0))
            else:
                self.cambio_var.set(format_currency(cambio))
        except ValueError:
            self.cambio_var.set("$0.00")
    
    def finalizar_venta(self):
        """Finaliza la venta (MODIFICADO para guardar recibido y cambio)"""
        if getattr(self, '_processing', False):
            return
        self._processing = True
        try:
            propina = float(self.propina_var.get()) if self.propina_var.get() else 0
            total = self.subtotal + propina
            recibido_str = self.recibido_var.get().replace(',', '')
            recibido = float(recibido_str) if recibido_str else 0
        
            # Validar que el dinero recibido sea suficiente
            if recibido < total:
                messagebox.showerror("Error", 
                                f"El dinero recibido ({format_currency(recibido)}) es menor al total ({format_currency(total)})",
                                parent=self.dialog)
                self._processing = False
                return
    
            cambio = recibido - total
            metodo_pago = self.metodo_var.get()
    
            # MODIFICADO: Capturar error de stock insuficiente
            try:
                # Guardar venta en base de datos (AHORA INCLUYE recibido y cambio)
                numero_venta = db.finalizar_venta(self.productos, metodo_pago, 
                                                self.mesa, propina, recibido, cambio)
            except ValueError as stock_error:
                # Error de stock insuficiente
                messagebox.showerror("Stock Insuficiente", str(stock_error), parent=self.dialog)
                self._processing = False
                return
    
            # Abrir caja si el pago es en efectivo
            if metodo_pago == 'Efectivo':
                open_cash_drawer()

            # Preparar datos de la venta
            from datetime import datetime
            venta_data = {
                'numero_venta': numero_venta,
                'fecha': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'productos': self.productos,
                'subtotal': self.subtotal,
                'propina': propina,
                'total': total,
                'recibido': recibido,
                'cambio': cambio,
                'metodo_pago': metodo_pago,
                'mesa': self.mesa
            }
    
            try:
                # 1. Generar PDF como respaldo
                ticket_path = ticket_generator.generate_ticket_pdf(venta_data)
        
                # Guardar ruta del último ticket
                db.set_last_ticket_path(ticket_path)
        
                # 2. Imprimir en térmica si está activada la impresión automática
                if db.get_auto_print():
                    ticket_generator.print_thermal_ticket(venta_data)
        
            except Exception as e:
                messagebox.showerror("Error", f"Error al generar/imprimir ticket: {str(e)}", parent=self.dialog)
    
            # Mostrar resumen
            messagebox.showinfo("Venta Completada", 
                            f"Venta #{numero_venta} completada exitosamente\n\n"
                            f"Total: {format_currency(total)}\n"
                            f"Recibido: {format_currency(recibido)}\n"
                            f"Cambio: {format_currency(cambio)}",
                            parent=self.dialog)
    
            self.dialog.destroy()
    
            if self.callback:
                self.callback()
    
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos. Verifica propina y dinero recibido.", parent=self.dialog)
            self._processing = False
        except Exception as e:
            messagebox.showerror("Error", f"Error al finalizar venta: {str(e)}", parent=self.dialog)
            self._processing = False

            
class FinalizarDiaWindow:
    def __init__(self, parent, callback=None):
        self.callback = callback
        
        # MODIFICADO: Verificar si hay un corte activo
        corte_activo_id = db.get_corte_activo_id()
        if not corte_activo_id:
            messagebox.showerror("Error", 
                               "No hay ningún corte activo. Primero debes iniciar un turno ingresando el dinero inicial.")
            return
        
        # Verificar si hay ventas pendientes - BLOQUEAR si las hay
        mesas_pendientes = db.get_mesas_con_ventas_pendientes()
        if mesas_pendientes:
            messagebox.showerror("Ventas Pendientes", 
                               f"No se puede cerrar el corte porque hay {len(mesas_pendientes)} mesa(s) con ventas pendientes:\n\n"
                               f"{', '.join(mesas_pendientes)}\n\n"
                               f"Por favor, finaliza o cancela estas ventas antes de cerrar el corte.")
            return
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Finalizar Día - Corte de Caja")
        self.dialog.geometry("650x600")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        # Centrar ventana
        self.center_dialog()
        
        self.denominaciones_cantidad = {}
        
        self.setup_ui()
        
        open_cash_drawer()
        
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 650
        height = 600
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.resizable(False, False)
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Título
        tk.Label(main_frame, text="Finalizar Día - Corte de Caja", 
                font=FONTS['title'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=(0, 20))
        
        # Crear un frame para la sección superior (tablas)
        top_section_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        top_section_frame.pack(fill=tk.X)
        
        # Frame scrollable
        canvas = tk.Canvas(top_section_frame, bg=COLORS['bg_primary'], 
                          highlightthickness=0, height=250)
        scrollbar = tk.Scrollbar(top_section_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame para billetes
        from config import DENOMINACIONES
        
        billetes_frame = tk.LabelFrame(self.scrollable_frame, text="Billetes", 
                                       font=FONTS['heading'],
                                       bg=COLORS['bg_secondary'],
                                       fg=COLORS['text_primary'],
                                       relief=tk.RAISED, borderwidth=2)
        billetes_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0, 20), padx=10)
        
        for denominacion in DENOMINACIONES['billetes']:
            self.create_denominacion_row(billetes_frame, denominacion, 'billete')
        
        # Frame para monedas
        monedas_frame = tk.LabelFrame(self.scrollable_frame, text="Monedas", 
                                      font=FONTS['heading'],
                                      bg=COLORS['bg_secondary'],
                                      fg=COLORS['text_primary'],
                                      relief=tk.RAISED, borderwidth=2)
        monedas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0, 20), padx=10)
        
        for denominacion in DENOMINACIONES['monedas']:
            self.create_denominacion_row(monedas_frame, denominacion, 'moneda')
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Crear un frame para la sección inferior
        bottom_section_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        bottom_section_frame.pack(fill=tk.X, pady=(10, 0))

        # Entrada manual de total
        manual_entry_frame = tk.Frame(bottom_section_frame, bg=COLORS['bg_primary'])
        manual_entry_frame.pack(pady=(5, 5))
        
        tk.Label(manual_entry_frame, text="Ingresar total manualmente:", 
                 font=FONTS['normal'], bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.manual_total_var = tk.StringVar(value="0")
        manual_entry = tk.Entry(manual_entry_frame, textvariable=self.manual_total_var, 
                                font=FONTS['normal'], width=15, justify='center')
        manual_entry.pack(side=tk.LEFT)
        
        # Total contado
        total_frame = tk.Frame(bottom_section_frame, bg=COLORS['bg_primary'])
        total_frame.pack(pady=10)
        
        tk.Label(total_frame, text="Corte Final (contado):", font=FONTS['heading'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.total_var = tk.StringVar(value="$0.00")
        tk.Label(total_frame, textvariable=self.total_var, font=FONTS['heading'],
                bg=COLORS['bg_primary'], fg=COLORS['accent']).pack(side=tk.LEFT) 
        
        # Botones
        button_frame = tk.Frame(bottom_section_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Finalizar Día", command=self.finalizar_dia,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=12).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=12).pack(side=tk.LEFT, padx=10)
    
    def create_denominacion_row(self, parent, denominacion, tipo):
        """Crea una fila para ingresar cantidad de una denominación"""
        row_frame = tk.Frame(parent, bg=COLORS['bg_secondary'])
        row_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(row_frame, text=format_currency(denominacion), 
                font=FONTS['normal'], bg=COLORS['bg_secondary'],
                width=15, anchor='w').pack(side=tk.LEFT, padx=5)
        
        cantidad_var = tk.StringVar(value="0")
        cantidad_var.trace('w', lambda *args: self.calculate_total())
        
        entry = tk.Entry(row_frame, textvariable=cantidad_var, 
                        font=FONTS['normal'], width=10, justify='center')
        entry.pack(side=tk.LEFT, padx=5)
        
        # Seleccionar todo al hacer clic
        entry.bind('<Button-1>', lambda e, ent=entry: ent.select_range(0, tk.END))
        
        key = f"{tipo}_{denominacion}"
        self.denominaciones_cantidad[key] = {
            'var': cantidad_var,
            'denominacion': denominacion,
            'tipo': tipo
        }
    
    def calculate_total(self):
        """Calcula el total del corte"""
        total = 0
        
        # Si se está usando la entrada manual, no calcular desde denominaciones
        try:
            manual_total = float(self.manual_total_var.get())
            if manual_total > 0:
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
        
        self.total_var.set(format_currency(total))
    
    def finalizar_dia(self):
        """Finaliza el día y realiza el corte - MODIFICADO con nuevo resumen"""
        if getattr(self, '_processing', False):
            return
        self._processing = True
        try:
            # Calcular corte final desde denominaciones
            denominacion_total = 0
            for key, data in self.denominaciones_cantidad.items():
                try:
                    cantidad = int(data['var'].get())
                    if cantidad >= 0:
                        denominacion_total += cantidad * data['denominacion']
                    else:
                        messagebox.showerror("Error", "Las cantidades no pueden ser negativas")
                        self._processing = False
                        return
                except ValueError:
                    messagebox.showerror("Error", "Todas las cantidades deben ser números enteros")
                    self._processing = False
                    return

            # Verificar si se usó la entrada manual
            try:
                manual_total = float(self.manual_total_var.get())
            except ValueError:
                manual_total = 0

            # Decidir qué total usar
            if denominacion_total == 0 and manual_total > 0:
                corte_final = manual_total
            else:
                corte_final = denominacion_total
            
            # NUEVO: Cerrar el corte activo usando el nuevo sistema
            corte_id = db.cerrar_corte_activo(corte_final)
            
            if not corte_id:
                messagebox.showerror("Error", "No se pudo cerrar el corte. No hay corte activo.")
                self._processing = False
                return
            
            # NUEVO: Obtener información completa del corte recién cerrado
            db.cursor.execute('SELECT * FROM cortes WHERE id = ?', (corte_id,))
            corte = dict(db.cursor.fetchone())

            # NUEVO: Crear checkpoint de la base de datos
            db.create_checkpoint(corte['numero_corte'])
            
            # Verificar permisos para mostrar resumen
            mostrar_resumen = True
            if db.is_auth_enabled() and not session.is_admin():
                mostrar_resumen = False

            if mostrar_resumen:
                # NUEVO: Resumen mejorado con separación de efectivo y transferencia
                resumen = f"""
╔══════════════════════════════════════╗
         CORTE DE CAJA #{corte['numero_corte']}
╚══════════════════════════════════════╝

Dinero inicial:          {format_currency(corte['dinero_en_caja'])}

────────────────────────────────────────
VENTAS DEL CORTE:
────────────────────────────────────────
Ventas en Efectivo:      {format_currency(corte['ventas_efectivo'])}
Ventas por Transferencia: {format_currency(corte['ventas_transferencia'])}
Ventas con Tarjeta:      {format_currency(corte['ventas_tarjeta'])}
Total de Ventas:         {format_currency(corte['ventas_efectivo'] + corte['ventas_transferencia'] + corte['ventas_tarjeta'])}

Egresos/Retiros:         {format_currency(corte['retiros'])}

────────────────────────────────────────
RESULTADO DEL CORTE:
────────────────────────────────────────
Corte esperado:          {format_currency(corte['corte_esperado'])}


Corte final (contado):   {format_currency(corte['corte_final'])}

Diferencia:              {format_currency(abs(corte['diferencia']))}
Estado:                  {self.get_estado_emoji(corte['estado'])} {corte['estado']}

────────────────────────────────────────
RENTABILIDAD:
────────────────────────────────────────
Ganancias Netas:         {format_currency(corte['ganancias'])}

────────────────────────────────────────
                """
                
                messagebox.showinfo("Corte de Caja Completado", resumen)
            else:
                messagebox.showinfo("Corte de Caja Completado", "El corte de caja se ha realizado correctamente.")
            
            self.dialog.destroy()
            
            if self.callback:
                self.callback()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al finalizar día: {str(e)}")
            self._processing = False
    
    def get_estado_emoji(self, estado):
        """Retorna emoji según el estado del corte"""
        if estado == 'Cuadrado':
            return '✓'
        elif estado == 'Sobrante':
            return '⬆'
        elif estado == 'Faltante':
            return '⬇'
        return '•'


class RetiroDialog:
    def __init__(self, parent, callback=None):
        self.parent = parent
        self.callback = callback

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Realizar Retiro")
        self.dialog.geometry("450x350") # Adjusted height since description is removed
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

        self.setup_ui()
        self.center_dialog()
        
        # open_cash_drawer() # Removed from here

    def center_dialog(self):
        self.dialog.update_idletasks()
        width = 450
        height = 350 # Adjusted height
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        tk.Label(main_frame, text="Registrar Retiro de Caja", font=FONTS['subtitle'],
                 bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=(0, 20))

        # Monto
        tk.Label(main_frame, text="Monto ($):", font=FONTS['normal'],
                 bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        self.monto_var = tk.StringVar()
        monto_entry = tk.Entry(main_frame, textvariable=self.monto_var, font=FONTS['normal'])
        monto_entry.pack(fill=tk.X, pady=(0, 15))
        monto_entry.focus()

        # Motivo
        tk.Label(main_frame, text="Motivo:", font=FONTS['normal'],
                 bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        self.motivo_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=self.motivo_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 20)) # Adjusted pady

        # Descripción (removed)
        # tk.Label(main_frame, text="Descripción (opcional):", font=FONTS['normal'],
        #          bg=COLORS['bg_primary']).pack(anchor='w', pady=(0, 5))
        # self.descripcion_var = tk.StringVar()
        # tk.Entry(main_frame, textvariable=self.descripcion_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 20))

        # Botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Guardar Retiro", command=self.save_retiro,
                  font=FONTS['button'], bg=COLORS['success'], fg='white').pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                  font=FONTS['button'], bg=COLORS['danger'], fg='white').pack(side=tk.LEFT, padx=10)

    def save_retiro(self):
        monto_str = self.monto_var.get().strip()
        motivo = self.motivo_var.get().strip()
        #descripcion = self.descripcion_var.get().strip() # Removed

        if not monto_str or not motivo:
            messagebox.showerror("Error", "El monto y el motivo son obligatorios.", parent=self.dialog)
            return

        try:
            monto = float(monto_str)
            if monto <= 0:
                messagebox.showerror("Error", "El monto debe ser un número positivo.", parent=self.dialog)
                return
        except ValueError:
            messagebox.showerror("Error", "El monto debe ser un número válido.", parent=self.dialog)
            return

        # Obtener el ID del usuario actual o None si no hay sesión activa
        from auth import session
        usuario_id = session.get_current_user()['id'] if session.is_logged_in() else None
        usuario_nombre = session.get_current_user()['username'] if session.is_logged_in() else "N/A"

        # Obtener el corte activo
        corte_id = db.get_corte_activo_id()
        if not corte_id:
            messagebox.showerror("Error", "No hay un corte de caja activo para registrar el retiro.", parent=self.dialog)
            return

        try:
            # Guardar el retiro en la base de datos
            db.add_retiro(monto, motivo, "", corte_id, usuario_id) # La descripción se eliminó de la UI, se pasa vacío

            # Registrar en auditoría
            db.add_auditoria(usuario_id, 'retiro_caja', f"Retiro de {format_currency(monto)} por '{motivo}' realizado por {usuario_nombre}")

            messagebox.showinfo("Retiro Registrado", "El retiro se ha registrado exitosamente.", parent=self.dialog)
            open_cash_drawer() # Abrir caja después de registrar el retiro
            if self.callback:
                self.callback()
            self.dialog.destroy() # Moved this line

        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar el retiro: {str(e)}", parent=self.dialog)
            self.dialog.destroy() # Moved this line
            
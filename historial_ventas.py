"""
Módulo de Historial de Ventas para Mitsy's POS
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from config import COLORS, FONTS
from utils import format_currency, get_current_datetime, calculate_week_range, calculate_month_range
from database import db

class HistorialVentasWindow:
    def __init__(self, parent, on_close=None):
        self.on_close_callback = on_close
        
        self.window = tk.Toplevel(parent)
        self.window.title("Historial de Ventas - Mitsy's POS")
        self.window.geometry("1400x800")
        self.window.configure(bg=COLORS['bg_primary'])
        
        # Centrar ventana
        self.center_window()
        
        # Forzar al frente
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        # Protocolo de cierre
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        # Variables de filtro
        self.current_filters = {}
        
        self.setup_ui()
        self.load_ventas()
    
    def center_window(self):
        """Centra la ventana en la pantalla"""
        self.window.update_idletasks()
        width = 1400
        height = 800
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(main_frame, text="Historial de Ventas", 
                              font=FONTS['title'], bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=(0, 20))
        
        # Frame de filtros superior
        filters_top_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        filters_top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Búsqueda general
        tk.Label(filters_top_frame, text="Buscar:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(filters_top_frame, textvariable=self.search_var,
                               font=FONTS['normal'], width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # Fecha Inicio
        tk.Label(filters_top_frame, text="Fecha Inicio:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.fecha_inicio = DateEntry(filters_top_frame, width=12, 
                                      background='darkblue', foreground='white',
                                      borderwidth=2, date_pattern='dd/mm/yyyy')
        self.fecha_inicio.pack(side=tk.LEFT, padx=(0, 20))
        
        # Fecha Fin
        tk.Label(filters_top_frame, text="Fecha Fin:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.fecha_fin = DateEntry(filters_top_frame, width=12,
                                   background='darkblue', foreground='white',
                                   borderwidth=2, date_pattern='dd/mm/yyyy')
        self.fecha_fin.pack(side=tk.LEFT, padx=(0, 20))
        
        # Botón aplicar filtros
        tk.Button(filters_top_frame, text="Aplicar Filtros", 
                 command=self.aplicar_filtros,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=15, pady=5).pack(side=tk.LEFT)
        
        # Frame de botones rápidos
        quick_filters_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        quick_filters_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(quick_filters_frame, text="Rápidos:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        quick_buttons = [
            ("Hoy", self.filtro_hoy),
            ("Ayer", self.filtro_ayer),
            ("Esta Semana", self.filtro_semana),
            ("Este Mes", self.filtro_mes),
            ("Limpiar Fechas", self.limpiar_fechas)
        ]
        
        for text, command in quick_buttons:
            btn = tk.Button(quick_filters_frame, text=text, command=command,
                          font=FONTS['normal'], bg=COLORS['button_bg'],
                          relief=tk.RAISED, borderwidth=2, padx=10, pady=3)
            btn.pack(side=tk.LEFT, padx=5)
        
        # Separador
        tk.Label(quick_filters_frame, text="  |  ", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=5)
        
        # Filtros por método de pago
        tk.Button(quick_filters_frame, text="Efectivo", 
                 command=lambda: self.filtro_metodo_pago('Efectivo'),
                 font=FONTS['normal'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(quick_filters_frame, text="Transferencia", 
                 command=lambda: self.filtro_metodo_pago('Transferencia'),
                 font=FONTS['normal'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        # Frame de filtros adicionales
        extra_filters_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        extra_filters_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Más vendido / Menos vendido
        tk.Button(extra_filters_frame, text="Más Vendido", 
                 command=self.filtro_mas_vendido,
                 font=FONTS['normal'], bg=COLORS['button_bg'],
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(extra_filters_frame, text="Menos Vendido", 
                 command=self.filtro_menos_vendido,
                 font=FONTS['normal'], bg=COLORS['button_bg'],
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=20)
        
        # No. Venta
        tk.Label(extra_filters_frame, text="No. Venta:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.num_venta_var = tk.StringVar()
        num_venta_entry = tk.Entry(extra_filters_frame, textvariable=self.num_venta_var,
                                   font=FONTS['normal'], width=10)
        num_venta_entry.pack(side=tk.LEFT, padx=(0, 10))
        num_venta_entry.bind('<Return>', lambda e: self.filtro_numero_venta())
        
        tk.Button(extra_filters_frame, text="Buscar", 
                 command=self.filtro_numero_venta,
                 font=FONTS['normal'], bg=COLORS['button_bg'],
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=(0, 20))
        
        # Limpiar todos los filtros
        tk.Button(extra_filters_frame, text="Limpiar Filtros", 
                 command=self.limpiar_filtros,
                 font=FONTS['button'], bg=COLORS['warning'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=15, pady=5).pack(side=tk.LEFT)
        
        # Frame con scrollbar para la tabla
        table_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview (tabla)
        columns = ('No. Venta', 'Fecha', 'Producto', 'Cantidad', 'Costo', 'Total', 'Método')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar.set, selectmode='extended')
        
        # Configurar columnas
        self.tree.heading('No. Venta', text='No. Venta')
        self.tree.heading('Fecha', text='Fecha')
        self.tree.heading('Producto', text='Producto')
        self.tree.heading('Cantidad', text='Cantidad')
        self.tree.heading('Costo', text='Precio Unitario')
        self.tree.heading('Total', text='Total')
        self.tree.heading('Método', text='Método')
        
        self.tree.column('No. Venta', width=100, anchor='center')
        self.tree.column('Fecha', width=180, anchor='center')
        self.tree.column('Producto', width=250)
        self.tree.column('Cantidad', width=100, anchor='center')
        self.tree.column('Costo', width=150, anchor='e')
        self.tree.column('Total', width=150, anchor='e')
        self.tree.column('Método', width=120, anchor='center')
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Colores alternados
        self.tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        self.tree.tag_configure('efectivo', background='#E8F5E9')
        self.tree.tag_configure('transferencia', background='#E3F2FD')
        
        # Frame de botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(fill=tk.X)
        
        buttons = [
            ("Regresar", self.close_window),
            ("Modificar Venta", self.modificar_venta),
            ("Borrar Venta", self.borrar_venta),
            ("Agregar Venta", self.agregar_venta)
        ]
        
        for text, command in buttons:
            btn = tk.Button(button_frame, text=text, command=command,
                          font=FONTS['button'], bg=COLORS['button_bg'],
                          fg=COLORS['text_primary'], relief=tk.RAISED,
                          borderwidth=2, padx=20, pady=10)
            btn.pack(side=tk.LEFT, padx=5)
    
    def load_ventas(self, ventas=None):
        """Carga las ventas en la tabla"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Obtener ventas
        if ventas is None:
            db.cursor.execute('SELECT * FROM ventas ORDER BY fecha DESC, numero_venta DESC')
            ventas = [dict(row) for row in db.cursor.fetchall()]
        
        # Cargar en tabla
        for idx, v in enumerate(ventas):
            # Determinar tag por método de pago
            if v['metodo_pago'] == 'Efectivo':
                tag = 'efectivo'
            elif v['metodo_pago'] == 'Transferencia':
                tag = 'transferencia'
            else:
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            values = (
                v['numero_venta'],
                v['fecha'],
                v['producto'],
                f"{v['cantidad']:.1f}",
                format_currency(v['precio_unitario']),
                format_currency(v['total']),
                v['metodo_pago']
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
    
    def aplicar_filtros(self):
        """Aplica los filtros de búsqueda"""
        query = self.search_var.get().strip()
        fecha_inicio = self.fecha_inicio.get_date()
        fecha_fin = self.fecha_fin.get_date()
        
        # Construir query SQL
        sql = 'SELECT * FROM ventas WHERE 1=1'
        params = []
        
        # Filtro de búsqueda general
        if query:
            from utils import normalize_text
            sql += ' AND (LOWER(producto) LIKE ? OR CAST(numero_venta AS TEXT) LIKE ?)'
            params.extend([f'%{query.lower()}%', f'%{query}%'])
        
        # Filtro de fechas
        fecha_inicio_str = fecha_inicio.strftime('%d/%m/%Y')
        fecha_fin_str = fecha_fin.strftime('%d/%m/%Y')
        
        sql += ' AND DATE(SUBSTR(fecha, 7, 4) || "-" || SUBSTR(fecha, 4, 2) || "-" || SUBSTR(fecha, 1, 2)) BETWEEN ? AND ?'
        params.extend([fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')])
        
        sql += ' ORDER BY fecha DESC, numero_venta DESC'
        
        # Ejecutar query
        db.cursor.execute(sql, params)
        ventas = [dict(row) for row in db.cursor.fetchall()]
        
        self.load_ventas(ventas)
    
    def filtro_hoy(self):
        """Filtra ventas de hoy"""
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy)
        self.fecha_fin.set_date(hoy)
        self.aplicar_filtros()
    
    def filtro_ayer(self):
        """Filtra ventas de ayer"""
        ayer = datetime.now().date() - timedelta(days=1)
        self.fecha_inicio.set_date(ayer)
        self.fecha_fin.set_date(ayer)
        self.aplicar_filtros()
    
    def filtro_semana(self):
        """Filtra ventas de esta semana (viernes a miércoles)"""
        viernes, miercoles = calculate_week_range()
        self.fecha_inicio.set_date(viernes.date())
        self.fecha_fin.set_date(miercoles.date())
        self.aplicar_filtros()
    
    def filtro_mes(self):
        """Filtra ventas de este mes (día 1 hasta hoy)"""
        primer_dia, hoy = calculate_month_range()
        self.fecha_inicio.set_date(primer_dia.date())
        self.fecha_fin.set_date(hoy.date())
        self.aplicar_filtros()
    
    def limpiar_fechas(self):
        """Limpia los filtros de fecha"""
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy - timedelta(days=30))
        self.fecha_fin.set_date(hoy)
        self.aplicar_filtros()
    
    def filtro_metodo_pago(self, metodo):
        """Filtra por método de pago"""
        db.cursor.execute('SELECT * FROM ventas WHERE metodo_pago = ? ORDER BY fecha DESC', (metodo,))
        ventas = [dict(row) for row in db.cursor.fetchall()]
        self.load_ventas(ventas)
    
    def filtro_mas_vendido(self):
        """Muestra el producto más vendido"""
        db.cursor.execute('''
            SELECT producto, SUM(cantidad) as total_cantidad, COUNT(*) as num_ventas
            FROM ventas
            GROUP BY producto
            ORDER BY total_cantidad DESC
            LIMIT 1
        ''')
        
        result = db.cursor.fetchone()
        if result:
            producto_mas_vendido = result['producto']
            db.cursor.execute('SELECT * FROM ventas WHERE producto = ? ORDER BY fecha DESC', 
                            (producto_mas_vendido,))
            ventas = [dict(row) for row in db.cursor.fetchall()]
            self.load_ventas(ventas)
            
            messagebox.showinfo("Producto Más Vendido", 
                              f"Producto: {producto_mas_vendido}\n"
                              f"Cantidad total vendida: {result['total_cantidad']:.1f}\n"
                              f"Número de ventas: {result['num_ventas']}")
    
    def filtro_menos_vendido(self):
        """Muestra el producto menos vendido"""
        db.cursor.execute('''
            SELECT producto, SUM(cantidad) as total_cantidad, COUNT(*) as num_ventas
            FROM ventas
            GROUP BY producto
            ORDER BY total_cantidad ASC
            LIMIT 1
        ''')
        
        result = db.cursor.fetchone()
        if result:
            producto_menos_vendido = result['producto']
            db.cursor.execute('SELECT * FROM ventas WHERE producto = ? ORDER BY fecha DESC', 
                            (producto_menos_vendido,))
            ventas = [dict(row) for row in db.cursor.fetchall()]
            self.load_ventas(ventas)
            
            messagebox.showinfo("Producto Menos Vendido", 
                              f"Producto: {producto_menos_vendido}\n"
                              f"Cantidad total vendida: {result['total_cantidad']:.1f}\n"
                              f"Número de ventas: {result['num_ventas']}")
    
    def filtro_numero_venta(self):
        """Filtra por número de venta"""
        num_venta = self.num_venta_var.get().strip()
        if not num_venta:
            messagebox.showwarning("Advertencia", "Ingresa un número de venta")
            return
        
        try:
            num_venta = int(num_venta)
            db.cursor.execute('SELECT * FROM ventas WHERE numero_venta = ? ORDER BY fecha DESC', 
                            (num_venta,))
            ventas = [dict(row) for row in db.cursor.fetchall()]
            
            if not ventas:
                messagebox.showinfo("No encontrado", f"No se encontró la venta #{num_venta}")
            
            self.load_ventas(ventas)
        except ValueError:
            messagebox.showerror("Error", "El número de venta debe ser un número entero")
    
    def limpiar_filtros(self):
        """Limpia todos los filtros"""
        self.search_var.set("")
        self.num_venta_var.set("")
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy - timedelta(days=30))
        self.fecha_fin.set_date(hoy)
        self.load_ventas()
    
    def modificar_venta(self):
        """Abre diálogo para modificar venta"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona una venta para modificar")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona solo una venta para modificar")
            return
        
        item = self.tree.item(selection[0])
        venta_id = self.get_venta_id_from_values(item['values'])
        
        if venta_id:
            VentaDialog(self.window, venta_id=venta_id, callback=self.load_ventas)
    
    def borrar_venta(self):
        """Elimina ventas seleccionadas"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona al menos una venta para borrar")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Estás seguro de borrar {len(selection)} venta(s)?\n\n"
                                   "ADVERTENCIA: Esto NO restaurará el inventario."):
            return
        
        for item in selection:
            values = self.tree.item(item)['values']
            venta_id = self.get_venta_id_from_values(values)
            if venta_id:
                db.cursor.execute('DELETE FROM ventas WHERE id = ?', (venta_id,))
        
        db.conn.commit()
        messagebox.showinfo("Éxito", "Venta(s) eliminada(s) correctamente")
        self.load_ventas()
    
    def agregar_venta(self):
        """Abre diálogo para agregar venta manual"""
        VentaDialog(self.window, callback=self.load_ventas)
    
    def get_venta_id_from_values(self, values):
        """Obtiene el ID de la venta desde los valores mostrados"""
        numero_venta = values[0]
        fecha = values[1]
        producto = values[2]
        
        db.cursor.execute('''
            SELECT id FROM ventas 
            WHERE numero_venta = ? AND fecha = ? AND producto = ?
            LIMIT 1
        ''', (numero_venta, fecha, producto))
        
        result = db.cursor.fetchone()
        return result['id'] if result else None
    
    def close_window(self):
        """Cierra la ventana y vuelve al menú"""
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()


class VentaDialog:
    def __init__(self, parent, venta_id=None, callback=None):
        self.venta_id = venta_id
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Añadir Venta" if not venta_id else "Modificar Venta")
        self.dialog.geometry("500x600")
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
        
        if venta_id:
            self.load_venta_data()
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 500
        height = 600
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Número de venta
        tk.Label(main_frame, text="Número de Venta:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(10, 5))
        self.num_venta_var = tk.StringVar()
        if not self.venta_id:
            self.num_venta_var.set(str(db.get_next_numero_venta()))
        tk.Entry(main_frame, textvariable=self.num_venta_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Fecha
        tk.Label(main_frame, text="Fecha:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.fecha_var = tk.StringVar(value=get_current_datetime())
        tk.Entry(main_frame, textvariable=self.fecha_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Producto
        tk.Label(main_frame, text="Producto:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        
        self.producto_var = tk.StringVar()
        self.producto_combo = ttk.Combobox(main_frame, textvariable=self.producto_var,
                                          font=FONTS['normal'], state='readonly')
        self.producto_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Cargar productos
        productos = db.get_productos()
        self.productos_dict = {f"{p['nombre']} (ID: {p['id']})": p for p in productos}
        self.producto_combo['values'] = list(self.productos_dict.keys())
        
        # Cantidad
        tk.Label(main_frame, text="Cantidad:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.cantidad_var = tk.StringVar(value="1")
        tk.Entry(main_frame, textvariable=self.cantidad_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Precio Unitario
        tk.Label(main_frame, text="Precio Unitario:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.precio_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=self.precio_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Total (calculado automáticamente)
        tk.Label(main_frame, text="Total:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.total_var = tk.StringVar(value="0.00")
        total_label = tk.Label(main_frame, textvariable=self.total_var, 
                              font=FONTS['heading'], bg=COLORS['bg_secondary'],
                              fg=COLORS['accent'], relief=tk.SUNKEN, padx=10, pady=5)
        total_label.pack(fill=tk.X, pady=(0, 10))
        
        # Actualizar total automáticamente
        self.cantidad_var.trace('w', self.calcular_total)
        self.precio_var.trace('w', self.calcular_total)
        
        # Método de pago
        tk.Label(main_frame, text="Método de Pago:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        
        metodo_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        metodo_frame.pack(anchor='w', pady=(0, 10))
        
        self.metodo_var = tk.StringVar(value='Efectivo')
        
        tk.Radiobutton(metodo_frame, text="Efectivo", variable=self.metodo_var,
                      value='Efectivo', font=FONTS['normal'],
                      bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(metodo_frame, text="Transferencia", variable=self.metodo_var,
                      value='Transferencia', font=FONTS['normal'],
                      bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=10)
        
        # Mesa (opcional)
        tk.Label(main_frame, text="Mesa (opcional):", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.mesa_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=self.mesa_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Aceptar", command=self.save_venta,)
"""
Módulo de Historial de Ventas para Mitsy's POS (REWORK)
Con dos vistas: Analytics y Detalle
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from config import COLORS, FONTS
from utils import format_currency, get_current_datetime, calculate_week_range, calculate_month_range
from database import db
from excel_utils import ExcelManager, importar_ventas_excel

class HistorialVentasWindow:
    def __init__(self, parent, on_close=None):
        self.on_close_callback = on_close
        
        self.window = tk.Toplevel(parent)
        self.window.title("Historial de Ventas - Mitsy's POS")
        self.window.state("zoomed")
        self.window.configure(bg=COLORS['bg_primary'])
        
    
        
        # Forzar al frente
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        # Protocolo de cierre
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        # Variables de filtro
        self.current_filters = {}
        
        # Mostrar vista de analytics por defecto
        self.show_analytics_view()
    
    def center_window(self):
        """Centra la ventana en la pantalla"""
        self.window.update_idletasks()
        width = 1400
        height = 950
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def clear_window(self):
        """Limpia la ventana y quita bindeos de mouse"""
        self.window.unbind_all('<MouseWheel>')
        for widget in self.window.winfo_children():
            widget.destroy()
    
    def show_analytics_view(self):
        """Muestra la vista principal de analytics"""
        self.clear_window()

        # --- Implementación de Scroll ---
        # 1. Contenedor principal que aloja el canvas y la scrollbar
        container = tk.Frame(self.window, bg=COLORS['bg_primary'])
        container.pack(fill=tk.BOTH, expand=True)

        # 2. Canvas para hacer el contenido desplazable
        canvas = tk.Canvas(container, bg=COLORS['bg_primary'], highlightthickness=0)
        
        # 3. Scrollbar
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # 4. Frame interior que contendrá todos los widgets
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # 5. Funciones para configurar el scroll y el tamaño del frame
        def on_frame_configure(event):
            # Cada vez que el frame interior cambia de tamaño, actualizamos la región de scroll
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            # Ajustar el ancho del frame interior al ancho del canvas
            canvas.itemconfig(canvas_window, width=event.width)

        scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        # 6. Bindeo de la rueda del mouse para el scroll
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bindeamos al canvas y al frame interior. No usamos bind_all para no interferir con los Treeviews.
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
        canvas.bind('<Leave>', lambda e: self.window.unbind_all('<MouseWheel>'))

        # --- Fin de Implementación de Scroll ---

        # El 'main_frame' ahora se coloca dentro del 'scrollable_frame' para tener el padding correcto
        main_frame = tk.Frame(scrollable_frame, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(main_frame, text="Historial de Ventas - Analytics", 
                              font=FONTS['title'], bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=(0, 20))
        
        # Frame de filtros
        self.setup_analytics_filters(main_frame)
        
        # Contenedor para las dos tablas
        tables_container = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        tables_container.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Tabla de productos (Arriba)
        self.setup_products_table(tables_container)
        
        # Tabla de fechas (Abajo)
        self.setup_dates_table(tables_container)
        
        # Botones inferiores
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(fill=tk.X)
        
        tk.Button(button_frame, text="Cambiar Vista", command=self.show_detail_view,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Regresar", command=self.close_window,
                 font=FONTS['button'], bg=COLORS['button_bg'],
                 fg=COLORS['text_primary'], relief=tk.RAISED,
                 borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        # Cargar datos iniciales
        self.load_analytics_data()
    
    def setup_analytics_filters(self, parent):
        """Configura los filtros para la vista de analytics"""
        # Frame de filtros superior
        filters_top_frame = tk.Frame(parent, bg=COLORS['bg_primary'])
        filters_top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Fecha Inicio
        tk.Label(filters_top_frame, text="Fecha Inicio:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.analytics_fecha_inicio = DateEntry(filters_top_frame, width=12, 
                                               background='darkblue', foreground='white',
                                               borderwidth=2, date_pattern='dd/mm/yyyy')
        # Por defecto: último mes
        self.analytics_fecha_inicio.set_date(datetime.now().date() - timedelta(days=30))
        self.analytics_fecha_inicio.pack(side=tk.LEFT, padx=(0, 10))
        
        # Fecha Fin
        tk.Label(filters_top_frame, text="Fecha Fin:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.analytics_fecha_fin = DateEntry(filters_top_frame, width=12,
                                            background='darkblue', foreground='white',
                                            borderwidth=2, date_pattern='dd/mm/yyyy')
        self.analytics_fecha_fin.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botón aplicar filtros
        tk.Button(filters_top_frame, text="Aplicar Filtros", 
                 command=self.load_analytics_data,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=15, pady=5).pack(side=tk.LEFT, padx=(0, 15))

        # Separador
        tk.Label(filters_top_frame, text="|", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=5)

        # Botones rápidos
        quick_buttons = [
            ("Hoy", self.analytics_filtro_hoy),
            ("Ayer", self.analytics_filtro_ayer),
            ("Esta Semana", self.analytics_filtro_semana),
            ("Este Mes", self.analytics_filtro_mes),
        ]
        
        for text, command in quick_buttons:
            btn = tk.Button(filters_top_frame, text=text, command=command,
                          font=FONTS['normal'], bg=COLORS['button_bg'],
                          relief=tk.RAISED, borderwidth=2, padx=10, pady=3)
            btn.pack(side=tk.LEFT, padx=5)

        # Botón para limpiar filtros
        tk.Button(filters_top_frame, text="Limpiar Filtros", 
                 command=self.analytics_limpiar_filtros,
                 font=FONTS['normal'], bg=COLORS['warning'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=(15, 5))
    
    def setup_products_table(self, parent):
        """Configura la tabla de productos"""
        products_frame = tk.LabelFrame(parent, text="Análisis por Producto", 
                                      font=FONTS['heading'],
                                      bg=COLORS['bg_primary'],
                                      fg=COLORS['text_primary'])
        products_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Botones de exportación
        export_button_frame = tk.Frame(products_frame, bg=COLORS['bg_primary'])
        export_button_frame.pack(anchor='ne', pady=(0, 5), padx=5)

        tk.Button(export_button_frame, text="Exportar a Excel",
                  command=self.exportar_productos_analytics,
                  font=FONTS['normal'], bg=COLORS['success'], fg='white',
                  relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack()
        
        # Frame con scrollbar
        table_frame = tk.Frame(products_frame, bg=COLORS['bg_primary'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Columnas
        columns = ('Producto', 'P. Unitario', 'Unidades Vendidas', 'Costo/Pieza', 
                   'Costo Total', 'Profit/Pieza', 'Ingresos Totales', 'Profit Total')
        
        self.products_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                         yscrollcommand=scrollbar.set, selectmode='browse')
        
        # Configurar columnas
        self.products_tree.heading('Producto', text='Producto')
        self.products_tree.heading('P. Unitario', text='P. Unitario')
        self.products_tree.heading('Unidades Vendidas', text='Unidades Vendidas')
        self.products_tree.heading('Costo/Pieza', text='Costo/Pieza')
        self.products_tree.heading('Costo Total', text='Costo Total')
        self.products_tree.heading('Profit/Pieza', text='Profit/Pieza')
        self.products_tree.heading('Ingresos Totales', text='Ingresos Totales')
        self.products_tree.heading('Profit Total', text='Profit Total')
        
        self.products_tree.column('Producto', width=180)
        self.products_tree.column('P. Unitario', width=100, anchor='e')
        self.products_tree.column('Unidades Vendidas', width=140, anchor='center')
        self.products_tree.column('Costo/Pieza', width=110, anchor='e')
        self.products_tree.column('Costo Total', width=110, anchor='e')
        self.products_tree.column('Profit/Pieza', width=110, anchor='e')
        self.products_tree.column('Ingresos Totales', width=130, anchor='e')
        self.products_tree.column('Profit Total', width=120, anchor='e')
        
        self.products_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.products_tree.yview)
        
        # Colores alternados
        self.products_tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.products_tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
    
    def setup_dates_table(self, parent):
        """Configura la tabla de fechas"""
        dates_frame = tk.LabelFrame(parent, text="Análisis por Fecha", 
                                   font=FONTS['heading'],
                                   bg=COLORS['bg_primary'],
                                   fg=COLORS['text_primary'])
        dates_frame.pack(fill=tk.BOTH, expand=True)
        
        # Botones de exportación
        export_button_frame = tk.Frame(dates_frame, bg=COLORS['bg_primary'])
        export_button_frame.pack(anchor='ne', pady=(0, 5), padx=5)

        tk.Button(export_button_frame, text="Exportar a Excel",
                  command=self.exportar_fechas_analytics,
                  font=FONTS['normal'], bg=COLORS['success'], fg='white',
                  relief=tk.RAISED, borderwidth=2, padx=9, pady=2).pack()
        
        # Frame con scrollbar
        table_frame = tk.Frame(dates_frame, bg=COLORS['bg_primary'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Columnas
        columns = ('Fecha', 'Ingresos Totales', 'Costos', 'Profit')
        
        self.dates_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                      yscrollcommand=scrollbar.set, selectmode='browse')
        
        # Configurar columnas
        self.dates_tree.heading('Fecha', text='Fecha')
        self.dates_tree.heading('Ingresos Totales', text='Ingresos Totales')
        self.dates_tree.heading('Costos', text='Costos')
        self.dates_tree.heading('Profit', text='Profit')
        
        self.dates_tree.column('Fecha', width=200, anchor='center')
        self.dates_tree.column('Ingresos Totales', width=200, anchor='e')
        self.dates_tree.column('Costos', width=200, anchor='e')
        self.dates_tree.column('Profit', width=200, anchor='e')
        
        self.dates_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.dates_tree.yview)
        
        # Colores alternados
        self.dates_tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.dates_tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        self.dates_tree.tag_configure('total', background='#E3F2FD', font=FONTS['heading'])
    
    def load_analytics_data(self):
        """Carga los datos de analytics"""
        fecha_inicio = self.analytics_fecha_inicio.get_date()
        fecha_fin = self.analytics_fecha_fin.get_date()
        
        # Limpiar tablas
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        for item in self.dates_tree.get_children():
            self.dates_tree.delete(item)
        
        # Obtener datos de productos
        self.load_products_analytics(fecha_inicio, fecha_fin)
        
        # Obtener datos por fecha
        self.load_dates_analytics(fecha_inicio, fecha_fin)
    
    def load_products_analytics(self, fecha_inicio, fecha_fin):
        """Carga análisis por producto"""
        # Query para obtener productos
        db.cursor.execute('''
            SELECT 
                p.id,
                p.nombre,
                p.precio_unitario,
                p.costo,
                p.ganancia,
                COALESCE(SUM(v.cantidad), 0) as unidades_vendidas,
                COALESCE(SUM(v.total), 0) as ingresos_totales
            FROM productos p
            LEFT JOIN ventas v ON p.id = v.id_producto
                AND DATE(SUBSTR(v.fecha, 7, 4) || "-" || SUBSTR(v.fecha, 4, 2) || "-" || SUBSTR(v.fecha, 1, 2)) 
                    BETWEEN ? AND ?
            WHERE p.activo = 1
            GROUP BY p.id, p.nombre, p.precio_unitario, p.costo, p.ganancia
            ORDER BY unidades_vendidas DESC
        ''', (fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')))
        
        productos = [dict(row) for row in db.cursor.fetchall()]
        
        for idx, prod in enumerate(productos):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            # Calcular valores
            costo_pieza = prod['costo']
            costo_total = costo_pieza * prod['unidades_vendidas']
            profit_pieza = prod['ganancia']
            profit_total = profit_pieza * prod['unidades_vendidas']
            
            # Si no hay recetas o gestión de stock, mostrar vacío en columnas de costo
            if costo_pieza == 0:
                costo_pieza_str = ""
                costo_total_str = ""
                profit_pieza_str = ""
                profit_total_str = ""
            else:
                costo_pieza_str = format_currency(costo_pieza)
                costo_total_str = format_currency(costo_total)
                profit_pieza_str = format_currency(profit_pieza)
                profit_total_str = format_currency(profit_total)
            
            values = (
                prod['nombre'],
                format_currency(prod['precio_unitario']),
                f"{prod['unidades_vendidas']:.0f}",
                costo_pieza_str,
                costo_total_str,
                profit_pieza_str,
                format_currency(prod['ingresos_totales']),
                profit_total_str
            )
            
            self.products_tree.insert('', tk.END, values=values, tags=(tag,))
    
    def load_dates_analytics(self, fecha_inicio, fecha_fin):
        """Carga análisis por fecha"""
        # Query para obtener datos por fecha
        db.cursor.execute('''
            SELECT 
                DATE(SUBSTR(v.fecha, 7, 4) || "-" || SUBSTR(v.fecha, 4, 2) || "-" || SUBSTR(v.fecha, 1, 2)) as fecha_sql,
                SUBSTR(v.fecha, 1, 10) as fecha_display,
                SUM(v.total) as ingresos,
                SUM(p.costo * v.cantidad) as costos,
                SUM((p.precio_unitario - p.costo) * v.cantidad) as profit
            FROM ventas v
            JOIN productos p ON v.id_producto = p.id
            WHERE DATE(SUBSTR(v.fecha, 7, 4) || "-" || SUBSTR(v.fecha, 4, 2) || "-" || SUBSTR(v.fecha, 1, 2))
                BETWEEN ? AND ?
            GROUP BY fecha_sql, fecha_display
            ORDER BY fecha_sql ASC
        ''', (fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')))
        
        fechas = [dict(row) for row in db.cursor.fetchall()]
        
        # Variables para totales
        total_ingresos = 0
        total_costos = 0
        total_profit = 0
        
        for idx, fecha in enumerate(fechas):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            ingresos = fecha['ingresos'] if fecha['ingresos'] else 0
            costos = fecha['costos'] if fecha['costos'] else 0
            profit = fecha['profit'] if fecha['profit'] else 0
            
            total_ingresos += ingresos
            total_costos += costos
            total_profit += profit
            
            # Si no hay costos calculables, mostrar vacío
            costos_str = format_currency(costos) if costos > 0 else ""
            profit_str = format_currency(profit) if costos > 0 else ""
            
            values = (
                fecha['fecha_display'],
                format_currency(ingresos),
                costos_str,
                profit_str
            )
            
            self.dates_tree.insert('', tk.END, values=values, tags=(tag,))
        
        # Agregar fila de TOTAL
        if fechas:
            total_costos_str = format_currency(total_costos) if total_costos > 0 else ""
            total_profit_str = format_currency(total_profit) if total_costos > 0 else ""
            
            total_values = (
                "TOTAL",
                format_currency(total_ingresos),
                total_costos_str,
                total_profit_str
            )
            
            self.dates_tree.insert('', tk.END, values=total_values, tags=('total',))
    
    # Filtros para analytics
    def analytics_filtro_hoy(self):
        """Filtra datos de hoy"""
        hoy = datetime.now().date()
        self.analytics_fecha_inicio.set_date(hoy)
        self.analytics_fecha_fin.set_date(hoy)
        self.load_analytics_data()
    
    def analytics_filtro_ayer(self):
        """Filtra datos de ayer"""
        ayer = datetime.now().date() - timedelta(days=1)
        self.analytics_fecha_inicio.set_date(ayer)
        self.analytics_fecha_fin.set_date(ayer)
        self.load_analytics_data()
    
    def analytics_filtro_semana(self):
        """Filtra datos de esta semana"""
        viernes, miercoles = calculate_week_range()
        self.analytics_fecha_inicio.set_date(viernes.date())
        self.analytics_fecha_fin.set_date(miercoles.date())
        self.load_analytics_data()
    
    def analytics_filtro_mes(self):
        """Filtra datos de este mes"""
        primer_dia, hoy = calculate_month_range()
        self.analytics_fecha_inicio.set_date(primer_dia.date())
        self.analytics_fecha_fin.set_date(hoy.date())
        self.load_analytics_data()
    
    def analytics_limpiar_filtros(self):
        """Limpia filtros de analytics"""
        hoy = datetime.now().date()
        self.analytics_fecha_inicio.set_date(hoy - timedelta(days=30))
        self.analytics_fecha_fin.set_date(hoy)
        self.load_analytics_data()
    
    
    
    
    
    def exportar_productos_analytics(self):
        """Exporta la tabla de análisis de productos a Excel"""
        ExcelManager.exportar_treeview_a_excel(
            self.products_tree, 
            "analisis_productos", 
            "Análisis por Producto"
        )

    def exportar_fechas_analytics(self):
        """Exporta la tabla de análisis por fecha a Excel"""
        ExcelManager.exportar_treeview_a_excel(
            self.dates_tree, 
            "analisis_fechas", 
            "Análisis por Fecha"
        )

    # ==================== VISTA DE DETALLE ====================
    
    def show_detail_view(self):
        """Muestra la vista de detalle (historial original)"""
        self.clear_window()
        
        main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(main_frame, text="Historial de Ventas - Detalle", 
                              font=FONTS['title'], bg=COLORS['bg_primary'],
                              fg=COLORS['text_primary'])
        title_label.pack(pady=(0, 20))
        
        # Setup filtros
        self.setup_detail_filters(main_frame)
        
        # Frame con scrollbar para la tabla
        table_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview (tabla)
        columns = ('No. Venta', 'Fecha', 'Producto', 'ID Producto', 'Cantidad', 'Precio Unitario', 'Total', 'Método')
        
        self.detail_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                       yscrollcommand=scrollbar.set, selectmode='extended')
        
        # Configurar columnas
        self.detail_tree.heading('No. Venta', text='No. Venta')
        self.detail_tree.heading('Fecha', text='Fecha')
        self.detail_tree.heading('Producto', text='Producto')
        self.detail_tree.heading('ID Producto', text='ID Prod.')
        self.detail_tree.heading('Cantidad', text='Cantidad')
        self.detail_tree.heading('Precio Unitario', text='Precio Unitario')
        self.detail_tree.heading('Total', text='Total')
        self.detail_tree.heading('Método', text='Método')
        
        self.detail_tree.column('No. Venta', width=100, anchor='center')
        self.detail_tree.column('Fecha', width=180, anchor='center')
        self.detail_tree.column('Producto', width=250)
        self.detail_tree.column('ID Producto', width=80, anchor='center')
        self.detail_tree.column('Cantidad', width=100, anchor='center')
        self.detail_tree.column('Precio Unitario', width=150, anchor='e')
        self.detail_tree.column('Total', width=150, anchor='e')
        self.detail_tree.column('Método', width=120, anchor='center')
        
        self.detail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.detail_tree.yview)
        
        # Colores alternados
        self.detail_tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.detail_tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        self.detail_tree.tag_configure('efectivo', background='#E8F5E9')
        self.detail_tree.tag_configure('transferencia', background='#E3F2FD')
        
        # Frame de botones de acción
        action_button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        action_button_frame.pack(fill=tk.X, pady=(0, 10))
        
        buttons = [
            ("Regresar", self.show_analytics_view),
            ("Modificar Venta", self.modificar_venta),
            ("Borrar Venta", self.borrar_venta),
            ("Agregar Venta", self.agregar_venta)
        ]
        
        for text, command in buttons:
            btn = tk.Button(action_button_frame, text=text, command=command,
                          font=FONTS['button'], bg=COLORS['button_bg'],
                          fg=COLORS['text_primary'], relief=tk.RAISED,
                          borderwidth=2, padx=15, pady=10)
            btn.pack(side=tk.LEFT, padx=5)

        tk.Button(action_button_frame, text="Exportar a Excel", 
                  command=self.exportar_ventas_detalle,
                  font=FONTS['button'], bg=COLORS['success'], fg='white',
                  relief=tk.RAISED, borderwidth=2, padx=15, pady=10).pack(side=tk.LEFT, padx=5)

        tk.Button(action_button_frame, text="Importar desde Excel", 
                  command=self.importar_ventas_detalle,
                  font=FONTS['button'], bg=COLORS['accent'], fg='white',
                  relief=tk.RAISED, borderwidth=2, padx=15, pady=10).pack(side=tk.LEFT, padx=5)
        
        # --- Zona de Peligro ---
        danger_zone_frame = tk.LabelFrame(main_frame, text="Zona de Peligro", 
                                          font=FONTS['heading'], fg="red",
                                          bg=COLORS['bg_primary'], relief=tk.RIDGE, borderwidth=2)
        danger_zone_frame.pack(fill=tk.X, pady=(20, 0), padx=5)

        tk.Button(danger_zone_frame, text="Reemplazar Base de Datos", 
                  command=self.reemplazar_base_de_datos_ventas,
                  font=FONTS['button'], bg=COLORS['danger'], fg='white',
                  relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=10, pady=10)

        tk.Button(danger_zone_frame, text="Borrar Toda la Información", 
                  command=self.borrar_todas_las_ventas,
                  font=FONTS['button'], bg=COLORS['danger'], fg='white',
                  relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=10, pady=10)
        
        # Cargar datos
        self.load_detail_data()
    
    def setup_detail_filters(self, parent):
        """Configura los filtros para la vista de detalle"""
        # Frame de filtros superior
        filters_top_frame = tk.Frame(parent, bg=COLORS['bg_primary'])
        filters_top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Búsqueda general
        tk.Label(filters_top_frame, text="Buscar:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.detail_search_var = tk.StringVar()
        search_entry = tk.Entry(filters_top_frame, textvariable=self.detail_search_var,
                               font=FONTS['normal'], width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # Fecha Inicio
        tk.Label(filters_top_frame, text="Fecha Inicio:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.detail_fecha_inicio = DateEntry(filters_top_frame, width=12, 
                                             background='darkblue', foreground='white',
                                             borderwidth=2, date_pattern='dd/mm/yyyy')
        self.detail_fecha_inicio.pack(side=tk.LEFT, padx=(0, 20))
        
        # Fecha Fin
        tk.Label(filters_top_frame, text="Fecha Fin:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.detail_fecha_fin = DateEntry(filters_top_frame, width=12,
                                          background='darkblue', foreground='white',
                                          borderwidth=2, date_pattern='dd/mm/yyyy')
        self.detail_fecha_fin.pack(side=tk.LEFT, padx=(0, 20))
        
        # Botón aplicar filtros
        tk.Button(filters_top_frame, text="Aplicar Filtros", 
                 command=self.aplicar_filtros_detail,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=15, pady=5).pack(side=tk.LEFT)
        
        # Frame de botones rápidos
        quick_filters_frame = tk.Frame(parent, bg=COLORS['bg_primary'])
        quick_filters_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(quick_filters_frame, text="Rápidos:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
        
        quick_buttons = [
            ("Hoy", self.detail_filtro_hoy),
            ("Ayer", self.detail_filtro_ayer),
            ("Esta Semana", self.detail_filtro_semana),
            ("Este Mes", self.detail_filtro_mes),
            ("Limpiar Fechas", self.detail_limpiar_fechas)
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
                 command=lambda: self.detail_filtro_metodo_pago('Efectivo'),
                 font=FONTS['normal'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(quick_filters_frame, text="Transferencia", 
                 command=lambda: self.detail_filtro_metodo_pago('Transferencia'),
                 font=FONTS['normal'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        # Frame de filtros adicionales
        extra_filters_frame = tk.Frame(parent, bg=COLORS['bg_primary'])
        extra_filters_frame.pack(fill=tk.X, pady=(0, 10))
        
        # No. Venta
        tk.Label(extra_filters_frame, text="No. Venta:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.detail_num_venta_var = tk.StringVar()
        num_venta_entry = tk.Entry(extra_filters_frame, textvariable=self.detail_num_venta_var,
                                   font=FONTS['normal'], width=10)
        num_venta_entry.pack(side=tk.LEFT, padx=(0, 10))
        num_venta_entry.bind('<Return>', lambda e: self.detail_filtro_numero_venta())
        
        tk.Button(extra_filters_frame, text="Buscar", 
                 command=self.detail_filtro_numero_venta,
                 font=FONTS['normal'], bg=COLORS['button_bg'],
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=(0, 20))
        
        # Limpiar todos los filtros
        tk.Button(extra_filters_frame, text="Limpiar Filtros", 
                 command=self.detail_limpiar_filtros,
                 font=FONTS['button'], bg=COLORS['warning'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=15, pady=5).pack(side=tk.LEFT)
    
    def load_detail_data(self, ventas=None):
        """Carga las ventas en la tabla de detalle"""
        # Limpiar tabla
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)
        
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
                v['id_producto'],
                f"{v['cantidad']:.1f}",
                format_currency(v['precio_unitario']),
                format_currency(v['total']),
                v['metodo_pago']
            )
            
            self.detail_tree.insert('', tk.END, values=values, tags=(tag,))
    
    def aplicar_filtros_detail(self):
        """Aplica los filtros de búsqueda en detalle"""
        query = self.detail_search_var.get().strip()
        fecha_inicio = self.detail_fecha_inicio.get_date()
        fecha_fin = self.detail_fecha_fin.get_date()
        
        # Construir query SQL
        sql = 'SELECT * FROM ventas WHERE 1=1'
        params = []
        
        # Filtro de búsqueda general
        if query:
            from utils import normalize_text
            sql += ' AND (LOWER(producto) LIKE ? OR CAST(numero_venta AS TEXT) LIKE ?)'
            params.extend([f'%{query.lower()}%', f'%{query}%'])
        
        # Filtro de fechas
        sql += ' AND DATE(SUBSTR(fecha, 7, 4) || "-" || SUBSTR(fecha, 4, 2) || "-" || SUBSTR(fecha, 1, 2)) BETWEEN ? AND ?'
        params.extend([fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')])
        
        sql += ' ORDER BY fecha DESC, numero_venta DESC'
        
        # Ejecutar query
        db.cursor.execute(sql, params)
        ventas = [dict(row) for row in db.cursor.fetchall()]
        
        self.load_detail_data(ventas)
    
    def detail_filtro_hoy(self):
        """Filtra ventas de hoy"""
        hoy = datetime.now().date()
        self.detail_fecha_inicio.set_date(hoy)
        self.detail_fecha_fin.set_date(hoy)
        self.aplicar_filtros_detail()
    
    def detail_filtro_ayer(self):
        """Filtra ventas de ayer"""
        ayer = datetime.now().date() - timedelta(days=1)
        self.detail_fecha_inicio.set_date(ayer)
        self.detail_fecha_fin.set_date(ayer)
        self.aplicar_filtros_detail()
    
    def detail_filtro_semana(self):
        """Filtra ventas de esta semana"""
        viernes, miercoles = calculate_week_range()
        self.detail_fecha_inicio.set_date(viernes.date())
        self.detail_fecha_fin.set_date(miercoles.date())
        self.aplicar_filtros_detail()
    
    def detail_filtro_mes(self):
        """Filtra ventas de este mes"""
        primer_dia, hoy = calculate_month_range()
        self.detail_fecha_inicio.set_date(primer_dia.date())
        self.detail_fecha_fin.set_date(hoy.date())
        self.aplicar_filtros_detail()
    
    def detail_limpiar_fechas(self):
        """Limpia los filtros de fecha"""
        hoy = datetime.now().date()
        self.detail_fecha_inicio.set_date(hoy - timedelta(days=30))
        self.detail_fecha_fin.set_date(hoy)
        self.aplicar_filtros_detail()
    
    def detail_filtro_metodo_pago(self, metodo):
        """Filtra por método de pago"""
        db.cursor.execute('SELECT * FROM ventas WHERE metodo_pago = ? ORDER BY fecha DESC', (metodo,))
        ventas = [dict(row) for row in db.cursor.fetchall()]
        self.load_detail_data(ventas)
    
    def detail_filtro_numero_venta(self):
        """Filtra por número de venta"""
        num_venta = self.detail_num_venta_var.get().strip()
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
            
            self.load_detail_data(ventas)
        except ValueError:
            messagebox.showerror("Error", "El número de venta debe ser un número entero")
    
    def detail_limpiar_filtros(self):
        """Limpia todos los filtros"""
        self.detail_search_var.set("")
        self.detail_num_venta_var.set("")
        hoy = datetime.now().date()
        self.detail_fecha_inicio.set_date(hoy - timedelta(days=30))
        self.detail_fecha_fin.set_date(hoy)
        self.load_detail_data()
    
    def modificar_venta(self):
        """Abre diálogo para modificar venta"""
        selection = self.detail_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona una venta para modificar")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona solo una venta para modificar")
            return
        
        item = self.detail_tree.item(selection[0])
        venta_id = self.get_venta_id_from_values(item['values'])
        
        if venta_id:
            VentaDialog(self.window, venta_id=venta_id, callback=self.load_detail_data)
    
    def borrar_venta(self):
        """Elimina ventas seleccionadas"""
        selection = self.detail_tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona al menos una venta para borrar")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Estás seguro de borrar {len(selection)} venta(s)?\n\n" 
                                   "ADVERTENCIA: Esto NO restaurará el inventario."):
            return
        
        for item in selection:
            values = self.detail_tree.item(item)['values']
            venta_id = self.get_venta_id_from_values(values)
            if venta_id:
                db.cursor.execute('DELETE FROM ventas WHERE id = ?', (venta_id,))
        
        db.conn.commit()
        messagebox.showinfo("Éxito", "Venta(s) eliminada(s) correctamente")
        self.load_detail_data()
    
    def agregar_venta(self):
        """Abre diálogo para agregar venta manual"""
        VentaDialog(self.window, callback=self.load_detail_data)
    
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
    
    def exportar_ventas_detalle(self):
        """Exporta la tabla de detalle de ventas a Excel"""
        ExcelManager.exportar_treeview_a_excel(
            self.detail_tree, 
            "historial_ventas_detalle", 
            "Detalle de Ventas"
        )

    def importar_ventas_detalle(self):
        """Importa ventas desde un archivo Excel"""
        if not messagebox.askokcancel("Importar Ventas",
                                      "Se intentarán agregar las ventas desde un archivo Excel.\n\n"
                                      "Asegúrate de que el archivo tenga el formato correcto y que los 'ID Producto' existan en la base de datos.\n\n"
                                      "Se recomienda hacer un respaldo de la base de datos antes de proceder."):
            return

        ventas_a_importar = importar_ventas_excel()

        if not ventas_a_importar:
            return

        errores = []
        exitos = 0
        for venta in ventas_a_importar:
            try:
                # Verificar si el producto existe
                db.cursor.execute("SELECT id FROM productos WHERE id = ?", (venta['id_producto'],))
                if not db.cursor.fetchone():
                    errores.append(f"Venta para producto '{venta['producto']}' (ID: {venta['id_producto']}) omitida: El producto no existe.")
                    continue

                db.add_imported_venta(
                    numero_venta=venta['numero_venta'],
                    fecha=venta['fecha'],
                    producto=venta['producto'],
                    id_producto=venta['id_producto'],
                    cantidad=venta['cantidad'],
                    precio_unitario=venta['precio_unitario'],
                    total=venta['total'],
                    metodo_pago=venta['metodo_pago'],
                    mesa=venta.get('mesa')
                )
                exitos += 1
            except Exception as e:
                errores.append(f"Error al importar venta para producto '{venta['producto']}': {e}")
        
        if exitos > 0:
            db.conn.commit()
            messagebox.showinfo("Importación Parcial/Completa", f"{exitos} venta(s) importada(s) correctamente.")
        else:
            db.conn.rollback()

        if errores:
            error_str = "\n".join(errores)
            messagebox.showwarning("Errores de Importación", f"Ocurrieron los siguientes errores:\n\n{error_str}")

        self.load_detail_data()
    
    def borrar_todas_las_ventas(self):
        """Elimina TODAS las ventas del historial."""
        if not messagebox.askyesno("Confirmación Extrema",
                                   "¿ESTÁS COMPLETAMENTE SEGURO?\n\n"
                                   "Esta acción borrará permanentemente TODO el historial de ventas. "
                                   "Esta acción no se puede deshacer.\n\n"
                                   "Se recomienda encarecidamente hacer una copia de seguridad de 'data/mitsys.db' antes de continuar.\n\n"
                                   "¿Deseas continuar y borrar todas las ventas?"):
            return
        
        try:
            db.borrar_todas_las_ventas_db()
            messagebox.showinfo("Éxito", "Se ha borrado todo el historial de ventas.")
            self.load_detail_data()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al borrar las ventas:\n{e}")

    def reemplazar_base_de_datos_ventas(self):
        """Reemplaza la base de datos de ventas con datos de un archivo Excel."""
        if not messagebox.askyesno("Confirmación Extrema",
                                   "¿ESTÁS COMPLETAMENTE SEGURO?\n\n"
                                   "Esta acción reemplazará permanentemente TODO el historial de ventas con los datos del archivo que selecciones. "
                                   "La información actual se perderá.\n\n"
                                   "Asegúrate de que el archivo Excel tiene el formato correcto.\n\n"
                                   "¿Deseas continuar?"):
            return

        ventas_a_importar = importar_ventas_excel()

        if not ventas_a_importar:
            return

        try:
            db.reemplazar_ventas(ventas_a_importar)
            messagebox.showinfo("Éxito", f"La base de datos de ventas ha sido reemplazada con {len(ventas_a_importar)} registros.")
            self.load_detail_data()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al reemplazar la base de datos:\n{e}")
            # Recargar los datos originales si es posible, aunque ya se borraron.
            self.load_detail_data()
    
    def close_window(self):
        """Cierra la ventana y vuelve al menú"""
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()


# Clase VentaDialog (mantener la del código original)
class VentaDialog:
    def __init__(self, parent, venta_id=None, callback=None):
        self.venta_id = venta_id
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Añadir Venta" if not venta_id else "Modificar Venta")
        self.dialog.geometry("500x800")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        self.center_dialog()
        self.setup_ui()
        
        if venta_id:
            self.load_venta_data()
    
    def center_dialog(self):
        self.dialog.update_idletasks()
        width = 500
        height = 700
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
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
        
        tk.Button(button_frame, text="Aceptar", command=self.save_venta,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def calcular_total(self, *args):
        try:
            cantidad = float(self.cantidad_var.get())
            precio = float(self.precio_var.get())
            total = cantidad * precio
            self.total_var.set(format_currency(total))
        except ValueError:
            self.total_var.set("$0.00")
    
    def load_venta_data(self):
        db.cursor.execute('SELECT * FROM ventas WHERE id = ?', (self.venta_id,))
        venta = db.cursor.fetchone()
        
        if not venta:
            messagebox.showerror("Error", "Venta no encontrada")
            self.dialog.destroy()
            return
        
        venta = dict(venta)
        
        self.num_venta_var.set(str(venta['numero_venta']))
        self.fecha_var.set(venta['fecha'])
        
        producto_key = f"{venta['producto']} (ID: {venta['id_producto']})"
        if producto_key in self.productos_dict:
            self.producto_var.set(producto_key)
        
        self.cantidad_var.set(str(venta['cantidad']))
        self.precio_var.set(str(venta['precio_unitario']))
        self.metodo_var.set(venta['metodo_pago'])
        if venta['mesa']:
            self.mesa_var.set(venta['mesa'])
    
    def save_venta(self):
        try:
            numero_venta = int(self.num_venta_var.get())
            fecha = self.fecha_var.get().strip()
            cantidad = float(self.cantidad_var.get())
            precio = float(self.precio_var.get())
        except ValueError:
            messagebox.showerror("Error", "Valores numéricos inválidos")
            return
        
        if not fecha or not self.producto_var.get():
            messagebox.showerror("Error", "Completa todos los campos obligatorios")
            return
        
        producto = self.productos_dict[self.producto_var.get()]
        total = cantidad * precio
        metodo_pago = self.metodo_var.get()
        mesa = self.mesa_var.get().strip() if self.mesa_var.get() else None
        
        try:
            if self.venta_id:
                db.cursor.execute('''
                    UPDATE ventas 
                    SET numero_venta = ?, fecha = ?, producto = ?, id_producto = ?,
                        cantidad = ?, precio_unitario = ?, total = ?, metodo_pago = ?, mesa = ?
                    WHERE id = ?
                ''', (numero_venta, fecha, producto['nombre'], producto['id'],
                      cantidad, precio, total, metodo_pago, mesa, self.venta_id))
            else:
                db.add_venta(numero_venta, producto['nombre'], producto['id'],
                           cantidad, precio, total, metodo_pago, mesa)
                
                ultimo_num = int(db.get_config('ultimo_numero_venta') or 0)
                if numero_venta > ultimo_num:
                    db.set_config('ultimo_numero_venta', str(numero_venta))
            
            db.conn.commit()
            messagebox.showinfo("Éxito", "Venta guardada correctamente")
            
            if self.callback:
                self.callback()
            
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar venta: {str(e)}")
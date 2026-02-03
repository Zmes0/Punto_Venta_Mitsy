"""
Módulo de Historial de Cortes para Mitsy's POS (OPTIMIZADO)
Optimizaciones:
- Queries simplificadas sin conversiones innecesarias de fechas
- Uso de SUBSTR para comparaciones de fechas
- Límites en consultas iniciales
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from config import COLORS, FONTS
from utils import format_currency, get_current_datetime, calculate_week_range, calculate_month_range, get_resource_path
import utils
from database import db
from excel_utils import ExcelManager, exportar_cortes_excel, importar_cortes_excel

class CortesWindow:
    def __init__(self, parent, on_close=None, authorized_admin_id=None):
        self.on_close_callback = on_close
        self.authorized_admin_id = authorized_admin_id
        
        self.window = tk.Toplevel(parent)
        self.window.title("Cortes - Mitsy's POS")
        self.window.state("zoomed")
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.minsize(1400, 800)
        
        # Forzar al frente
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        self.window.iconbitmap(get_resource_path('icono.ico'))
        
        # Protocolo de cierre
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        self.setup_ui()
        # Cargar datos de forma diferida
        self.window.after(100, self.load_cortes)
    
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
        title_label = tk.Label(main_frame, text="Cortes", 
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
        
        # Set default dates
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy - timedelta(days=30))
        self.fecha_fin.set_date(hoy)
        
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
        
        # Filtros por estado
        tk.Button(quick_filters_frame, text="Sobrante", 
                 command=lambda: self.filtro_estado('Sobrante'),
                 font=FONTS['normal'], bg='#E3F2FD', fg='black',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(quick_filters_frame, text="Faltante", 
                 command=lambda: self.filtro_estado('Faltante'),
                 font=FONTS['normal'], bg='#FFEBEE', fg='black',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(quick_filters_frame, text="Cuadrado", 
                 command=lambda: self.filtro_estado('Cuadrado'),
                 font=FONTS['normal'], bg='#E8F5E9', fg='black',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        # Frame de filtros adicionales
        extra_filters_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        extra_filters_frame.pack(fill=tk.X, pady=(0, 10))
        
        # No. Corte
        tk.Label(extra_filters_frame, text="No. Corte:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.num_corte_var = tk.StringVar()
        num_corte_entry = tk.Entry(extra_filters_frame, textvariable=self.num_corte_var,
                                   font=FONTS['normal'], width=10)
        num_corte_entry.pack(side=tk.LEFT, padx=(0, 10))
        num_corte_entry.bind('<Return>', lambda e: self.filtro_numero_corte())
        
        tk.Button(extra_filters_frame, text="Buscar", 
                 command=self.filtro_numero_corte,
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
        columns = ('ID', 'No. Corte', 'Fecha', 'Dinero en Caja', 'Corte Final', 
                   'Corte Esperado', 'Retiros', 'Diferencia', 'Estado', 
                   'Ventas Efectivo', 'Ventas Transferencia', 'Ventas Tarjeta', 'Total Ventas',
                   'Usuario Inicio', 'Usuario Cierre')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar.set, selectmode='extended')
        utils.enable_drag_selection(self.tree)
        
        # Configurar columnas
        for col in columns:
            self.tree.heading(col, text=col)
        
        self.tree.column('ID', width=0, stretch=tk.NO)
        self.tree.column('No. Corte', width=100, anchor='center')
        self.tree.column('Fecha', width=180, anchor='center')
        self.tree.column('Dinero en Caja', width=130, anchor='e')
        self.tree.column('Corte Final', width=120, anchor='e')
        self.tree.column('Corte Esperado', width=130, anchor='e')
        self.tree.column('Retiros', width=100, anchor='e')
        self.tree.column('Diferencia', width=100, anchor='e')
        self.tree.column('Estado', width=100, anchor='center')
        self.tree.column('Ventas Efectivo', width=130, anchor='e')
        self.tree.column('Ventas Transferencia', width=150, anchor='e')
        self.tree.column('Ventas Tarjeta', width=120, anchor='e')
        self.tree.column('Total Ventas', width=120, anchor='e')
        self.tree.column('Usuario Inicio', width=120, anchor='center')
        self.tree.column('Usuario Cierre', width=120, anchor='center')
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Colores por estado
        self.tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        self.tree.tag_configure('Cuadrado', background='#E8F5E9')
        self.tree.tag_configure('Sobrante', background='#E3F2FD')
        self.tree.tag_configure('Faltante', background='#FFEBEE')
        
        # Doble clic para ver detalles
        self.tree.bind('<Double-1>', self.ver_detalles_corte)
        
        # Frame de botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(fill=tk.X)
        
        buttons = [
            ("Regresar", self.close_window, COLORS['button_bg'], COLORS['text_primary']),
            ("Ver Detalles", self.ver_detalles_corte, COLORS['button_bg'], COLORS['text_primary']),
            ("Modificar Corte", self.modificar_corte, COLORS['button_bg'], COLORS['text_primary']),
            ("Borrar Corte", self.borrar_corte, COLORS['button_bg'], COLORS['text_primary']),
            ("Agregar Corte", self.agregar_corte, COLORS['button_bg'], COLORS['text_primary']),
            ("Exportar a Excel", self.exportar_cortes, COLORS['success'], 'white'),
            ("Importar desde Excel", self.importar_cortes, COLORS['accent'], 'white')
        ]
        
        for text, command, bg, fg in buttons:
            btn = tk.Button(button_frame, text=text, command=command,
                  font=FONTS['button'], bg=bg, fg=fg,
                  relief=tk.RAISED, borderwidth=2, padx=20, pady=10)
            btn.pack(side=tk.LEFT, padx=5)
    
    def load_cortes(self, cortes=None):
        """Carga los cortes en la tabla - OPTIMIZADO"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if cortes is None:
            # Query optimizada con límite
            db.cursor.execute('''
                SELECT c.*, u_inicio.username AS usuario_inicio_username, u_cierre.username AS usuario_cierre_username
                FROM cortes c
                LEFT JOIN usuarios u_inicio ON c.usuario_inicio_id = u_inicio.id
                LEFT JOIN usuarios u_cierre ON c.usuario_cierre_id = u_cierre.id
                ORDER BY numero_corte DESC
                LIMIT 500
            ''')
            cortes = [dict(row) for row in db.cursor.fetchall()]
        
        for idx, c in enumerate(cortes):
            tag = c['estado']
            
            fecha_mostrar = c['fecha_cierre'] if c['fecha_cierre'] else c['fecha_inicio']
            
            # Calcular total de ventas
            total_ventas = c.get('ventas_efectivo', 0) + c.get('ventas_transferencia', 0) + c.get('ventas_tarjeta', 0)
            
            values = (
                c['id'],
                c['numero_corte'],
                fecha_mostrar,
                format_currency(c['dinero_en_caja']),
                format_currency(c['corte_final']),
                format_currency(c['corte_esperado']),
                format_currency(c['retiros']),
                format_currency(c['diferencia']),
                c['estado'],
                format_currency(c.get('ventas_efectivo', 0)),
                format_currency(c.get('ventas_transferencia', 0)),
                format_currency(c.get('ventas_tarjeta', 0)),
                format_currency(total_ventas),
                c['usuario_inicio_username'] if c['usuario_inicio_username'] else 'N/A',
                c['usuario_cierre_username'] if c['usuario_cierre_username'] else 'N/A'
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
    
    def aplicar_filtros(self):
        """Aplica los filtros de búsqueda de texto y fecha - OPTIMIZADO"""
        query = self.search_var.get().strip()
        
        try:
            fecha_inicio = self.fecha_inicio.get_date()
            fecha_fin = self.fecha_fin.get_date()
        except (ValueError, TypeError):
            messagebox.showerror("Error de Fecha", "El formato de fecha no es válido.")
            return

        # Convertir a formato YYYY-MM-DD
        fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
        fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')

        sql = '''
            SELECT c.*, u_inicio.username AS usuario_inicio_username, u_cierre.username AS usuario_cierre_username
            FROM cortes c
            LEFT JOIN usuarios u_inicio ON c.usuario_inicio_id = u_inicio.id
            LEFT JOIN usuarios u_cierre ON c.usuario_cierre_id = u_cierre.id
            WHERE 1=1
        '''
        params = []
        
        if query:
            sql += ' AND (LOWER(c.estado) LIKE ? OR CAST(c.numero_corte AS TEXT) LIKE ? OR LOWER(u_inicio.username) LIKE ? OR LOWER(u_cierre.username) LIKE ?)'
            params.extend([f'%{query.lower()}%', f'%{query.lower()}%', f'%{query.lower()}%', f'%{query.lower()}%'])
        
        # Filtro de fechas OPTIMIZADO - convertir DD/MM/YYYY a YYYY-MM-DD para comparar
        sql += ''' AND (SUBSTR(c.fecha_inicio, 7, 4) || '-' || SUBSTR(c.fecha_inicio, 4, 2) || '-' || SUBSTR(c.fecha_inicio, 1, 2)) >= ? 
                   AND (SUBSTR(c.fecha_inicio, 7, 4) || '-' || SUBSTR(c.fecha_inicio, 4, 2) || '-' || SUBSTR(c.fecha_inicio, 1, 2)) <= ?'''
        params.extend([fecha_inicio_str, fecha_fin_str])
        
        sql += ' ORDER BY c.numero_corte DESC LIMIT 500'
        
        db.cursor.execute(sql, params)
        cortes = [dict(row) for row in db.cursor.fetchall()]
        
        self.load_cortes(cortes)
    
    def filtro_hoy(self):
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy)
        self.fecha_fin.set_date(hoy)
        self.aplicar_filtros()
    
    def filtro_ayer(self):
        ayer = datetime.now().date() - timedelta(days=1)
        self.fecha_inicio.set_date(ayer)
        self.fecha_fin.set_date(ayer)
        self.aplicar_filtros()
    
    def filtro_semana(self):
        viernes, miercoles = calculate_week_range()
        self.fecha_inicio.set_date(viernes.date())
        self.fecha_fin.set_date(miercoles.date())
        self.aplicar_filtros()
    
    def filtro_mes(self):
        primer_dia, hoy = calculate_month_range()
        self.fecha_inicio.set_date(primer_dia.date())
        self.fecha_fin.set_date(hoy.date())
        self.aplicar_filtros()
    
    def limpiar_fechas(self):
        """ Restablece las fechas al rango por defecto y aplica el filtro. """
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy - timedelta(days=30))
        self.fecha_fin.set_date(hoy)
        self.aplicar_filtros()
    
    def filtro_estado(self, estado):
        """Filtra los cortes por estado, ignorando otros filtros."""
        self.search_var.set("")
        self.num_corte_var.set("")
        
        sql = '''
            SELECT c.*, u_inicio.username AS usuario_inicio_username, u_cierre.username AS usuario_cierre_username
            FROM cortes c
            LEFT JOIN usuarios u_inicio ON c.usuario_inicio_id = u_inicio.id
            LEFT JOIN usuarios u_cierre ON c.usuario_cierre_id = u_cierre.id
            WHERE c.estado = ? 
            ORDER BY c.numero_corte DESC
        '''
        db.cursor.execute(sql, (estado,))
        cortes = [dict(row) for row in db.cursor.fetchall()]
        
        if not cortes:
            messagebox.showinfo("No encontrado", f"No se encontraron cortes con estado '{estado}' en todo el historial.")
        
        self.load_cortes(cortes)
    
    def filtro_numero_corte(self):
        num_corte = self.num_corte_var.get().strip()
        if not num_corte:
            self.load_cortes()
            return
        
        try:
            num_corte_int = int(num_corte)
            sql = '''
                SELECT c.*, u_inicio.username AS usuario_inicio_username, u_cierre.username AS usuario_cierre_username
                FROM cortes c
                LEFT JOIN usuarios u_inicio ON c.usuario_inicio_id = u_inicio.id
                LEFT JOIN usuarios u_cierre ON c.usuario_cierre_id = u_cierre.id
                WHERE c.numero_corte = ?
                ORDER BY c.fecha_inicio DESC
            '''
            db.cursor.execute(sql, (num_corte_int,))
            cortes = [dict(row) for row in db.cursor.fetchall()]
            
            if not cortes:
                messagebox.showinfo("No encontrado", f"No se encontró el corte #{num_corte}")
            
            self.load_cortes(cortes)
        except ValueError:
            messagebox.showerror("Error", "El número de corte debe ser un número entero")
    
    def limpiar_filtros(self):
        self.search_var.set("")
        self.num_corte_var.set("")
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy - timedelta(days=30))
        self.fecha_fin.set_date(hoy)
        self.load_cortes()
    
    def get_selected_corte_id(self, required=True):
        """Obtiene el ID del corte seleccionado en la tabla"""
        selection = self.tree.selection()
        
        if not selection:
            if required:
                messagebox.showwarning("Advertencia", "Por favor selecciona un corte.")
            return None
        
        if len(selection) > 1:
            if required:
                messagebox.showwarning("Advertencia", "Por favor selecciona solo un corte.")
            return None
            
        item = self.tree.item(selection[0])
        return item['values'][0]

    def ver_detalles_corte(self, event=None):
        corte_id = self.get_selected_corte_id()
        if corte_id:
            DetallesCorteDialog(self.window, corte_id)
    
    def modificar_corte(self):
        corte_id = self.get_selected_corte_id()
        if corte_id:
            CorteDialog(self.window, corte_id=corte_id, callback=self.load_cortes)
    
    def borrar_corte(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona al menos un corte para borrar.")
            return

        ids_to_delete = []
        for item_id in selection:
            item = self.tree.item(item_id)
            corte_id = item['values'][0]
            
            db.cursor.execute("SELECT estado_corte FROM cortes WHERE id = ?", (corte_id,))
            corte = db.cursor.fetchone()
            if corte and corte['estado_corte'] == 'abierto':
                messagebox.showerror("Error", "No se puede borrar el corte de caja que está actualmente abierto.")
                return
            
            ids_to_delete.append(corte_id)

        if not messagebox.askyesno("Confirmar", f"¿Estás seguro de borrar {len(selection)} corte(s)? Esta acción no se puede deshacer."):
            return
        
        db.delete_cortes_and_reorganize(ids_to_delete)
        
        messagebox.showinfo("Éxito", f"{len(ids_to_delete)} corte(s) eliminado(s) correctamente.")
        self.load_cortes()
    
    def agregar_corte(self):
        CorteDialog(self.window, callback=self.load_cortes)
    
    def close_window(self):
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()
    
    def exportar_cortes(self):
        """Exporta los cortes mostrados actualmente a Excel"""
        corte_ids = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            corte_ids.append(values[0])
    
        if not corte_ids:
            messagebox.showwarning("Sin datos", "No hay cortes para exportar")
            return
    
        placeholders = ','.join('?' for _ in corte_ids)
        db.cursor.execute(f'''
            SELECT numero_corte, fecha_inicio, fecha_cierre, dinero_en_caja,
                   ventas_efectivo, ventas_transferencia, ventas_tarjeta, corte_final,
                   corte_esperado, retiros, diferencia, estado, ganancias
            FROM cortes
            WHERE id IN ({placeholders})
            ORDER BY numero_corte DESC
        ''', corte_ids)
    
        cortes = [dict(row) for row in db.cursor.fetchall()]
    
        from excel_utils import exportar_cortes_excel
        exportar_cortes_excel(cortes)
        
    def importar_cortes(self):
        """Importa cortes desde un archivo Excel"""
        if not messagebox.askokcancel("Importar Cortes",
                                  "Se intentarán agregar los cortes desde un archivo Excel.\n\n"
                                  "Los cortes con números duplicados serán ignorados.\n\n"
                                  "Se recomienda hacer un respaldo de la base de datos antes de proceder."):
            return
    
        cortes_a_importar = importar_cortes_excel()
    
        if not cortes_a_importar:
            return
    
        errores = []
        exitos = 0
        
        for corte in cortes_a_importar:
            try:
                # Verificar si el número de corte ya existe
                db.cursor.execute("SELECT id FROM cortes WHERE numero_corte = ?", (corte['numero_corte'],))
                if db.cursor.fetchone():
                    errores.append(f"Corte #{corte['numero_corte']} ya existe. Omitido.")
                    continue
            
                # Extraer valores con valores por defecto
                dinero_caja = float(corte.get('dinero_en_caja', 0))
                ventas_efectivo = float(corte.get('ventas_efectivo', 0))
                ventas_transferencia = float(corte.get('ventas_transferencia', 0))
                ventas_tarjeta = float(corte.get('ventas_tarjeta', 0))
                corte_final = float(corte.get('corte_final', 0))
                retiros = float(corte.get('retiros', 0))
                ganancias = float(corte.get('ganancias', 0))
                fecha_inicio = str(corte.get('fecha_inicio', ''))
            
                # Validar fecha_inicio
                if not fecha_inicio:
                    errores.append(f"Corte #{corte['numero_corte']}: Fecha Inicio es obligatoria.")
                    continue
                
                # Calcular valores derivados
                corte_esperado = dinero_caja + ventas_efectivo - retiros
                diferencia = corte_final - corte_esperado
                
                if abs(diferencia) < 0.01:
                    estado = 'Cuadrado'
                elif diferencia > 0:
                    estado = 'Sobrante'
                else:
                    estado = 'Faltante'
                    
                # Fecha cierre: usar la del Excel si existe, sino usar fecha_inicio
                fecha_cierre = corte.get('fecha_cierre', None)
                if fecha_cierre:
                    fecha_cierre = str(fecha_cierre)
                else:
                    fecha_cierre = fecha_inicio
                    
                # Insertar corte
                db.cursor.execute('''
                    INSERT INTO cortes (
                        numero_corte, fecha_inicio, fecha_cierre, dinero_en_caja,
                        ventas_efectivo, ventas_transferencia, ventas_tarjeta, corte_final,
                        corte_esperado, retiros, diferencia, estado, ganancias, estado_corte
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'cerrado')    
                ''', (
                    corte['numero_corte'],
                    fecha_inicio,
                    fecha_cierre,
                    dinero_caja,
                    ventas_efectivo,
                    ventas_transferencia,
                    ventas_tarjeta,
                    corte_final,
                    corte_esperado,
                    retiros,
                    diferencia,
                    estado,
                    ganancias
                ))
                
                exitos += 1
                
            except KeyError as e:
                errores.append(f"Corte #{corte.get('numero_corte', '?')}: Falta el campo {str(e)}")
            except Exception as e:
                errores.append(f"Corte #{corte.get('numero_corte', '?')}: {str(e)}")

        if exitos > 0:
            db.conn.commit()
            
            # Actualizar ultimo_numero_corte si es necesario
            db.cursor.execute('SELECT MAX(numero_corte) as max_num FROM cortes')
            result = db.cursor.fetchone()
            max_num = result['max_num'] if result['max_num'] else 0
            db.set_config('ultimo_numero_corte', str(max_num))
        
            messagebox.showinfo("Importación Completada", 
                              f"{exitos} corte(s) importado(s) correctamente.")
        else:
            db.conn.rollback()
            
        if errores:
            error_str = "\n".join(errores[:10])
            if len(errores) > 10:
                error_str += f"\n\n... y {len(errores) - 10} errores más."
            messagebox.showwarning("Errores de Importación", 
                                 f"Ocurrieron los siguientes errores:\n\n{error_str}")
    
        # Recargar la tabla
        self.load_cortes()
        

# Las clases DetallesCorteDialog y CorteDialog permanecen sin cambios
# ya que no tienen problemas de rendimiento significativos

class DetallesCorteDialog:
    def __init__(self, parent, corte_id):
        self.corte_id = corte_id
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Detalles del Corte")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.geometry("850x550")
        self.dialog.minsize(850, 550)
        
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        self.center_dialog()
        self.setup_ui()
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
    
    def center_dialog(self):
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def add_info_grid(self, parent, row, col, label, value, color=None, columnspan=1):
        tk.Label(parent, text=label, font=FONTS['normal'],
                bg=COLORS['bg_secondary'], anchor='w').grid(row=row, column=col, sticky='w', padx=(20, 10), pady=5)
        
        value_color = color if color else COLORS['text_primary']
        value_label = tk.Label(parent, text=str(value), font=FONTS['heading'],
                bg=COLORS['bg_secondary'], fg=value_color, anchor='w')
        value_label.grid(row=row, column=col + 1, sticky='w', padx=(0, 20), pady=5, columnspan=columnspan)
        return value_label

    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        db.cursor.execute('SELECT * FROM cortes WHERE id = ?', (self.corte_id,))
        corte = db.cursor.fetchone()
        
        if not corte:
            messagebox.showerror("Error", "Corte no encontrado")
            self.dialog.destroy()
            return
        
        corte = dict(corte)
        
        tk.Label(main_frame, text=f"Corte de Caja #{corte['numero_corte']}", 
                font=FONTS['title'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=(0, 15))
        
        info_frame = tk.Frame(main_frame, bg=COLORS['bg_secondary'],
                             relief=tk.RAISED, borderwidth=1)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        info_frame.columnconfigure(1, weight=1)
        info_frame.columnconfigure(3, weight=1)

        # Data
        usuario_inicio_username = db.get_usuario(corte['usuario_inicio_id'])['username'] if corte['usuario_inicio_id'] else 'N/A'
        usuario_cierre_username = db.get_usuario(corte['usuario_cierre_id'])['username'] if corte['usuario_cierre_id'] else 'N/A'
        total_ventas = corte['ventas_efectivo'] + corte['ventas_transferencia'] + corte['ventas_tarjeta']

        # Layout using grid
        row = 0
        # Section titles
        tk.Label(info_frame, text="Información General", font=FONTS['heading'], bg=COLORS['bg_secondary'], fg=COLORS['accent']).grid(row=row, column=0, columnspan=2, sticky='w', padx=20, pady=(10,5))
        tk.Label(info_frame, text="Resumen de Ventas", font=FONTS['heading'], bg=COLORS['bg_secondary'], fg=COLORS['accent']).grid(row=row, column=2, columnspan=2, sticky='w', padx=20, pady=(10,5))
        row += 1

        # Row 1
        self.add_info_grid(info_frame, row, 0, "Fecha Inicio:", corte['fecha_inicio'])
        self.add_info_grid(info_frame, row, 2, "Ventas en Efectivo:", format_currency(corte['ventas_efectivo']))
        row += 1
        
        # Row 2
        if corte['fecha_cierre']:
            self.add_info_grid(info_frame, row, 0, "Fecha Cierre:", corte['fecha_cierre'])
        self.add_info_grid(info_frame, row, 2, "Ventas Transferencia:", format_currency(corte['ventas_transferencia']))
        row += 1

        # Row 3
        self.add_info_grid(info_frame, row, 0, "Iniciado por:", usuario_inicio_username)
        self.add_info_grid(info_frame, row, 2, "Ventas con Tarjeta:", format_currency(corte['ventas_tarjeta']))
        row += 1

        # Row 4
        self.add_info_grid(info_frame, row, 0, "Cerrado por:", usuario_cierre_username)
        self.add_info_grid(info_frame, row, 2, "Total de Ventas:", format_currency(total_ventas), COLORS['accent'])
        row += 1

        # Separator
        tk.Frame(info_frame, bg=COLORS['border'], height=1).grid(row=row, columnspan=4, sticky='ew', pady=10, padx=20)
        row += 1

        # Row 5
        self.add_info_grid(info_frame, row, 0, "Dinero en Caja:", format_currency(corte['dinero_en_caja']))
        self.add_info_grid(info_frame, row, 2, "Corte Esperado:", format_currency(corte['corte_esperado']))
        row += 1

        # Row 6
        if corte['retiros'] > 0:
            self.add_info_grid(info_frame, row, 0, "Retiros/Egresos:", format_currency(corte['retiros']))
        self.add_info_grid(info_frame, row, 2, "Corte Final (contado):", format_currency(corte['corte_final']), COLORS['accent'])
        row += 1

        # Separator
        tk.Frame(info_frame, bg=COLORS['border'], height=1).grid(row=row, columnspan=4, sticky='ew', pady=10, padx=20)
        row += 1

        # Results section
        diferencia_color = COLORS['success'] if corte['estado'] == 'Sobrante' else COLORS['danger'] if corte['estado'] == 'Faltante' else COLORS['text_primary']
        estado_color = COLORS['accent'] if corte['estado'] == 'Cuadrado' else diferencia_color

        self.add_info_grid(info_frame, row, 0, "Diferencia:", format_currency(corte['diferencia']), diferencia_color)
        self.add_info_grid(info_frame, row, 2, "Estado del Corte:", corte['estado'], estado_color)
        row += 1

        self.add_info_grid(info_frame, row, 0, "Ganancias del Día:", format_currency(corte['ganancias']), COLORS['success'], columnspan=3)
        
        tk.Button(main_frame, text="Cerrar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=40, pady=10).pack(side=tk.BOTTOM, pady=(20,0))


class CorteDialog:
    def __init__(self, parent, corte_id=None, callback=None):
        self.corte_id = corte_id
        self.callback = callback
        self.corte_data = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Añadir Corte" if not corte_id else "Modificar Corte")
        self.dialog.geometry("900x700")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        self.dialog.minsize(900, 700)
        
        self.center_dialog()
        self.setup_ui()
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
        
        if self.corte_id:
            self.load_corte_data()
        
        self.calcular_diferencia()

    def center_dialog(self):
        self.dialog.update_idletasks()
        width = 900
        height = 700
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Variables
        self.num_corte_var = tk.StringVar()
        self.fecha_inicio_var = tk.StringVar(value=get_current_datetime())
        self.fecha_cierre_var = tk.StringVar(value=get_current_datetime())
        self.dinero_caja_var = tk.StringVar(value="0")
        self.ventas_efectivo_var = tk.StringVar(value="0")
        self.ventas_transferencia_var = tk.StringVar(value="0")
        self.ventas_tarjeta_var = tk.StringVar(value="0")
        self.corte_final_var = tk.StringVar(value="0")
        self.retiros_var = tk.StringVar(value="0")
        self.ganancias_var = tk.StringVar(value="0")
        self.corte_esperado_var = tk.StringVar()
        self.diferencia_var = tk.StringVar()
        self.estado_var = tk.StringVar()

        # Trace
        for var in [self.dinero_caja_var, self.ventas_efectivo_var, self.ventas_transferencia_var, self.ventas_tarjeta_var, self.retiros_var, self.corte_final_var]:
            var.trace('w', self.calcular_diferencia)

        # Input Widgets Frame
        inputs_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        inputs_frame.pack(fill=tk.X, pady=(10, 20))
        inputs_frame.columnconfigure(1, weight=1)
        inputs_frame.columnconfigure(3, weight=1)

        # Column 1
        tk.Label(inputs_frame, text="Número de Corte:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        num_corte_entry = tk.Entry(inputs_frame, textvariable=self.num_corte_var, font=FONTS['normal'])
        num_corte_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        if not self.corte_id:
            self.num_corte_var.set(str(db.get_next_numero_corte()))

        tk.Label(inputs_frame, text="Fecha Inicio:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=1, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(inputs_frame, textvariable=self.fecha_inicio_var, font=FONTS['normal']).grid(row=1, column=1, sticky='ew', padx=5, pady=5)

        tk.Label(inputs_frame, text="Fecha Cierre (opcional):", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=2, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(inputs_frame, textvariable=self.fecha_cierre_var, font=FONTS['normal']).grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        
        tk.Label(inputs_frame, text="Dinero en Caja (Inicial):", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=3, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(inputs_frame, textvariable=self.dinero_caja_var, font=FONTS['normal']).grid(row=3, column=1, sticky='ew', padx=5, pady=5)

        tk.Label(inputs_frame, text="Ganancias del Día:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=4, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(inputs_frame, textvariable=self.ganancias_var, font=FONTS['normal']).grid(row=4, column=1, sticky='ew', padx=5, pady=5)

        # Column 2
        tk.Label(inputs_frame, text="Ventas en Efectivo:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=0, column=2, sticky='w', padx=(20, 5), pady=5)
        tk.Entry(inputs_frame, textvariable=self.ventas_efectivo_var, font=FONTS['normal']).grid(row=0, column=3, sticky='ew', padx=5, pady=5)

        tk.Label(inputs_frame, text="Ventas por Transferencia:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=1, column=2, sticky='w', padx=(20, 5), pady=5)
        tk.Entry(inputs_frame, textvariable=self.ventas_transferencia_var, font=FONTS['normal']).grid(row=1, column=3, sticky='ew', padx=5, pady=5)

        tk.Label(inputs_frame, text="Ventas con Tarjeta:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=2, column=2, sticky='w', padx=(20, 5), pady=5)
        tk.Entry(inputs_frame, textvariable=self.ventas_tarjeta_var, font=FONTS['normal']).grid(row=2, column=3, sticky='ew', padx=5, pady=5)

        tk.Label(inputs_frame, text="Retiros/Egresos:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=3, column=2, sticky='w', padx=(20, 5), pady=5)
        tk.Entry(inputs_frame, textvariable=self.retiros_var, font=FONTS['normal']).grid(row=3, column=3, sticky='ew', padx=5, pady=5)

        tk.Label(inputs_frame, text="Corte Final (Dinero contado):", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=4, column=2, sticky='w', padx=(20, 5), pady=5)
        tk.Entry(inputs_frame, textvariable=self.corte_final_var, font=FONTS['normal']).grid(row=4, column=3, sticky='ew', padx=5, pady=5)

        # Calculated Fields Frame
        calculated_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        calculated_frame.pack(fill=tk.X, pady=10)
        calculated_frame.columnconfigure(0, weight=1)

        tk.Label(calculated_frame, text="Corte Esperado:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=0, column=0, sticky='w', pady=(10,0))
        tk.Label(calculated_frame, textvariable=self.corte_esperado_var, font=FONTS['heading'], bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], relief=tk.SUNKEN, padx=10, pady=5, anchor='w').grid(row=1, column=0, sticky='ew', pady=(0, 10))
        
        tk.Label(calculated_frame, text="Diferencia:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=2, column=0, sticky='w')
        self.diferencia_label = tk.Label(calculated_frame, textvariable=self.diferencia_var, font=FONTS['heading'], bg=COLORS['bg_secondary'], relief=tk.SUNKEN, padx=10, pady=5, anchor='w')
        self.diferencia_label.grid(row=3, column=0, sticky='ew', pady=(0, 10))
        
        tk.Label(calculated_frame, text="Estado del Corte:", font=FONTS['normal'], bg=COLORS['bg_primary']).grid(row=4, column=0, sticky='w')
        self.estado_label = tk.Label(calculated_frame, textvariable=self.estado_var, font=FONTS['heading'], bg=COLORS['bg_secondary'], relief=tk.SUNKEN, padx=10, pady=5, anchor='w')
        self.estado_label.grid(row=5, column=0, sticky='ew', pady=(0, 10))
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Guardar", command=self.save_corte, font=FONTS['button'], bg=COLORS['success'], fg='white', relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy, font=FONTS['button'], bg=COLORS['danger'], fg='white', relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def calcular_diferencia(self, *args):
        try:
            dinero_caja = float(self.dinero_caja_var.get() or 0)
            ventas_efectivo = float(self.ventas_efectivo_var.get() or 0)
            ventas_tarjeta = float(self.ventas_tarjeta_var.get() or 0)
            retiros = float(self.retiros_var.get() or 0)
            corte_final = float(self.corte_final_var.get() or 0)
            
            corte_esperado = dinero_caja + ventas_efectivo - retiros
            diferencia = corte_final - corte_esperado
            
            self.corte_esperado_var.set(format_currency(corte_esperado))
            self.diferencia_var.set(format_currency(diferencia))
            
            if abs(diferencia) < 0.01:
                estado = 'Cuadrado'
                color = COLORS['accent']
            elif diferencia > 0:
                estado = 'Sobrante'
                color = COLORS['success']
            else:
                estado = 'Faltante'
                color = COLORS['danger']
            
            self.estado_var.set(estado)
            self.diferencia_label.config(fg=color)
            self.estado_label.config(fg=color)
        except (ValueError, tk.TclError):
            pass
    
    def load_corte_data(self):
        db.cursor.execute('SELECT * FROM cortes WHERE id = ?', (self.corte_id,))
        self.corte_data = db.cursor.fetchone()
        
        if not self.corte_data:
            messagebox.showerror("Error", "Corte no encontrado.")
            self.dialog.destroy()
            return
        
        self.num_corte_var.set(self.corte_data['numero_corte'])
        self.fecha_inicio_var.set(self.corte_data['fecha_inicio'])
        self.fecha_cierre_var.set(self.corte_data['fecha_cierre'] or '')
        self.dinero_caja_var.set(self.corte_data['dinero_en_caja'])
        self.ventas_efectivo_var.set(self.corte_data['ventas_efectivo'])
        self.ventas_transferencia_var.set(self.corte_data['ventas_transferencia'])
        self.ventas_tarjeta_var.set(self.corte_data['ventas_tarjeta'])
        self.corte_final_var.set(self.corte_data['corte_final'])
        self.retiros_var.set(self.corte_data['retiros'])
        self.ganancias_var.set(self.corte_data['ganancias'])
    
    def save_corte(self):
        try:
            # Recolectar y validar datos
            numero_corte = int(self.num_corte_var.get())
            fecha_inicio = self.fecha_inicio_var.get().strip()
            fecha_cierre = self.fecha_cierre_var.get().strip() or None
            dinero_caja = float(self.dinero_caja_var.get() or 0)
            ventas_efectivo = float(self.ventas_efectivo_var.get() or 0)
            ventas_transferencia = float(self.ventas_transferencia_var.get() or 0)
            ventas_tarjeta = float(self.ventas_tarjeta_var.get() or 0)
            retiros = float(self.retiros_var.get() or 0)
            corte_final = float(self.corte_final_var.get() or 0)
            ganancias = float(self.ganancias_var.get() or 0)

            if not fecha_inicio:
                messagebox.showerror("Error", "La fecha de inicio es obligatoria.")
                return

            # Calcular valores derivados
            corte_esperado = dinero_caja + ventas_efectivo - retiros
            diferencia = corte_final - corte_esperado
            
            if abs(diferencia) < 0.01:
                estado = 'Cuadrado'
            elif diferencia > 0:
                estado = 'Sobrante'
            else:
                estado = 'Faltante'

            # Construir tupla de parámetros
            params = (
                numero_corte, fecha_inicio, fecha_cierre, dinero_caja,
                ventas_efectivo, ventas_transferencia, ventas_tarjeta, corte_final,
                corte_esperado, retiros, diferencia, estado, ganancias
            )

            # Ejecutar SQL
            if self.corte_id:
                sql = '''UPDATE cortes SET 
                            numero_corte=?, fecha_inicio=?, fecha_cierre=?, dinero_en_caja=?,
                            ventas_efectivo=?, ventas_transferencia=?, ventas_tarjeta=?, corte_final=?,
                            corte_esperado=?, retiros=?, diferencia=?, estado=?, ganancias=?
                         WHERE id = ?'''
                db.cursor.execute(sql, params + (self.corte_id,))
            else:
                sql = '''INSERT INTO cortes (
                            numero_corte, fecha_inicio, fecha_cierre, dinero_en_caja,
                            ventas_efectivo, ventas_transferencia, ventas_tarjeta, corte_final,
                            corte_esperado, retiros, diferencia, estado, ganancias, estado_corte
                         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'cerrado')'''
                db.cursor.execute(sql, params)
            
            db.conn.commit()
            messagebox.showinfo("Éxito", "Corte guardado correctamente.")
            
            if self.callback:
                self.callback()
            
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("Error", "Valores numéricos inválidos. Asegúrate de que todos los campos de dinero sean números.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al guardar el corte: {e}")
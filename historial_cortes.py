"""
Módulo de Historial de Cortes para Mitsy's POS
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from config import COLORS, FONTS
from utils import format_currency, get_current_datetime, calculate_week_range, calculate_month_range
from database import db

class CortesWindow:
    def __init__(self, parent, on_close=None):
        self.on_close_callback = on_close
        
        self.window = tk.Toplevel(parent)
        self.window.title("Cortes - Mitsy's POS")
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
        
        self.setup_ui()
        self.load_cortes()
    
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
                 font=FONTS['normal'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(quick_filters_frame, text="Faltante", 
                 command=lambda: self.filtro_estado('Faltante'),
                 font=FONTS['normal'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(quick_filters_frame, text="Cuadrado", 
                 command=lambda: self.filtro_estado('Cuadrado'),
                 font=FONTS['normal'], bg=COLORS['accent'], fg='white',
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
        columns = ('No. Corte', 'Fecha', 'Dinero en Caja', 'Corte Final', 
                   'Corte Esperado', 'Retiros', 'Diferencia', 'Estado', 'Ganancias')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar.set, selectmode='extended')
        
        # Configurar columnas
        self.tree.heading('No. Corte', text='No. Corte')
        self.tree.heading('Fecha', text='Fecha')
        self.tree.heading('Dinero en Caja', text='Dinero en Caja')
        self.tree.heading('Corte Final', text='Corte Final')
        self.tree.heading('Corte Esperado', text='Corte Esperado')
        self.tree.heading('Retiros', text='Retiros')
        self.tree.heading('Diferencia', text='Diferencia')
        self.tree.heading('Estado', text='Estado')
        self.tree.heading('Ganancias', text='Ganancias')
        
        self.tree.column('No. Corte', width=100, anchor='center')
        self.tree.column('Fecha', width=180, anchor='center')
        self.tree.column('Dinero en Caja', width=140, anchor='e')
        self.tree.column('Corte Final', width=140, anchor='e')
        self.tree.column('Corte Esperado', width=140, anchor='e')
        self.tree.column('Retiros', width=120, anchor='e')
        self.tree.column('Diferencia', width=120, anchor='e')
        self.tree.column('Estado', width=100, anchor='center')
        self.tree.column('Ganancias', width=140, anchor='e')
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Colores por estado
        self.tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
        self.tree.tag_configure('cuadrado', background='#E8F5E9')
        self.tree.tag_configure('sobrante', background='#E3F2FD')
        self.tree.tag_configure('faltante', background='#FFEBEE')
        
        # Doble clic para ver detalles
        self.tree.bind('<Double-1>', self.ver_detalles_corte)
        
        # Frame de botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(fill=tk.X)
        
        buttons = [
            ("Regresar", self.close_window),
            ("Ver Detalles", self.ver_detalles_corte),
            ("Modificar Corte", self.modificar_corte),
            ("Borrar Corte", self.borrar_corte),
            ("Agregar Corte", self.agregar_corte)
        ]
        
        for text, command in buttons:
            btn = tk.Button(button_frame, text=text, command=command,
                          font=FONTS['button'], bg=COLORS['button_bg'],
                          fg=COLORS['text_primary'], relief=tk.RAISED,
                          borderwidth=2, padx=20, pady=10)
            btn.pack(side=tk.LEFT, padx=5)
    
    def load_cortes(self, cortes=None):
        """Carga los cortes en la tabla"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Obtener cortes
        if cortes is None:
            db.cursor.execute('SELECT * FROM cortes ORDER BY fecha DESC, numero_corte DESC')
            cortes = [dict(row) for row in db.cursor.fetchall()]
        
        # Cargar en tabla
        for idx, c in enumerate(cortes):
            # Determinar tag por estado
            if c['estado'] == 'Cuadrado':
                tag = 'cuadrado'
            elif c['estado'] == 'Sobrante':
                tag = 'sobrante'
            elif c['estado'] == 'Faltante':
                tag = 'faltante'
            else:
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            values = (
                c['numero_corte'],
                c['fecha'],
                format_currency(c['dinero_en_caja']),
                format_currency(c['corte_final']),
                format_currency(c['corte_esperado']),
                format_currency(c['retiros']),
                format_currency(abs(c['diferencia'])),
                c['estado'],
                format_currency(c['ganancias'])
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
    
    def aplicar_filtros(self):
        """Aplica los filtros de búsqueda"""
        query = self.search_var.get().strip()
        fecha_inicio = self.fecha_inicio.get_date()
        fecha_fin = self.fecha_fin.get_date()
        
        # Construir query SQL
        sql = 'SELECT * FROM cortes WHERE 1=1'
        params = []
        
        # Filtro de búsqueda general
        if query:
            sql += ' AND (estado LIKE ? OR CAST(numero_corte AS TEXT) LIKE ?)'
            params.extend([f'%{query}%', f'%{query}%'])
        
        # Filtro de fechas
        sql += ' AND DATE(SUBSTR(fecha, 7, 4) || "-" || SUBSTR(fecha, 4, 2) || "-" || SUBSTR(fecha, 1, 2)) BETWEEN ? AND ?'
        params.extend([fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')])
        
        sql += ' ORDER BY fecha DESC, numero_corte DESC'
        
        # Ejecutar query
        db.cursor.execute(sql, params)
        cortes = [dict(row) for row in db.cursor.fetchall()]
        
        self.load_cortes(cortes)
    
    def filtro_hoy(self):
        """Filtra cortes de hoy"""
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy)
        self.fecha_fin.set_date(hoy)
        self.aplicar_filtros()
    
    def filtro_ayer(self):
        """Filtra cortes de ayer"""
        ayer = datetime.now().date() - timedelta(days=1)
        self.fecha_inicio.set_date(ayer)
        self.fecha_fin.set_date(ayer)
        self.aplicar_filtros()
    
    def filtro_semana(self):
        """Filtra cortes de esta semana (viernes a miércoles)"""
        viernes, miercoles = calculate_week_range()
        self.fecha_inicio.set_date(viernes.date())
        self.fecha_fin.set_date(miercoles.date())
        self.aplicar_filtros()
    
    def filtro_mes(self):
        """Filtra cortes de este mes (día 1 hasta hoy)"""
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
    
    def filtro_estado(self, estado):
        """Filtra por estado del corte"""
        db.cursor.execute('SELECT * FROM cortes WHERE estado = ? ORDER BY fecha DESC', (estado,))
        cortes = [dict(row) for row in db.cursor.fetchall()]
        self.load_cortes(cortes)
    
    def filtro_numero_corte(self):
        """Filtra por número de corte"""
        num_corte = self.num_corte_var.get().strip()
        if not num_corte:
            messagebox.showwarning("Advertencia", "Ingresa un número de corte")
            return
        
        try:
            num_corte = int(num_corte)
            db.cursor.execute('SELECT * FROM cortes WHERE numero_corte = ? ORDER BY fecha DESC', 
                            (num_corte,))
            cortes = [dict(row) for row in db.cursor.fetchall()]
            
            if not cortes:
                messagebox.showinfo("No encontrado", f"No se encontró el corte #{num_corte}")
            
            self.load_cortes(cortes)
        except ValueError:
            messagebox.showerror("Error", "El número de corte debe ser un número entero")
    
    def limpiar_filtros(self):
        """Limpia todos los filtros"""
        self.search_var.set("")
        self.num_corte_var.set("")
        hoy = datetime.now().date()
        self.fecha_inicio.set_date(hoy - timedelta(days=30))
        self.fecha_fin.set_date(hoy)
        self.load_cortes()
    
    def ver_detalles_corte(self, event=None):
        """Muestra detalles completos del corte"""
        selection = self.tree.selection()
        
        if not selection:
            if event:
                return
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona un corte para ver detalles")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona solo un corte")
            return
        
        item = self.tree.item(selection[0])
        corte_id = self.get_corte_id_from_values(item['values'])
        
        if corte_id:
            DetallesCorteDialog(self.window, corte_id)
    
    def modificar_corte(self):
        """Abre diálogo para modificar corte"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona un corte para modificar")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona solo un corte para modificar")
            return
        
        item = self.tree.item(selection[0])
        corte_id = self.get_corte_id_from_values(item['values'])
        
        if corte_id:
            CorteDialog(self.window, corte_id=corte_id, callback=self.load_cortes)
    
    def borrar_corte(self):
        """Elimina cortes seleccionados"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona al menos un corte para borrar")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Estás seguro de borrar {len(selection)} corte(s)?"):
            return
        
        for item in selection:
            values = self.tree.item(item)['values']
            corte_id = self.get_corte_id_from_values(values)
            if corte_id:
                db.cursor.execute('DELETE FROM cortes WHERE id = ?', (corte_id,))
        
        db.conn.commit()
        messagebox.showinfo("Éxito", "Corte(s) eliminado(s) correctamente")
        self.load_cortes()
    
    def agregar_corte(self):
        """Abre diálogo para agregar corte manual"""
        CorteDialog(self.window, callback=self.load_cortes)
    
    def get_corte_id_from_values(self, values):
        """Obtiene el ID del corte desde los valores mostrados"""
        numero_corte = values[0]
        fecha = values[1]
        
        db.cursor.execute('''
            SELECT id FROM cortes 
            WHERE numero_corte = ? AND fecha = ?
            LIMIT 1
        ''', (numero_corte, fecha))
        
        result = db.cursor.fetchone()
        return result['id'] if result else None
    
    def close_window(self):
        """Cierra la ventana y vuelve al menú"""
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()


class DetallesCorteDialog:
    def __init__(self, parent, corte_id):
        self.corte_id = corte_id
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Detalles del Corte")
        self.dialog.geometry("600x700")
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
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 600
        height = 700
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Obtener datos del corte
        db.cursor.execute('SELECT * FROM cortes WHERE id = ?', (self.corte_id,))
        corte = db.cursor.fetchone()
        
        if not corte:
            messagebox.showerror("Error", "Corte no encontrado")
            self.dialog.destroy()
            return
        
        corte = dict(corte)
        
        # Título
        tk.Label(main_frame, text=f"Corte de Caja #{corte['numero_corte']}", 
                font=FONTS['title'], bg=COLORS['bg_primary'],
                fg=COLORS['text_primary']).pack(pady=(0, 20))
        
        # Frame de información
        info_frame = tk.Frame(main_frame, bg=COLORS['bg_secondary'],
                             relief=tk.RAISED, borderwidth=2)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Fecha
        self.add_info_row(info_frame, "Fecha:", corte['fecha'])
        
        # Dinero en caja
        self.add_info_row(info_frame, "Dinero en Caja:", 
                         format_currency(corte['dinero_en_caja']))
        
        # Corte final
        self.add_info_row(info_frame, "Corte Final (contado):", 
                         format_currency(corte['corte_final']), COLORS['accent'])
        
        # Corte esperado
        self.add_info_row(info_frame, "Corte Esperado:", 
                         format_currency(corte['corte_esperado']))
        
        # Retiros
        self.add_info_row(info_frame, "Retiros/Egresos:", 
                         format_currency(corte['retiros']))
        
        # Diferencia
        diferencia_color = COLORS['text_primary']
        if corte['estado'] == 'Sobrante':
            diferencia_color = COLORS['success']
        elif corte['estado'] == 'Faltante':
            diferencia_color = COLORS['danger']
        
        self.add_info_row(info_frame, "Diferencia:", 
                         format_currency(abs(corte['diferencia'])), diferencia_color)
        
        # Estado
        estado_color = COLORS['text_primary']
        if corte['estado'] == 'Cuadrado':
            estado_color = COLORS['accent']
        elif corte['estado'] == 'Sobrante':
            estado_color = COLORS['success']
        elif corte['estado'] == 'Faltante':
            estado_color = COLORS['danger']
        
        self.add_info_row(info_frame, "Estado del Corte:", 
                         corte['estado'], estado_color)
        
        # Ganancias
        self.add_info_row(info_frame, "Ganancias del Día:", 
                         format_currency(corte['ganancias']), COLORS['success'])
        
        # Botón cerrar
        tk.Button(main_frame, text="Cerrar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['accent'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=40, pady=12).pack(pady=20)
    
    def add_info_row(self, parent, label, value, color=None):
        """Añade una fila de información"""
        row_frame = tk.Frame(parent, bg=COLORS['bg_secondary'])
        row_frame.pack(fill=tk.X, padx=20, pady=8)
        
        tk.Label(row_frame, text=label, font=FONTS['normal'],
                bg=COLORS['bg_secondary'], anchor='w').pack(side=tk.LEFT)
        
        value_color = color if color else COLORS['text_primary']
        tk.Label(row_frame, text=str(value), font=FONTS['heading'],
                bg=COLORS['bg_secondary'], fg=value_color,
                anchor='e').pack(side=tk.RIGHT)


class CorteDialog:
    def __init__(self, parent, corte_id=None, callback=None):
        self.corte_id = corte_id
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Añadir Corte" if not corte_id else "Modificar Corte")
        self.dialog.geometry("550x650")
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
        
        if corte_id:
            self.load_corte_data()
    
    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = 550
        height = 650
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Número de corte
        tk.Label(main_frame, text="Número de Corte:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(10, 5))
        self.num_corte_var = tk.StringVar()
        if not self.corte_id:
            self.num_corte_var.set(str(db.get_next_numero_corte()))
        tk.Entry(main_frame, textvariable=self.num_corte_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Fecha
        tk.Label(main_frame, text="Fecha:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.fecha_var = tk.StringVar(value=get_current_datetime())
        tk.Entry(main_frame, textvariable=self.fecha_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Dinero en caja
        tk.Label(main_frame, text="Dinero en Caja:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.dinero_caja_var = tk.StringVar(value="0")
        tk.Entry(main_frame, textvariable=self.dinero_caja_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Corte final
        tk.Label(main_frame, text="Corte Final (contado):", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.corte_final_var = tk.StringVar(value="0")
        self.corte_final_var.trace('w', self.calcular_diferencia)
        tk.Entry(main_frame, textvariable=self.corte_final_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Retiros
        tk.Label(main_frame, text="Retiros/Egresos:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.retiros_var = tk.StringVar(value="0")
        self.retiros_var.trace('w', self.calcular_diferencia)
        tk.Entry(main_frame, textvariable=self.retiros_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Corte esperado (calculado automáticamente)
        tk.Label(main_frame, text="Corte Esperado:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.corte_esperado_var = tk.StringVar(value="$0.00")
        tk.Label(main_frame, textvariable=self.corte_esperado_var, 
                font=FONTS['heading'], bg=COLORS['bg_secondary'],
                fg=COLORS['text_primary'], relief=tk.SUNKEN, 
                padx=10, pady=5, anchor='w').pack(fill=tk.X, pady=(0, 10))
        
        # Diferencia (calculada automáticamente)
        tk.Label(main_frame, text="Diferencia:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.diferencia_var = tk.StringVar(value="$0.00")
        self.diferencia_label = tk.Label(main_frame, textvariable=self.diferencia_var, 
                                        font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                        relief=tk.SUNKEN, padx=10, pady=5, anchor='w')
        self.diferencia_label.pack(fill=tk.X, pady=(0, 10))
        
        # Estado (calculado automáticamente)
        tk.Label(main_frame, text="Estado del Corte:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.estado_var = tk.StringVar(value="Cuadrado")
        self.estado_label = tk.Label(main_frame, textvariable=self.estado_var, 
                                     font=FONTS['heading'], bg=COLORS['bg_secondary'],
                                     relief=tk.SUNKEN, padx=10, pady=5, anchor='w')
        self.estado_label.pack(fill=tk.X, pady=(0, 10))
        
        # Ganancias
        tk.Label(main_frame, text="Ganancias del Día:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.ganancias_var = tk.StringVar(value="0")
        tk.Entry(main_frame, textvariable=self.ganancias_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Aceptar", command=self.save_corte,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def calcular_diferencia(self, *args):
        """Calcula la diferencia y estado automáticamente"""
        try:
            dinero_caja = float(self.dinero_caja_var.get())
            corte_final = float(self.corte_final_var.get())
            retiros = float(self.retiros_var.get())
            
            # Calcular corte esperado (esto es simplificado, en realidad 
            # debería calcularse basado en ventas del día)
            # Por ahora usamos: dinero_caja + ventas_efectivo - retiros
            # Pero como es manual, el usuario puede ajustarlo
            
            # Para simplificar, el corte esperado es el dinero en caja
            # (asumiendo que todas las ventas ya están incluidas)
            corte_esperado = dinero_caja - retiros
            
            self.corte_esperado_var.set(format_currency(corte_esperado))
            
            # Calcular diferencia
            diferencia = corte_final - corte_esperado
            
            self.diferencia_var.set(format_currency(abs(diferencia)))
            
            # Determinar estado y color
            if abs(diferencia) < 0.01:  # Tolerancia de 1 centavo
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
            
        except ValueError:
            pass
    
    def load_corte_data(self):
        """Carga los datos del corte a editar"""
        db.cursor.execute('SELECT * FROM cortes WHERE id = ?', (self.corte_id,))
        corte = db.cursor.fetchone()
        
        if not corte:
            messagebox.showerror("Error", "Corte no encontrado")
            self.dialog.destroy()
            return
        
        corte = dict(corte)
        
        self.num_corte_var.set(str(corte['numero_corte']))
        self.fecha_var.set(corte['fecha'])
        self.dinero_caja_var.set(str(corte['dinero_en_caja']))
        self.corte_final_var.set(str(corte['corte_final']))
        self.retiros_var.set(str(corte['retiros']))
        self.ganancias_var.set(str(corte['ganancias']))
        
        # Los campos calculados se actualizarán automáticamente
        self.calcular_diferencia()
    
    def save_corte(self):
        """Guarda el corte"""
        # Validaciones
        try:
            numero_corte = int(self.num_corte_var.get())
            dinero_caja = float(self.dinero_caja_var.get())
            corte_final = float(self.corte_final_var.get())
            retiros = float(self.retiros_var.get())
            ganancias = float(self.ganancias_var.get())
        except ValueError:
            messagebox.showerror("Error", "Valores numéricos inválidos")
            return
        
        fecha = self.fecha_var.get().strip()
        if not fecha:
            messagebox.showerror("Error", "La fecha es obligatoria")
            return
        
        # Calcular valores
        corte_esperado = dinero_caja - retiros
        diferencia = corte_final - corte_esperado
        
        if abs(diferencia) < 0.01:
            estado = 'Cuadrado'
        elif diferencia > 0:
            estado = 'Sobrante'
        else:
            estado = 'Faltante'
        
        try:
            if self.corte_id:
                # Actualizar corte existente
                db.cursor.execute('''
                    UPDATE cortes 
                    SET numero_corte = ?, fecha = ?, dinero_en_caja = ?,
                        corte_final = ?, corte_esperado = ?, retiros = ?,
                        diferencia = ?, estado = ?, ganancias = ?
                    WHERE id = ?
                ''', (numero_corte, fecha, dinero_caja, corte_final, corte_esperado,
                      retiros, diferencia, estado, ganancias, self.corte_id))
            else:
                # Crear nuevo corte
                db.cursor.execute('''
                    INSERT INTO cortes (numero_corte, fecha, dinero_en_caja,
                                      corte_final, corte_esperado, retiros,
                                      diferencia, estado, ganancias)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (numero_corte, fecha, dinero_caja, corte_final, corte_esperado,
                      retiros, diferencia, estado, ganancias))
                
                # Actualizar último número de corte si es mayor
                ultimo_num = int(db.get_config('ultimo_numero_corte') or 0)
                if numero_corte > ultimo_num:
                    db.set_config('ultimo_numero_corte', str(numero_corte))
            
            db.conn.commit()
            messagebox.showinfo("Éxito", "Corte guardado correctamente")
            
            if self.callback:
                self.callback()
            
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar corte: {str(e)}")
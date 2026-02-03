"""
Módulo de gestión de productos - ACTUALIZADO con sistema de clasificaciones
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import os
from config import COLORS, FONTS
from utils import format_currency, parse_currency, validate_float, get_resource_path
import utils
from database import db
from excel_utils import exportar_productos_excel, importar_productos_excel

class ProductosWindow:
    def __init__(self, parent, on_close=None):
        self.on_close_callback = on_close
        self.viewing_clasificaciones = False  # Estado de la vista actual
        
        self.window = tk.Toplevel(parent)
        self.window.title("Productos - Mitsy's POS")
        self.window.configure(bg=COLORS['bg_primary'])
        self.window.minsize(800, 600)
        
        # Maximizar ventana
        self.window.state('zoomed')
        
        # Forzar al frente
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        self.window.iconbitmap(get_resource_path('icono.ico'))
        
        # Protocolo de cierre
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        
        self.selected_items = []
        
        self.setup_ui()
        self.load_productos()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
    
        # Frame principal
        self.main_frame = tk.Frame(self.window, bg=COLORS['bg_primary'])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
        # Título
        self.title_label = tk.Label(self.main_frame, text="Productos", 
                            font=FONTS['title'], bg=COLORS['bg_primary'],
                            fg=COLORS['text_primary'])
        self.title_label.pack(pady=(0, 20))
    
        # Frame de búsqueda y botones de Excel
        self.top_controls_frame = tk.Frame(self.main_frame, bg=COLORS['bg_primary'])
        self.top_controls_frame.pack(fill=tk.X, pady=(0, 20))
    
        # Búsqueda (lado izquierdo)
        search_frame = tk.Frame(self.top_controls_frame, bg=COLORS['bg_primary'])
        search_frame.pack(side=tk.LEFT)
    
        tk.Label(search_frame, text="Buscar:", font=FONTS['normal'],
            bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=(0, 10))
    
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.search_items())
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                           font=FONTS['normal'], width=40)
        self.search_entry.pack(side=tk.LEFT)
    
        # Botones de Excel (lado derecho)
        excel_frame = tk.Frame(self.top_controls_frame, bg=COLORS['bg_primary'])
        excel_frame.pack(side=tk.RIGHT)
    
        tk.Button(excel_frame, text="📊 Exportar a Excel", 
                command=self.exportar_excel,
                font=FONTS['button'], bg=COLORS['success'], fg='white',
                relief=tk.RAISED, borderwidth=2, padx=15, pady=8).pack(side=tk.LEFT, padx=5)
    
        tk.Button(excel_frame, text="📁 Importar desde Excel", 
                command=self.importar_excel,
                font=FONTS['button'], bg=COLORS['accent'], fg='white',
                relief=tk.RAISED, borderwidth=2, padx=15, pady=8).pack(side=tk.LEFT, padx=5)
    
        # Frame con scrollbar para la tabla
        self.table_frame = tk.Frame(self.main_frame, bg=COLORS['bg_primary'])
        self.table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
    
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.table_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        # Treeview (tabla) - Se creará dinámicamente
        self.create_productos_table()
    
        # Frame de botones
        self.button_frame = tk.Frame(self.main_frame, bg=COLORS['bg_primary'])
        self.button_frame.pack(fill=tk.X)
        
        # Botón para alternar vista
        self.toggle_btn = tk.Button(self.button_frame, text="Ver Clasificaciones", 
                          command=self.toggle_view,
                          font=FONTS['button'], bg=COLORS['accent'], fg='white',
                          relief=tk.RAISED, borderwidth=2, padx=20, pady=10)
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
    
        # Botones dinámicos
        self.create_action_buttons()
    
    def create_productos_table(self):
        """Crea la tabla de productos"""
        if hasattr(self, 'tree'):
            self.tree.destroy()
            
        columns = ('ID', 'Nombre', 'Clasificación', 'Precio', 'Costo', 'Ganancia', 'U. Medida', 
                'Stock', 'Gestión Stock')
    
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show='headings',
                            yscrollcommand=self.scrollbar.set, selectmode='extended')
        utils.enable_drag_selection(self.tree)
    
        # Configurar columnas
        self.tree.heading('ID', text='ID')
        self.tree.heading('Nombre', text='Nombre')
        self.tree.heading('Clasificación', text='Clasificación')
        self.tree.heading('Precio', text='Precio Unitario')
        self.tree.heading('Costo', text='Costo')
        self.tree.heading('Ganancia', text='Ganancia')
        self.tree.heading('U. Medida', text='U. Medida')
        self.tree.heading('Stock', text='Stock Estimado')
        self.tree.heading('Gestión Stock', text='Gestión Stock')
    
        self.tree.column('ID', width=50, anchor='center')
        self.tree.column('Nombre', width=200)
        self.tree.column('Clasificación', width=150)
        self.tree.column('Precio', width=120, anchor='e')
        self.tree.column('Costo', width=120, anchor='e')
        self.tree.column('Ganancia', width=120, anchor='e')
        self.tree.column('U. Medida', width=100, anchor='center')
        self.tree.column('Stock', width=120, anchor='e')
        self.tree.column('Gestión Stock', width=120, anchor='center')
    
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.tree.yview)
    
        # Configurar colores alternados en filas
        self.tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
    
    def create_clasificaciones_table(self):
        """Crea la tabla de clasificaciones"""
        if hasattr(self, 'tree'):
            self.tree.destroy()
            
        columns = ('ID', 'Nombre', 'Productos', 'Fecha Creación')
    
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show='headings',
                            yscrollcommand=self.scrollbar.set, selectmode='extended')
        utils.enable_drag_selection(self.tree)
    
        # Configurar columnas
        self.tree.heading('ID', text='ID')
        self.tree.heading('Nombre', text='Nombre')
        self.tree.heading('Productos', text='# Productos')
        self.tree.heading('Fecha Creación', text='Fecha Creación')
    
        self.tree.column('ID', width=80, anchor='center')
        self.tree.column('Nombre', width=300)
        self.tree.column('Productos', width=150, anchor='center')
        self.tree.column('Fecha Creación', width=200, anchor='center')
    
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.tree.yview)
    
        # Configurar colores alternados
        self.tree.tag_configure('evenrow', background=COLORS['table_row_even'])
        self.tree.tag_configure('oddrow', background=COLORS['table_row_odd'])
    
    def create_action_buttons(self):
        """Crea los botones de acción según la vista actual"""
        # Eliminar botones existentes (excepto el de toggle y regresar)
        for widget in self.button_frame.winfo_children():
            if widget != self.toggle_btn:
                widget.destroy()
        
        # Recrear el botón toggle
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        
        if self.viewing_clasificaciones:
            # Botones para clasificaciones
            buttons = [
                ("Añadir Clasificación", self.add_clasificacion, COLORS['success']),
                ("Editar Clasificación", self.editar_clasificacion, COLORS['button_bg']),
                ("Borrar Clasificación", self.borrar_clasificacion, COLORS['danger']),
            ]
        else:
            # Botones para productos
            buttons = [
                ("Editar Producto", self.editar_producto, COLORS['button_bg']),
                ("Borrar Producto", self.borrar_producto, COLORS['danger']),
                ("Añadir Producto", self.add_producto_dialog, COLORS['success']),
                ("Registrar Compra", self.registrar_compra_unitaria, COLORS['button_bg']),
            ]
        
        for text, command, color in buttons:
            fg = 'white' if color != COLORS['button_bg'] else COLORS['text_primary']
            btn = tk.Button(self.button_frame, text=text, command=command,
                          font=FONTS['button'], bg=color, fg=fg,
                          relief=tk.RAISED, borderwidth=2, padx=20, pady=10)
            btn.pack(side=tk.LEFT, padx=5)
        
        # Botón regresar siempre al final
        btn = tk.Button(self.button_frame, text="Regresar", command=self.close_window,
                      font=FONTS['button'], bg=COLORS['button_bg'],
                      fg=COLORS['text_primary'], relief=tk.RAISED,
                      borderwidth=2, padx=20, pady=10)
        btn.pack(side=tk.LEFT, padx=5)
    
    def toggle_view(self):
        """Alterna entre vista de productos y clasificaciones"""
        self.viewing_clasificaciones = not self.viewing_clasificaciones
        
        if self.viewing_clasificaciones:
            self.title_label.config(text="Clasificaciones de Productos")
            self.toggle_btn.config(text="Ver Productos")
            self.create_clasificaciones_table()
            self.load_clasificaciones()
        else:
            self.title_label.config(text="Productos")
            self.toggle_btn.config(text="Ver Clasificaciones")
            self.create_productos_table()
            self.load_productos()
        
        # Recrear botones de acción
        self.create_action_buttons()
    
    def load_productos(self):
        """Carga los productos en la tabla"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Cargar productos
        productos = db.get_productos()
        
        for idx, p in enumerate(productos):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            # Obtener nombre de clasificación
            clasificacion_nombre = p.get('clasificacion_nombre', 'Sin clasificación')
            if not clasificacion_nombre:
                clasificacion_nombre = 'Sin clasificación'
            
            values = (
                p['id'],
                p['nombre'],
                clasificacion_nombre,
                format_currency(p['precio_unitario']),
                format_currency(p['costo']),
                format_currency(p['ganancia']),
                p['unidad_medida'],
                f"{p['stock_estimado']:.2f}" if db.is_gestion_stock_active() else "N/A",
                'Sí' if p['gestion_stock'] else 'No'
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
    
    def load_clasificaciones(self):
        """Carga las clasificaciones en la tabla"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Cargar clasificaciones
        clasificaciones = db.get_clasificaciones()
        
        for idx, c in enumerate(clasificaciones):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            # Contar productos de esta clasificación
            db.cursor.execute('SELECT COUNT(*) as count FROM productos WHERE clasificacion_id = ? AND activo = 1', (c['id'],))
            count_result = db.cursor.fetchone()
            num_productos = count_result['count'] if count_result else 0
            
            values = (
                c['id'],
                c['nombre'],
                num_productos,
                c['fecha_creacion'] or '-'
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
    
    def search_items(self):
        """Busca según la vista actual"""
        if self.viewing_clasificaciones:
            self.search_clasificaciones()
        else:
            self.search_productos()
    
    def search_productos(self):
        """Busca productos según el texto ingresado"""
        query = self.search_var.get()
        
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not query:
            self.load_productos()
            return
        
        # Buscar productos
        productos = db.search_productos(query)
        
        for idx, p in enumerate(productos):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            # Obtener nombre de clasificación
            clasificacion = db.get_clasificacion(p['clasificacion_id']) if p['clasificacion_id'] else None
            clasificacion_nombre = clasificacion['nombre'] if clasificacion else 'Sin clasificación'
            
            values = (
                p['id'],
                p['nombre'],
                clasificacion_nombre,
                format_currency(p['precio_unitario']),
                format_currency(p['costo']),
                format_currency(p['ganancia']),
                p['unidad_medida'],
                f"{p['stock_estimado']:.2f}" if db.is_gestion_stock_active() else "N/A",
                'Sí' if p['gestion_stock'] else 'No'
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
    
    def search_clasificaciones(self):
        """Busca clasificaciones según el texto ingresado"""
        query = self.search_var.get().strip().lower()
        
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not query:
            self.load_clasificaciones()
            return
        
        # Buscar clasificaciones
        clasificaciones = db.get_clasificaciones()
        
        resultados = [c for c in clasificaciones if query in c['nombre'].lower()]
        
        for idx, c in enumerate(resultados):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            # Contar productos
            db.cursor.execute('SELECT COUNT(*) as count FROM productos WHERE clasificacion_id = ? AND activo = 1', (c['id'],))
            count_result = db.cursor.fetchone()
            num_productos = count_result['count'] if count_result else 0
            
            values = (
                c['id'],
                c['nombre'],
                num_productos,
                c['fecha_creacion'] or '-'
            )
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
    
    # ========== MÉTODOS PARA PRODUCTOS ==========
    
    def add_producto_dialog(self):
        """Abre diálogo para añadir producto"""
        ProductoDialog(self.window, callback=self.load_productos)
    
    def editar_producto(self):
        """Abre diálogo para editar producto seleccionado"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona un producto para editar")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona solo un producto para editar")
            return
        
        item = self.tree.item(selection[0])
        producto_id = item['values'][0]
        
        ProductoDialog(self.window, producto_id=producto_id, 
                      callback=self.load_productos)
    
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
        
        ids_a_borrar = [self.tree.item(item)['values'][0] for item in selection]
        
        db.delete_productos(ids_a_borrar)
        
        messagebox.showinfo("Éxito", "Producto(s) eliminado(s) correctamente")
        self.load_productos()

    def registrar_compra_unitaria(self):
        """Abre diálogo para registrar compra de producto unitario"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor selecciona un producto para registrar la compra.")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Advertencia", "Por favor selecciona solo un producto.")
            return
        
        item = self.tree.item(selection[0])
        producto_id = item['values'][0]
        
        # Verificar que el producto no tenga receta
        recetas = db.get_recetas_producto(producto_id)
        if recetas:
            messagebox.showerror("Operación no permitida", "Esta función es solo para productos unitarios (sin receta).\n\nPara productos con receta, por favor, registre la compra de sus ingredientes en el módulo de 'Materia Prima'.")
            return
            
        producto_nombre = item['values'][1]
        RegistrarCompraUnitariaDialog(self.window, producto_id, producto_nombre, callback=self.load_productos)
    
    # ========== MÉTODOS PARA CLASIFICACIONES ==========
    
    def add_clasificacion(self):
        """Abre diálogo para añadir clasificación"""
        ClasificacionDialog(self.window, callback=self.load_clasificaciones)
    
    def editar_clasificacion(self):
        """Abre diálogo para editar clasificación seleccionada"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona una clasificación para editar")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona solo una clasificación para editar")
            return
        
        item = self.tree.item(selection[0])
        clasificacion_id = item['values'][0]
        
        ClasificacionDialog(self.window, clasificacion_id=clasificacion_id, 
                          callback=self.load_clasificaciones)
    
    def borrar_clasificacion(self):
        """Elimina clasificaciones seleccionadas"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Advertencia", 
                                  "Por favor selecciona al menos una clasificación para borrar")
            return
        
        # Advertir que los productos se quedarán sin clasificación
        if not messagebox.askyesno("Confirmar", 
                                   f"¿Estás seguro de borrar {len(selection)} clasificación(es)?\n\n"
                                   "Los productos asociados quedarán sin clasificación."):
            return
        
        ids_a_borrar = [self.tree.item(item)['values'][0] for item in selection]
        
        for id_clasificacion in ids_a_borrar:
            db.delete_clasificacion(id_clasificacion)
        
        messagebox.showinfo("Éxito", "Clasificación(es) eliminada(s) correctamente")
        self.load_clasificaciones()
    
    # ========== MÉTODOS GENERALES ==========
    
    def close_window(self):
        """Cierra la ventana y vuelve al menú"""
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()

    def exportar_excel(self):
        """Exporta productos a Excel"""
        productos = db.get_productos()
    
        if not productos:
            messagebox.showwarning("Sin datos", "No hay productos para exportar")
            return
    
        exportar_productos_excel(productos)

    def importar_excel(self):
        """Importa productos desde Excel"""
        productos_importados = importar_productos_excel()
    
        if not productos_importados:
            return
    
        # Confirmar importación
        mensaje = f"Se importarán {len(productos_importados)} productos.\n\n"
        mensaje += "ADVERTENCIA: Si ya existen productos con los mismos IDs, serán reemplazados.\n\n"
        mensaje += "¿Desea continuar?"
    
        if not messagebox.askyesno("Confirmar Importación", mensaje):
            return
    
        try:
            # Importar productos
            productos_creados = 0
            productos_actualizados = 0
        
            for prod in productos_importados:
                existe = db.id_exists('productos', prod['id'])
            
                if existe:
                    # Actualizar producto existente
                    db.update_producto(
                        prod['id'], 
                        prod['id'],
                        nombre=prod['nombre'],
                        precio_unitario=prod['precio_unitario'],
                        costo=prod['costo'],
                        unidad_medida=prod['unidad_medida'],
                        stock_minimo=prod['stock_minimo'],
                        gestion_stock=1 if prod['gestion_stock'] else 0,
                        imagen=prod.get('imagen')
                    )
                    productos_actualizados += 1
                else:
                    # Crear nuevo producto
                    db.add_producto(
                        prod['id'],
                        prod['nombre'],
                        prod['precio_unitario'],
                        prod['costo'],
                        prod['unidad_medida'],
                        prod['gestion_stock'],
                        stock_minimo=prod['stock_minimo'],
                        imagen=prod.get('imagen')
                    )
                    productos_creados += 1
        
            # Recargar tabla
            self.load_productos()
        
            # Mensaje de éxito
            mensaje_resultado = f"Importación completada:\n\n"
            mensaje_resultado += f"✓ Productos creados: {productos_creados}\n"
            mensaje_resultado += f"✓ Productos actualizados: {productos_actualizados}"
        
            messagebox.showinfo("Éxito", mensaje_resultado)
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al importar productos:\n{str(e)}")


class ClasificacionDialog:
    """Diálogo para crear/editar clasificaciones"""
    def __init__(self, parent, clasificacion_id=None, callback=None):
        self.clasificacion_id = clasificacion_id
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Añadir Clasificación" if not clasificacion_id else "Editar Clasificación")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.minsize(450, 400)
        
        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        self.setup_ui()
        
        if clasificacion_id:
            self.load_clasificacion_data()

        # Centrar después de crear UI y cargar datos
        self.center_dialog()
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
    
    IMAGE_DISPLAY_SIZE = (150, 150)

    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_reqwidth()
        height = self.dialog.winfo_reqheight()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _display_image(self, image_path):
        """Carga, redimensiona y muestra una imagen en el image_label."""
        try:
            if image_path and os.path.exists(image_path):
                original_image = Image.open(image_path)
            else:
                original_image = Image.open(get_resource_path('images/placeholder.png'))
            
            # Redimensionar imagen manteniendo el aspecto
            original_width, original_height = original_image.size
            ratio = min(self.IMAGE_DISPLAY_SIZE[0] / original_width,
                        self.IMAGE_DISPLAY_SIZE[1] / original_height)
            
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            
            resized_image = original_image.resize((new_width, new_height), Image.LANCZOS)
            
            self.tk_image = ImageTk.PhotoImage(resized_image)
            self.image_label.config(image=self.tk_image)
            self.image_label.image = self.tk_image
        except Exception as e:
            print(f"Error al cargar o mostrar imagen: {e}")
            try:
                placeholder_image = Image.open(get_resource_path('images/placeholder.png'))
                placeholder_image = placeholder_image.resize(self.IMAGE_DISPLAY_SIZE, Image.LANCZOS)
                self.tk_image = ImageTk.PhotoImage(placeholder_image)
                self.image_label.config(image=self.tk_image)
                self.image_label.image = self.tk_image
            except Exception as e_placeholder:
                print(f"Error al cargar placeholder: {e_placeholder}")
                self.image_label.config(image='')

    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        titulo = "Nueva Clasificación" if not self.clasificacion_id else "Editar Clasificación"
        tk.Label(main_frame, text=titulo, font=FONTS['subtitle'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=(0, 20))

        # Nombre
        tk.Label(main_frame, text="Nombre de la Clasificación:", font=FONTS['normal'], 
                bg=COLORS['bg_primary']).pack(anchor='w', pady=(10, 5))
        
        self.nombre_var = tk.StringVar()
        nombre_entry = tk.Entry(main_frame, textvariable=self.nombre_var, font=FONTS['normal'])
        nombre_entry.pack(fill=tk.X, pady=(0, 15))
        nombre_entry.focus()

        # Imagen
        tk.Label(main_frame, text="Imagen de la Clasificación:", font=FONTS['normal'], 
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        
        self.imagen_var = tk.StringVar()

        # Área para mostrar la imagen
        self.image_label = tk.Label(main_frame, bg=COLORS['bg_primary'])
        self.image_label.pack(pady=(5, 10))
        self._display_image(None)

        tk.Button(main_frame, text="Examinar", command=self.browse_image, 
                 font=FONTS['button'], bg=COLORS['button_bg'], 
                 relief=tk.RAISED, borderwidth=2, padx=10, pady=5).pack(pady=(0, 20))

        # Botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Guardar", command=self.save_clasificacion,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def load_clasificacion_data(self):
        """Carga los datos de la clasificación a editar"""
        clasificacion = db.get_clasificacion(self.clasificacion_id)
        
        if not clasificacion:
            messagebox.showerror("Error", "Clasificación no encontrada")
            self.dialog.destroy()
            return
        
        self.nombre_var.set(clasificacion['nombre'])
        
        if clasificacion.get('imagen'):
            self.imagen_var.set(clasificacion['imagen'])
            self._display_image(clasificacion['imagen'])
    
    def browse_image(self):
        """Abre diálogo para seleccionar imagen"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="Seleccionar imagen de la clasificación",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if filename:
            # Copiar imagen a la carpeta images/clasificaciones/
            import shutil
            os.makedirs('images/clasificaciones', exist_ok=True)
            
            # Generar nombre único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            extension = os.path.splitext(filename)[1]
            nuevo_nombre = f"clasificacion_{timestamp}{extension}"
            destino = os.path.join('images/clasificaciones', nuevo_nombre)
            
            try:
                shutil.copy2(filename, destino)
                self.imagen_var.set(destino)
                self._display_image(destino)
                messagebox.showinfo("Éxito", "Imagen cargada correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"Error al copiar imagen: {str(e)}")
    
    def save_clasificacion(self):
        """Guarda la clasificación"""
        nombre = self.nombre_var.get().strip()
        
        if not nombre:
            messagebox.showerror("Error", "El nombre es obligatorio")
            return
        
        # Verificar si el nombre ya existe
        if db.clasificacion_nombre_exists(nombre, exclude_id=self.clasificacion_id):
            messagebox.showerror("Error", f"Ya existe una clasificación con el nombre '{nombre}'")
            return
        
        try:
            if self.clasificacion_id:
                # Actualizar clasificación existente
                db.update_clasificacion(
                    self.clasificacion_id,
                    nombre=nombre,
                    imagen=self.imagen_var.get() or None
                )
                messagebox.showinfo("Éxito", "Clasificación actualizada correctamente")
            else:
                # Crear nueva clasificación
                db.add_clasificacion(
                    nombre=nombre,
                    imagen=self.imagen_var.get() or None
                )
                messagebox.showinfo("Éxito", "Clasificación creada correctamente")
            
            if self.callback:
                self.callback()
            
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar clasificación: {str(e)}")


# El resto de las clases (ProductoDialog, IngredienteRecetaDialog, RegistrarCompraUnitariaDialog) 
# continúan en la siguiente parte...

class ProductoDialog:
    def __init__(self, parent, producto_id=None, callback=None):
        self.producto_id = producto_id
        self.callback = callback
        self.ingredientes_agregados = []
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Añadir Producto" if not producto_id else "Editar Producto")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.minsize(600, 500)
        
        # Forzar al frente
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        self.setup_ui()
        
        if producto_id:
            self.load_producto_data()

        # Centrar después de crear UI y cargar datos
        self.center_dialog()
        self.dialog.iconbitmap(get_resource_path('icono.ico'))
    
    IMAGE_DISPLAY_SIZE = (150, 150)

    def center_dialog(self):
        """Centra el diálogo en la pantalla"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_reqwidth()
        height = self.dialog.winfo_reqheight()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _display_image(self, image_path):
        """Carga, redimensiona y muestra una imagen en el image_label."""
        try:
            if image_path and os.path.exists(image_path):
                original_image = Image.open(image_path)
            else:
                original_image = Image.open(get_resource_path('images/placeholder.png'))
            
            # Redimensionar imagen manteniendo el aspecto
            original_width, original_height = original_image.size
            ratio = min(self.IMAGE_DISPLAY_SIZE[0] / original_width,
                        self.IMAGE_DISPLAY_SIZE[1] / original_height)
            
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            
            resized_image = original_image.resize((new_width, new_height), Image.LANCZOS)
            
            self.tk_image = ImageTk.PhotoImage(resized_image)
            self.image_label.config(image=self.tk_image)
            self.image_label.image = self.tk_image
        except Exception as e:
            print(f"Error al cargar o mostrar imagen: {e}")
            try:
                placeholder_image = Image.open(get_resource_path('images/placeholder.png'))
                placeholder_image = placeholder_image.resize(self.IMAGE_DISPLAY_SIZE, Image.LANCZOS)
                self.tk_image = ImageTk.PhotoImage(placeholder_image)
                self.image_label.config(image=self.tk_image)
                self.image_label.image = self.tk_image
            except Exception as e_placeholder:
                print(f"Error al cargar placeholder: {e_placeholder}")
                self.image_label.config(image='')

    def setup_ui(self):
        """Configura la interfaz del diálogo con dos columnas"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar grid para dos columnas
        main_frame.grid_columnconfigure(0, weight=1, minsize=250)
        main_frame.grid_columnconfigure(1, weight=1, minsize=250)

        # --- Columna Izquierda ---
        left_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # ID (editable)
        tk.Label(left_frame, text="ID:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(10, 5))
        self.id_var = tk.StringVar()
        if not self.producto_id:
            self.id_var.set(str(db.get_next_producto_id()))
        else:
            self.id_var.set(str(self.producto_id))
        tk.Entry(left_frame, textvariable=self.id_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))

        # Nombre
        tk.Label(left_frame, text="Nombre:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(10, 5))
        self.nombre_var = tk.StringVar()
        tk.Entry(left_frame, textvariable=self.nombre_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))

        # NUEVO: Clasificación
        tk.Label(left_frame, text="Clasificación:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(10, 5))
        self.clasificacion_var = tk.StringVar(value='Sin clasificación')
        
        clasificaciones = db.get_clasificaciones()
        clasificaciones_dict = {'Sin clasificación': None}
        for c in clasificaciones:
            clasificaciones_dict[c['nombre']] = c['id']
        
        self.clasificaciones_dict = clasificaciones_dict
        clasificacion_combo = ttk.Combobox(left_frame, textvariable=self.clasificacion_var,
                                          font=FONTS['normal'], state='readonly',
                                          values=list(clasificaciones_dict.keys()))
        clasificacion_combo.pack(fill=tk.X, pady=(0, 10))

        # Precio Unitario
        tk.Label(left_frame, text="Precio Unitario:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.precio_var = tk.StringVar()
        tk.Entry(left_frame, textvariable=self.precio_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))

        # Costo
        tk.Label(left_frame, text="Costo:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.costo_var = tk.StringVar()
        costo_entry = tk.Entry(left_frame, textvariable=self.costo_var, font=FONTS['normal'])
        costo_entry.pack(fill=tk.X, pady=(0, 5))
        tk.Label(left_frame, text="(Se calcula si tiene receta)", font=FONTS['small'], bg=COLORS['bg_primary'], fg=COLORS['text_secondary']).pack(anchor='w', pady=(0, 10))

        # Cantidad en stock (opcional)
        tk.Label(left_frame, text="Cantidad en Stock (opcional):", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.stock_var = tk.StringVar(value="0")
        tk.Entry(left_frame, textvariable=self.stock_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))

        # --- Columna Derecha ---
        right_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Unidad de Medida
        tk.Label(right_frame, text="Unidad de Medida:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=(10, 5))
        unidad_frame = tk.Frame(right_frame, bg=COLORS['bg_primary'])
        unidad_frame.pack(anchor='w', pady=(0, 10), fill=tk.X)
        self.unidad_var = tk.StringVar(value='Pza')
        for unidad in ['Pza', 'Kg', 'L']:
            tk.Radiobutton(unidad_frame, text=unidad, variable=self.unidad_var, value=unidad, font=FONTS['normal'], bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=5)

        # Gestionar inventario
        tk.Label(right_frame, text="Gestionar inventario:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        gestion_frame = tk.Frame(right_frame, bg=COLORS['bg_primary'])
        gestion_frame.pack(anchor='w', pady=(0, 10), fill=tk.X)
        self.gestion_var = tk.BooleanVar(value=False)
        self.gestion_var.trace('w', self.toggle_ingredientes)
        tk.Radiobutton(gestion_frame, text="Sí", variable=self.gestion_var, value=True, font=FONTS['normal'], bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(gestion_frame, text="No", variable=self.gestion_var, value=False, font=FONTS['normal'], bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=5)

        # Imagen del producto
        tk.Label(right_frame, text="Imagen del producto:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.imagen_var = tk.StringVar()

        # Área para mostrar la imagen
        self.image_label = tk.Label(right_frame, bg=COLORS['bg_primary'])
        self.image_label.pack(pady=(5, 10))
        self._display_image(None)

        tk.Button(right_frame, text="Examinar", command=self.browse_image, font=FONTS['button'], bg=COLORS['button_bg'], relief=tk.RAISED, borderwidth=2, padx=10, pady=5).pack(pady=(0, 10))

        # --- Frame de Ingredientes (oculto inicialmente) ---
        self.ingredientes_frame = tk.Frame(main_frame, bg=COLORS['bg_secondary'], relief=tk.SUNKEN, borderwidth=2)
        self.ingredientes_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=10)
        
        tk.Label(self.ingredientes_frame, text="Ingredientes de la receta:", font=FONTS['heading'], bg=COLORS['bg_secondary']).pack(pady=10)
        self.ingredientes_listbox = tk.Listbox(self.ingredientes_frame, font=FONTS['normal'], height=5)
        self.ingredientes_listbox.pack(fill=tk.X, expand=True, padx=10, pady=5)
        
        self.btn_add_ingrediente = tk.Button(self.ingredientes_frame, text="Añadir Ingrediente", command=self.add_ingrediente_dialog, font=FONTS['button'], bg=COLORS['button_bg'], relief=tk.RAISED, borderwidth=2, padx=15, pady=5)
        self.btn_add_ingrediente.pack(pady=10)
        self.ingredientes_frame.grid_remove()

        # --- Botones ---
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        tk.Button(button_frame, text="Aceptar", command=self.save_producto, font=FONTS['button'], bg=COLORS['success'], fg='white', relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy, font=FONTS['button'], bg=COLORS['danger'], fg='white', relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)

    def toggle_ingredientes(self, *args):
        """Muestra/oculta el frame de ingredientes y ajusta la ventana."""
        if self.gestion_var.get():
            self.ingredientes_frame.grid()
        else:
            self.ingredientes_frame.grid_remove()
        
        # Forzar actualización de tamaño y recentrar
        self.dialog.update_idletasks()
        self.center_dialog()
    
    def load_producto_data(self):
        """Carga los datos del producto a editar"""
        producto = db.get_producto(self.producto_id)
        
        if not producto:
            messagebox.showerror("Error", "Producto no encontrado")
            self.dialog.destroy()
            return
        
        self.id_var.set(str(producto['id']))
        self.nombre_var.set(producto['nombre'])
        self.precio_var.set(str(producto['precio_unitario']))
        self.costo_var.set(str(producto['costo']))
        self.unidad_var.set(producto['unidad_medida'])
        self.gestion_var.set(bool(producto['gestion_stock']))
        self.stock_var.set(str(producto['stock_estimado']))
        
        # Cargar clasificación
        if producto.get('clasificacion_id'):
            clasificacion = db.get_clasificacion(producto['clasificacion_id'])
            if clasificacion:
                self.clasificacion_var.set(clasificacion['nombre'])
        else:
            self.clasificacion_var.set('Sin clasificación')
        
        # Cargar ingredientes si tiene
        if producto['gestion_stock']:
            recetas = db.get_recetas_producto(self.producto_id)
            for receta in recetas:
                self.ingredientes_agregados.append({
                    'id': receta['id_ingrediente'],
                    'nombre': receta['ingrediente_nombre'],
                    'cantidad': receta['cantidad_requerida'],
                    'unidad': receta['unidad_porcionamiento']
                })
            
            self.update_ingredientes_list()
            
        if producto.get('imagen'):
            self.imagen_var.set(producto['imagen'])
            self._display_image(producto['imagen'])
    
    def add_ingrediente_dialog(self):
        """Abre diálogo para añadir ingrediente"""
        IngredienteRecetaDialog(self.dialog, callback=self.add_ingrediente_to_list)
    
    def add_ingrediente_to_list(self, ingrediente_data):
        """Añade un ingrediente a la lista"""
        self.ingredientes_agregados.append(ingrediente_data)
        self.update_ingredientes_list()
    
    def update_ingredientes_list(self):
        """Actualiza la lista de ingredientes"""
        self.ingredientes_listbox.delete(0, tk.END)
        
        for ing in self.ingredientes_agregados:
            text = f"{ing['nombre']} - {ing['cantidad']} {ing['unidad']}"
            self.ingredientes_listbox.insert(tk.END, text)
    
    def save_producto(self):
        """Guarda el producto"""
        # Validar ID
        try:
            new_id = int(self.id_var.get())
            if new_id <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "El ID debe ser un número entero positivo")
            return
        
        # Validaciones
        nombre = self.nombre_var.get().strip()
        if not nombre:
            messagebox.showerror("Error", "El nombre es obligatorio")
            return
        
        try:
            precio = float(self.precio_var.get())
            costo = float(self.costo_var.get()) if self.costo_var.get() else 0
            stock = float(self.stock_var.get()) if self.stock_var.get() else 0
        except ValueError:
            messagebox.showerror("Error", "Precio, costo y stock deben ser números válidos")
            return
        
        gestion = self.gestion_var.get()
        
        # Obtener clasificacion_id
        clasificacion_nombre = self.clasificacion_var.get()
        clasificacion_id = self.clasificaciones_dict.get(clasificacion_nombre)
        
        if gestion and not self.ingredientes_agregados:
            messagebox.showwarning("Advertencia", 
                                   "Si gestiona inventario, debe añadir al menos un ingrediente")
            return
        
        try:
            if self.producto_id:
                # Actualizar producto
                db.update_producto(self.producto_id, new_id,
                                 nombre=nombre,
                                 precio_unitario=precio,
                                 costo=costo,
                                 unidad_medida=self.unidad_var.get(),
                                 gestion_stock=1 if gestion else 0,
                                 stock_estimado=stock,
                                 imagen=self.imagen_var.get() or None,
                                 clasificacion_id=clasificacion_id)
                
                # Eliminar recetas anteriores
                recetas_anteriores = db.get_recetas_producto(new_id)
                for receta in recetas_anteriores:
                    db.delete_receta(receta['id'])
                
                producto_id = new_id
            else:
                # Verificar si el ID ya existe
                if db.id_exists('productos', new_id):
                    messagebox.showerror("Error", f"El ID {new_id} ya existe")
                    return
                
                # Crear nuevo producto
                producto_id = db.add_producto(new_id, nombre, precio, costo,
                                            self.unidad_var.get(), gestion,
                                            stock, imagen=self.imagen_var.get() or None,
                                            clasificacion_id=clasificacion_id)
            
            # Añadir ingredientes (recetas)
            if gestion:
                for ing in self.ingredientes_agregados:
                    receta_id = db.get_next_receta_id()
                    db.add_receta(receta_id, producto_id, ing['id'], 
                                ing['cantidad'], ing['unidad'])
            
            if self.callback:
                self.callback()
            
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar producto: {str(e)}")
            
    def browse_image(self):
        """Abre diálogo para seleccionar imagen"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="Seleccionar imagen del producto",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if filename:
            # Copiar imagen a la carpeta images/productos/
            import shutil
            os.makedirs('images/productos', exist_ok=True)
            
            # Generar nombre único
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            extension = os.path.splitext(filename)[1]
            nuevo_nombre = f"producto_{timestamp}{extension}"
            destino = os.path.join('images/productos', nuevo_nombre)
            
            try:
                shutil.copy2(filename, destino)
                self.imagen_var.set(destino)
                self._display_image(destino)
                messagebox.showinfo("Éxito", "Imagen cargada correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"Error al copiar imagen: {str(e)}")


class IngredienteRecetaDialog:
    def __init__(self, parent, callback=None):
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Añadir Ingrediente a Receta")
        self.dialog.geometry("400x300")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.minsize(400, 250)
        
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
        width = 400
        height = 300
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Configura la interfaz"""
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Ingrediente
        tk.Label(main_frame, text="Ingrediente:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        
        self.ingrediente_var = tk.StringVar()
        self.ingrediente_combo = ttk.Combobox(main_frame, 
                                             textvariable=self.ingrediente_var,
                                             font=FONTS['normal'], state='readonly')
        self.ingrediente_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Cargar ingredientes
        ingredientes = db.get_ingredientes()
        self.ingredientes_dict = {f"{i['nombre']} (ID: {i['id']})": i 
                                 for i in ingredientes}
        self.ingrediente_combo['values'] = list(self.ingredientes_dict.keys())
        
        # Cantidad requerida
        tk.Label(main_frame, text="Cantidad Requerida:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        self.cantidad_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=self.cantidad_var, 
                font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))
        
        # Unidad de porcionamiento
        tk.Label(main_frame, text="Unidad de Porcionamiento:", font=FONTS['normal'],
                bg=COLORS['bg_primary']).pack(anchor='w', pady=5)
        
        unidad_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        unidad_frame.pack(anchor='w', pady=(0, 20))
        
        self.unidad_var = tk.StringVar(value='Kg')
        for unidad in ['Pza', 'Kg', 'L']:
            tk.Radiobutton(unidad_frame, text=unidad, variable=self.unidad_var,
                          value=unidad, font=FONTS['normal'],
                          bg=COLORS['bg_primary']).pack(side=tk.LEFT, padx=10)
        
        # Botones
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack()
        
        tk.Button(button_frame, text="Aceptar", command=self.accept,
                 font=FONTS['button'], bg=COLORS['success'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy,
                 font=FONTS['button'], bg=COLORS['danger'], fg='white',
                 relief=tk.RAISED, borderwidth=2, padx=30, pady=10).pack(side=tk.LEFT, padx=10)
    
    def accept(self):
        """Acepta y retorna los datos"""
        if not self.ingrediente_var.get():
            messagebox.showerror("Error", "Debe seleccionar un ingrediente")
            return
        
        try:
            cantidad = float(self.cantidad_var.get())
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número válido")
            return
        
        ingrediente = self.ingredientes_dict[self.ingrediente_var.get()]
        
        data = {
            'id': ingrediente['id'],
            'nombre': ingrediente['nombre'],
            'cantidad': cantidad,
            'unidad': self.unidad_var.get()
        }
        
        if self.callback:
            self.callback(data)
        
        self.dialog.destroy()


class RegistrarCompraUnitariaDialog:
    def __init__(self, parent, producto_id, producto_nombre, callback=None):
        self.producto_id = producto_id
        self.producto_nombre = producto_nombre
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Registrar Compra de Producto")
        self.dialog.configure(bg=COLORS['bg_primary'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.minsize(400, 300)
        
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.after(100, lambda: self.dialog.attributes('-topmost', False))
        
        self.setup_ui()
        self.center_dialog()
        self.dialog.iconbitmap(get_resource_path('icono.ico'))

    def center_dialog(self):
        self.dialog.update_idletasks()
        width = 400
        height = 300
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg=COLORS['bg_primary'], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text=f"Producto: {self.producto_nombre}", font=FONTS['heading'], bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=(0, 15))

        tk.Label(main_frame, text="Cantidad por Caja:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w')
        self.cantidad_caja_var = tk.StringVar(value="1")
        tk.Entry(main_frame, textvariable=self.cantidad_caja_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 10))

        tk.Label(main_frame, text="Cajas Compradas:", font=FONTS['normal'], bg=COLORS['bg_primary']).pack(anchor='w')
        self.cajas_var = tk.StringVar(value="1")
        tk.Entry(main_frame, textvariable=self.cajas_var, font=FONTS['normal']).pack(fill=tk.X, pady=(0, 20))

        button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        button_frame.pack()
        
        tk.Button(button_frame, text="Aceptar", command=self.accept, font=FONTS['button'], bg=COLORS['success'], fg='white', relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancelar", command=self.dialog.destroy, font=FONTS['button'], bg=COLORS['danger'], fg='white', relief=tk.RAISED, borderwidth=2, padx=20, pady=10).pack(side=tk.LEFT, padx=10)

    def accept(self):
        try:
            cantidad_caja = int(self.cantidad_caja_var.get())
            cajas = int(self.cajas_var.get())
            
            if cantidad_caja <= 0 or cajas <= 0:
                messagebox.showerror("Error", "Las cantidades deben ser números enteros mayores a 0.")
                return

            total_a_sumar = cantidad_caja * cajas
            
            producto = db.get_producto(self.producto_id)
            stock_actual = producto['stock_estimado']
            nuevo_stock = stock_actual + total_a_sumar
            
            db.update_producto(self.producto_id, self.producto_id, stock_estimado=nuevo_stock)
            
            messagebox.showinfo("Éxito", f"Se agregaron {total_a_sumar} unidades al stock de '{self.producto_nombre}'.\nNuevo stock: {nuevo_stock}")
            
            if self.callback:
                self.callback()
            
            self.dialog.destroy()

        except ValueError:
            messagebox.showerror("Error", "Por favor, ingrese números enteros válidos.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
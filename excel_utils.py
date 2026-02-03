"""
Utilidades para importar y exportar datos a Excel
"""
import pandas as pd
from tkinter import filedialog, messagebox
from datetime import datetime
import os
import zipfile
import tempfile
import shutil


class ExcelManager:
    """Gestor de importación/exportación de Excel"""
    
    @staticmethod
    def exportar_a_excel(data, columnas, nombre_archivo_sugerido, titulo_hoja="Datos"):
        """
        Exporta datos a Excel
        
        Args:
            data: Lista de tuplas con los datos
            columnas: Lista de nombres de columnas
            nombre_archivo_sugerido: Nombre sugerido para el archivo
            titulo_hoja: Nombre de la hoja de Excel
        """
        try:
            # Abrir diálogo para guardar archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_default = f"{nombre_archivo_sugerido}_{timestamp}.xlsx"
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=nombre_default,
                title="Guardar archivo Excel"
            )
            
            if not filename:
                return False
            
            # Crear DataFrame
            df = pd.DataFrame(data, columns=columnas)
            
            # Exportar a Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=titulo_hoja, index=False)
                
                # Ajustar ancho de columnas
                worksheet = writer.sheets[titulo_hoja]
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
            
            messagebox.showinfo("Éxito", f"Datos exportados correctamente a:\n{filename}")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar a Excel:\n{str(e)}")
            return False
    
    @staticmethod
    def importar_desde_excel(columnas_esperadas, titulo_dialogo="Seleccionar archivo Excel"):
        """
        Importa datos desde Excel
        
        Args:
            columnas_esperadas: Lista de nombres de columnas esperadas
            titulo_dialogo: Título del diálogo de selección
            
        Returns:
            Lista de diccionarios con los datos o None si hay error
        """
        try:
            # Abrir diálogo para seleccionar archivo
            filename = filedialog.askopenfilename(
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
                title=titulo_dialogo
            )
            
            if not filename:
                return None
            
            # Leer archivo Excel
            df = pd.read_excel(filename, engine='openpyxl')
            
            # Verificar columnas
            columnas_faltantes = set(columnas_esperadas) - set(df.columns)
            if columnas_faltantes:
                messagebox.showerror(
                    "Error de formato",
                    f"El archivo no tiene las columnas requeridas.\n\n"
                    f"Columnas faltantes: {', '.join(columnas_faltantes)}\n\n"
                    f"Columnas esperadas: {', '.join(columnas_esperadas)}"
                )
                return None
            
            # Convertir a lista de diccionarios
            datos = df.to_dict('records')
            
            # Limpiar valores NaN
            for registro in datos:
                for key in registro:
                    if pd.isna(registro[key]):
                        registro[key] = None
            
            messagebox.showinfo("Éxito", f"Se importaron {len(datos)} registros correctamente")
            return datos
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al importar desde Excel:\n{str(e)}")
            return None
    
    @staticmethod
    def exportar_treeview_a_excel(tree, nombre_archivo_sugerido, titulo_hoja="Datos"):
        """
        Exporta datos directamente desde un Treeview a Excel
        
        Args:
            tree: Widget Treeview de tkinter
            nombre_archivo_sugerido: Nombre sugerido para el archivo
            titulo_hoja: Nombre de la hoja de Excel
        """
        try:
            # Obtener columnas
            columnas = list(tree['columns'])
            
            # Obtener datos
            datos = []
            for item in tree.get_children():
                valores = tree.item(item)['values']
                datos.append(valores)
            
            if not datos:
                messagebox.showwarning("Sin datos", "No hay datos para exportar")
                return False
            
            return ExcelManager.exportar_a_excel(datos, columnas, nombre_archivo_sugerido, titulo_hoja)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar:\n{str(e)}")
            return False


# Funciones específicas para cada módulo

def exportar_productos_excel(productos):
    """Exporta productos y clasificaciones a un archivo ZIP con Excel e imágenes."""
    from database import db # Import db locally

    # --- Preparar datos de Productos ---
    columnas_productos = ['ID', 'Nombre', 'Clasificación', 'Precio Unitario', 'Costo', 'Ganancia', 
                          'Unidad Medida', 'Stock Estimado', 'Stock Mínimo', 'Gestión Stock', 'Imagen']
    
    datos_productos_excel = []
    rutas_imagenes = []
    
    for p in productos:
        nombre_imagen = None
        if p.get('imagen') and os.path.exists(p['imagen']):
            nombre_imagen = os.path.basename(p['imagen'])
            rutas_imagenes.append(p['imagen'])
        
        datos_productos_excel.append((
            p['id'],
            p['nombre'],
            p.get('clasificacion_nombre', ''), # Añadir nombre de clasificación
            p['precio_unitario'],
            p['costo'],
            p['ganancia'],
            p['unidad_medida'],
            p['stock_estimado'],
            p['stock_minimo'],
            'Sí' if p['gestion_stock'] else 'No',
            nombre_imagen
        ))

    # --- Preparar datos de Clasificaciones ---
    clasificaciones = db.get_clasificaciones(activos_only=True)
    columnas_clasificaciones = ['ID', 'Nombre']
    datos_clasificaciones_excel = [(c['id'], c['nombre']) for c in clasificaciones]

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_default = f"exportacion_productos_{timestamp}.zip"
        
        zip_filename = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip")],
            initialfile=nombre_default,
            title="Guardar exportación de productos"
        )
        
        if not zip_filename:
            return False
            
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Guardar el archivo Excel con ambas hojas
            excel_path = os.path.join(temp_dir, "productos_y_clasificaciones.xlsx")
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Hoja de Productos
                df_productos = pd.DataFrame(datos_productos_excel, columns=columnas_productos)
                df_productos.to_excel(writer, sheet_name="Productos", index=False)
                
                # Hoja de Clasificaciones
                df_clasificaciones = pd.DataFrame(datos_clasificaciones_excel, columns=columnas_clasificaciones)
                df_clasificaciones.to_excel(writer, sheet_name="Clasificaciones", index=False)

            # 2. Copiar imágenes
            imagenes_dir = os.path.join(temp_dir, "imagenes_productos")
            os.makedirs(imagenes_dir, exist_ok=True)
            
            for ruta_img in rutas_imagenes:
                shutil.copy(ruta_img, imagenes_dir)
            
            # 3. Crear el archivo ZIP
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                zipf.write(excel_path, arcname="productos_y_clasificaciones.xlsx")
                for ruta_img in rutas_imagenes:
                    nombre_img = os.path.basename(ruta_img)
                    zipf.write(os.path.join(imagenes_dir, nombre_img), arcname=f"imagenes_productos/{nombre_img}")

        messagebox.showinfo("Éxito", f"Productos y clasificaciones exportados correctamente a:\n{zip_filename}")
        return True

    except Exception as e:
        messagebox.showerror("Error", f"Error al exportar productos:\n{str(e)}")
        return False


def importar_productos_excel():
    """Importa productos y clasificaciones desde un archivo ZIP."""
    from database import db # Import db locally

    columnas_productos_esperadas = ['ID', 'Nombre', 'Clasificación', 'Precio Unitario', 'Costo', 
                                    'Unidad Medida', 'Stock Mínimo', 'Gestión Stock']
    columnas_clasificaciones_esperadas = ['ID', 'Nombre']
    
    zip_filename = filedialog.askopenfilename(
        filetypes=[("ZIP files", "*.zip")],
        title="Importar Productos y Clasificaciones desde ZIP"
    )
    
    if not zip_filename:
        return None
        
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Extraer el ZIP
            with zipfile.ZipFile(zip_filename, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # 2. Encontrar el archivo Excel
            excel_path = None
            for file in os.listdir(temp_dir):
                if file.endswith(".xlsx"):
                    excel_path = os.path.join(temp_dir, file)
                    break
            
            if not excel_path:
                messagebox.showerror("Error", "No se encontró un archivo .xlsx en el ZIP.")
                return None

            # 3. Leer ambas hojas del Excel
            try:
                dfs = pd.read_excel(excel_path, engine='openpyxl', sheet_name=['Productos', 'Clasificaciones'])
                df_productos = dfs['Productos']
                df_clasificaciones = dfs['Clasificaciones']
            except ValueError as e:
                messagebox.showerror("Error de formato", f"El archivo Excel debe contener las hojas 'Productos' y 'Clasificaciones'.\nDetalle: {e}")
                return None

            # 4. Validar columnas
            if not set(columnas_productos_esperadas).issubset(set(df_productos.columns)):
                faltantes = set(columnas_productos_esperadas) - set(df_productos.columns)
                messagebox.showerror("Error de formato", f"Columnas requeridas faltantes en la hoja 'Productos': {', '.join(faltantes)}")
                return None
            if not set(columnas_clasificaciones_esperadas).issubset(set(df_clasificaciones.columns)):
                faltantes = set(columnas_clasificaciones_esperadas) - set(df_clasificaciones.columns)
                messagebox.showerror("Error de formato", f"Columnas requeridas faltantes en la hoja 'Clasificaciones': {', '.join(faltantes)}")
                return None

            # 5. Procesar e importar Clasificaciones
            clasificaciones_importadas = df_clasificaciones.to_dict('records')
            mapa_nombres_clasif = {}
            
            for clasif in clasificaciones_importadas:
                nombre_clasif = str(clasif['Nombre']).strip()
                if nombre_clasif:
                    if not db.clasificacion_nombre_exists(nombre_clasif):
                        db.add_clasificacion(nombre=nombre_clasif)
                    
                    # Obtener el ID para el mapa (ya sea el recién creado o el existente)
                    c = db.cursor.execute('SELECT id FROM clasificaciones WHERE nombre = ? AND activo = 1', (nombre_clasif,)).fetchone()
                    if c:
                        mapa_nombres_clasif[nombre_clasif] = c['id']

            # 6. Procesar e importar Productos
            datos_productos = df_productos.to_dict('records')
            productos_validos = []
            for idx, registro in enumerate(datos_productos, start=2):
                try:
                    nombre_clasif_prod = str(registro.get('Clasificación', '')).strip()
                    clasificacion_id = mapa_nombres_clasif.get(nombre_clasif_prod)

                    producto = {
                        'id': int(registro['ID']),
                        'nombre': str(registro['Nombre']).strip(),
                        'precio_unitario': float(registro['Precio Unitario']),
                        'costo': float(registro.get('Costo', 0)),
                        'unidad_medida': str(registro.get('Unidad Medida', 'Pza')),
                        'stock_minimo': float(registro.get('Stock Mínimo', 0)),
                        'gestion_stock': str(registro.get('Gestión Stock', 'No')).lower() in ['sí', 'si', 'yes', '1', 'true'],
                        'clasificacion_id': clasificacion_id,
                        'imagen': None
                    }
                    
                    # Procesar imagen si existe
                    if 'Imagen' in registro and registro['Imagen'] and pd.notna(registro['Imagen']):
                        nombre_imagen = str(registro['Imagen'])
                        ruta_imagen_origen = os.path.join(temp_dir, "imagenes_productos", nombre_imagen)
                        
                        if os.path.exists(ruta_imagen_origen):
                            dest_folder = "images/productos"
                            os.makedirs(dest_folder, exist_ok=True)
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            _, extension = os.path.splitext(nombre_imagen)
                            nuevo_nombre = f"producto_{timestamp}_{idx}{extension}"
                            ruta_imagen_destino = os.path.join(dest_folder, nuevo_nombre)
                            shutil.copy(ruta_imagen_origen, ruta_imagen_destino)
                            producto['imagen'] = ruta_imagen_destino
                    
                    # Validaciones
                    if producto['id'] <= 0: raise ValueError("ID debe ser mayor a 0")
                    if not producto['nombre']: raise ValueError("Nombre es obligatorio")
                    
                    productos_validos.append(producto)
                    
                except Exception as e:
                    messagebox.showerror("Error en fila", f"Error en la fila {idx} de Productos: {str(e)}\n\nLa importación se detendrá.")
                    return None
            
            messagebox.showinfo("Éxito", f"Se procesaron {len(productos_validos)} productos y {len(clasificaciones_importadas)} clasificaciones para importar.")
            return productos_validos

    except Exception as e:
        messagebox.showerror("Error", f"Error al importar desde ZIP:\n{str(e)}")
        return None


def exportar_ingredientes_excel(ingredientes):
    """Exporta ingredientes a Excel"""
    columnas = ['ID', 'Ingrediente', 'Unidad Almacén', 'Costo Unitario', 
                'Cantidad Stock', 'Gestión Stock']
    
    datos = []
    for i in ingredientes:
        datos.append((
            i['id'],
            i['nombre'],
            i['unidad_almacen'],
            i['costo_unitario'],
            i['cantidad_stock'],
            'Sí' if i['gestion_stock'] else 'No'
        ))
    
    return ExcelManager.exportar_a_excel(datos, columnas, "ingredientes", "Ingredientes")


def importar_ingredientes_excel():
    """Importa ingredientes desde Excel"""
    columnas = ['ID', 'Ingrediente', 'Unidad Almacén', 'Costo Unitario', 
                'Cantidad Stock', 'Gestión Stock']
    
    datos = ExcelManager.importar_desde_excel(columnas, "Importar Ingredientes")
    
    if datos:
        ingredientes_validos = []
        for idx, registro in enumerate(datos, start=2):
            try:
                ingrediente = {
                    'id': int(registro['ID']),
                    'nombre': str(registro['Ingrediente']).strip(),
                    'unidad_almacen': str(registro['Unidad Almacén']),
                    'costo_unitario': float(registro['Costo Unitario']),
                    'cantidad_stock': float(registro.get('Cantidad Stock', 0)),
                    'gestion_stock': str(registro.get('Gestión Stock', 'No')).lower() in ['sí', 'si', 'yes', '1', 'true']
                }
                
                if ingrediente['id'] <= 0:
                    raise ValueError("ID debe ser mayor a 0")
                if not ingrediente['nombre']:
                    raise ValueError("Nombre es obligatorio")
                if ingrediente['unidad_almacen'] not in ['Pza', 'Kg', 'L']:
                    raise ValueError("Unidad debe ser Pza, Kg o L")
                
                ingredientes_validos.append(ingrediente)
                
            except Exception as e:
                messagebox.showerror("Error en fila", 
                    f"Error en fila {idx}: {str(e)}\n\nLa importación se detendrá.")
                return None
        
        return ingredientes_validos
    
    return None


def exportar_recetas_excel(recetas):
    """Exporta recetas a Excel"""
    columnas = ['ID Receta', 'ID Producto', 'Producto', 'ID Ingrediente', 
                'Ingrediente', 'Cantidad Requerida', 'Unidad Porcionamiento']
    
    datos = []
    for r in recetas:
        datos.append((
            r['id'],
            r['id_producto'],
            r['producto_nombre'],
            r['id_ingrediente'],
            r['ingrediente_nombre'],
            r['cantidad_requerida'],
            r['unidad_porcionamiento']
        ))
    
    return ExcelManager.exportar_a_excel(datos, columnas, "recetas", "Recetas")


def importar_recetas_excel():
    """Importa recetas desde Excel"""
    columnas = ['ID Receta', 'ID Producto', 'ID Ingrediente', 
                'Cantidad Requerida', 'Unidad Porcionamiento']
    
    datos = ExcelManager.importar_desde_excel(columnas, "Importar Recetas")
    
    if datos:
        recetas_validas = []
        for idx, registro in enumerate(datos, start=2):
            try:
                receta = {
                    'id': int(registro['ID Receta']),
                    'id_producto': int(registro['ID Producto']),
                    'id_ingrediente': int(registro['ID Ingrediente']),
                    'cantidad_requerida': float(registro['Cantidad Requerida']),
                    'unidad_porcionamiento': str(registro['Unidad Porcionamiento'])
                }
                
                if receta['id'] <= 0 or receta['id_producto'] <= 0 or receta['id_ingrediente'] <= 0:
                    raise ValueError("Los IDs deben ser mayores a 0")
                if receta['cantidad_requerida'] <= 0:
                    raise ValueError("Cantidad debe ser mayor a 0")
                if receta['unidad_porcionamiento'] not in ['Pza', 'Kg', 'L']:
                    raise ValueError("Unidad debe ser Pza, Kg o L")
                
                recetas_validas.append(receta)
                
            except Exception as e:
                messagebox.showerror("Error en fila", 
                    f"Error en fila {idx}: {str(e)}\n\nLa importación se detendrá.")
                return None
        
        return recetas_validas
    
    return None


def exportar_ventas_excel(ventas):
    """Exporta ventas a Excel - Formato simplificado"""
    columnas = ['No. Venta', 'No. Corte', 'Fecha', 'Producto', 'ID Producto',
                'Cantidad', 'Precio Unitario', 'Total', 'Método']
    
    datos = []
    for v in ventas:
        # Obtener numero_corte desde corte_id
        numero_corte = None
        if v.get('corte_id'):
            from database import db
            db.cursor.execute('SELECT numero_corte FROM cortes WHERE id = ?', (v['corte_id'],))
            result = db.cursor.fetchone()
            if result:
                numero_corte = result['numero_corte']
        
        datos.append((
            v['numero_venta'],
            numero_corte if numero_corte is not None else '',
            v['fecha'],
            v['producto'],
            v['id_producto'],
            v['cantidad'],
            v['precio_unitario'],
            v['total'],
            v['metodo_pago']
        ))
    
    return ExcelManager.exportar_a_excel(datos, columnas, "historial_ventas", "Ventas")


def importar_ventas_excel():
    """Importa ventas desde Excel - Formato simplificado"""
    columnas = ['No. Venta', 'No. Corte', 'Fecha', 'Producto', 'ID Producto', 
                'Cantidad', 'Precio Unitario', 'Total', 'Método']
    
    datos = ExcelManager.importar_desde_excel(columnas, "Importar Ventas")
    
    if datos:
        ventas_validas = []
        for idx, registro in enumerate(datos, start=2):
            try:
                # Obtener y validar numero_corte
                numero_corte = None
                if registro.get('No. Corte') is not None and pd.notna(registro.get('No. Corte')):
                    try:
                        numero_corte = int(registro['No. Corte'])
                    except ValueError:
                        pass
                
                venta = {
                    'numero_venta': int(registro['No. Venta']),
                    'numero_corte': numero_corte,
                    'fecha': str(registro['Fecha']),
                    'producto': str(registro['Producto']).strip(),
                    'id_producto': int(registro['ID Producto']),
                    'cantidad': float(registro['Cantidad']),
                    'precio_unitario': float(registro['Precio Unitario']),
                    'total': float(registro['Total']),
                    'metodo_pago': str(registro['Método']).strip(),
                    'mesa': None  # No se usa en este formato
                }
                
                # Validaciones
                if venta['numero_venta'] <= 0:
                    raise ValueError("Número de venta debe ser mayor a 0")
                if venta['cantidad'] <= 0:
                    raise ValueError("Cantidad debe ser mayor a 0")
                if venta['metodo_pago'] not in ['Efectivo', 'Transferencia', 'Tarjeta']:
                    raise ValueError("Método debe ser Efectivo, Transferencia o Tarjeta")
                
                ventas_validas.append(venta)
                
            except Exception as e:
                messagebox.showerror("Error en fila", 
                    f"Error en fila {idx}: {str(e)}\n\nLa importación se detendrá.")
                return None
        
        return ventas_validas
    
    return None



def exportar_cortes_excel(cortes):
    """Exporta cortes a Excel"""
    columnas = ['No. Corte', 'Fecha Inicio', 'Fecha Cierre', 'Dinero en Caja', 
                'Ventas Efectivo', 'Ventas Transferencia', 'Ventas Tarjeta', 'Total Ventas',
                'Corte Final', 'Corte Esperado', 'Retiros', 
                'Diferencia', 'Estado', 'Ganancias']
    
    datos = []
    for c in cortes:
        # Calcular total de ventas
        total_ventas = c.get('ventas_efectivo', 0) + c.get('ventas_transferencia', 0) + c.get('ventas_tarjeta', 0)
        
        # Usar fecha_cierre si existe, sino fecha_inicio
        fecha_inicio = c.get('fecha_inicio', c.get('fecha', ''))
        fecha_cierre = c.get('fecha_cierre', '')
        
        datos.append((
            c['numero_corte'],
            fecha_inicio,
            fecha_cierre,
            c['dinero_en_caja'],
            c.get('ventas_efectivo', 0),
            c.get('ventas_transferencia', 0),
            c.get('ventas_tarjeta', 0),
            total_ventas,
            c['corte_final'],
            c['corte_esperado'],
            c['retiros'],
            c['diferencia'],
            c['estado'],
            c['ganancias']
        ))
    
    return ExcelManager.exportar_a_excel(datos, columnas, "cortes", "Cortes")


def importar_cortes_excel():
    """Importa cortes desde Excel"""
    columnas = ['No. Corte', 'Fecha Inicio', 'Dinero en Caja', 
                'Ventas Efectivo', 'Ventas Transferencia', 'Ventas Tarjeta',
                'Corte Final', 'Retiros', 'Ganancias']
    
    datos = ExcelManager.importar_desde_excel(columnas, "Importar Cortes")
    
    if datos:
        cortes_validos = []
        for idx, registro in enumerate(datos, start=2):
            try:
                # Fecha Cierre es opcional
                fecha_cierre = registro.get('Fecha Cierre', None)
                if fecha_cierre and pd.notna(fecha_cierre):
                    fecha_cierre = str(fecha_cierre)
                else:
                    fecha_cierre = None
                
                corte = {
                    'numero_corte': int(registro['No. Corte']),
                    'fecha_inicio': str(registro['Fecha Inicio']),
                    'fecha_cierre': fecha_cierre,
                    'dinero_en_caja': float(registro['Dinero en Caja']),
                    'ventas_efectivo': float(registro.get('Ventas Efectivo', 0)),
                    'ventas_transferencia': float(registro.get('Ventas Transferencia', 0)),
                    'ventas_tarjeta': float(registro.get('Ventas Tarjeta', 0)),
                    'corte_final': float(registro['Corte Final']),
                    'retiros': float(registro.get('Retiros', 0)),
                    'ganancias': float(registro.get('Ganancias', 0))
                }
                
                if corte['numero_corte'] <= 0:
                    raise ValueError("Número de corte debe ser mayor a 0")
                
                cortes_validos.append(corte)
                
            except Exception as e:
                messagebox.showerror("Error en fila", 
                    f"Error en fila {idx}: {str(e)}\n\nLa importación se detendrá.")
                return None
        
        return cortes_validos
    
    return None

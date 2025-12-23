"""
Utilidades para importar y exportar datos a Excel
"""
import pandas as pd
from tkinter import filedialog, messagebox
from datetime import datetime
import os


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
    """Exporta productos a Excel"""
    columnas = ['ID', 'Nombre', 'Precio Unitario', 'Costo', 'Ganancia', 
                'Unidad Medida', 'Stock Estimado', 'Stock Mínimo', 'Gestión Stock']
    
    datos = []
    for p in productos:
        datos.append((
            p['id'],
            p['nombre'],
            p['precio_unitario'],
            p['costo'],
            p['ganancia'],
            p['unidad_medida'],
            p['stock_estimado'],
            p['stock_minimo'],
            'Sí' if p['gestion_stock'] else 'No'
        ))
    
    return ExcelManager.exportar_a_excel(datos, columnas, "productos", "Productos")


def importar_productos_excel():
    """Importa productos desde Excel"""
    columnas = ['ID', 'Nombre', 'Precio Unitario', 'Costo', 'Unidad Medida', 
                'Stock Mínimo', 'Gestión Stock']
    
    datos = ExcelManager.importar_desde_excel(columnas, "Importar Productos")
    
    if datos:
        # Validar y convertir datos
        productos_validos = []
        for idx, registro in enumerate(datos, start=2):  # Empieza en 2 por el header
            try:
                producto = {
                    'id': int(registro['ID']),
                    'nombre': str(registro['Nombre']).strip(),
                    'precio_unitario': float(registro['Precio Unitario']),
                    'costo': float(registro.get('Costo', 0)),
                    'unidad_medida': str(registro.get('Unidad Medida', 'Pza')),
                    'stock_minimo': float(registro.get('Stock Mínimo', 0)),
                    'gestion_stock': str(registro.get('Gestión Stock', 'No')).lower() in ['sí', 'si', 'yes', '1', 'true']
                }
                
                # Validaciones
                if producto['id'] <= 0:
                    raise ValueError("ID debe ser mayor a 0")
                if not producto['nombre']:
                    raise ValueError("Nombre es obligatorio")
                if producto['precio_unitario'] < 0:
                    raise ValueError("Precio no puede ser negativo")
                
                productos_validos.append(producto)
                
            except Exception as e:
                messagebox.showerror("Error en fila", 
                    f"Error en fila {idx}: {str(e)}\n\nLa importación se detendrá.")
                return None
        
        return productos_validos
    
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
    """Exporta ventas a Excel"""
    columnas = ['No. Venta', 'Fecha', 'Producto', 'Cantidad', 
                'Precio Unitario', 'Total', 'Método', 'Mesa']
    
    datos = []
    for v in ventas:
        datos.append((
            v['numero_venta'],
            v['fecha'],
            v['producto'],
            v['cantidad'],
            v['precio_unitario'],
            v['total'],
            v['metodo_pago'],
            v['mesa'] if v['mesa'] else ''
        ))
    
    return ExcelManager.exportar_a_excel(datos, columnas, "historial_ventas", "Ventas")


def importar_ventas_excel():
    """Importa ventas desde Excel"""
    columnas = ['No. Venta', 'No. Corte', 'Fecha', 'Producto', 'ID Producto', 'Cantidad', 
                'Precio Unitario', 'Total', 'Método']
    
    datos = ExcelManager.importar_desde_excel(columnas, "Importar Ventas")
    
    if datos:
        ventas_validas = []
        for idx, registro in enumerate(datos, start=2):
            try:
                venta = {
                    'numero_venta': int(registro['No. Venta']),
                    'numero_corte': int(registro['No. Corte']) if registro.get('No. Corte') is not None and pd.notna(registro['No. Corte']) else None,
                    'fecha': str(registro['Fecha']),
                    'producto': str(registro['Producto']).strip(),
                    'id_producto': int(registro['ID Producto']),
                    'cantidad': float(registro['Cantidad']),
                    'precio_unitario': float(registro['Precio Unitario']),
                    'total': float(registro['Total']),
                    'metodo_pago': str(registro.get('Método', 'Efectivo')),
                    'mesa': str(registro.get('Mesa', '')) if registro.get('Mesa') else None
                }
                
                if venta['numero_venta'] <= 0:
                    raise ValueError("Número de venta debe ser mayor a 0")
                if venta['cantidad'] <= 0:
                    raise ValueError("Cantidad debe ser mayor a 0")
                if venta['metodo_pago'] not in ['Efectivo', 'Transferencia']:
                    raise ValueError("Método debe ser Efectivo o Transferencia")
                
                ventas_validas.append(venta)
                
            except Exception as e:
                messagebox.showerror("Error en fila", 
                    f"Error en fila {idx}: {str(e)}\n\nLa importación se detendrá.")
                return None
        
        return ventas_validas
    
    return None



def exportar_cortes_excel(cortes):
    """Exporta cortes a Excel"""
    columnas = ['No. Corte', 'Fecha', 'Dinero en Caja', 'Corte Final', 
                'Corte Esperado', 'Retiros', 'Diferencia', 'Estado', 'Ganancias']
    
    datos = []
    for c in cortes:
        datos.append((
            c['numero_corte'],
            c['fecha'],
            c['dinero_en_caja'],
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
    columnas = ['No. Corte', 'Fecha', 'Dinero en Caja', 'Corte Final', 
                'Retiros', 'Ganancias']
    
    datos = ExcelManager.importar_desde_excel(columnas, "Importar Cortes")
    
    if datos:
        cortes_validos = []
        for idx, registro in enumerate(datos, start=2):
            try:
                corte = {
                    'numero_corte': int(registro['No. Corte']),
                    'fecha': str(registro['Fecha']),
                    'dinero_en_caja': float(registro['Dinero en Caja']),
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
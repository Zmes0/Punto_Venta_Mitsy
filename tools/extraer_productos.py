"""
Script para extraer productos de la base de datos antigua (mitsys.db)
y generar un archivo Excel compatible con el sistema actual
"""
import sqlite3
import pandas as pd
from datetime import datetime
import os

def extraer_productos_de_bd_antigua(db_path="mitsys_antigua.db"):
    """
    Extrae productos de la base de datos antigua y genera Excel
    
    Args:
        db_path: Ruta a la base de datos antigua (renombra tu archivo a este nombre)
    """
    
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró el archivo '{db_path}'")
        print(f"   Por favor, coloca tu archivo 'mitsys.db' en la misma carpeta")
        print(f"   y renómbralo a '{db_path}' para evitar sobrescribir la BD actual")
        return
    
    try:
        # Conectar a la base de datos antigua
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Extraer productos
        cursor.execute('''
            SELECT 
                id,
                nombre,
                precio_unitario,
                costo,
                ganancia,
                unidad_medida,
                stock_estimado,
                stock_minimo,
                gestion_stock,
                imagen,
                activo
            FROM productos
            WHERE activo = 1
            ORDER BY id
        ''')
        
        productos = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        if not productos:
            print("⚠ No se encontraron productos en la base de datos")
            return
        
        print(f"✓ Se encontraron {len(productos)} productos")
        
        # Crear DataFrame con el formato correcto para importar
        data = []
        for p in productos:
            data.append({
                'ID': p['id'],
                'Nombre': p['nombre'],
                'Precio Unitario': p['precio_unitario'],
                'Costo': p['costo'],
                'Unidad Medida': p['unidad_medida'],
                'Stock Mínimo': p['stock_minimo'],
                'Gestión Stock': 'Sí' if p['gestion_stock'] else 'No'
            })
        
        df = pd.DataFrame(data)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"productos_extraidos_{timestamp}.xlsx"
        
        # Exportar a Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Productos', index=False)
            
            # Ajustar ancho de columnas
            worksheet = writer.sheets['Productos']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
        
        print(f"\n✅ Productos exportados correctamente a: {filename}")
        print(f"\nPasos siguientes:")
        print(f"1. Abre el archivo '{filename}'")
        print(f"2. Verifica que los datos sean correctos")
        print(f"3. En tu sistema, ve a Productos → 📥 Importar desde Excel")
        print(f"4. Selecciona este archivo")
        
        # Mostrar resumen
        print(f"\n📊 Resumen de productos extraídos:")
        print(f"   Total: {len(productos)}")
        print(f"   Con gestión de stock: {sum(1 for p in productos if p['gestion_stock'])}")
        print(f"   Sin gestión de stock: {sum(1 for p in productos if not p['gestion_stock'])}")
        
        # Mostrar lista de productos
        print(f"\n📋 Lista de productos:")
        for p in productos:
            stock_text = "(Con stock)" if p['gestion_stock'] else ""
            print(f"   {p['id']:2d}. {p['nombre']:<30s} ${p['precio_unitario']:6.2f} {stock_text}")
        
    except sqlite3.Error as e:
        print(f"❌ Error al leer la base de datos: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


def extraer_ingredientes_de_bd_antigua(db_path="mitsys_antigua.db"):
    """
    Extrae ingredientes de la base de datos antigua
    """
    
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró el archivo '{db_path}'")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                nombre,
                unidad_almacen,
                costo_unitario,
                cantidad_stock,
                gestion_stock,
                activo
            FROM ingredientes
            WHERE activo = 1
            ORDER BY id
        ''')
        
        ingredientes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        if not ingredientes:
            print("⚠ No se encontraron ingredientes en la base de datos")
            return
        
        print(f"✓ Se encontraron {len(ingredientes)} ingredientes")
        
        # Crear DataFrame
        data = []
        for i in ingredientes:
            data.append({
                'ID': i['id'],
                'Ingrediente': i['nombre'],
                'Unidad Almacén': i['unidad_almacen'],
                'Costo Unitario': i['costo_unitario'],
                'Cantidad Stock': i['cantidad_stock'],
                'Gestión Stock': 'Sí' if i['gestion_stock'] else 'No'
            })
        
        df = pd.DataFrame(data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ingredientes_extraidos_{timestamp}.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Ingredientes', index=False)
            worksheet = writer.sheets['Ingredientes']
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(str(col))) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
        
        print(f"\n✅ Ingredientes exportados a: {filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def extraer_recetas_de_bd_antigua(db_path="mitsys_antigua.db"):
    """
    Extrae recetas de la base de datos antigua
    """
    
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró el archivo '{db_path}'")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                r.id,
                r.id_producto,
                p.nombre as producto_nombre,
                r.id_ingrediente,
                i.nombre as ingrediente_nombre,
                r.cantidad_requerida,
                r.unidad_porcionamiento
            FROM recetas r
            JOIN productos p ON r.id_producto = p.id
            JOIN ingredientes i ON r.id_ingrediente = i.id
            WHERE p.activo = 1 AND i.activo = 1
            ORDER BY r.id
        ''')
        
        recetas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        if not recetas:
            print("⚠ No se encontraron recetas en la base de datos")
            return
        
        print(f"✓ Se encontraron {len(recetas)} recetas")
        
        # Crear DataFrame
        data = []
        for r in recetas:
            data.append({
                'ID Receta': r['id'],
                'ID Producto': r['id_producto'],
                'ID Ingrediente': r['id_ingrediente'],
                'Cantidad Requerida': r['cantidad_requerida'],
                'Unidad Porcionamiento': r['unidad_porcionamiento']
            })
        
        df = pd.DataFrame(data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recetas_extraidas_{timestamp}.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Recetas', index=False)
            worksheet = writer.sheets['Recetas']
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(str(col))) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
        
        print(f"\n✅ Recetas exportadas a: {filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


# Ejecutar la extracción
if __name__ == "__main__":
    print("=" * 60)
    print("  EXTRACTOR DE DATOS - Mitsys POS")
    print("=" * 60)
    print()
    
    # Pedir ruta del archivo
    db_antigua = input("Nombre del archivo de BD antigua (default: mitsys_antigua.db): ").strip()
    if not db_antigua:
        db_antigua = "mitsys_antigua.db"
    
    print("\n¿Qué deseas extraer?")
    print("1. Solo Productos")
    print("2. Solo Ingredientes")
    print("3. Solo Recetas")
    print("4. Todo (Productos, Ingredientes y Recetas)")
    
    opcion = input("\nSelecciona una opción (1-4): ").strip()
    
    print("\n" + "=" * 60)
    
    if opcion == "1":
        extraer_productos_de_bd_antigua(db_antigua)
    elif opcion == "2":
        extraer_ingredientes_de_bd_antigua(db_antigua)
    elif opcion == "3":
        extraer_recetas_de_bd_antigua(db_antigua)
    elif opcion == "4":
        print("\n📦 Extrayendo PRODUCTOS...")
        extraer_productos_de_bd_antigua(db_antigua)
        print("\n" + "-" * 60)
        
        print("\n🥕 Extrayendo INGREDIENTES...")
        extraer_ingredientes_de_bd_antigua(db_antigua)
        print("\n" + "-" * 60)
        
        print("\n📝 Extrayendo RECETAS...")
        extraer_recetas_de_bd_antigua(db_antigua)
    else:
        print("❌ Opción no válida")
    
    print("\n" + "=" * 60)
    print("✅ Proceso completado")
    print("=" * 60)
    input("\nPresiona ENTER para salir...")
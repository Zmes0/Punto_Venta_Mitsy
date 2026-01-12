"""
Módulo para el control de la caja registradora.
"""
try:
    from escpos.printer import Win32Raw
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False
    print("⚠ Advertencia: python-escpos no instalado. Control de caja deshabilitado.")

def open_cash_drawer():
    """
    Envía el comando para abrir la caja registradora.
    """
    if not ESCPOS_AVAILABLE:
        print("❌ Error: No se puede abrir la caja. python-escpos no está instalado.")
        return False
    
    try:
        # Usar el mismo nombre de impresora que en tickets.py
        p = Win32Raw("POS-58") 
        p.cashdraw(2)  # Envía el pulso al pin 2
        p.close()
        print("✓ Comando para abrir caja enviado.")
        return True
    except Exception as e:
        print(f"❌ Error al intentar abrir la caja registradora: {e}")
        # En un entorno de GUI, sería bueno mostrar un error al usuario.
        # from tkinter import messagebox
        # messagebox.showerror("Error de Impresora", 
        #                      f"No se pudo abrir la caja registradora.\n" 
        #                      f"Verifica la conexión de la impresora.\n\nError: {e}")
        return False

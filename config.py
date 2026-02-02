"""
Configuración global del sistema Mitsy's POS
"""

# Colores del tema (inspirado en las imágenes de referencia)
COLORS = {
    'bg_primary': '#E8E8E8',
    'bg_secondary': '#F5F5F5',
    'button_bg': '#FFFFFF',
    'button_hover': '#D0D0D0',
    'border': '#A0A0A0',
    'text_primary': '#2C2C2C',
    'text_secondary': '#666666',
    'accent': '#4A90E2',
    'success': '#4CAF50',
    'warning': '#FF9800',
    'danger': '#F44336',
    'table_header': '#D9D9D9',
    'table_row_even': '#FFFFFF',
    'table_row_odd': '#F9F9F9',
    # Colores para estados de mesas
    'mesa_libre': '#FFFFFF',           # Blanco - Mesa libre
    'mesa_ocupada': '#FFD54F',         # Amarillo - Ocupada sin pedido
    'mesa_pedido_pendiente': '#FF9800',# Naranja - Pedido pendiente
    'mesa_pedido_terminado': '#66BB6A' # Verde - Pedido terminado
}

# Fuentes
FONTS = {
    'title': ('Segoe UI', 20, 'bold'),
    'subtitle': ('Segoe UI', 18, 'bold'),
    'heading': ('Segoe UI', 12, 'bold'),
    'normal': ('Segoe UI', 11),
    'small': ('Segoe UI', 9),
    'button': ('Segoe UI', 11, 'bold')
}

# Configuración de ventanas
WINDOW_CONFIG = {
    'splash_duration': 3000,  # ms
    'min_width': 800,
    'min_height': 600
}

# Información del negocio (para tickets)
BUSINESS_INFO = {
    'name': "Mitsy's",
    'address': "Tecámac-Col. Ejidal-San Lucas Xolox",
    'city': "Calle Liverpool-Esquina Pinos, S/N.",
    'phone': "713-137-4243"
}

# Denominaciones de dinero
DENOMINACIONES = {
    'billetes': [500, 200, 100, 50, 20],
    'monedas': [10, 5, 2, 1]
}

# Configuración de punto de venta
MESAS = [f"Mesa {i}" for i in range(1, 7)] + ["Para llevar"]

# Información actualizada del negocio (para tickets)
BUSINESS_INFO = {
    'name': "Los Abuelos",
    'subtitle': "Antojitos Mexicanos",
    'address': "Tecámac-Col. Ejidal-San Lucas Xolox",
    'city': "Calle Liverpool-Esquina Pinos, S/N.",
    'phone': "713-137-4243",
    'logo_path': "images/logo.png"  # Ruta al logo
}

# Configuración de tickets
TICKET_CONFIG = {
    'width_mm': 58,  # Ancho del ticket en mm
    'font_size_title': 12,
    'font_size_normal': 9,
    'font_size_small': 7,
    'line_spacing': 1.2
}

# Configuración de impresión automática
PRINT_CONFIG = {
    'auto_print': False,  # Por defecto NO imprimir automáticamente
    'last_ticket_path': None  # Ruta del último ticket generado
}
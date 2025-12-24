"""
Funciones auxiliares y utilidades generales
"""
import re
from datetime import datetime, timedelta
from typing import Optional
import unicodedata
from tkinter import ttk

def format_currency(amount: float) -> str:
    """
    Formatea un número como moneda mexicana
    Ejemplo: 1234.56 -> $1,234.56
    """
    if amount is None:
        return "$0.00"
    return f"${amount:,.2f}"

def format_number(number: float, decimals: int = 2) -> str:
    """
    Formatea un número con separadores de miles
    Ejemplo: 1234.56 -> 1,234.56
    """
    if number is None:
        return "0.00"
    return f"{number:,.{decimals}f}"

def parse_currency(text: str) -> float:
    """
    Convierte texto de moneda a float
    Ejemplo: "$1,234.56" -> 1234.56
    """
    if not text:
        return 0.0
    # Remover $, comas y espacios
    clean = re.sub(r'[$,\s]', '', text)
    try:
        return float(clean)
    except ValueError:
        return 0.0

def format_datetime(dt: Optional[datetime] = None) -> str:
    """
    Formatea fecha y hora según el formato requerido
    Formato: dd/mm/yyyy hh:mm:ss
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%d/%m/%Y %H:%M:%S')

def format_date(dt: Optional[datetime] = None) -> str:
    """
    Formatea solo la fecha
    Formato: dd/mm/yyyy
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%d/%m/%Y')

def parse_datetime(date_str: str) -> Optional[datetime]:
    """
    Convierte string a datetime
    """
    try:
        return datetime.strptime(date_str, '%d/%m/%Y %H:%M:%S')
    except:
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except:
            return None

def normalize_text(text: str) -> str:
    """
    Normaliza texto removiendo acentos y convirtiendo a minúsculas
    Para búsquedas que ignoran acentos
    """
    if not text:
        return ""
    # Remover acentos
    nfkd = unicodedata.normalize('NFKD', text)
    text_sin_acentos = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return text_sin_acentos.lower()

def validate_float(value: str) -> bool:
    """
    Valida si un string puede convertirse a float
    """
    try:
        float(value)
        return True
    except ValueError:
        return False

def validate_int(value: str) -> bool:
    """
    Valida si un string puede convertirse a int
    """
    try:
        int(value)
        return True
    except ValueError:
        return False

def get_current_date() -> str:
    """
    Obtiene la fecha actual en formato dd/mm/yyyy
    """
    return datetime.now().strftime('%d/%m/%Y')

def get_current_datetime() -> str:
    """
    Obtiene la fecha y hora actual en formato dd/mm/yyyy hh:mm:ss
    """
    return datetime.now().strftime('%d/%m/%Y %H:%M:%S')

def calculate_week_range(date: datetime = None) -> tuple:
    """
    Calcula el rango de la semana de Viernes a Miércoles.

    La semana se considera de la siguiente manera:
    - Inicia el Viernes.
    - Termina el Miércoles siguiente (5 días después).

    Ejemplos:
    - Si la fecha es Martes 23/12/2025, la semana es del Vie 19/12 al Mie 24/12.
    - Si la fecha es Jueves 25/12/2025, la semana es del Vie 19/12 al Mie 24/12.
    """
    if date is None:
        date = datetime.now()
    
    today = date.date()
    
    # Lunes=0, Martes=1, ..., Viernes=4, ..., Domingo=6
    weekday = today.weekday()
    
    # Días a restar para encontrar el último viernes.
    # (weekday - 4 + 7) % 7 nos da la distancia al viernes anterior.
    days_to_subtract = (weekday - 4 + 7) % 7
    friday_date = today - timedelta(days=days_to_subtract)
    
    # El miércoles de esa semana siempre está 5 días después del viernes.
    wednesday_date = friday_date + timedelta(days=5)
    
    # Devolver como objetos datetime con la hora al inicio y fin del día.
    start_of_week = datetime.combine(friday_date, datetime.min.time())
    end_of_week = datetime.combine(wednesday_date, datetime.max.time())
    
    return start_of_week, end_of_week

def calculate_month_range(date: datetime = None) -> tuple:
    """
    Calcula el rango del mes (día 1 hasta hoy)
    """
    if date is None:
        date = datetime.now()
    
    first_day = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return (first_day, last_day)

def enable_drag_selection(tree: ttk.Treeview):
    """
    Habilita la selección por arrastre en un widget Treeview.
    Permite al usuario mantener presionado el botón izquierdo del ratón y
    arrastrar para seleccionar múltiples filas.
    """
    
    def on_drag_motion(event):
        """Manejador para el evento de arrastre del ratón."""
        item = tree.identify_row(event.y)
        if item:
            # El comportamiento de clic normal (Button-1) ya ha manejado
            # la selección inicial (limpiar o extender).
            # B1-Motion solo necesita AÑADIR a la selección.
            tree.selection_add(item)

    tree.bind("<B1-Motion>", on_drag_motion)

"""
Módulo de generación de tickets para Mitsy's POS
Soporta generación de PDF (respaldo) e impresión directa en térmica ESC/POS
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from datetime import datetime
from config import BUSINESS_INFO, TICKET_CONFIG
from utils import format_currency, get_resource_path
from PIL import Image

# Importaciones para ESC/POS
try:
    from escpos.printer import Win32Raw
    from escpos import printer
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False
    print("⚠ Advertencia: python-escpos no instalado. Impresión térmica deshabilitada.")

class TicketGenerator:
    def __init__(self):
        self.width = TICKET_CONFIG['width_mm'] * mm
        self.margin = 2 * mm
        self.line_height = 3 * mm
        self.current_y = 0
        
        # Configuración de impresora térmica
        self.thermal_printer_name = "POS-58"
        
    def generate_ticket_pdf(self, venta_data, filename=None):
        """
        Genera un ticket en PDF (RESPALDO ÚNICAMENTE)
        
        venta_data = {
            'numero_venta': 1,
            'fecha': '02/11/2025 19:14:30',
            'productos': [
                {'nombre': 'Tacos', 'cantidad': 2, 'precio': 15.00, 'total': 30.00},
                {'nombre': 'Coca-Cola', 'cantidad': 1, 'precio': 30.00, 'total': 30.00}
            ],
            'subtotal': 60.00,
            'propina': 5.00,
            'total': 60.00,
            'recibido': 100.00,
            'cambio': 40.00,
            'metodo_pago': 'Efectivo',
            'mesa': 'Mesa 1'
        }
        """
        
        # Crear nombre de archivo si no se proporciona
        if not filename:
            tickets_dir = os.path.join(os.path.dirname(get_resource_path('')), 'tickets')
            os.makedirs(tickets_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(tickets_dir, f'ticket_{venta_data["numero_venta"]}_{timestamp}.pdf')
        
        # Calcular altura necesaria
        estimated_height = self._estimate_height(venta_data)
        page_height = max(estimated_height, 100 * mm)
        
        # Crear canvas
        c = canvas.Canvas(filename, pagesize=(self.width, page_height))
        
        # Iniciar desde arriba
        self.current_y = page_height - (5 * mm)
        
        # Dibujar contenido
        self._draw_header(c, venta_data)
        self._draw_separator(c, dashed=False)
        self._draw_products(c, venta_data)
        self._draw_separator(c, dashed=True)
        self._draw_totals(c, venta_data)
        self._draw_separator(c, dashed=False)
        self._draw_footer(c)
        
        # Guardar PDF
        c.save()
        
        return filename
    
    def print_thermal_ticket(self, venta_data):
        """
        Imprime ticket directamente en impresora térmica usando ESC/POS
        
        Returns:
            bool: True si se imprimió correctamente, False si hubo error
        """
        if not ESCPOS_AVAILABLE:
            print("❌ Error: python-escpos no está instalado")
            return False
        
        try:
            # Conectar a la impresora térmica con perfil configurado
            p = Win32Raw(self.thermal_printer_name, profile='POS-5890')
            
            # Inicializar impresora
            p.hw('INIT')
            
            # ========== LOGO ==========
            logo_path = get_resource_path(BUSINESS_INFO['logo_path'])
            if os.path.exists(logo_path):
                try:
                    # Cargar y procesar imagen
                    img = Image.open(logo_path)
                    
                    # Convertir a blanco y negro
                    img = img.convert('1')
                    
                    # Redimensionar para 58mm (300 píxeles recomendado para centrado)
                    max_width = 300
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.LANCZOS)
                    
                    # Imprimir imagen centrada usando center en el método image
                    # Nota: Ignorar la advertencia del perfil, la imagen se centrará
                    p.image(img, impl='bitImageColumn', center=True)
                    p.text('\n')
                    
                except Exception as e:
                    print(f"⚠ Error al cargar logo: {e}")
                    # Si falla el logo, imprimir nombre del negocio
                    p.set(align='center', bold=True)
                    p.text(f"{BUSINESS_INFO['name']}\n")
                    p.set(align='center', bold=False)
                    p.text(f"{BUSINESS_INFO['subtitle']}\n")
            else:
                # Sin logo, imprimir nombre
                p.set(align='center', bold=True)
                p.text(f"{BUSINESS_INFO['name']}\n")
                p.set(align='center', bold=False)
                p.text(f"{BUSINESS_INFO['subtitle']}\n")
            
            # ========== INFORMACIÓN DEL NEGOCIO ==========
            p.set(align='center')
            p.text(f"{BUSINESS_INFO['address']}\n")
            p.text(f"{BUSINESS_INFO['city']}\n")
            p.text(f"Tel: {BUSINESS_INFO['phone']}\n")
            p.text('\n')
            
            # ========== INFORMACIÓN DEL TICKET ==========
            p.set(align='center', bold=True)
            p.text(f"Ticket #: {venta_data['numero_venta']}\n")
            p.set(align='center', bold=False)
            p.text(f"Fecha: {venta_data['fecha']}\n")
            
            if venta_data.get('mesa'):
                p.text(f"{venta_data['mesa']}\n")
            
            p.text('\n')
            
            # ========== LÍNEA SEPARADORA ==========
            p.set(align='center')
            p.text('================================\n')
            
            # ========== PRODUCTOS ==========
            p.set(align='left', bold=True)
            # Formato: Cant(6) + Descripcion(18) + Total(8) = 32 caracteres
            p.text(f"{'Cant.':<6}{'Descripción':<18}{'Total':>8}\n")
            p.set(align='left', bold=False)
            
            for producto in venta_data['productos']:
                cant = str(int(producto['cantidad']))
                nombre = producto['nombre']
                
                # Truncar nombre si es muy largo
                if len(nombre) > 18:
                    nombre = nombre[:15] + "..."
                
                total = format_currency(producto['total'])
                
                # Línea del producto
                p.text(f"{cant:<6}{nombre:<18}{total:>8}\n")
                
                # Precio unitario (más pequeño)
                precio_unit = format_currency(producto['precio'])
                p.text(f"      {precio_unit} c/u\n")
            
            p.text('\n')
            
            # ========== LÍNEA SEPARADORA PUNTEADA ==========
            p.set(align='center')
            p.text('- - - - - - - - - - - - - - - -\n')
            p.text('\n')
            
            # ========== TOTALES ==========
            p.set(align='left')
            
            # Subtotal (si hay propina)
            if venta_data.get('propina', 0) > 0:
                subtotal = format_currency(venta_data['subtotal'])
                p.text(f"{'Subtotal:':<24}{subtotal:>8}\n")
                
                propina = format_currency(venta_data['propina'])
                p.text(f"{'Propina:':<24}{propina:>8}\n")
                p.text('\n')
            
            # Total (sin doble tamaño, solo negrita)
            p.set(bold=True)
            total = format_currency(venta_data['total'])
            p.text(f"{'TOTAL:':<24}{total:>8}\n")
            
            p.set(bold=False)
            p.text('\n')
            
            # Recibido (tamaño normal)
            recibido = format_currency(venta_data['recibido'])
            p.text(f"{'Recibido:':<24}{recibido:>8}\n")
            
            # Cambio (tamaño normal)
            cambio = format_currency(venta_data['cambio'])
            p.text(f"{'Cambio:':<24}{cambio:>8}\n")
            
            p.text('\n')
            
            # Método de pago (tamaño normal)
            p.set(align='center')
            p.text(f"Metodo de pago:\n")
            p.text(f"{venta_data['metodo_pago']}\n")
            
            # ========== LÍNEA SEPARADORA ==========
            p.text('================================\n')
            p.text('\n')
            
            # ========== FOOTER ==========
            p.set(align='center', bold=True)
            p.text("¡Gracias por su compra!\n")
            p.set(align='center', bold=False)
            p.text("Vuelva pronto\n")
            
            p.cut()
            
            # Cerrar conexión
            p.close()
            
            print("✓ Ticket impreso correctamente en impresora térmica")
            return True
            
        except Exception as e:
            print(f"❌ Error al imprimir en térmica: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def print_ticket(self, venta_data_or_filename):
        """
        Método unificado para imprimir tickets.
        
        Args:
            venta_data_or_filename: Puede ser:
                - dict con venta_data: imprime directamente en térmica
                - str con filename: carga el PDF y NO hace nada (solo respaldo)
        
        Returns:
            bool: True si se imprimió correctamente
        """
        # Si es un diccionario, es venta_data -> imprimir en térmica
        if isinstance(venta_data_or_filename, dict):
            return self.print_thermal_ticket(venta_data_or_filename)
        
        # Si es string (filename), no hacer nada (el PDF es solo respaldo)
        # Esta función ya no imprime PDFs, solo genera
        print("ℹ El PDF se ha generado como respaldo, no se imprime")
        return True
    
    # ========== MÉTODOS PARA GENERACIÓN DE PDF (sin cambios) ==========
    
    def _estimate_height(self, venta_data):
        """Estima la altura necesaria para el ticket"""
        height = 30 * mm  # Header
        height += len(venta_data['productos']) * 6 * mm  # Productos
        height += 30 * mm  # Totales
        height += 55 * mm  # Footer
        return height
    
    def _draw_header(self, c, venta_data):
        """Dibuja el encabezado del ticket"""
        logo_path = get_resource_path(BUSINESS_INFO['logo_path'])
        
        # Intentar cargar logo
        if os.path.exists(logo_path):
            try:
                logo_width = 30 * mm
                logo_height = 30 * mm
                x_pos = (self.width - logo_width) / 2
                
                c.drawImage(logo_path, 
                           x_pos, self.current_y - logo_height,
                           width=logo_width, height=logo_height,
                           preserveAspectRatio=True, mask='auto')
                
                self.current_y -= (logo_height + 2 * mm)
            except:
                # Si falla, mostrar texto
                self._draw_centered_text(c, BUSINESS_INFO['name'], 12, bold=True)
                self._draw_centered_text(c, BUSINESS_INFO['subtitle'], 9)
        else:
            # Sin logo, mostrar texto
            self._draw_centered_text(c, BUSINESS_INFO['name'], 12, bold=True)
            self._draw_centered_text(c, BUSINESS_INFO['subtitle'], 9)
        
        # Información del negocio
        self._draw_centered_text(c, BUSINESS_INFO['address'], 7)
        self._draw_centered_text(c, BUSINESS_INFO['city'], 7)
        self._draw_centered_text(c, f"Tel: {BUSINESS_INFO['phone']}", 7)
        
        self.current_y -= 2 * mm
        
        # Información del ticket
        self._draw_centered_text(c, f"Ticket #: {venta_data['numero_venta']}", 9, bold=True)
        self._draw_centered_text(c, f"Fecha: {venta_data['fecha']}", 7)
        
        if venta_data.get('mesa'):
            self._draw_centered_text(c, f"{venta_data['mesa']}", 8)
        
        self.current_y -= 2 * mm
    
    def _draw_separator(self, c, dashed=False):
        """Dibuja una línea separadora"""
        if dashed:
            c.setDash(1, 2)
        else:
            c.setDash()
        
        c.line(self.margin, self.current_y, self.width - self.margin, self.current_y)
        self.current_y -= 2 * mm
    
    def _draw_products(self, c, venta_data):
        """Dibuja la lista de productos"""
        self.current_y -= 1 * mm
        
        # Encabezado
        c.setFont("Helvetica-Bold", 8)
        c.drawString(self.margin, self.current_y, "Cant.")
        c.drawString(self.margin + 10 * mm, self.current_y, "Descripción")
        c.drawRightString(self.width - self.margin, self.current_y, "Total")
        self.current_y -= 3 * mm
        
        # Productos
        c.setFont("Helvetica", 8)
        for producto in venta_data['productos']:
            # Cantidad
            c.drawString(self.margin, self.current_y, str(int(producto['cantidad'])))
            
            # Nombre del producto
            nombre = producto['nombre']
            if len(nombre) > 18:
                nombre = nombre[:18] + "..."
            c.drawString(self.margin + 10 * mm, self.current_y, nombre)
            
            # Total
            c.drawRightString(self.width - self.margin, self.current_y, 
                            format_currency(producto['total']))
            
            self.current_y -= 3 * mm
            
            # Precio unitario (línea adicional más pequeña)
            c.setFont("Helvetica", 6)
            c.drawString(self.margin + 10 * mm, self.current_y, 
                        f"  {format_currency(producto['precio'])} c/u")
            c.setFont("Helvetica", 8)
            self.current_y -= 3 * mm
        
        self.current_y -= 3 * mm
    
    def _draw_totals(self, c, venta_data):
        """Dibuja los totales"""
        self.current_y -= 3 * mm
        
        # Subtotal (si hay propina)
        if venta_data.get('propina', 0) > 0:
            c.setFont("Helvetica", 9)
            c.drawString(self.margin, self.current_y, "Subtotal:")
            c.drawRightString(self.width - self.margin, self.current_y, 
                            format_currency(venta_data['subtotal']))
            self.current_y -= 4 * mm
            
            # Propina
            c.drawString(self.margin, self.current_y, "Propina:")
            c.drawRightString(self.width - self.margin, self.current_y, 
                            format_currency(venta_data['propina']))
            self.current_y -= 4 * mm
        
        # Total
        c.setFont("Helvetica-Bold", 11)
        c.drawString(self.margin, self.current_y, "TOTAL:")
        c.drawRightString(self.width - self.margin, self.current_y, 
                        format_currency(venta_data['total']))
        self.current_y -= 5 * mm
        
        # Recibido
        c.setFont("Helvetica", 9)
        c.drawString(self.margin, self.current_y, "Recibido:")
        c.drawRightString(self.width - self.margin, self.current_y, 
                        format_currency(venta_data['recibido']))
        self.current_y -= 4 * mm
        
        # Cambio
        c.drawString(self.margin, self.current_y, "Cambio:")
        c.drawRightString(self.width - self.margin, self.current_y, 
                        format_currency(venta_data['cambio']))
        self.current_y -= 4 * mm
        
        # Método de pago
        c.setFont("Helvetica", 7)
        self._draw_centered_text_at(c, f"Método de pago: {venta_data['metodo_pago']}", 
                                    self.current_y, 7)
        self.current_y -= 3 * mm
    
    def _draw_footer(self, c):
        """Dibuja el pie del ticket"""
        self.current_y -= 2 * mm
        c.setFont("Helvetica-Bold", 9)
        self._draw_centered_text_at(c, "¡Gracias por su compra!", self.current_y, 9)
        self.current_y -= 3 * mm
        
        c.setFont("Helvetica", 8)
        self._draw_centered_text_at(c, "Vuelva pronto", self.current_y, 8)
    
    def _draw_centered_text(self, c, text, size, bold=False):
        """Dibuja texto centrado y actualiza current_y"""
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        
        text_width = c.stringWidth(text, font, size)
        x = (self.width - text_width) / 2
        
        c.drawString(x, self.current_y, text)
        self.current_y -= (size * 0.5 * mm)
    
    def _draw_centered_text_at(self, c, text, y, size, bold=False):
        """Dibuja texto centrado en una posición Y específica"""
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        
        text_width = c.stringWidth(text, font, size)
        x = (self.width - text_width) / 2
        
        c.drawString(x, y, text)


# Instancia global
ticket_generator = TicketGenerator()
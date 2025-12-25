from PIL import Image
import os

# --- CONFIGURACIÓN ---
input_path = "images/logo.png"  # TU LOGO ORIGINAL A COLOR
output_path = "images/logo_thermal.png" # EL LOGO RESULTANTE
target_width = 300 # Ancho ideal para 58mm
# ---------------------

def preparar_logo_termico():
    if not os.path.exists(input_path):
        print(f"Error: No encuentro {input_path}")
        return

    try:
        # 1. Abrir imagen
        img = Image.open(input_path)

        # 2. Convertir a escala de grises si tiene color
        img = img.convert('L')

        # 3. Redimensionar manteniendo proporciones
        width_percent = (target_width / float(img.size[0]))
        height_size = int((float(img.size[1]) * float(width_percent)))
        img = img.resize((target_width, height_size), Image.Resampling.LANCZOS)

        # 4. Convertir a BLANCO Y NEGRO PURO (Thresholding)
        # Esto convierte los grises claros en blanco y los oscuros en negro.
        # Puedes ajustar el '128' (de 0 a 255) si queda muy oscuro o muy claro.
        img = img.point(lambda x: 0 if x < 128 else 255, '1')

        # 5. Guardar
        img.save(output_path)
        print(f"¡Listo! Logo preparado guardado en: {output_path}")
        print("Usa este nuevo archivo en tu sistema POS.")

    except Exception as e:
        print(f"Error al procesar la imagen: {e}")

# Ejecutar
preparar_logo_termico()
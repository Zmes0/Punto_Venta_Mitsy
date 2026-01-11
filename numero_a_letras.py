"""
Conversor de números a letras (pesos mexicanos)
"""

def numero_a_letras(numero):
    """
    Convierte un número a su representación en letras (formato bancario mexicano)
    Ejemplo: 425.50 -> "CUATROCIENTOS VEINTICINCO PESOS 50/100 M.N."
    """
    
    # Separar parte entera y decimal
    partes = str(numero).split('.')
    entero = int(partes[0])
    
    # Manejar decimales correctamente
    if len(partes) > 1:
        # Asegurar que tenga 2 dígitos
        decimal_str = partes[1].ljust(2, '0')[:2]  # ✅ Mantener como string
    else:
        decimal_str = "00"
    
    # Convertir parte entera a letras
    if entero == 0:
        letras = "CERO"
    else:
        letras = convertir_entero(entero)
    
    # Formato final
    return f"{letras} PESOS {decimal_str}/100 M.N."  # ✅ Usar string directamente

def convertir_entero(numero):
    """Convierte un número entero a letras"""
    
    if numero == 0:
        return ""
    
    unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
    
    decenas_especiales = {
        10: "DIEZ", 11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE",
        15: "QUINCE", 16: "DIECISÉIS", 17: "DIECISIETE", 18: "DIECIOCHO", 19: "DIECINUEVE"
    }
    
    decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA",
               "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    
    centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS",
                "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
    
    if numero < 10:
        return unidades[numero]
    
    elif numero < 20:
        return decenas_especiales[numero]
    
    elif numero < 100:
        decena = numero // 10
        unidad = numero % 10
        if unidad == 0:
            return decenas[decena]
        elif decena == 2:
            return "VEINTI" + unidades[unidad]
        else:
            return decenas[decena] + " Y " + unidades[unidad]
    
    elif numero == 100:
        return "CIEN"
    
    elif numero < 1000:
        centena = numero // 100
        resto = numero % 100
        if resto == 0:
            return centenas[centena]
        else:
            return centenas[centena] + " " + convertir_entero(resto)
    
    elif numero < 1000000:
        miles = numero // 1000
        resto = numero % 1000
        
        if miles == 1:
            texto_miles = "MIL"
        else:
            texto_miles = convertir_entero(miles) + " MIL"
        
        if resto == 0:
            return texto_miles
        else:
            return texto_miles + " " + convertir_entero(resto)
    
    elif numero < 1000000000:
        millones = numero // 1000000
        resto = numero % 1000000
        
        if millones == 1:
            texto_millones = "UN MILLÓN"
        else:
            texto_millones = convertir_entero(millones) + " MILLONES"
        
        if resto == 0:
            return texto_millones
        else:
            return texto_millones + " " + convertir_entero(resto)
    
    else:
        return "NÚMERO DEMASIADO GRANDE"
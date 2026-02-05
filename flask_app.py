"""
Servidor Flask para aplicación web móvil - Mitsy's POS
OPTIMIZADO: Imágenes servidas como archivos estáticos
"""
from flask import Flask, request, jsonify, render_template, session, redirect, send_from_directory
from functools import wraps
from database import db
from tickets import ticket_generator
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ==================== SERVIR IMÁGENES COMO ARCHIVOS ESTÁTICOS ====================

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Sirve imágenes de productos desde el directorio images/"""
    try:
        # Obtener directorio base del proyecto
        base_dir = os.path.dirname(os.path.abspath(__file__))
        images_dir = os.path.join(base_dir, 'images')
        return send_from_directory(images_dir, filename)
    except Exception as e:
        # Si no se encuentra la imagen, retornar un placeholder
        return '', 404

# ==================== DECORADOR DE AUTENTICACIÓN ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autenticado'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTENTICACIÓN ====================

@app.route('/api/login', methods=['POST'])
def login():
    """Autentica usuario contra la BD del POS"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
        
        user = db.authenticate_user(username, password)
        
        if user and user['activo']:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nombre_completo'] = user['nombre_completo']
            
            db.add_auditoria(user['id'], 'login_web', f"Inicio de sesión web: {username}")
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'nombre_completo': user['nombre_completo']
                }
            })
        else:
            return jsonify({'error': 'Credenciales incorrectas'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Cierra sesión"""
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        
        if user_id:
            db.add_auditoria(user_id, 'logout_web', f"Cierre de sesión web: {username}")
        
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session', methods=['GET'])
def check_session():
    """Verifica si hay sesión activa"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session['username'],
                'nombre_completo': session.get('nombre_completo')
            }
        })
    else:
        return jsonify({'authenticated': False}), 401

# ==================== MESAS ====================

@app.route('/api/mesas', methods=['GET'])
@login_required
def get_mesas():
    """Retorna todas las mesas con sus estados (para polling)"""
    try:
        import json
        
        mesas_json = db.get_config('mesas_config')
        if mesas_json:
            mesas_nombres = json.loads(mesas_json)
        else:
            from config import MESAS
            mesas_nombres = list(MESAS)
        
        estados_mesas = db.get_mesas_por_estado()
        mesas_con_pedidos = db.get_mesas_con_pedidos_activos()
        mesas_bloqueadas = db.get_mesas_bloqueadas()
        
        mesas_data = []
        for mesa in mesas_nombres:
            estado = estados_mesas.get(mesa, 'libre')
            tiene_pedido = mesa in mesas_con_pedidos
            bloqueada_info = mesas_bloqueadas.get(mesa)
            
            mesas_data.append({
                'nombre': mesa,
                'estado': estado,
                'tiene_pedido': tiene_pedido,
                'bloqueada': bloqueada_info is not None,
                'bloqueada_por': bloqueada_info['username'] if bloqueada_info else None
            })
        
        return jsonify(mesas_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mesas/<mesa>/estado', methods=['PUT'])
@login_required
def cambiar_estado_mesa(mesa):
    """Cambia estado de mesa (libre/ocupada/terminado)"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in ['libre', 'ocupada_sin_pedido', 'pedido_pendiente', 'pedido_terminado']:
            return jsonify({'error': 'Estado inválido'}), 400
        
        estado_actual = db.get_estado_mesa(mesa)
        
        transiciones_validas = {
            'libre': ['ocupada_sin_pedido'],
            'ocupada_sin_pedido': ['libre', 'pedido_pendiente'],
            'pedido_pendiente': ['pedido_terminado', 'ocupada_sin_pedido'],
            'pedido_terminado': ['pedido_pendiente', 'libre']
        }
        
        if nuevo_estado not in transiciones_validas.get(estado_actual, []):
            return jsonify({'error': f'No se puede cambiar de {estado_actual} a {nuevo_estado}'}), 400
        
        db.set_estado_mesa(mesa, nuevo_estado)
        
        db.add_auditoria(session['user_id'], 'cambio_estado_mesa_web', 
                        f"{mesa}: {estado_actual} → {nuevo_estado}")
        
        return jsonify({'success': True, 'nuevo_estado': nuevo_estado})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== PEDIDOS ====================

@app.route('/api/mesas/<mesa>/pedido', methods=['GET'])
@login_required
def get_pedido_mesa(mesa):
    """Obtiene pedido activo + productos ya enviados de la mesa"""
    try:
        pedido_carrito = db.get_pedido_activo(mesa)
        
        carrito = []
        if pedido_carrito:
            productos_carrito = db.get_productos_pedido(pedido_carrito['id'])
            carrito = [{
                'id': p['id'],
                'producto_id': p['producto_id'],
                'nombre': p['nombre_producto'],
                'cantidad': p['cantidad']
            } for p in productos_carrito]
        
        bloqueada_info = db.get_usuario_bloqueando_mesa(mesa)
        
        return jsonify({
            'pedido_id': pedido_carrito['id'] if pedido_carrito else None,
            'carrito': carrito,
            'bloqueada': bloqueada_info is not None,
            'bloqueada_por': bloqueada_info['username'] if bloqueada_info else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pedidos', methods=['POST'])
@login_required
def crear_pedido_nuevo():
    """Crea un nuevo pedido en_carrito"""
    try:
        data = request.get_json()
        mesa = data.get('mesa')
        
        if not mesa:
            return jsonify({'error': 'Mesa requerida'}), 400
        
        pedido_existente = db.get_pedido_activo(mesa)
        if pedido_existente:
            return jsonify({'pedido_id': pedido_existente['id']})
        
        pedido_id = db.crear_pedido(mesa, session['user_id'])
        
        return jsonify({'success': True, 'pedido_id': pedido_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pedidos/<int:pedido_id>/productos', methods=['POST'])
@login_required
def agregar_producto(pedido_id):
    """Agrega producto al pedido"""
    try:
        data = request.get_json()
        producto_id = data.get('producto_id')
        cantidad = data.get('cantidad', 1)
        
        if not producto_id:
            return jsonify({'error': 'producto_id requerido'}), 400
        
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Pedido no válido'}), 400
        
        db.agregar_producto_a_pedido(pedido_id, producto_id, cantidad)
        
        estado_actual = db.get_estado_mesa(pedido['mesa'])
        if estado_actual != 'pedido_pendiente':
            db.set_estado_mesa(pedido['mesa'], 'pedido_pendiente')
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pedidos/<int:pedido_id>/productos/<int:detalle_id>', methods=['DELETE'])
@login_required
def eliminar_producto_pedido(pedido_id, detalle_id):
    """Elimina un producto del pedido"""
    try:
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Pedido no válido'}), 400
        
        db.eliminar_producto_pedido(detalle_id)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pedidos/<int:pedido_id>/productos/<int:detalle_id>/cantidad', methods=['PUT'])
@login_required
def modificar_cantidad_producto(pedido_id, detalle_id):
    """Modifica la cantidad de un producto en el pedido"""
    try:
        data = request.get_json()
        nueva_cantidad = data.get('cantidad')
        
        if nueva_cantidad is None or nueva_cantidad < 1:
            return jsonify({'error': 'Cantidad inválida'}), 400
        
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Pedido no válido'}), 400
        
        db.modificar_cantidad_producto_pedido(detalle_id, nueva_cantidad)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pedidos/<int:pedido_id>/enviar', methods=['POST'])
@login_required
def enviar_a_pos(pedido_id):
    """Envía pedido al POS e imprime ticket de cocina"""
    try:
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Pedido no válido'}), 400
        
        productos_pedido = db.get_productos_pedido(pedido_id)
        
        if not productos_pedido:
            return jsonify({'error': 'El pedido está vacío'}), 400
        
        db.enviar_pedido_a_pos(pedido_id)
        
        productos_ticket = [{
            'nombre': p['nombre_producto'],
            'cantidad': p['cantidad']
        } for p in productos_pedido]
        
        ticket_generado = ticket_generator.print_kitchen_ticket(
            pedido['mesa'],
            productos_ticket,
            session.get('nombre_completo') or session.get('username')
        )
        
        if ticket_generado:
            db.marcar_pedido_impreso(pedido_id)
        
        db.add_auditoria(session['user_id'], 'enviar_pedido_web', 
                        f"Pedido enviado desde web - {pedido['mesa']}")
        
        return jsonify({
            'success': True,
            'ticket_impreso': ticket_generado
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pedidos/<int:pedido_id>/limpiar', methods=['DELETE'])
@login_required
def limpiar_pedido_carrito(pedido_id):
    """Limpia productos del carrito"""
    try:
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Solo se puede limpiar pedidos en carrito'}), 400
        
        db.limpiar_pedido(pedido_id)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== PRODUCTOS ====================

@app.route('/api/clasificaciones', methods=['GET'])
@login_required
def get_clasificaciones():
    """Retorna clasificaciones con conteo de productos"""
    try:
        clasificaciones = db.get_clasificaciones_by_sales()
        
        clasificaciones_data = [{
            'id': c['id'],
            'nombre': c['nombre'],
            'total_productos': db.contar_productos_por_clasificacion(c['id']) if c['id'] else db.contar_productos_sin_clasificacion()
        } for c in clasificaciones]
        
        return jsonify(clasificaciones_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/productos', methods=['GET'])
@login_required
def get_productos():
    """
    OPTIMIZADO: Retorna productos con rutas de imagen en lugar de Base64
    """
    try:
        clasificacion_id = request.args.get('clasificacion_id', 'all')
        
        if clasificacion_id == 'all':
            productos = db.get_productos_by_sales_frequency()
        elif clasificacion_id == 'null':
            productos = db.get_productos_by_sales_frequency(clasificacion_id=None)
        else:
            try:
                clasificacion_id = int(clasificacion_id)
                productos = db.get_productos_by_sales_frequency(clasificacion_id=clasificacion_id)
            except ValueError:
                return jsonify({'error': 'clasificacion_id inválido'}), 400
        
        # OPTIMIZADO: Enviar solo la ruta de la imagen, no Base64
        productos_data = []
        for p in productos:
            imagen_url = None
            if p['imagen']:
                # Convertir ruta absoluta a URL relativa
                # Ejemplo: images/productos/taco.png -> /images/productos/taco.png
                imagen_path = p['imagen'].replace('\\', '/')
                if 'images/' in imagen_path:
                    imagen_url = '/' + imagen_path.split('images/')[-1]
                    imagen_url = '/images/' + imagen_url.split('/')[-1]
            
            productos_data.append({
                'id': p['id'],
                'nombre': p['nombre'],
                'precio': p['precio_unitario'],
                'imagen_url': imagen_url  # URL en lugar de Base64
            })
        
        return jsonify(productos_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== BLOQUEO DE MESAS ====================

@app.route('/api/mesas/<mesa>/bloquear', methods=['POST'])
@login_required
def bloquear_mesa_api(mesa):
    """Intenta bloquear una mesa para el usuario actual"""
    try:
        bloqueado = db.bloquear_mesa(mesa, session['user_id'], session['username'])
        
        if bloqueado:
            return jsonify({'success': True})
        else:
            bloqueada_por = db.get_usuario_bloqueando_mesa(mesa)
            return jsonify({
                'success': False,
                'bloqueada_por': bloqueada_por['username'] if bloqueada_por else 'Desconocido'
            }), 409
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mesas/<mesa>/desbloquear', methods=['POST'])
@login_required
def desbloquear_mesa_api(mesa):
    """Libera el bloqueo de una mesa"""
    try:
        db.desbloquear_mesa(mesa, session['user_id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== LIMPIEZA AUTOMÁTICA ====================

@app.before_request
def limpiar_bloqueos_antes_de_request():
    """Limpia bloqueos antiguos antes de cada request"""
    db.limpiar_bloqueos_antiguos(minutos=15)

# ==================== VISTAS HTML ====================

@app.route('/')
def index():
    """Página de login"""
    if 'user_id' in session:
        return redirect('/mesas')
    return render_template('login.html')

@app.route('/mesas')
def vista_mesas():
    """Vista de grid de mesas"""
    if 'user_id' not in session:
        return redirect('/')
    return render_template('mesas.html', username=session.get('username'))

@app.route('/mesas/<mesa>')
def vista_mesa_detalle(mesa):
    """Vista de detalle de mesa"""
    if 'user_id' not in session:
        return redirect('/')
    return render_template('mesa_detalle.html', mesa=mesa, username=session.get('username'))

# ==================== INICIAR SERVIDOR ====================

if __name__ == '__main__':
    db.limpiar_bloqueos_antiguos(minutos=0)
    
    print("=" * 50)
    print("🌐 Servidor Flask iniciado (OPTIMIZADO)")
    print("=" * 50)
    print("📱 Accede desde cualquier dispositivo en la red:")
    print("   http://TU_IP:5000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

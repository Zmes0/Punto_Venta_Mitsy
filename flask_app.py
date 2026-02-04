"""
Servidor Flask para aplicación web móvil - Mitsy's POS
Permite tomar pedidos desde tablets/celulares
"""
from flask import Flask, request, jsonify, render_template, session, redirect
from functools import wraps
from database import db
from tickets import ticket_generator
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Genera clave secreta aleatoria

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
        
        # Autenticar contra la BD
        user = db.authenticate_user(username, password)
        
        if user and user['activo']:
            # Guardar en sesión
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nombre_completo'] = user['nombre_completo']
            
            # Registrar en auditoría
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
        
        # Obtener configuración de mesas
        mesas_json = db.get_config('mesas_config')
        if mesas_json:
            mesas_nombres = json.loads(mesas_json)
        else:
            from config import MESAS
            mesas_nombres = list(MESAS)
        
        # Obtener estados de todas las mesas
        estados_mesas = db.get_mesas_por_estado()
        
        # Obtener mesas con pedidos pendientes (en_carrito o enviado_pos)
        mesas_con_pedidos = db.get_mesas_con_pedidos_activos()
        
        # Obtener mesas bloqueadas
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
        
        # Obtener estado actual
        estado_actual = db.get_estado_mesa(mesa)
        
        # Validar transiciones permitidas - CORREGIDO
        transiciones_validas = {
            'libre': ['ocupada_sin_pedido'],
            'ocupada_sin_pedido': ['libre', 'pedido_pendiente'],
            'pedido_pendiente': ['pedido_terminado', 'ocupada_sin_pedido'],  # Permitir volver a ocupada_sin_pedido
            'pedido_terminado': ['pedido_pendiente', 'libre']
        }
        
        if nuevo_estado not in transiciones_validas.get(estado_actual, []):
            return jsonify({'error': f'No se puede cambiar de {estado_actual} a {nuevo_estado}'}), 400
        
        # Cambiar estado
        db.set_estado_mesa(mesa, nuevo_estado)
        
        # Registrar en auditoría
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
        # Obtener pedido en carrito (si existe)
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
        
        # Verificar si la mesa está bloqueada
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
        
        # Verificar si ya existe un pedido en carrito
        pedido_existente = db.get_pedido_activo(mesa)
        if pedido_existente:
            return jsonify({'pedido_id': pedido_existente['id']})
        
        # Crear nuevo pedido
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
        
        # Verificar que el pedido existe y está en_carrito
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Pedido no válido'}), 400
        
        # Agregar producto
        db.agregar_producto_a_pedido(pedido_id, producto_id, cantidad)
        
        # Cambiar estado de mesa a pedido_pendiente si estaba en otro estado
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
        # Verificar que el pedido está en_carrito
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Pedido no válido'}), 400
        
        # Eliminar producto
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
        
        # Verificar que el pedido está en_carrito
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Pedido no válido'}), 400
        
        # Modificar cantidad
        db.modificar_cantidad_producto_pedido(detalle_id, nueva_cantidad)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pedidos/<int:pedido_id>/enviar', methods=['POST'])
@login_required
def enviar_a_pos(pedido_id):
    """Envía pedido al POS e imprime ticket de cocina"""
    try:
        # Verificar que el pedido existe y está en_carrito
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Pedido no válido'}), 400
        
        # Obtener productos del pedido
        productos_pedido = db.get_productos_pedido(pedido_id)
        
        if not productos_pedido:
            return jsonify({'error': 'El pedido está vacío'}), 400
        
        # Marcar pedido como enviado
        db.enviar_pedido_a_pos(pedido_id)
        
        # Preparar datos para ticket de cocina
        productos_ticket = [{
            'nombre': p['nombre_producto'],
            'cantidad': p['cantidad']
        } for p in productos_pedido]
        
        # Imprimir ticket de cocina
        ticket_generado = ticket_generator.print_kitchen_ticket(
            pedido['mesa'],
            productos_ticket,
            session.get('nombre_completo') or session.get('username')
        )
        
        if ticket_generado:
            db.marcar_pedido_impreso(pedido_id)
        
        # Registrar en auditoría
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
        # Verificar que el pedido está en_carrito
        pedido = db.get_pedido_by_id(pedido_id)
        if not pedido or pedido['estado'] != 'en_carrito':
            return jsonify({'error': 'Solo se puede limpiar pedidos en carrito'}), 400
        
        # Limpiar pedido
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
    """Retorna productos (filtrados por clasificación si se especifica)"""
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
        
        productos_data = [{
            'id': p['id'],
            'nombre': p['nombre'],
            'precio': p['precio_unitario'],
            'imagen': p['imagen']
        } for p in productos]
        
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
    # Limpiar bloqueos antiguos al iniciar
    db.limpiar_bloqueos_antiguos(minutos=0)
    
    print("=" * 50)
    print("🌐 Servidor Flask iniciado")
    print("=" * 50)
    print("📱 Accede desde cualquier dispositivo en la red:")
    print("   http://TU_IP:5000")
    print("=" * 50)
    
    # Ejecutar en modo debug para desarrollo
    # En producción, usar un servidor WSGI como Gunicorn
    app.run(host='0.0.0.0', port=5000, debug=True)

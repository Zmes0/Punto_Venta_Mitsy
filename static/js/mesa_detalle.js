// mesa_detalle.js - Gestión de pedidos en mesa individual

let pollingInterval = null;
let pedidoActual = null;
let clasificacionActual = 'all';
let clasificaciones = [];
let productos = [];
let carrito = [];
let productosAnteriores = [];

// Inicializar cuando cargue la página
document.addEventListener('DOMContentLoaded', () => {
    verificarSesion();
    bloquearMesa();
    cargarClasificaciones();
    cargarPedidoMesa();
    iniciarPolling();
});

// Verificar sesión activa
async function verificarSesion() {
    try {
        const response = await fetch('/api/session');
        if (!response.ok) {
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Error verificando sesión:', error);
        window.location.href = '/';
    }
}

// Bloquear mesa al entrar
async function bloquearMesa() {
    try {
        const response = await fetch(`/api/mesas/${MESA}/bloquear`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (!data.success) {
            alert(`⚠️ Esta mesa está siendo atendida por ${data.bloqueada_por}`);
        }
    } catch (error) {
        console.error('Error bloqueando mesa:', error);
    }
}

// Desbloquear mesa al salir
async function desbloquearMesa() {
    try {
        await fetch(`/api/mesas/${MESA}/desbloquear`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('Error desbloqueando mesa:', error);
    }
}

// Cargar clasificaciones
async function cargarClasificaciones() {
    try {
        const response = await fetch('/api/clasificaciones');
        clasificaciones = await response.json();
        
        renderizarClasificaciones();
        cargarProductos();
    } catch (error) {
        console.error('Error cargando clasificaciones:', error);
    }
}

// Renderizar clasificaciones
function renderizarClasificaciones() {
    const container = document.getElementById('clasificacionesScroll');
    container.innerHTML = '';
    
    // Botón "Todos"
    const btnTodos = document.createElement('button');
    btnTodos.className = 'clasificacion-btn active';
    btnTodos.textContent = 'Todos';
    btnTodos.onclick = () => seleccionarClasificacion('all', btnTodos);
    container.appendChild(btnTodos);
    
    // Botones de clasificaciones
    clasificaciones.forEach(c => {
        const btn = document.createElement('button');
        btn.className = 'clasificacion-btn';
        btn.textContent = `${c.nombre} (${c.total_productos})`;
        btn.onclick = () => seleccionarClasificacion(c.id === null ? 'null' : c.id, btn);
        container.appendChild(btn);
    });
}

// Seleccionar clasificación
function seleccionarClasificacion(id, btnElement) {
    clasificacionActual = id;
    
    // Actualizar botón activo
    document.querySelectorAll('.clasificacion-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    btnElement.classList.add('active');
    
    cargarProductos();
}

// Cargar productos
async function cargarProductos() {
    try {
        const url = clasificacionActual === 'all' 
            ? '/api/productos' 
            : `/api/productos?clasificacion_id=${clasificacionActual}`;
        
        const response = await fetch(url);
        productos = await response.json();
        
        renderizarProductos();
    } catch (error) {
        console.error('Error cargando productos:', error);
    }
}

// Renderizar productos
function renderizarProductos() {
    const grid = document.getElementById('productosGrid');
    grid.innerHTML = '';
    
    if (productos.length === 0) {
        grid.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No hay productos en esta categoría</p>';
        return;
    }
    
    productos.forEach(producto => {
        const card = document.createElement('div');
        card.className = 'producto-card';
        
        let imagenHTML = '';
        if (producto.imagen) {
            imagenHTML = `<img src="data:image/png;base64,${producto.imagen}" alt="${producto.nombre}">`;
        } else {
            imagenHTML = '<div class="producto-sin-imagen">📦</div>';
        }
        
        card.innerHTML = `
            ${imagenHTML}
            <div class="nombre">${producto.nombre}</div>
        `;
        
        card.onclick = () => agregarProductoAlCarrito(producto);
        
        grid.appendChild(card);
    });
}

// Cargar pedido de la mesa
async function cargarPedidoMesa() {
    try {
        const response = await fetch(`/api/mesas/${MESA}/pedido`);
        
        if (!response.ok) {
            throw new Error('Error al cargar pedido');
        }
        
        const data = await response.json();
        
        pedidoActual = data.pedido_id;
        carrito = data.carrito || [];
        productosAnteriores = data.productos_anteriores || [];
        
        renderizarCarrito();
        renderizarProductosAnteriores();
        
        // Verificar si otro usuario bloqueó la mesa
        if (data.bloqueada && data.bloqueada_por !== USERNAME) {
            mostrarAdvertenciaBloqueada(data.bloqueada_por);
        }
    } catch (error) {
        console.error('Error cargando pedido:', error);
    }
}

// Agregar producto al carrito
async function agregarProductoAlCarrito(producto) {
    try {
        // Si no hay pedido activo, crear uno
        if (!pedidoActual) {
            const response = await fetch('/api/pedidos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mesa: MESA })
            });
            
            const data = await response.json();
            pedidoActual = data.pedido_id;
        }
        
        // Agregar producto al pedido
        const response = await fetch(`/api/pedidos/${pedidoActual}/productos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                producto_id: producto.id,
                cantidad: 1
            })
        });
        
        if (response.ok) {
            // Recargar pedido
            await cargarPedidoMesa();
        } else {
            const data = await response.json();
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Error agregando producto:', error);
        alert('Error al agregar producto');
    }
}

// Eliminar producto del carrito
async function eliminarProductoCarrito(detalleId) {
    if (!confirm('¿Eliminar este producto del carrito?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/pedidos/${pedidoActual}/productos/${detalleId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await cargarPedidoMesa();
        } else {
            const data = await response.json();
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Error eliminando producto:', error);
        alert('Error al eliminar producto');
    }
}

// Renderizar carrito
function renderizarCarrito() {
    const lista = document.getElementById('carritoLista');
    
    if (carrito.length === 0) {
        lista.innerHTML = '<p class="carrito-vacio">El carrito está vacío</p>';
        return;
    }
    
    lista.innerHTML = '';
    
    carrito.forEach(item => {
        const div = document.createElement('div');
        div.className = 'carrito-item';
        
        div.innerHTML = `
            <div class="carrito-item-info">
                <div class="carrito-item-nombre">${item.nombre}</div>
                <div class="carrito-item-cantidad">Cantidad: ${item.cantidad}</div>
            </div>
            <button class="carrito-item-eliminar" onclick="eliminarProductoCarrito(${item.id})">
                Eliminar
            </button>
        `;
        
        lista.appendChild(div);
    });
}

// Renderizar productos anteriores
function renderizarProductosAnteriores() {
    const container = document.getElementById('productosAnteriores');
    const lista = document.getElementById('listaAnteriores');
    
    if (productosAnteriores.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    lista.innerHTML = '';
    
    productosAnteriores.forEach(item => {
        const div = document.createElement('div');
        div.className = 'producto-anterior-item';
        
        div.innerHTML = `
            <span>${item.nombre}</span>
            <span><strong>x${item.cantidad}</strong></span>
        `;
        
        lista.appendChild(div);
    });
}

// Enviar pedido al POS
async function enviarAPOS() {
    if (carrito.length === 0) {
        alert('El carrito está vacío');
        return;
    }
    
    if (!confirm(`¿Enviar pedido de ${MESA} a la cocina?`)) {
        return;
    }
    
    mostrarLoading('Enviando pedido...');
    
    try {
        const response = await fetch(`/api/pedidos/${pedidoActual}/enviar`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        ocultarLoading();
        
        if (response.ok) {
            if (data.ticket_impreso) {
                alert('✓ Pedido enviado e impreso en cocina');
            } else {
                alert('✓ Pedido enviado (advertencia: no se pudo imprimir)');
            }
            
            // Recargar pedido
            pedidoActual = null;
            await cargarPedidoMesa();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        ocultarLoading();
        console.error('Error enviando pedido:', error);
        alert('Error al enviar pedido');
    }
}

// Limpiar venta
async function limpiarVenta() {
    if (carrito.length === 0) {
        alert('El carrito ya está vacío');
        return;
    }
    
    if (!confirm('¿Limpiar todos los productos del carrito?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/pedidos/${pedidoActual}/limpiar`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            pedidoActual = null;
            await cargarPedidoMesa();
        } else {
            const data = await response.json();
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Error limpiando venta:', error);
        alert('Error al limpiar venta');
    }
}

// Cambiar estado de mesa
async function cambiarEstado(nuevoEstado) {
    const mensajes = {
        'libre': '¿Marcar mesa como libre?',
        'ocupada_sin_pedido': '¿Marcar mesa como ocupada?',
        'pedido_terminado': '¿Marcar pedido como terminado?'
    };
    
    if (!confirm(mensajes[nuevoEstado])) {
        return;
    }
    
    try {
        const response = await fetch(`/api/mesas/${MESA}/estado`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado: nuevoEstado })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('✓ Estado actualizado');
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Error cambiando estado:', error);
        alert('Error al cambiar estado');
    }
}

// Iniciar polling
function iniciarPolling() {
    pollingInterval = setInterval(actualizarPedido, 3000);
}

// Actualizar pedido vía polling
async function actualizarPedido() {
    try {
        const response = await fetch(`/api/mesas/${MESA}/pedido`);
        
        if (response.status === 401) {
            detenerPolling();
            window.location.href = '/';
            return;
        }
        
        if (!response.ok) {
            return; // Intentar nuevamente en el próximo ciclo
        }
        
        const data = await response.json();
        
        // Actualizar datos
        const carritoAnterior = JSON.stringify(carrito);
        const anteriorAnterior = JSON.stringify(productosAnteriores);
        
        carrito = data.carrito || [];
        productosAnteriores = data.productos_anteriores || [];
        
        // Re-renderizar solo si cambió
        if (JSON.stringify(carrito) !== carritoAnterior) {
            renderizarCarrito();
        }
        
        if (JSON.stringify(productosAnteriores) !== anteriorAnterior) {
            renderizarProductosAnteriores();
        }
        
        // Verificar bloqueo
        if (data.bloqueada && data.bloqueada_por !== USERNAME) {
            mostrarAdvertenciaBloqueada(data.bloqueada_por);
        }
    } catch (error) {
        console.error('Error en polling:', error);
    }
}

// Detener polling
function detenerPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Volver a mesas
function volverAMesas() {
    detenerPolling();
    desbloquearMesa();
    window.location.href = '/mesas';
}

// Mostrar advertencia de mesa bloqueada
function mostrarAdvertenciaBloqueada(usuario) {
    const modal = document.getElementById('modalBloqueada');
    const mensaje = document.getElementById('mensajeBloqueada');
    
    mensaje.textContent = `Esta mesa está siendo atendida por ${usuario}. Los cambios que veas pueden estar desactualizados.`;
    modal.style.display = 'flex';
}

// Cerrar modal de bloqueada
function cerrarModalBloqueada() {
    document.getElementById('modalBloqueada').style.display = 'none';
}

// Mostrar loading
function mostrarLoading(mensaje = 'Procesando...') {
    const overlay = document.getElementById('loadingOverlay');
    const messageEl = document.getElementById('loadingMessage');
    
    messageEl.textContent = mensaje;
    overlay.style.display = 'flex';
}

// Ocultar loading
function ocultarLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Detener polling y desbloquear al salir
window.addEventListener('beforeunload', () => {
    detenerPolling();
    desbloquearMesa();
});

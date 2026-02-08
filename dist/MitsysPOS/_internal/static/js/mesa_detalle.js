// mesa_detalle.js - OPTIMIZADO: Mantiene orden del carrito + Lazy loading de imágenes

let pollingInterval = null;
let pedidoActual = null;
let clasificacionActual = 'all';
let clasificaciones = [];
let productos = [];
let carrito = [];
let carritoOrdenOriginal = []; // NUEVO: Mantener orden original

// Inicializar cuando cargue la página
document.addEventListener('DOMContentLoaded', () => {
    verificarSesion();
    bloquearMesa();
    cargarClasificaciones();
    cargarProductos();
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
    } catch (error) {
        console.error('Error cargando clasificaciones:', error);
    }
}

// Renderizar clasificaciones
function renderizarClasificaciones() {
    const container = document.getElementById('clasificacionesScroll');
    container.innerHTML = '';
    
    const btnTodos = document.createElement('button');
    btnTodos.className = 'clasificacion-btn active';
    btnTodos.textContent = 'Todos';
    btnTodos.onclick = () => seleccionarClasificacion('all', btnTodos);
    container.appendChild(btnTodos);
    
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
    
    document.querySelectorAll('.clasificacion-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    btnElement.classList.add('active');
    
    cargarProductos();
}

// Cargar productos - OPTIMIZADO
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

// Renderizar productos - OPTIMIZADO con lazy loading
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
        if (producto.imagen_url) {
            // OPTIMIZADO: Usar lazy loading y URL en lugar de Base64
            imagenHTML = `<img src="${producto.imagen_url}" alt="${producto.nombre}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                         <div class="producto-sin-imagen" style="display:none;">📦</div>`;
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
        
        // NUEVO: Mantener orden original del carrito
        const nuevoCarrito = data.carrito || [];
        
        // Si es la primera carga, guardar orden
        if (carritoOrdenOriginal.length === 0 && nuevoCarrito.length > 0) {
            carritoOrdenOriginal = nuevoCarrito.map(item => ({
                id: item.id,
                producto_id: item.producto_id
            }));
        }
        
        // Reordenar carrito según orden original
        carrito = reordenarCarritoSegunOrden(nuevoCarrito);
        
        renderizarCarrito();
        
        if (data.bloqueada && data.bloqueada_por !== USERNAME) {
            mostrarAdvertenciaBloqueada(data.bloqueada_por);
        }
    } catch (error) {
        console.error('Error cargando pedido:', error);
    }
}

// NUEVO: Función para mantener el orden del carrito
function reordenarCarritoSegunOrden(nuevoCarrito) {
    if (carritoOrdenOriginal.length === 0) {
        return nuevoCarrito;
    }
    
    const ordenado = [];
    const nuevosProductos = [];
    
    // Primero, agregar productos en el orden original
    carritoOrdenOriginal.forEach(itemOrden => {
        const producto = nuevoCarrito.find(p => p.id === itemOrden.id);
        if (producto) {
            ordenado.push(producto);
        }
    });
    
    // Agregar productos nuevos al final
    nuevoCarrito.forEach(producto => {
        if (!carritoOrdenOriginal.find(o => o.id === producto.id)) {
            nuevosProductos.push(producto);
            carritoOrdenOriginal.push({
                id: producto.id,
                producto_id: producto.producto_id
            });
        }
    });
    
    // Actualizar orden original para reflejar eliminaciones
    carritoOrdenOriginal = carritoOrdenOriginal.filter(itemOrden => 
        nuevoCarrito.find(p => p.id === itemOrden.id)
    );
    
    return [...ordenado, ...nuevosProductos];
}

// Agregar producto al carrito
async function agregarProductoAlCarrito(producto) {
    try {
        if (!pedidoActual) {
            const response = await fetch('/api/pedidos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mesa: MESA })
            });
            
            const data = await response.json();
            pedidoActual = data.pedido_id;
        }
        
        const response = await fetch(`/api/pedidos/${pedidoActual}/productos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                producto_id: producto.id,
                cantidad: 1
            })
        });
        
        if (response.ok) {
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

// Modificar cantidad de producto
async function modificarCantidad(detalleId, nuevaCantidad) {
    if (nuevaCantidad < 1) {
        return;
    }
    
    try {
        const response = await fetch(`/api/pedidos/${pedidoActual}/productos/${detalleId}/cantidad`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cantidad: nuevaCantidad })
        });
        
        if (response.ok) {
            await cargarPedidoMesa();
        } else {
            const data = await response.json();
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Error modificando cantidad:', error);
        alert('Error al modificar cantidad');
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

// Renderizar carrito - OPTIMIZADO: Actualización incremental
function renderizarCarrito() {
    const lista = document.getElementById('carritoLista');
    
    if (carrito.length === 0) {
        lista.innerHTML = '<p class="carrito-vacio">El carrito está vacío</p>';
        return;
    }
    
    // Mapa de elementos existentes
    const existingItemsMap = new Map();
    Array.from(lista.children).forEach(child => {
        if (child.classList.contains('carrito-item')) {
            const itemId = parseInt(child.dataset.id);
            existingItemsMap.set(itemId, child);
        }
    });

    const fragment = document.createDocumentFragment();
    
    carrito.forEach(item => {
        let itemDiv;
        
        if (existingItemsMap.has(item.id)) {
            // Item existe, solo actualizar cantidad
            itemDiv = existingItemsMap.get(item.id);
            itemDiv.querySelector('.cantidad-display').textContent = item.cantidad;
            itemDiv.querySelector('.btn-cantidad:first-child').setAttribute('onclick', `modificarCantidad(${item.id}, ${item.cantidad - 1})`);
            itemDiv.querySelector('.btn-cantidad:last-child').setAttribute('onclick', `modificarCantidad(${item.id}, ${item.cantidad + 1})`);
            existingItemsMap.delete(item.id);
        } else {
            // Nuevo item
            itemDiv = document.createElement('div');
            itemDiv.className = 'carrito-item';
            itemDiv.dataset.id = item.id;
            
            itemDiv.innerHTML = `
                <div class="carrito-item-info">
                    <div class="carrito-item-nombre">${item.nombre}</div>
                </div>
                <div class="carrito-item-controles">
                    <div class="cantidad-controles">
                        <button class="btn-cantidad" onclick="modificarCantidad(${item.id}, ${item.cantidad - 1})">−</button>
                        <span class="cantidad-display">${item.cantidad}</span>
                        <button class="btn-cantidad" onclick="modificarCantidad(${item.id}, ${item.cantidad + 1})">+</button>
                    </div>
                    <button class="carrito-item-eliminar" onclick="eliminarProductoCarrito(${item.id})">
                        Eliminar
                    </button>
                </div>
            `;
        }
        fragment.appendChild(itemDiv);
    });

    // Eliminar items que ya no están
    existingItemsMap.forEach(itemDiv => {
        itemDiv.remove();
    });

    lista.innerHTML = '';
    lista.appendChild(fragment);
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
            
            pedidoActual = null;
            carritoOrdenOriginal = []; // Resetear orden
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
            carritoOrdenOriginal = []; // Resetear orden
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
            return;
        }
        
        const data = await response.json();
        
        const carritoAnterior = JSON.stringify(carrito);
        
        const nuevoCarrito = data.carrito || [];
        carrito = reordenarCarritoSegunOrden(nuevoCarrito);
        
        if (JSON.stringify(carrito) !== carritoAnterior) {
            renderizarCarrito();
        }
        
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

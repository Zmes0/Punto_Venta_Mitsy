// mesas.js - Gestión de la vista de grid de mesas

let pollingInterval = null;
let mesas = [];

// Iniciar cuando cargue la página
document.addEventListener('DOMContentLoaded', () => {
    verificarSesion();
    cargarMesas();
    iniciarPolling();
});

// Verificar que hay sesión activa
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

// Cargar mesas por primera vez
async function cargarMesas() {
    try {
        document.getElementById('loading').style.display = 'flex';
        
        const response = await fetch('/api/mesas');
        
        if (response.status === 401) {
            window.location.href = '/';
            return;
        }
        
        if (!response.ok) {
            throw new Error('Error al cargar mesas');
        }
        
        mesas = await response.json();
        renderizarMesas();
        
        document.getElementById('loading').style.display = 'none';
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('loading').style.display = 'none';
        alert('Error al cargar las mesas. Recargando página...');
        setTimeout(() => location.reload(), 2000);
    }
}

// Renderizar mesas en el grid
function renderizarMesas() {
    const grid = document.getElementById('mesasGrid');
    grid.innerHTML = '';
    
    mesas.forEach(mesa => {
        const card = document.createElement('div');
        card.className = `mesa-card mesa-${mesa.estado}`;
        card.id = `mesa-${mesa.nombre}`;
        
        if (mesa.bloqueada) {
            card.classList.add('mesa-bloqueada');
        }
        
        card.innerHTML = `
            <div>${mesa.nombre}</div>
        `;
        
        card.addEventListener('click', () => abrirMesa(mesa.nombre));
        
        grid.appendChild(card);
    });
}

// Abrir detalle de mesa
function abrirMesa(nombreMesa) {
    window.location.href = `/mesas/${nombreMesa}`;
}

// Iniciar polling (cada 3 segundos)
function iniciarPolling() {
    pollingInterval = setInterval(actualizarMesas, 3000);
}

// Actualizar mesas vía polling
async function actualizarMesas() {
    try {
        const response = await fetch('/api/mesas');
        
        if (response.status === 401) {
            detenerPolling();
            window.location.href = '/';
            return;
        }
        
        if (!response.ok) {
            return; // Intentar nuevamente en el próximo ciclo
        }
        
        const nuevasMesas = await response.json();
        
        // Actualizar solo si hay cambios
        if (JSON.stringify(nuevasMesas) !== JSON.stringify(mesas)) {
            mesas = nuevasMesas;
            actualizarMesasVisualmente();
        }
    } catch (error) {
        console.error('Error en polling:', error);
        // No hacer nada, reintentará en 3 segundos
    }
}

// Actualizar solo las clases CSS sin re-renderizar todo
function actualizarMesasVisualmente() {
    mesas.forEach(mesa => {
        const elemento = document.getElementById(`mesa-${mesa.nombre}`);
        if (elemento) {
            // Limpiar clases de estado
            elemento.className = `mesa-card mesa-${mesa.estado}`;
            
            if (mesa.bloqueada) {
                elemento.classList.add('mesa-bloqueada');
            }
        }
    });
}

// Detener polling
function detenerPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Cerrar sesión
async function logout() {
    if (!confirm('¿Seguro que deseas cerrar sesión?')) {
        return;
    }
    
    detenerPolling();
    
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/';
    } catch (error) {
        console.error('Error:', error);
        window.location.href = '/';
    }
}

// Detener polling cuando se cierra la pestaña
window.addEventListener('beforeunload', () => {
    detenerPolling();
});

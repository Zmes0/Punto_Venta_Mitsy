// login.js - Manejo de autenticación

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('errorMessage');
    
    // Ocultar mensajes de error previos
    errorDiv.style.display = 'none';
    
    // Validar campos
    if (!username || !password) {
        mostrarError('Por favor completa todos los campos');
        return;
    }
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Login exitoso, redirigir a mesas
            window.location.href = '/mesas';
        } else {
            mostrarError(data.error || 'Error al iniciar sesión');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error de conexión con el servidor');
    }
});

function mostrarError(mensaje) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = mensaje;
    errorDiv.style.display = 'block';
}

// Auto-focus en el campo de usuario
document.getElementById('username').focus();

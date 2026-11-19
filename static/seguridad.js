(function () {
    const sesion = JSON.parse(sessionStorage.getItem('usuario_sesion') || 'null');
    if (!sesion) {
        window.location.replace('/login');
        return;
    }

    // 1. Interceptor global de fetch: inyecta X-Usuario en cada llamada a /api/...
    const _fetchOriginal = window.fetch;
    window.fetch = async function (url, options = {}) {
        if (typeof url === 'string' && url.startsWith('/api/')) {
            options.headers = {
                ...(options.headers || {}),
                'X-Usuario': sesion.usuario
            };
        }

        const response = await _fetchOriginal(url, options);

        // Si el servidor bloquea la acción (403 Forbidden), muestra alerta clara
        if (response.status === 403) {
            const clon = response.clone();
            try {
                const err = await clon.json();
                alert(err.detail || 'No tenés permisos para realizar esta acción (solo consulta).');
            } catch (_) {
                alert('No tenés permisos para realizar esta acción (solo consulta).');
            }
        }

        return response;
    };

    // 2. Bloqueo visual de botones según permisos GET / POST / PUT / DELETE
    function aplicarBloqueoVisual(datosUser) {
        const esAdmin = (datosUser.rol || '').toLowerCase() === 'admin';
        if (esAdmin) return;

        // Sin POST (puede_crear = false)
        if (!datosUser.puede_crear) {
            document.querySelectorAll('button[type="submit"], .btn-guardar, .btn-nuevo').forEach(btn => {
                btn.disabled = true;
                btn.title = 'Sin permiso para crear (POST)';
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
            });
        }

        // Sin PUT (puede_editar = false)
        if (!datosUser.puede_editar) {
            document.querySelectorAll('.btn-editar').forEach(btn => {
                btn.disabled = true;
                btn.title = 'Sin permiso para editar (PUT)';
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
            });
        }

        // Sin DELETE (puede_eliminar = false)
        if (!datosUser.puede_eliminar) {
            document.querySelectorAll('.btn-eliminar, .btn-borrar').forEach(btn => {
                btn.disabled = true;
                btn.title = 'Sin permiso para eliminar (DELETE)';
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
            });
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        aplicarBloqueoVisual(sesion);

        // Observa tablas o modales que se carguen dinámicamente por JS
        const observer = new MutationObserver(() => aplicarBloqueoVisual(sesion));
        observer.observe(document.body, { childList: true, subtree: true });
    });
})();
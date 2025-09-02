// Funciones globales para la aplicación
class InventarioApp {
    constructor() {
        this.apiBase = '/api';
        this.init();
    }

    init() {
        // Inicializar tooltips de Bootstrap
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Verificar autenticación en cada página
        this.checkAuth();
    }

    checkAuth() {
        // Verificar si el usuario está autenticado en páginas que lo requieran
        const protectedPages = ['dashboard', 'inventario', 'productos', 'movimientos', 'reportes', 'admin'];
        
        if (protectedPages.some(page => window.location.pathname.includes(page))) {
            fetch(`${this.apiBase}/check-auth`)
                .then(response => {
                    if (response.status === 401) {
                        window.location.href = '/login';
                    }
                });
        }
    }

    // Métodos para API calls
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.apiBase}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            return await this.handleApiError(response);
        } catch (error) {
            console.error('Error en la llamada API:', error);
            this.showAlert('Error de conexión', 'danger');
        }
    }

    handleApiError(response) {
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            return response.text().then(text => {
                throw new Error('El servidor devolvió HTML en lugar de JSON. Posible error 500.');
            });
        }
        return response.json();
    }

    showAlert(message, type = 'info', duration = 5000) {
        // Crear y mostrar alerta
        const alertId = 'alert-' + Date.now();
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // Añadir alerta al contenedor o crear uno
        let alertContainer = document.getElementById('alertContainer');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'alertContainer';
            alertContainer.className = 'position-fixed top-0 end-0 p-3';
            alertContainer.style.zIndex = '1050';
            document.body.appendChild(alertContainer);
        }

        alertContainer.insertAdjacentHTML('afterbegin', alertHtml);

        // Auto-eliminar después de un tiempo
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    bootstrap.Alert.getOrCreateInstance(alert).close();
                }
            }, duration);
        }
    }

    // Métodos para gestionar formularios
    serializeForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return {};
        
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    }

    // Métodos para tablas
    initDataTable(tableId, options = {}) {
        // Inicializar tabla con funcionalidad extra
        const table = document.getElementById(tableId);
        if (!table) return;

        // Aquí se podría integrar DataTables.js o similar para funcionalidad avanzada
        console.log(`Tabla ${tableId} inicializada`);
    }
}

// Inicializar la aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    window.inventarioApp = new InventarioApp();
});

// Función para agregar botella completa
async function agregarBotellaCompleta(productoId) {
    if (!confirm('¿Agregar una botella completa al inventario?')) return;
    
    try {
        const response = await fetch('/api/agregar-botella', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ producto_id: productoId })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Botella completa agregada');
            location.reload();
        } else {
            alert('Error: ' + result.message);
        }
    } catch (error) {
        alert('Error al agregar botella');
    }
}

// Función para quitar botella completa
async function quitarBotellaCompleta(productoId) {
    if (!confirm('¿Quitar una botella completa del inventario?')) return;
    
    try {
        const response = await fetch('/api/quitar-botella', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ producto_id: productoId })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Botella completa retirada');
            location.reload();
        } else {
            alert('Error: ' + result.message);
        }
    } catch (error) {
        alert('Error al quitar botella');
    }
}

// Función global para manejar errores de API
function handleApiError(response) {
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
        return response.text().then(text => {
            throw new Error('El servidor devolvió HTML en lugar de JSON. Posible error 500.');
        });
    }
    return response.json();
}

// Función global para mostrar alertas
function showAlert(message, type = 'info', duration = 5000) {
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    let alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alertContainer';
        alertContainer.className = 'position-fixed top-0 end-0 p-3';
        alertContainer.style.zIndex = '1050';
        document.body.appendChild(alertContainer);
    }

    alertContainer.insertAdjacentHTML('afterbegin', alertHtml);

    if (duration > 0) {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                bootstrap.Alert.getOrCreateInstance(alert).close();
            }
        }, duration);
    }
}

// Guardar producto (versión mejorada con mejor manejo de errores)
async function guardarProducto() {
    // Validar campos obligatorios
    const nombre = document.getElementById('nombre').value;
    const marca = document.getElementById('marca').value;
    const tipo = document.getElementById('tipo').value;
    
    if (!nombre || !marca || !tipo) {
        showAlert('Por favor complete todos los campos obligatorios', 'danger');
        return;
    }
    
    const formData = {
        producto_id: document.getElementById('productoId').value,
        nombre: nombre,
        marca: marca,
        tipo: tipo,
        presentacion: document.getElementById('presentacion').value,
        densidad: parseFloat(document.getElementById('densidad').value),
        capacidad_ml: parseFloat(document.getElementById('capacidad_ml').value),
        peso_envase: parseFloat(document.getElementById('peso_envase').value),
        minimo_inventario: parseFloat(document.getElementById('minimo_inventario').value) / 100,
        activo: document.getElementById('activo').checked ? 1 : 0
    };
    
    console.log('Enviando datos:', formData);
    
    // Mostrar loading
    const submitBtn = document.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Guardando...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/guardar-producto', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        // Verificar si la respuesta es JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const errorText = await response.text();
            console.error('El servidor devolvió HTML:', errorText);
            throw new Error('Error interno del servidor. Por favor revise la consola para más detalles.');
        }
        
        const data = await response.json();
        console.log('Respuesta recibida:', data);
        
        if (data.success) {
            alert(data.message);
            window.location.href = "/productos";
        } else {
            showAlert(data.message || 'Error al guardar el producto', 'danger');
        }
    } catch (error) {
        console.error('Error en guardarProducto:', error);
        showAlert('Error: ' + error.message, 'danger');
    } finally {
        // Restaurar botón
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Función mejorada para exportar a PDF
async function exportarPDF() {
    const productoId = document.getElementById('productoReporte').value;
    const periodo = document.getElementById('periodoReporte').value;
    
    if (!productoId) {
        alert('Seleccione un producto para exportar');
        return;
    }
    
    try {
        // Obtener datos del reporte
        const response = await fetch('/api/generar-reporte', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                producto_id: productoId,
                periodo: periodo
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Crear PDF con jsPDF
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            // Logo y encabezado
            doc.setFontSize(16);
            doc.setTextColor(40, 40, 40);
            doc.text('INVENTARIO LICORES - REPORTE', 105, 20, { align: 'center' });
            
            doc.setFontSize(10);
            doc.setTextColor(100, 100, 100);
            doc.text(`Generado: ${new Date().toLocaleString()}`, 105, 28, { align: 'center' });
            
            // Línea separadora
            doc.setDrawColor(200, 200, 200);
            doc.line(20, 32, 190, 32);
            
            // Información del producto
            doc.setFontSize(12);
            doc.setTextColor(0, 0, 0);
            doc.text(`Producto: ${data.producto_nombre}`, 20, 42);
            doc.text(`Período: Últimos ${data.periodo} días`, 20, 49);
            
            // Gráfico de tendencia (si hay suficientes datos)
            if (data.fechas.length > 1) {
                // Aquí podrías agregar un gráfico simple
                doc.text('Tendencia de Consumo:', 20, 65);
                
                // Simular un gráfico simple con líneas
                doc.setDrawColor(0, 123, 255);
                doc.line(20, 70, 190, 70);
                
                // Puntos de datos
                data.consumos_netos.forEach((neto, index) => {
                    if (index < data.consumos_netos.length - 1) {
                        const x1 = 20 + (index * 170 / (data.fechas.length - 1));
                        const x2 = 20 + ((index + 1) * 170 / (data.fechas.length - 1));
                        const y1 = 70 - (neto / maxNeto * 30);
                        const y2 = 70 - (data.consumos_netos[index + 1] / maxNeto * 30);
                        doc.line(x1, y1, x2, y2);
                    }
                });
            }
            
            // Tabla de datos
            let y = 90;
            doc.setFontSize(10);
            
            // Encabezados de tabla
            doc.setFillColor(240, 240, 240);
            doc.rect(20, y, 170, 8, 'F');
            doc.setTextColor(0, 0, 0);
            doc.setFont(undefined, 'bold');
            
            doc.text('Fecha', 25, y + 5);
            doc.text('Entradas', 70, y + 5);
            doc.text('Salidas', 100, y + 5);
            doc.text('Neto', 130, y + 5);
            doc.text('Acumulado', 160, y + 5);
            
            y += 10;
            doc.setFont(undefined, 'normal');
            
            // Datos de la tabla
            let acumulado = 0;
            data.fechas.forEach((fecha, index) => {
                const entrada = data.entradas[index];
                const salida = data.salidas[index];
                const neto = entrada - salida; // Entradas suman, salidas restan
                acumulado += neto;
                
                doc.setTextColor(0, 0, 0);
                doc.text(fecha, 25, y);
                
                doc.setTextColor(40, 167, 69); // Verde para entradas
                doc.text(entrada.toFixed(1), 70, y);
                
                doc.setTextColor(220, 53, 69); // Rojo para salidas
                doc.text(salida.toFixed(1), 100, y);
                
                doc.setTextColor(neto >= 0 ? 40 : 220, neto >= 0 ? 167 : 53, neto >= 0 ? 69 : 69);
                doc.text(neto.toFixed(1), 130, y);
                
                doc.setTextColor(0, 0, 0);
                doc.text(acumulado.toFixed(1), 160, y);
                
                y += 6;
                
                // Nueva página si se necesita
                if (y > 270) {
                    doc.addPage();
                    y = 20;
                    
                    // Encabezados de tabla en nueva página
                    doc.setFillColor(240, 240, 240);
                    doc.rect(20, y, 170, 8, 'F');
                    doc.setTextColor(0, 0, 0);
                    doc.setFont(undefined, 'bold');
                    doc.text('Fecha', 25, y + 5);
                    doc.text('Entradas', 70, y + 5);
                    doc.text('Salidas', 100, y + 5);
                    doc.text('Neto', 130, y + 5);
                    doc.text('Acumulado', 160, y + 5);
                    y += 10;
                    doc.setFont(undefined, 'normal');
                }
            });
            
            // Totales
            y += 10;
            doc.setDrawColor(200, 200, 200);
            doc.line(20, y, 190, y);
            y += 7;
            
            const totalEntradas = data.entradas.reduce((a, b) => a + b, 0);
            const totalSalidas = data.salidas.reduce((a, b) => a + b, 0);
            const totalNeto = totalEntradas - totalSalidas;
            
            doc.setFontSize(11);
            doc.setFont(undefined, 'bold');
            doc.setTextColor(0, 0, 0);
            doc.text('TOTALES:', 25, y);
            
            doc.setTextColor(40, 167, 69);
            doc.text(totalEntradas.toFixed(1), 70, y);
            
            doc.setTextColor(220, 53, 69);
            doc.text(totalSalidas.toFixed(1), 100, y);
            
            doc.setTextColor(totalNeto >= 0 ? 40 : 220, totalNeto >= 0 ? 167 : 53, totalNeto >= 0 ? 69 : 69);
            doc.text(totalNeto.toFixed(1), 130, y);
            
            doc.setTextColor(0, 0, 0);
            doc.text(acumulado.toFixed(1), 160, y);
            
            // Guardar PDF
            const nombreArchivo = `reporte_${data.producto_nombre.replace(/[^a-z0-9]/gi, '_')}_${new Date().toISOString().split('T')[0]}.pdf`;
            doc.save(nombreArchivo);
            
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        alert('Error al generar PDF: ' + error);
    }
}
const API_URL = "https://tu-backend-flask-xxxxx-uc.a.run.app/api";  // Reemplaza con tu URL de Cloud Run

export const fetchProducts = async () => {
  const response = await fetch(`${API_URL}/products`);
  return await response.json();
};

export const login = async (username, password) => {
  const response = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return await response.json();
};

// ----------------------- Estado global -----------------------
let appState = {
  user: null,
  productos: [],
  movimientos: [],
  locales: [],
  usuarios: [],
  licoresComerciales: []
};

// ----------------------- Utilidades -----------------------
function log(...args) { console.log('[app.js]', ...args); }

function showError(msg) {
  console.error(msg);
  alert(msg);
}

function showSuccess(msg) {
  console.log(msg);
  alert(msg);
}

// Convierte peso total (g) a volumen (ml) dado densidad (g/ml) y peso_envase (g)
// volumen_ml = (peso_total - peso_envase) / densidad
function pesoToMl(pesoTotalGr, pesoEnvaseGr, densidad) {
  const volumen = (Number(pesoTotalGr) - Number(pesoEnvaseGr)) / Number(densidad || 1);
  return Math.max(0, Math.round(volumen * 100) / 100); // 2 decimales
}

// Convierte volumen (ml) a peso bruto (g): peso = volumen * densidad + peso_envase
function mlToPeso(volumenMl, pesoEnvaseGr, densidad) {
  const peso = Number(volumenMl) * Number(densidad || 1) + Number(pesoEnvaseGr || 0);
  return Math.round(peso * 100) / 100;
}

// Calcular botellas completas y ml parciales
function volumenToBotellasCapacidad(volumenMl, capacidadMl) {
  const completas = Math.floor(volumenMl / capacidadMl);
  const restante = Math.round((volumenMl - completas * capacidadMl) * 100) / 100;
  return { completas, restante };
}

// Formateo de fechas (YYYY-MM-DD HH:MM)
function formatDate(ts) {
  const d = ts ? new Date(ts) : new Date();
  return d.toLocaleString();
}

// ----------------------- Fetch con manejo -----------------------
async function fetchWithAuth(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    mode: 'cors'
  };
  const cfg = { ...defaults, ...options, headers: { ...defaults.headers, ...(options.headers || {}) } };

  try {
    const res = await fetch(url, cfg);

    if (res.status === 401) {
      throw new Error('No autorizado. Por favor inicie sesión.');
    }
    
    const text = await res.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch (e) { data = { text }; }

    if (!res.ok) {
      const errMsg = data?.error || data?.message || `HTTP error ${res.status}`;
      throw new Error(errMsg);
    }
    return data;
  } catch (err) {
    console.error('Fetch error', url, err);
    throw err;
  }
}

// ----------------------- API -----------------------
const api = {
  login: (u, p) => fetchWithAuth(`${API_BASE}/login`, { method: 'POST', body: JSON.stringify({ username: u, password: p }) }),
  logout: () => fetchWithAuth(`${API_BASE}/logout`, { method: 'POST' }),
  getMe: () => fetchWithAuth(`${API_BASE}/me`),

  // Productos
  getProducts: () => fetchWithAuth(`${API_BASE}/products`),
  getProduct: (id) => fetchWithAuth(`${API_BASE}/products/${id}`),
  createProduct: (prod) => fetchWithAuth(`${API_BASE}/products`, { method: 'POST', body: JSON.stringify(prod) }),
  updateProduct: (id, prod) => fetchWithAuth(`${API_BASE}/products/${id}`, { method: 'PUT', body: JSON.stringify(prod) }),
  deleteProduct: (id) => fetchWithAuth(`${API_BASE}/products/${id}`, { method: 'DELETE' }),

  // Movimientos
  getMovements: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchWithAuth(`${API_BASE}/movements${qs ? '?' + qs : ''}`);
  },
  createMovement: (mov) => fetchWithAuth(`${API_BASE}/movements`, { method: 'POST', body: JSON.stringify(mov) }),

  // Locales
  getLocales: () => fetchWithAuth(`${API_BASE}/locales`),
  createLocal: (l) => fetchWithAuth(`${API_BASE}/locales`, { method: 'POST', body: JSON.stringify(l) }),
  updateLocal: (id, l) => fetchWithAuth(`${API_BASE}/locales/${id}`, { method: 'PUT', body: JSON.stringify(l) }),
  deleteLocal: (id) => fetchWithAuth(`${API_BASE}/locales/${id}`, { method: 'DELETE' }),

  // Usuarios
  getUsuarios: () => fetchWithAuth(`${API_BASE}/usuarios`),
  createUsuario: (u) => fetchWithAuth(`${API_BASE}/usuarios`, { method: 'POST', body: JSON.stringify(u) }),
  updateUsuario: (id, u) => fetchWithAuth(`${API_BASE}/usuarios/${id}`, { method: 'PUT', body: JSON.stringify(u) }),
  deleteUsuario: (id) => fetchWithAuth(`${API_BASE}/usuarios/${id}`, { method: 'DELETE' }),

  // Licores comerciales
  getLicoresComerciales: () => fetchWithAuth(`${API_BASE}/licores-comerciales`),
  createLicorComercial: (licor) => fetchWithAuth(`${API_BASE}/licores-comerciales`, { 
    method: 'POST', 
    body: JSON.stringify(licor) 
  }),
  updateLicorComercial: (id, licor) => fetchWithAuth(`${API_BASE}/licores-comerciales/${id}`, { 
    method: 'PUT', 
    body: JSON.stringify(licor) 
  }),
  deleteLicorComercial: (id) => fetchWithAuth(`${API_BASE}/licores-comerciales/${id}`, { 
    method: 'DELETE' 
  })
};

// ----------------------- UI -----------------------
const UI = {
  initRoot() {
    if (!$('#root').length) {
      $('body').append('<div id="root"></div>');
    }
  },

  openMovimientoModal: function(movimiento) {
    movimiento = movimiento || null;
    
    // Crear modal si no existe
    if (!$('#modalMovimiento').length) {
      $('body').append(`
        <div class="modal fade" id="modalMovimiento" tabindex="-1">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">${movimiento ? 'Editar' : 'Nuevo'} Movimiento</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <form id="formMovimiento">
                  <input type="hidden" id="mov_id">
                  <div class="mb-3">
                    <label class="form-label">Producto</label>
                    <select id="mov_producto_id" class="form-select" required>
                      <option value="">Seleccionar producto</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Tipo</label>
                    <select id="mov_tipo" class="form-select" required>
                      <option value="entrada">Entrada</option>
                      <option value="salida">Salida</option>
                      <option value="ajuste">Ajuste</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Cantidad (ml)</label>
                    <input type="number" id="mov_cantidad" class="form-control" required>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Notas</label>
                    <textarea id="mov_notas" class="form-control"></textarea>
                  </div>
                </form>
              </div>
              <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button class="btn btn-primary" id="btnGuardarMovimiento">Guardar</button>
              </div>
            </div>
          </div>
        </div>
      `);
    }

    const $modal = $('#modalMovimiento');
    const $form = $('#formMovimiento');
    $form.trigger('reset');

    // Llenar select de productos
    const $selectProducto = $('#mov_producto_id');
    $selectProducto.empty().append('<option value="">Seleccionar producto</option>');
    appState.productos.forEach(p => {
      $selectProducto.append(`<option value="${p.id}">${escapeHtml(p.nombre)} (${escapeHtml(p.marca)})</option>`);
    });

    if (movimiento && movimiento.producto) {
      $('#mov_producto_id').val(movimiento.producto.id);
      $('#mov_tipo').val(movimiento.tipo || 'entrada');
      $('#mov_cantidad').val(movimiento.cantidad_ml || '');
      $('#mov_notas').val(movimiento.notas || '');
    }

    // Configurar eventos
    $('#btnGuardarMovimiento').off('click').on('click', async () => {
      const data = {
        producto_id: $('#mov_producto_id').val(),
        tipo: $('#mov_tipo').val(),
        cantidad_ml: Number($('#mov_cantidad').val()),
        notas: $('#mov_notas').val().trim()
      };

      if (!data.producto_id || isNaN(data.cantidad_ml)) {
        return showError('Complete todos los campos requeridos');
      }

      try {
        await api.createMovement(data);
        showSuccess('Movimiento registrado');
        $modal.modal('hide');
        await this.cargarMovimientos();
        await this.reloadProductos(); // Actualizar stock
      } catch (err) {
        showError('Error al guardar movimiento: ' + err.message);
      }
    });

    $modal.modal('show');
  },

  openUsuarioModal: function(usuario = null) {
    // Crear modal si no existe
    if (!$('#modalUsuario').length) {
      $('body').append(`
        <div class="modal fade" id="modalUsuario" tabindex="-1">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">${usuario ? 'Editar' : 'Nuevo'} Usuario</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <form id="formUsuario">
                  <input type="hidden" id="usuario_id">
                  <div class="mb-3">
                    <label class="form-label">Nombre completo</label>
                    <input id="usuario_nombre" class="form-control" required>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Nombre de usuario</label>
                    <input id="usuario_username" class="form-control" required>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Contraseña</label>
                    <input type="password" id="usuario_password" class="form-control" ${!usuario ? 'required' : ''}>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Rol</label>
                    <select id="usuario_rol" class="form-select" required>
                      <option value="admin">Administrador</option>
                      <option value="empleado">Empleado</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Local</label>
                    <select id="usuario_local_id" class="form-select">
                      <option value="">Sin local asignado</option>
                    </select>
                  </div>
                </form>
              </div>
              <div class="modal-footer">
                <button class="btn btn-danger me-auto" id="btnEliminarUsuario" ${!usuario ? 'style="display:none"' : ''}>
                  Eliminar
                </button>
                <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button class="btn btn-primary" id="btnGuardarUsuario">Guardar</button>
              </div>
            </div>
          </div>
        </div>
      `);
    }

    const $modal = $('#modalUsuario');
    const $form = $('#formUsuario');
    $form.trigger('reset');

    // Llenar select de locales
    const $selectLocal = $('#usuario_local_id');
    $selectLocal.empty().append('<option value="">Sin local asignado</option>');
    appState.locales.forEach(l => {
      $selectLocal.append(`<option value="${l.id}">${escapeHtml(l.nombre)}</option>`);
    });

    if (usuario) {
      $('#usuario_id').val(usuario.id);
      $('#usuario_nombre').val(usuario.nombre);
      $('#usuario_username').val(usuario.username);
      $('#usuario_rol').val(usuario.rol);
      $('#usuario_local_id').val(usuario.local_id || '');
    }

    // Configurar eventos
    $('#btnGuardarUsuario').off('click').on('click', async () => {
      const data = {
        nombre: $('#usuario_nombre').val().trim(),
        username: $('#usuario_username').val().trim(),
        password: $('#usuario_password').val().trim(),
        rol: $('#usuario_rol').val(),
        local_id: $('#usuario_local_id').val() || null
      };

      if (!data.nombre || !data.username || !data.rol || (!usuario && !data.password)) {
        return showError('Complete todos los campos requeridos');
      }

      try {
        const id = $('#usuario_id').val();
        if (id) {
          await api.updateUsuario(id, data);
          showSuccess('Usuario actualizado');
        } else {
          await api.createUsuario(data);
          showSuccess('Usuario creado');
        }
        $modal.modal('hide');
        await this.cargarUsuarios();
      } catch (err) {
        showError('Error al guardar usuario: ' + err.message);
      }
    });

    $('#btnEliminarUsuario').off('click').on('click', async () => {
      if (!confirm('¿Eliminar este usuario permanentemente?')) return;
      try {
        await api.deleteUsuario($('#usuario_id').val());
        showSuccess('Usuario eliminado');
        $modal.modal('hide');
        await this.cargarUsuarios();
      } catch (err) {
        showError('Error al eliminar usuario: ' + err.message);
      }
    });

    $modal.modal('show');
  },

  openLicorComercialModal: function(licor = null) {
    if (!$('#modalLicorComercial').length) {
      $('body').append(`
        <div class="modal fade" id="modalLicorComercial" tabindex="-1">
          <div class="modal-dialog modal-lg">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">${licor ? 'Editar' : 'Nuevo'} Licor Comercial</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <form id="formLicorComercial">
                  <input type="hidden" id="licor_id">
                  <div class="row g-3">
                    <div class="col-md-4">
                      <label class="form-label">Nombre</label>
                      <input id="licor_nombre" class="form-control" required>
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Marca</label>
                      <input id="licor_marca" class="form-control" required>
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Tipo</label>
                      <input id="licor_tipo" class="form-control" required>
                    </div>
                    
                    <div class="col-12">
                      <h5 class="mt-3 mb-2">Presentaciones</h5>
                      <div id="presentacionesContainer">
                        <!-- Las presentaciones se agregarán aquí dinámicamente -->
                      </div>
                      <button type="button" class="btn btn-sm btn-outline-primary mt-2" id="btnAgregarPresentacion">
                        <i class="bi bi-plus"></i> Agregar Presentación
                      </button>
                    </div>
                  </div>
                </form>
              </div>
              <div class="modal-footer">
                <button class="btn btn-danger me-auto" id="btnEliminarLicor" ${!licor ? 'style="display:none"' : ''}>
                  Eliminar
                </button>
                <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button class="btn btn-primary" id="btnGuardarLicor">Guardar</button>
              </div>
            </div>
          </div>
        </div>
      `);
    }

    const $modal = $('#modalLicorComercial');
    const $form = $('#formLicorComercial');
    $form.trigger('reset');
    $('#presentacionesContainer').empty();

    if (licor) {
      $('#licor_id').val(licor.id || '');
      $('#licor_nombre').val(licor.nombre || '');
      $('#licor_marca').val(licor.marca || '');
      $('#licor_tipo').val(licor.tipo || '');
      
      // Limpiar presentaciones existentes
      $('#presentacionesContainer').empty();
      
      // Agregar presentaciones existentes
      if (licor.presentaciones && licor.presentaciones.length > 0) {
        licor.presentaciones.forEach((presentacion, index) => {
          this.agregarPresentacionALicor({
            presentacion_ml: presentacion,
            densidad: licor.densidades ? licor.densidades[index] : '',
            peso_envase: licor.pesos_envase ? licor.pesos_envase[index] : ''
          });
        });
      } else {
        // Agregar presentación por defecto si no hay presentaciones
        this.agregarPresentacionALicor();
      }
    } else {
      // Agregar una presentación por defecto para nuevo licor
      this.agregarPresentacionALicor();
    }

    // Configurar eventos
    $('#btnAgregarPresentacion').off('click').on('click', () => this.agregarPresentacionALicor());
    
    $('#btnGuardarLicor').off('click').on('click', async () => {
      const presentaciones = [];
      const densidades = [];
      const pesos_envase = [];
      
      $('.presentacion-item').each(function() {
  const $item = $(this);
  const ml = Number($item.find('.presentacion-ml').val()) || 0;
  const densidad = Number($item.find('.presentacion-densidad').val()) || 0;
  const peso = Number($item.find('.presentacion-peso').val()) || 0;
  
  presentaciones.push(ml);
  densidades.push(densidad);
  pesos_envase.push(peso);
});
      
      const data = {
        nombre: $('#licor_nombre').val().trim(),
        marca: $('#licor_marca').val().trim(),
        tipo: $('#licor_tipo').val().trim(),
        presentaciones: presentaciones,
        densidades: densidades,
        pesos_envase: pesos_envase
      };

      if (!data.nombre || !data.marca || !data.tipo || presentaciones.length === 0) {
        return showError('Complete todos los campos requeridos');
      }

      try {
        const id = $('#licor_id').val();
        if (id) {
          await api.updateLicorComercial(id, data);
          showSuccess('Licor comercial actualizado');
        } else {
          await api.createLicorComercial(data);
          showSuccess('Licor comercial creado');
        }
        $modal.modal('hide');
        await this.cargarLicoresComerciales();
      } catch (err) {
        showError('Error al guardar licor comercial: ' + err.message);
      }
    });

    $('#btnEliminarLicor').off('click').on('click', async () => {
      if (!confirm('¿Eliminar este licor comercial permanentemente?')) return;
      try {
        await api.deleteLicorComercial($('#licor_id').val());
        showSuccess('Licor comercial eliminado');
        $modal.modal('hide');
        await this.cargarLicoresComerciales();
      } catch (err) {
        showError('Error al eliminar licor comercial: ' + err.message);
      }
    });

    $modal.modal('show');
  },

  agregarPresentacionALicor: function(presentacionData = {}) {
  const id = 'pres_' + Math.random().toString(36).substr(2, 9);
  const $container = $('#presentacionesContainer');
  
  // Validar que el contenedor exista
  if (!$container.length) {
    throw new Error('El contenedor de presentaciones no existe en el DOM');
  }

  // Crear el HTML de la presentación
  const presentacionHTML = `
    <div class="presentacion-item border p-3 mb-3 rounded" id="${id}">
      <div class="row g-2">
        <div class="col-md-3">
          <label class="form-label">Presentación (ml)</label>
          <select class="form-select presentacion-ml">
            <option value="750" ${presentacionData.presentacion_ml == 750 ? 'selected' : ''}>750 ml</option>
            <option value="1000" ${presentacionData.presentacion_ml == 1000 ? 'selected' : ''}>1 Litro (1000 ml)</option>
            <option value="375" ${presentacionData.presentacion_ml == 375 ? 'selected' : ''}>375 ml</option>
            <option value="500" ${presentacionData.presentacion_ml == 500 ? 'selected' : ''}>500 ml</option>
            <option value="700" ${presentacionData.presentacion_ml == 700 ? 'selected' : ''}>700 ml</option>
          </select>
        </div>
        <div class="col-md-3">
          <label class="form-label">Densidad (g/ml)</label>
          <input type="number" step="0.001" class="form-control presentacion-densidad" 
                 value="${presentacionData.densidad || ''}">
        </div>
        <div class="col-md-3">
          <label class="form-label">Peso envase (g)</label>
          <input type="number" step="1" class="form-control presentacion-peso" 
                 value="${presentacionData.peso_envase || ''}">
        </div>
        <div class="col-md-3 d-flex align-items-end">
          <button class="btn btn-sm btn-outline-danger w-100 btn-eliminar-presentacion" type="button">
            <i class="bi bi-trash"></i> Eliminar
          </button>
        </div>
      </div>
    </div>
  `;

  // Agregar al DOM
  $container.append(presentacionHTML);
  
  // Configurar evento de eliminación
  $(`#${id} .btn-eliminar-presentacion`).on('click', function() {
    if ($('.presentacion-item').length > 1) {
      $(this).closest('.presentacion-item').remove();
    } else {
      showError('Debe haber al menos una presentación');
    }
  });
},
  async showLoginView() {
    this.initRoot();
    $('#root').html(`
      <div class="container py-5">
        <div class="row justify-content-center">
          <div class="col-md-5">
            <div class="card shadow-sm">
              <div class="card-body">
                <h4 class="card-title mb-3">Iniciar Sesión</h4>
                <form id="loginForm">
                  <div class="mb-3">
                    <label class="form-label">Usuario</label>
                    <input id="loginUser" class="form-control" required>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Contraseña</label>
                    <input id="loginPass" type="password" class="form-control" required>
                  </div>
                  <button class="btn btn-primary w-100" type="submit">Ingresar</button>
                </form>
              </div>
            </div>
            <p class="text-center mt-2 text-muted small">Versión web del Inventario</p>
          </div>
        </div>
      </div>
    `);

    $('#loginForm').on('submit', async (e) => {
      e.preventDefault();
      const u = $('#loginUser').val().trim();
      const p = $('#loginPass').val().trim();
      try {
        const resp = await api.login(u, p);
        if (resp && resp.username) {
          appState.user = resp;
          this.showMainView();
        } else {
          showError('Credenciales inválidas');
        }
      } catch (err) {
        showError('Error login: ' + err.message);
      }
    });
  },

  openLocalModal: function(local = null) {
    // Crear el modal si no existe
    if (!$('#modalLocal').length) {
      $('body').append(`
        <div class="modal fade" id="modalLocal" tabindex="-1">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">${local ? 'Editar' : 'Nuevo'} Local</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <form id="formLocal">
                  <input type="hidden" id="local_id">
                  <div class="mb-3">
                    <label class="form-label">Nombre</label>
                    <input id="local_nombre" class="form-control" required>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Dirección</label>
                    <input id="local_direccion" class="form-control">
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Teléfono</label>
                    <input id="local_telefono" class="form-control">
                  </div>
                  <div class="form-check form-switch mb-3">
                    <input class="form-check-input" type="checkbox" id="local_activo">
                    <label class="form-check-label">Activo</label>
                  </div>
                </form>
              </div>
              <div class="modal-footer">
                <button class="btn btn-danger me-auto" id="btnEliminarLocal" ${!local ? 'style="display:none"' : ''}>
                  Eliminar
                </button>
                <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button class="btn btn-primary" id="btnGuardarLocal">Guardar</button>
              </div>
            </div>
          </div>
        </div>
      `);
    }

    // Llenar el formulario si hay datos
    const $modal = $('#modalLocal');
    const $form = $('#formLocal');
    $form.trigger('reset');

    if (local) {
      $('#local_id').val(local.id);
      $('#local_nombre').val(local.nombre);
      $('#local_direccion').val(local.direccion || '');
      $('#local_telefono').val(local.telefono || '');
      $('#local_activo').prop('checked', local.activo !== 0);
    }

    // Configurar eventos
    $('#btnGuardarLocal').off('click').on('click', async () => {
      const data = {
        nombre: $('#local_nombre').val().trim(),
        direccion: $('#local_direccion').val().trim(),
        telefono: $('#local_telefono').val().trim(),
        activo: $('#local_activo').is(':checked') ? 1 : 0
      };

      if (!data.nombre) {
        return showError('El nombre es obligatorio');
      }

      try {
        const id = $('#local_id').val();
        if (id) {
          await api.updateLocal(id, data);
          showSuccess('Local actualizado');
        } else {
          await api.createLocal(data);
          showSuccess('Local creado');
        }
        $modal.modal('hide');
        await this.cargarLocales();
      } catch (err) {
        showError('Error al guardar: ' + err.message);
      }
    });

    $('#btnEliminarLocal').off('click').on('click', async () => {
      if (!confirm('¿Eliminar este local permanentemente?')) return;
      try {
        await api.deleteLocal($('#local_id').val());
        showSuccess('Local eliminado');
        $modal.modal('hide');
        await this.cargarLocales();
      } catch (err) {
        showError('Error al eliminar: ' + err.message);
      }
    });

    $modal.modal('show');
  },

  showReportesView() {
    $('#contentView').html(`
      <div class="card">
        <div class="card-body">
          <h4>Reportes</h4>
          <div class="row">
            <div class="col-md-4">
              <div class="card text-white bg-primary mb-3">
                <div class="card-body">
                  <h5 class="card-title">Total Productos</h5>
                  <p class="card-text" id="totalProductos">0</p>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card text-white bg-success mb-3">
                <div class="card-body">
                  <h5 class="card-title">Stock Total (ml)</h5>
                  <p class="card-text" id="totalStock">0</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `);
    this.cargarDatosReportes();
  },

  async cargarDatosReportes() {
    try {
      const response = await api.getProducts();
      const productos = Array.isArray(response) ? response : response.products || [];
      const totalStock = productos.reduce((sum, p) => sum + (p.total_ml || 0), 0);
      
      $('#totalProductos').text(productos.length);
      $('#totalStock').text(totalStock);
    } catch (err) {
      showError('Error al cargar reportes: ' + err.message);
    }
  },

  async showLicoresView() {
    $('#contentView').html(`
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4>Licores Comerciales</h4>
        <button class="btn btn-sm btn-success" id="btnNuevoLicor">
          <i class="bi bi-plus-lg"></i> Nuevo Licor
        </button>
      </div>
      <div class="card">
        <div class="card-body">
          <table class="table table-hover" id="tablaLicores">
            <thead class="table-light">
              <tr>
                <th>Nombre</th>
                <th>Marca</th>
                <th>Tipo</th>
                <th>Presentaciones</th>
                <th>Densidad (g/ml)</th>
                <th>Peso Envase (g)</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    `);
    await this.cargarLicoresComerciales();
  },

  async cargarLicoresComerciales() {
    try {
      const response = await api.getLicoresComerciales();
      const licores = Array.isArray(response) ? response : response.licores || [];
      const $tbody = $('#tablaLicores tbody');
      $tbody.empty();

      // Configurar botón nuevo licor
      $('#btnNuevoLicor').off('click').on('click', () => this.openLicorComercialModal());

      licores.forEach(licor => {
        // Procesar presentaciones únicas
        const presentacionesUnicas = [...new Set(licor.presentaciones)];
        const presentacionesHtml = presentacionesUnicas.map(p => {
          if (p === 1000) return '1L';
          if (p === 750) return '750ml';
          if (p === 375) return '375ml';
          return `${p}ml`;
        }).join(' / ');

        // Obtener densidad y peso (tomamos el primero si hay varios)
        const densidad = licor.densidades && licor.densidades.length > 0 ? 
          licor.densidades[0].toFixed(3) : 'N/A';
        const peso = licor.pesos_envase && licor.pesos_envase.length > 0 ? 
          licor.pesos_envase[0].toFixed(1) : 'N/A';

        $tbody.append(`
          <tr>
            <td>${escapeHtml(licor.nombre)}</td>
            <td>${escapeHtml(licor.marca)}</td>
            <td>${escapeHtml(licor.tipo)}</td>
            <td>${presentacionesHtml}</td>
            <td>${densidad}</td>
            <td>${peso}</td>
            <td>
              <button class="btn btn-sm btn-outline-primary btn-edit-licor" 
                      data-id="${licor.id}" 
                      data-licor='${JSON.stringify(licor)}'>
                <i class="bi bi-pencil"></i> Editar
              </button>
              <button class="btn btn-sm btn-outline-danger btn-delete-licor" 
                      data-id="${licor.id}">
                <i class="bi bi-trash"></i> Eliminar
              </button>
            </td>
          </tr>
        `);
      });

      // Configurar eventos para los botones
      $('.btn-edit-licor').off('click').on('click', (e) => {
        const licorData = $(e.currentTarget).data('licor');
        if (licorData) {
          this.openLicorComercialModal(licorData);
        }
      });

      $('.btn-delete-licor').off('click').on('click', async (e) => {
        const id = $(e.currentTarget).data('id');
        if (confirm('¿Estás seguro de eliminar este licor?')) {
          try {
            await api.deleteLicorComercial(id);
            showSuccess('Licor eliminado correctamente');
            await this.cargarLicoresComerciales();
          } catch (err) {
            showError('Error al eliminar licor: ' + err.message);
          }
        }
      });

      appState.licoresComerciales = licores;
    } catch (err) {
      showError('Error al cargar licores: ' + err.message);
    }
  },

  showAboutView() {
    $('#contentView').html(`
      <div class="card">
        <div class="card-body">
          <h4>Acerca de la Aplicación</h4>
          <p>Versión 1.0</p>
          <p>Sistema de inventario para licores artesanales.</p>
        </div>
      </div>
    `);
  },

  async showUsuariosView() {
    $('#contentView').html(`
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4>Usuarios</h4>
        <button class="btn btn-sm btn-success" id="btnNuevoUsuario">Nuevo Usuario</button>
      </div>
      <div class="card">
        <div class="card-body">
          <table class="table" id="tablaUsuarios">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Local</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    `);
    await this.cargarUsuarios();
    $('#btnNuevoUsuario').off('click').on('click', () => this.openUsuarioModal());
  },

  async showLocalesView() {
    $('#contentView').html(`
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4>Locales</h4>
        <button class="btn btn-sm btn-success" id="btnNuevoLocal">
          <i class="bi bi-plus-lg"></i> Nuevo Local
        </button>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="tablaLocales">
              <thead class="table-light">
                <tr>
                  <th>Nombre</th>
                  <th>Dirección</th>
                  <th>Teléfono</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </div>
    `);

    // Configurar eventos
    $('#btnNuevoLocal').off('click').on('click', () => this.openLocalModal());
    await this.cargarLocales();
  },

  async cargarLocales() {
    try {
      const response = await api.getLocales();
      const locales = response.locales || []; 
      appState.locales = locales;
      
      const $tbody = $('#tablaLocales tbody');
      $tbody.empty();
      
      locales.forEach(local => {
        $tbody.append(`
          <tr>
            <td>${escapeHtml(local.nombre)}</td>
            <td>${escapeHtml(local.direccion || 'N/A')}</td>
            <td>${escapeHtml(local.telefono || 'N/A')}</td>
            <td>${local.activo ? 'Activo' : 'Inactivo'}</td>
            <td>
              <button class="btn btn-sm btn-outline-primary btn-edit-local" data-id="${local.id}">
                <i class="bi bi-pencil"></i> Editar
              </button>
              <button class="btn btn-sm btn-outline-danger btn-delete-local" data-id="${local.id}">
                <i class="bi bi-trash"></i> Eliminar
              </button>
            </td>
          </tr>
        `);
      });

      // Configurar eventos de los botones
      $('.btn-edit-local').off('click').on('click', function() {
        const id = $(this).data('id');
        const local = appState.locales.find(l => l.id === id);
        UI.openLocalModal(local);
      });

      $('.btn-delete-local').off('click').on('click', async function() {
        const id = $(this).data('id');
        if (confirm('¿Eliminar este local?')) {
          try {
            await api.deleteLocal(id);
            showSuccess('Local eliminado');
            await UI.cargarLocales();
          } catch (err) {
            showError('Error al eliminar local: ' + err.message);
          }
        }
      });
    } catch (err) {
      if (err.message.includes('403')) {
        showError('No tienes permisos para ver locales');
        $('#contentView').html('<p class="text-danger">No autorizado</p>');
      } else {
        showError('Error al cargar locales: ' + err.message);
      }
    }
  },

  async cargarUsuarios() {
    try {
      const response = await api.getUsuarios();
      const usuarios = response.usuarios || [];
      appState.usuarios = usuarios;
      
      const $tbody = $('#tablaUsuarios tbody');
      $tbody.empty();
      
      usuarios.forEach(usuario => {
        $tbody.append(`
          <tr>
            <td>${escapeHtml(usuario.nombre)}</td>
            <td>${escapeHtml(usuario.username)}</td>
            <td>${escapeHtml(usuario.rol)}</td>
            <td>${escapeHtml(usuario.local_nombre || 'N/A')}</td>
            <td>
              <button class="btn btn-sm btn-outline-primary btn-edit-user" data-id="${usuario.id}">
                Editar
              </button>
              ${usuario.rol !== 'admin' ? `
              <button class="btn btn-sm btn-outline-danger btn-delete-user" data-id="${usuario.id}">
                Eliminar
              </button>
              ` : ''}
            </td>
          </tr>
        `);
      });

      // Configurar eventos de los botones
      $('.btn-edit-user').off('click').on('click', function() {
        const id = $(this).data('id');
        const usuario = appState.usuarios.find(u => u.id === id);
        UI.openUsuarioModal(usuario);
      });

      $('.btn-delete-user').off('click').on('click', async function() {
        const id = $(this).data('id');
        if (confirm('¿Eliminar este usuario?')) {
          try {
            await api.deleteUsuario(id);
            showSuccess('Usuario eliminado');
            await UI.cargarUsuarios();
          } catch (err) {
            showError('Error al eliminar usuario: ' + err.message);
          }
        }
      });
    } catch (err) {
      if (err.message.includes('403')) {
        showError('No tienes permisos para ver usuarios');
        $('#contentView').html('<p class="text-danger">No autorizado</p>');
      } else {
        showError('Error al cargar usuarios: ' + err.message);
      }
    }
  },

  async showMainView() {
    this.initRoot();
    const nombre = appState.user?.nombre || appState.user?.username || 'Usuario';
    const rol = appState.user?.rol || 'empleado';

    $('#root').html(`
      <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
          <a class="navbar-brand" href="#">
            <i class="bi bi-cup-hot-fill me-2"></i>Inventario Licores
          </a>
          <div class="d-flex align-items-center text-white">
            <div class="me-3">
              <small class="d-block">${nombre}</small>
              <small class="d-block text-white-50">${capitalize(rol)}</small>
            </div>
            <button class="btn btn-outline-light btn-sm" id="btnLogout">
              <i class="bi bi-box-arrow-right"></i> Salir
            </button>
          </div>
        </div>
      </nav>

      <div class="container-fluid mt-3">
        <div class="row">
          <div class="col-md-2 px-0">
            <div class="list-group" id="sidebarMenu">
              <div class="sidebar-header">INVENTARIO</div>
              <button class="list-group-item sidebar-item" data-view="productos">
                <i class="bi bi-box-seam"></i> Productos
              </button>
              <button class="list-group-item sidebar-item" data-view="movimientos">
                <i class="bi bi-arrow-left-right"></i> Movimientos
              </button>
              
              <div class="sidebar-header">ADMINISTRACIÓN</div>
              <button class="list-group-item sidebar-item" data-view="locales">
                <i class="bi bi-shop"></i> Locales
              </button>
              <button class="list-group-item sidebar-item" data-view="usuarios">
                <i class="bi bi-people"></i> Usuarios
              </button>
              <button class="list-group-item sidebar-item" data-view="licores">
                <i class="bi bi-basket"></i> Licores Comerciales
              </button>
              
              <div class="sidebar-header">REPORTES</div>
              <button class="list-group-item sidebar-item" data-view="reportes">
                <i class="bi bi-graph-up"></i> Reportes
              </button>
              
              <div class="sidebar-header">SISTEMA</div>
              <button class="list-group-item sidebar-item" data-view="about">
                <i class="bi bi-info-circle"></i> Acerca de
              </button>
            </div>
          </div>
          <div class="col-md-10">
            <div id="contentView"></div>
          </div>
        </div>
      </div>
    `);

    // Activar el primer elemento del menú
    $('#sidebarMenu button[data-view="productos"]').addClass('active');

    // Eventos del sidebar con jQuery
    $('#sidebarMenu').on('click', 'button', (e) => {
      const $btn = $(e.currentTarget);
      $('#sidebarMenu button').removeClass('active');
      $btn.addClass('active');
      const view = $btn.data('view');
      if (view && typeof this[`show${capitalize(view)}View`] === 'function') {
        this[`show${capitalize(view)}View`]();
      } else {
        showError('Vista no implementada: ' + view);
      }
    });

    $('#btnLogout').on('click', async () => {
      try {
        await api.logout();
      } catch (e) { /* ignore */ }
      appState.user = null;
      this.showLoginView();
    });

    // Cargar datos esenciales
    await Promise.allSettled([
      this.cargarLocales(),
      this.cargarLicoresComerciales(),
      this.cargarUsuarios()
    ]);

    // Mostrar por defecto Productos
    this.showProductosView();
  },

  async showMovimientosView() {
    $('#contentView').html(`
      <div class="card">
        <div class="card-body">
          <h4>Movimientos</h4>
          <table class="table" id="tablaMovimientos">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Tipo</th>
                <th>Cantidad (ml)</th>
                <th>Fecha</th>
                <th>Notas</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    `);
    await this.cargarMovimientos();
  },

  async cargarMovimientos() {
    try {
      const response = await api.getMovements();
      const movimientos = Array.isArray(response) ? response : response.movements || [];
      const $tbody = $('#tablaMovimientos tbody');
      $tbody.empty();
      
      if (movimientos && movimientos.length) {
        movimientos.forEach(mov => {
          const producto = appState.productos.find(p => p.id === mov.producto_id) || {};
          $tbody.append(`
            <tr>
              <td>${escapeHtml(producto.nombre || 'N/A')}</td>
              <td>${escapeHtml(mov.tipo || '-')}</td>
              <td>${mov.cantidad_ml || '0'}</td>
              <td>${formatDate(mov.fecha)}</td>
              <td>${escapeHtml(mov.notas || '')}</td>
            </tr>
          `);
        });
      } else {
        $tbody.append('<tr><td colspan="5" class="text-center">No hay movimientos</td></tr>');
      }
    } catch (err) {
      showError('Error al cargar movimientos: ' + err.message);
    }
  },

  // ---------------- Productos ----------------
  async showProductosView() {
    $('#contentView').html(`
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4>Productos</h4>
        <div>
          <button class="btn btn-sm btn-success me-2" id="btnNuevoProducto"><i class="bi bi-plus-lg"></i> Nuevo</button>
          <button class="btn btn-sm btn-secondary" id="btnRefreshProductos">Actualizar</button>
        </div>
      </div>

      <div class="card mb-3">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-sm table-hover" id="tablaProductos">
              <thead class="table-light">
                <tr>
                  <th>Nombre</th><th>Marca</th><th>Tipo</th><th>Stock (ml)</th><th>Botellas</th><th>Local</th><th>Acciones</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Modal producto -->
      <div class="modal fade" id="modalProducto" tabindex="-1">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="productoModalTitle">Producto</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <form id="formProducto">
                <input type="hidden" id="prod_id">
                <div class="row g-2">
                  <div class="col-md-6">
                    <label class="form-label">Nombre</label>
                    <input id="prod_nombre" class="form-control" required>
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Marca</label>
                    <input id="prod_marca" class="form-control" required>
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Tipo</label>
                    <input id="prod_tipo" class="form-control" required>
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Densidad (g/ml)</label>
                    <input id="prod_densidad" class="form-control" required>
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Capacidad (ml)</label>
                    <input id="prod_capacidad" class="form-control" required>
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Peso envase (g)</label>
                    <input id="prod_peso_envase" class="form-control" required>
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Minimo inventario (%)</label>
                    <input id="prod_minimo" class="form-control" value="20" required>
                  </div>
                  <div class="col-12 mt-2">
                    <label class="form-label">Local</label>
                    <select id="prod_local" class="form-select"></select>
                  </div>
                </div>
              </form>
            </div>
            <div class="modal-footer">
              <button class="btn btn-danger me-auto" id="btnEliminarProductoModal">Eliminar</button>
              <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
              <button class="btn btn-primary" id="btnGuardarProductoModal">Guardar</button>
            </div>
          </div>
        </div>
      </div>
    `);

    // Cargar locales en el select
    $('#prod_local').html('<option value="">Seleccionar local</option>' +
      appState.locales.map(l => `<option value="${l.id}">${escapeHtml(l.nombre)}</option>`).join(''));

    $('#btnNuevoProducto').on('click', () => this.openProductoModal());
    $('#btnRefreshProductos').on('click', () => this.reloadProductos());

    // Cargar tabla
    await this.reloadProductos();
  },

  async reloadProductos() {
    try {
      const data = await api.getProducts();
      const productos = Array.isArray(data) ? data : data.products || [];
      appState.productos = productos;
      this.renderProductosTable();
    } catch (err) {
      showError('Error cargando productos: ' + err.message);
    }
  },

  renderProductosTable() {
    const $tbody = $('#tablaProductos tbody');
    $tbody.empty();
    
    appState.productos.forEach(p => {
      const vol = p.total_ml ?? p.stock_ml ?? p.capacidad_ml ?? 0;
      const caps = p.capacidad_ml || p.capacidad || 0;
      let botStr = '-';
      
      if (caps) {
        const vb = volumenToBotellasCapacidad(Number(vol), Number(caps));
        botStr = `${vb.completas} + ${vb.restante} ml`;
      }
      
      const localName = p.local_nombre || (appState.locales.find(l => l.id === p.local_id)?.nombre || '');
      
      $tbody.append(`
        <tr>
          <td>${escapeHtml(p.nombre)}</td>
          <td>${escapeHtml(p.marca)}</td>
          <td>${escapeHtml(p.tipo)}</td>
          <td>${vol}</td>
          <td>${botStr}</td>
          <td>${escapeHtml(localName)}</td>
          <td>
            <button class="btn btn-sm btn-outline-primary btn-edit" data-id="${p.id}">
              <i class="bi bi-pencil"></i> Editar
            </button>
            <button class="btn btn-sm btn-outline-success btn-mov" data-id="${p.id}">
              <i class="bi bi-arrow-repeat"></i> Movimiento
            </button>
            <button class="btn btn-sm btn-outline-danger btn-delete" data-id="${p.id}">
              <i class="bi bi-trash"></i> Eliminar
            </button>
          </td>
        </tr>
      `);
    });

    // Event delegation para los botones
    $tbody.off('click').on('click', 'button', function() {
      const $btn = $(this);
      const id = $btn.data('id');
      
      if ($btn.hasClass('btn-edit')) {
        const prod = appState.productos.find(p => String(p.id) === String(id));
        UI.openProductoModal(prod);
      } 
      else if ($btn.hasClass('btn-delete')) {
        if (confirm('¿Eliminar producto?')) {
          api.deleteProduct(id)
            .then(() => {
              showSuccess('Producto eliminado');
              UI.reloadProductos();
            })
            .catch(err => showError('Error al eliminar: ' + err.message));
        }
      }
      else if ($btn.hasClass('btn-mov')) {
        const prod = appState.productos.find(p => String(p.id) === String(id));
        UI.openMovimientoModal({ producto: prod });
      }
    });
  },

  openProductoModal(producto = null) {
    const $modal = $('#modalProducto');
    const $form = $('#formProducto');
    
    $form.trigger('reset');
    $('#prod_id').val(producto ? producto.id : '');
    $('#prod_nombre').val(producto ? producto.nombre : '');
    $('#prod_marca').val(producto ? producto.marca : '');
    $('#prod_tipo').val(producto ? producto.tipo : '');
    $('#prod_densidad').val(producto ? producto.densidad : '');
    $('#prod_capacidad').val(producto ? producto.capacidad_ml || producto.capacidad : '');
    $('#prod_peso_envase').val(producto ? producto.peso_envase : '');
    $('#prod_minimo').val(producto ? producto.minimo_inventario || 20 : 20);
    $('#prod_local').val(producto ? producto.local_id : (appState.locales[0] ? appState.locales[0].id : ''));

    // Configurar eventos con jQuery
    $('#btnGuardarProductoModal').off('click').on('click', async () => {
      const data = {
        nombre: $('#prod_nombre').val().trim(),
        marca: $('#prod_marca').val().trim(),
        tipo: $('#prod_tipo').val().trim(),
        densidad: Number($('#prod_densidad').val()) || 1,
        capacidad_ml: Number($('#prod_capacidad').val()) || 0,
        peso_envase: Number($('#prod_peso_envase').val()) || 0,
        minimo_inventario: Number($('#prod_minimo').val()) || 20,
        local_id: Number($('#prod_local').val()) || null
      };

      if (!data.nombre || !data.marca || !data.tipo || !data.local_id) {
        return showError('Complete nombre, marca, tipo y local');
      }

      try {
        if (producto && producto.id) {
          await api.updateProduct(producto.id, data);
          showSuccess('Producto actualizado');
        } else {
          await api.createProduct(data);
          showSuccess('Producto creado');
        }
        $modal.modal('hide');
        await UI.reloadProductos();
      } catch (err) {
        showError('Error guardando producto: ' + err.message);
      }
    });

    $('#btnEliminarProductoModal').off('click').on('click', async () => {
      const id = producto?.id || $('#prod_id').val();
      if (!id) return showError('No hay producto para eliminar');
      if (!confirm('Confirmar eliminación de producto')) return;
      try {
        await api.deleteProduct(id);
        showSuccess('Producto eliminado');
        $modal.modal('hide');
        await UI.reloadProductos();
      } catch (err) { 
        showError('Error eliminar producto: ' + err.message); 
      }
    });

    $modal.modal('show');
  },

  async reloadLocales() {
    try {
      const response = await api.getLocales();
      appState.locales = response.locales || [];
    } catch (err) {
      showError('Error al cargar locales: ' + err.message);
    }
  },

  async reloadUsuarios() {
    try {
      const response = await api.getUsuarios();
      appState.usuarios = response.usuarios || [];
    } catch (err) {
      showError('Error al cargar usuarios: ' + err.message);
    }
  }
};

// ----------------------- Helpers globales -----------------------
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[&<>"'`=\/]/g, function(s) { 
    return ({ 
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',
      "'":'&#39;','/':'&#x2F;','`':'&#x60;','=':'&#x3D;' 
    })[s]; 
  });
}

function capitalize(s) { 
  if (!s) return ''; 
  return s[0].toUpperCase() + s.slice(1); 
}

// ----------------------- Inicialización -----------------------
$(document).ready(function() {
  // Inicializar tooltips de Bootstrap
  $('[data-bs-toggle="tooltip"]').tooltip();
  
  // Intentar obtener sesión
  async function initApp() {
    try {
      const me = await api.getMe();
      if (me && me.logged) {
        appState.user = me;
        UI.showMainView();
      } else {
        UI.showLoginView();
      }
    } catch (err) {
      console.warn('No se pudo verificar sesión:', err.message);
      UI.showLoginView();
    }
  }
  
  initApp();
});

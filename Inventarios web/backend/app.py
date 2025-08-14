from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import os
from pathlib import Path
import models  # Asegúrate de tener tu archivo models.py
import sqlite3

# Configuración de rutas
BASE_DIR = Path(__file__).parent.parent
FRONTEND_BUILD_DIR = BASE_DIR / "frontend_build"

# Verificar y crear directorio si no existe
if not FRONTEND_BUILD_DIR.exists():
    FRONTEND_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📂 Se creó el directorio: {FRONTEND_BUILD_DIR}")

app = Flask(__name__, static_folder=str(FRONTEND_BUILD_DIR), static_url_path="")
with app.app_context():
    try:
        models.init_db()
        print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        raise
app.secret_key = 'clave_super_secreta_123456789_fija'

# Reemplaza la configuración CORS actual con esta:
CORS(app, supports_credentials=True, origins=[
    "http://localhost:3000", 
    "http://192.168.100.79:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000"
])

# =============================================
# Decoradores y funciones de ayuda
# =============================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({'ok': False, 'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated_function

# =============================================
# Rutas de autenticación
# =============================================

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Verificar credenciales en la base de datos
    conn = models._connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nombre, rol, local_id 
        FROM usuarios 
        WHERE username = ? AND password = ? AND activo = 1
    """, (username, password))
    usuario = cur.fetchone()
    conn.close()

    if usuario:
        session['username'] = username
        session['user_id'] = usuario['id']
        session['user_name'] = usuario['nombre']
        session['user_role'] = usuario['rol']
        session['local_id'] = usuario['local_id']
        return jsonify({
            'ok': True, 
            'username': username,
            'nombre': usuario['nombre'],
            'rol': usuario['rol'],
            'local_id': usuario['local_id']
        })
    return jsonify({'ok': False, 'error': 'Credenciales inválidas'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me')
def me():
    if 'username' in session:
        return jsonify({
            'logged': True, 
            'username': session['username'],
            'nombre': session.get('user_name'),
            'rol': session.get('user_role'),
            'local_id': session.get('local_id')
        })
    return jsonify({'logged': False}), 401

# =============================================
# Rutas de productos
# =============================================

@app.route('/api/products', methods=['GET'])
@login_required
def products_list():
    # Si es admin, muestra todos los productos, sino solo los del local del usuario
    local_id = None if session.get('user_role') == 'admin' else session.get('local_id')
    prods = models.get_products(local_id)
    return jsonify({'products': prods})

@app.route('/api/products/<int:product_id>', methods=['GET'])
@login_required
def product_detail(product_id):
    product = models.get_product(product_id)
    if product:
        return jsonify({'ok': True, 'product': product})
    return jsonify({'ok': False, 'error': 'Producto no encontrado'}), 404

@app.route('/api/products', methods=['POST'])
@login_required
def products_create():
    data = request.json
    if not data.get('nombre'):
        return jsonify({'ok': False, 'error': 'Falta nombre'}), 400
    
    # Si no es admin, asignar el local del usuario
    if session.get('user_role') != 'admin':
        data['local_id'] = session.get('local_id')
    
    try:
        new_id = models.add_product(data)
        return jsonify({'ok': True, 'id': new_id}), 201
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def products_update(product_id):
    data = request.json
    try:
        updated = models.update_product(product_id, data)
        if updated:
            return jsonify({'ok': True})
        return jsonify({'ok': False, 'error': 'Producto no encontrado'}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def products_delete(product_id):
    deleted = models.delete_product(product_id)
    if deleted:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Producto no encontrado'}), 404

# =============================================
# Rutas de movimientos
# =============================================

@app.route('/api/movements', methods=['GET'])
@login_required
def movements_list():
    product_id = request.args.get('product_id', type=int)
    limit = request.args.get('limit', default=100, type=int)
    
    movements = models.get_movements(product_id, limit)
    return jsonify({'movements': movements})

@app.route('/api/movements', methods=['POST'])
@login_required
def movements_create():
    data = request.json
    if not all(k in data for k in ['producto_id', 'tipo', 'cantidad_ml']):
        return jsonify({'ok': False, 'error': 'Faltan campos obligatorios'}), 400
    
    # Asignar el usuario actual
    data['user_id'] = session.get('user_id')
    
    try:
        new_id = models.add_movement(data)
        return jsonify({'ok': True, 'id': new_id}), 201
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

# =============================================
# Rutas administrativas (solo admin)
# =============================================

@app.route('/api/locales', methods=['GET'])
@login_required
def locales_list():
    if session.get('user_role') != 'admin':
        return jsonify({'ok': False, 'error': 'No autorizado'}), 403
    
    locales = models.get_locales()
    return jsonify({'locales': locales})

@app.route('/api/usuarios', methods=['GET'])
@login_required
def usuarios_list():
    if session.get('user_role') != 'admin':
        return jsonify({'ok': False, 'error': 'No autorizado'}), 403
    
    usuarios = models.get_usuarios()
    return jsonify({'usuarios': usuarios})

# =============================================
# Rutas para Licores Comerciales
# =============================================

@app.route('/api/licores-comerciales', methods=['GET'])
@login_required
def licores_comerciales_list():
    try:
        licores = models.get_licores_comerciales()
        return jsonify({'ok': True, 'licores': licores})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/licores-comerciales', methods=['POST'])
@login_required
def licores_comerciales_create():
    data = request.json
    try:
        ids = models.add_licor_comercial(data)
        return jsonify({'ok': True, 'ids': ids}), 201
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/licores-comerciales/<int:id>', methods=['PUT'])
@login_required
def licores_comerciales_update(id):
    data = request.json
    try:
        conn = models._connect()
        cur = conn.cursor()
        
        # Actualizar un licor específico (una presentación)
        cur.execute("""
            UPDATE licores_comerciales 
            SET nombre = ?, marca = ?, tipo = ?, 
                presentacion_ml = ?, densidad = ?, peso_envase = ?
            WHERE id = ?
        """, (
            data.get('nombre'),
            data.get('marca'),
            data.get('tipo'),
            data.get('presentacion_ml'),
            data.get('densidad'),
            data.get('peso_envase'),
            id
        ))
        
        conn.commit()
        return jsonify({'ok': True})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/licores-comerciales/<int:id>', methods=['DELETE'])
@login_required
def licores_comerciales_delete(id):
    try:
        conn = models._connect()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM licores_comerciales WHERE id = ?", (id,))
        conn.commit()
        
        return jsonify({'ok': True})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        conn.close()

# =============================================
# Rutas del frontend
# =============================================

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    # Verificar si el archivo solicitado existe
    file_path = os.path.join(app.static_folder, path)
    
    if path and os.path.exists(file_path) and not os.path.isdir(file_path):
        return send_from_directory(app.static_folder, path)
    
    # Servir index.html para cualquier otra ruta (para SPA)
    index_path = os.path.join(app.static_folder, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(app.static_folder, 'index.html')
    
    # Mensaje de error detallado si no se encuentra index.html
    return f"""
    <h1>Error: Archivos frontend no encontrados</h1>
    <p>El servidor backend está funcionando, pero no se encontraron los archivos del frontend.</p>
    <p>Directorio esperado: <code>{app.static_folder}</code></p>
    <p>Contenido del directorio: {os.listdir(app.static_folder) if os.path.exists(app.static_folder) else 'Directorio no existe'}</p>
    <h3>Pasos para solucionar:</h3>
    <ol>
        <li>Construye tu frontend (ejecuta <code>npm run build</code> en tu proyecto frontend)</li>
        <li>Copia los archivos generados a <code>{app.static_folder}</code></li>
        <li>Asegúrate que existe <code>index.html</code> en ese directorio</li>
    </ol>
    """, 404

# =============================================
# Inicio de la aplicación
# =============================================

if __name__ == '__main__':
    print(f"🚀 Iniciando servidor Flask")
    print(f"📂 Directorio estático: {FRONTEND_BUILD_DIR}")
    
    if FRONTEND_BUILD_DIR.exists():
        print(f"📄 Archivos encontrados: {os.listdir(FRONTEND_BUILD_DIR)}")
    else:
        print("⚠️ Advertencia: El directorio frontend_build no existe")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
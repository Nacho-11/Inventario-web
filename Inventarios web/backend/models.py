# models.py
import sqlite3
from typing import List, Dict, Optional
from pathlib import Path
import os

# Usar la misma ubicación de la base de datos que la app de escritorio
DB_PATH = str(Path.home() / "Documents" / "InventarioLicores" / "inventario_licores.db")

def _connect():
    """Establece conexión con la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_products(local_id: Optional[int] = None) -> List[Dict]:
    """Obtiene todos los productos, filtrados por local si se especifica"""
    conn = _connect()
    cur = conn.cursor()
    
    query = """
    SELECT 
        p.id, p.nombre, p.marca, p.tipo, p.densidad, p.capacidad_ml, p.peso_envase,
        p.botellas_completas, p.minimo_inventario, p.activo,
        COALESCE((SELECT SUM(CASE WHEN tipo = 'entrada' THEN cantidad_ml ELSE -cantidad_ml END) 
             FROM movimientos WHERE producto_id = p.id), 0) as total_ml,
        l.nombre as local_nombre
    FROM productos p
    JOIN locales l ON p.local_id = l.id
    """
    
    params = ()
    if local_id:
        query += " WHERE p.local_id = ?"
        params = (local_id,)
    
    query += " ORDER BY p.nombre"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# Añade esto al inicio de models.py, después de DB_PATH
def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    try:
        create_licores_table()
        # Verificar si hay datos iniciales
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM licores_comerciales")
        count = cur.fetchone()[0]
        if count == 0:
            insert_initial_data()
        conn.close()
        print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        raise

def get_product(product_id: int) -> Optional[Dict]:
    """Obtiene un producto específico por ID"""
    conn = _connect()
    cur = conn.cursor()
    
    query = """
    SELECT 
        p.*, 
        COALESCE((SELECT SUM(CASE WHEN tipo = 'entrada' THEN cantidad_ml ELSE -cantidad_ml END) 
             FROM movimientos WHERE producto_id = p.id), 0) as total_ml
    FROM productos p
    WHERE p.id = ?
    """
    
    cur.execute(query, (product_id,))
    row = cur.fetchone()
    conn.close()
    
    return dict(row) if row else None

def add_product(product_data: Dict) -> int:
    """Agrega un nuevo producto"""
    required_fields = ['nombre', 'marca', 'tipo', 'densidad', 'capacidad_ml', 'peso_envase', 'local_id']
    if not all(field in product_data for field in required_fields):
        raise ValueError("Faltan campos obligatorios")
    
    conn = _connect()
    cur = conn.cursor()
    
    query = """
    INSERT INTO productos (
        local_id, nombre, marca, tipo, densidad, capacidad_ml, 
        peso_envase, minimo_inventario, botellas_completas, activo
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    params = (
        product_data['local_id'],
        product_data['nombre'],
        product_data['marca'],
        product_data['tipo'],
        product_data['densidad'],
        product_data['capacidad_ml'],
        product_data['peso_envase'],
        product_data.get('minimo_inventario', 0.2),
        product_data.get('botellas_completas', 0),
        product_data.get('activo', 1)
    )
    
    cur.execute(query, params)
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    
    return new_id

def update_product(product_id: int, product_data: Dict) -> bool:
    """Actualiza un producto existente"""
    conn = _connect()
    cur = conn.cursor()
    
    query = """
    UPDATE productos 
    SET nombre = ?, marca = ?, tipo = ?, densidad = ?, capacidad_ml = ?,
        peso_envase = ?, minimo_inventario = ?, botellas_completas = ?, activo = ?
    WHERE id = ?
    """
    
    params = (
        product_data.get('nombre'),
        product_data.get('marca'),
        product_data.get('tipo'),
        product_data.get('densidad'),
        product_data.get('capacidad_ml'),
        product_data.get('peso_envase'),
        product_data.get('minimo_inventario', 0.2),
        product_data.get('botellas_completas', 0),
        product_data.get('activo', 1),
        product_id
    )
    
    cur.execute(query, params)
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    
    return updated

def delete_product(product_id: int) -> bool:
    """Elimina un producto y sus movimientos asociados"""
    conn = _connect()
    cur = conn.cursor()
    
    try:
        # Primero eliminar movimientos asociados
        cur.execute("DELETE FROM movimientos WHERE producto_id = ?", (product_id,))
        # Luego eliminar el producto
        cur.execute("DELETE FROM productos WHERE id = ?", (product_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return deleted

def get_movements(product_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
    """Obtiene movimientos, filtrados por producto si se especifica"""
    conn = _connect()
    cur = conn.cursor()
    
    query = """
    SELECT 
        m.id, m.fecha, m.tipo, m.cantidad_ml, m.peso_bruto, m.notas,
        p.nombre as producto_nombre, u.nombre as usuario_nombre
    FROM movimientos m
    JOIN productos p ON m.producto_id = p.id
    JOIN usuarios u ON m.user_id = u.id
    """
    
    params = ()
    if product_id:
        query += " WHERE m.producto_id = ?"
        params = (product_id,)
    
    query += " ORDER BY m.fecha DESC LIMIT ?"
    params += (limit,)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

def add_movement(movement_data: Dict) -> int:
    """Agrega un nuevo movimiento"""
    required_fields = ['producto_id', 'user_id', 'tipo', 'cantidad_ml']
    if not all(field in movement_data for field in required_fields):
        raise ValueError("Faltan campos obligatorios")
    
    conn = _connect()
    cur = conn.cursor()
    
    query = """
    INSERT INTO movimientos (
        producto_id, user_id, tipo, cantidad_ml, peso_bruto, notas
    ) VALUES (?, ?, ?, ?, ?, ?)
    """
    
    params = (
        movement_data['producto_id'],
        movement_data['user_id'],
        movement_data['tipo'],
        movement_data['cantidad_ml'],
        movement_data.get('peso_bruto'),
        movement_data.get('notas', '')
    )
    
    cur.execute(query, params)
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    
    return new_id

def get_locales() -> List[Dict]:
    """Obtiene todos los locales"""
    conn = _connect()
    cur = conn.cursor()
    
    query = "SELECT id, nombre, direccion, telefono, activo FROM locales ORDER BY nombre"
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

def get_usuarios() -> List[Dict]:
    """Obtiene todos los usuarios"""
    conn = _connect()
    cur = conn.cursor()
    
    query = """
    SELECT 
        u.id, u.username, u.nombre, u.rol, u.activo,
        l.nombre as local_nombre
    FROM usuarios u
    LEFT JOIN locales l ON u.local_id = l.id
    ORDER BY u.nombre
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

def get_licores_comerciales():
    """Obtiene los licores comerciales agrupados por nombre, marca y tipo"""
    conn = _connect()
    cur = conn.cursor()
    
    query = """
    SELECT 
        nombre, marca, tipo,
        GROUP_CONCAT(DISTINCT presentacion_ml) as presentaciones,
        GROUP_CONCAT(DISTINCT densidad) as densidades,
        GROUP_CONCAT(DISTINCT peso_envase) as pesos_envase,
        GROUP_CONCAT(id) as ids
    FROM licores_comerciales
    GROUP BY nombre, marca, tipo
    ORDER BY tipo, marca, nombre
    """
    
    try:
        cur.execute(query)
        rows = cur.fetchall()
        licores = []
        for row in rows:
            licor = {
                'nombre': row['nombre'],
                'marca': row['marca'],
                'tipo': row['tipo'],
                'ids': list(map(int, row['ids'].split(','))) if row['ids'] else [],
                'presentaciones': list(map(int, row['presentaciones'].split(','))) if row['presentaciones'] else [],
                'densidades': list(map(float, row['densidades'].split(','))) if row['densidades'] else [],
                'pesos_envase': list(map(float, row['pesos_envase'].split(','))) if row['pesos_envase'] else []
            }
            licores.append(licor)
        return licores
    except Exception as e:
        print(f"Error en get_licores_comerciales: {e}")
        raise
    finally:
        conn.close()

def table_exists(table_name):
    """Verifica si una tabla existe en la base de datos"""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def create_licores_table():
    """Crea o actualiza la tabla de licores comerciales con la estructura correcta"""
    conn = _connect()
    cur = conn.cursor()
    
    try:
        # Verificar si la tabla existe
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='licores_comerciales'")
        table_exists = cur.fetchone() is not None
        
        if table_exists:
            # Verificar si las columnas existen
            cur.execute("PRAGMA table_info(licores_comerciales)")
            columns = [col[1] for col in cur.fetchall()]
            
            # Agregar columnas faltantes
            if 'presentacion_ml' not in columns:
                cur.execute("ALTER TABLE licores_comerciales ADD COLUMN presentacion_ml INTEGER NOT NULL DEFAULT 750")
            
            if 'densidad' not in columns:
                cur.execute("ALTER TABLE licores_comerciales ADD COLUMN densidad REAL")
                
            if 'peso_envase' not in columns:
                cur.execute("ALTER TABLE licores_comerciales ADD COLUMN peso_envase REAL")
                
            print("✅ Estructura de tabla 'licores_comerciales' verificada y actualizada")
        else:
            # Crear tabla nueva
            create_sql = """
            CREATE TABLE licores_comerciales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                marca TEXT NOT NULL,
                tipo TEXT NOT NULL,
                presentacion_ml INTEGER NOT NULL,
                densidad REAL,
                peso_envase REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
            cur.execute(create_sql)
            print("✅ Tabla 'licores_comerciales' creada correctamente")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al verificar/crear tabla: {e}")
        raise
    finally:
        conn.close()
        
def insert_initial_data():
    """Inserta datos de ejemplo en la tabla"""
    initial_data = [
        ('Ron', 'Bacardí', 'Ron', 750, 0.95, 500.0),
        ('Ron', 'Bacardí', 'Ron', 1000, 0.95, 650.0),
        ('Vodka', 'Smirnoff', 'Vodka', 750, 0.95, 500.0),
        ('Whisky', 'Johnnie Walker', 'Whisky', 750, 0.94, 600.0)
    ]
    
    conn = _connect()
    cur = conn.cursor()
    
    try:
        cur.executemany("""
        INSERT INTO licores_comerciales (nombre, marca, tipo, presentacion_ml, densidad, peso_envase)
        VALUES (?, ?, ?, ?, ?, ?)
        """, initial_data)
        conn.commit()
        print("✅ Datos iniciales insertados correctamente")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al insertar datos: {e}")
    finally:
        conn.close()
        
def print_table_structure():
    """Muestra la estructura de la tabla para depuración"""
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(licores_comerciales)")
        print("Estructura de la tabla 'licores_comerciales':")
        for col in cur.fetchall():
            print(col)
    finally:
        conn.close()                

def add_licor_comercial(licor_data):
    """Agrega un nuevo licor comercial con sus presentaciones"""
    required_fields = ['nombre', 'marca', 'tipo', 'presentaciones']
    if not all(field in licor_data for field in required_fields):
        raise ValueError("Faltan campos obligatorios")
    
    conn = _connect()
    cur = conn.cursor()
    
    try:
        # Verificar si ya existe
        cur.execute("""
            SELECT 1 FROM licores_comerciales 
            WHERE nombre = ? AND marca = ? AND tipo = ?
            LIMIT 1
        """, (licor_data['nombre'], licor_data['marca'], licor_data['tipo']))
        
        if cur.fetchone():
            raise ValueError("Ya existe un licor con ese nombre, marca y tipo")
        
        # Insertar cada presentación
        ids = []
        for i in range(len(licor_data['presentaciones'])):
            cur.execute("""
                INSERT INTO licores_comerciales (
                    nombre, marca, tipo, presentacion_ml, densidad, peso_envase
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                licor_data['nombre'],
                licor_data['marca'],
                licor_data['tipo'],
                licor_data['presentaciones'][i],
                licor_data.get('densidades', [None] * len(licor_data['presentaciones']))[i],
                licor_data.get('pesos_envase', [None] * len(licor_data['presentaciones']))[i]
            ))
            ids.append(cur.lastrowid)
        
        conn.commit()
        return ids
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_licor_comercial(licor_id):
    """Elimina un licor comercial específico (una presentación)"""
    conn = _connect()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM licores_comerciales WHERE id = ?", (licor_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
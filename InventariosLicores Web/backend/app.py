from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, flash
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import use as matplotlib_use
matplotlib_use('Agg')  # Usar backend no interactivo
import io
import base64
from flask import send_from_directory
import os
from pathlib import Path
import threading
from datetime import datetime
import traceback
import logging
logging.basicConfig(level=logging.DEBUG)
from flask import send_file
from PIL import Image, ImageDraw
import io

# Crear el favicon directamente durante la inicialización
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
favicon_path = os.path.join(static_dir, 'favicon.ico')

if not os.path.exists(favicon_path):
    try:
        os.makedirs(static_dir, exist_ok=True)
        img = Image.new('RGB', (32, 32), color='red')
        draw = ImageDraw.Draw(img)
        draw.rectangle([8, 8, 24, 24], fill='white')
        img.save(favicon_path, format='ICO')
        print(f"Favicon creado en: {favicon_path}")
    except Exception as e:
        print(f"Error al crear favicon: {e}")

app = Flask(__name__, 
            template_folder='templates',
            static_folder=static_dir) 

# VERIFICACIÓN DE PLANTILLAS
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
print(f"Buscando plantillas en: {template_dir}")
print(f"¿Existe el directorio?: {os.path.exists(template_dir)}")

if os.path.exists(template_dir):
    print("Archivos encontrados:")
    for file in os.listdir(template_dir):
        print(f"  - {file}")
else:
    print("ERROR: No se encuentra la carpeta 'templates'")
    os.makedirs(template_dir, exist_ok=True)
    print("Carpeta 'templates' creada automáticamente")

app.secret_key = 'inventario_licores_secret_key_2025'
app.config['SESSION_TYPE'] = 'filesystem'
CORS(app)

# Constantes
ML_A_OZ = 0.033814  # 1 ml = 0.033814 oz
OZ_A_ML = 29.5735   # 1 oz = 29.5735 ml
VERSION = "1.2.0"
CLAVE_MAESTRA = "Admin2025!"

# Configuración de la base de datos
def get_db_path():
    """Obtiene la ruta de la base de datos"""
    try:
        # Intenta usar la misma ubicación que la aplicación original
        data_dir = Path.home() / "Documents" / "InventarioLicores"
        data_dir.mkdir(exist_ok=True, parents=True)
        db_path = data_dir / 'inventario_licores.db'
        print(f"Base de datos ubicada en: {db_path}")
        return str(db_path)
    except Exception as e:
        print(f"Error al obtener ruta de BD: {e}")
        # Fallback: usa una ruta relativa
        return 'inventario_licores.db'

class LicorDB:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()
        self.insertar_datos_iniciales()

    def get_config(self, clave, default=None):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
            result = cursor.fetchone()
            return result[0] if result else default
        except sqlite3.Error as e:
            print(f"Error al obtener configuración: {e}")
            return default
        finally:
            cursor.close()
    
    def set_config(self, clave, valor):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                (clave, valor)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error al guardar configuración: {e}")
            raise
        finally:
            cursor.close()

    def create_admin_user(self):
        cursor = self.conn.cursor()
    
        # Verificar si el usuario admin ya existe
        cursor.execute("SELECT id FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone() is not None:
            return
        
        # Crear local principal si no existe
        cursor.execute("SELECT id FROM locales WHERE nombre = 'Local Principal'")
        local = cursor.fetchone()
    
        if local is None:
            cursor.execute("INSERT INTO locales (nombre) VALUES ('Local Principal')")  # Faltaba )
            local_id = cursor.lastrowid
        else:
            local_id = local[0]
    
        # Crear usuario administrador
        cursor.execute(
            "INSERT INTO usuarios (username, password, nombre, rol, local_id) VALUES (?, ?, ?, ?, ?)",
            ('admin', 'admin123', 'Administrador', 'admin', local_id)
        )
        self.conn.commit()
    
    def insertar_licores_comerciales(self):
        licores = [
            # Whisky - Escocés
            ('Chivas Regal 12 años - 750ml', 'Chivas Regal', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Chivas Regal 12 años - 1L', 'Chivas Regal', 'Whisky', 'Botella 1L', 0.94, 1000, 650),
            ('Chivas Regal 18 años - 750ml', 'Chivas Regal', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Johnnie Walker Black Label - 750ml', 'Johnnie Walker', 'Whisky', 'Botella 750ml', 0.94, 750, 520),
            ('Johnnie Walker Red Label - 750ml', 'Johnnie Walker', 'Whisky', 'Botella 750ml', 0.94, 750, 520),
            ('Johnnie Walker Blue Label - 750ml', 'Johnnie Walker', 'Whisky', 'Botella 750ml', 0.94, 750, 520),
            ('Ballantine\'s Finest - 750ml', 'Ballantine\'s', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Ballantine\'s 12 años - 750ml', 'Ballantine\'s', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Jack Daniel\'s Old No.7 - 750ml', 'Jack Daniel\'s', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Jack Daniel\'s Honey - 750ml', 'Jack Daniel\'s', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Buchanan\'s 12 años - 750ml', 'Buchanan\'s', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Buchanan\'s 18 años - 750ml', 'Buchanan\'s', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
        
            # Whisky - Irlandés
            ('Jameson Original - 750ml', 'Jameson', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Jameson Black Barrel - 750ml', 'Jameson', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Tullamore D.E.W. - 750ml', 'Tullamore D.E.W.', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
        
            # Whisky - Americano (Bourbon)
            ('Jim Beam White Label - 750ml', 'Jim Beam', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Jim Beam Black Label - 750ml', 'Jim Beam', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Maker\'s Mark - 750ml', 'Maker\'s Mark', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
            ('Wild Turkey 101 - 750ml', 'Wild Turkey', 'Whisky', 'Botella 750ml', 0.94, 750, 500),
        
            # Vodka
            ('Absolut Vodka - 750ml', 'Absolut', 'Vodka', 'Botella 750ml', 0.95, 750, 500),
            ('Absolut Vodka - 1L', 'Absolut', 'Vodka', 'Botella 1L', 0.95, 1000, 650),
            ('Smirnoff Red Label - 750ml', 'Smirnoff', 'Vodka', 'Botella 750ml', 0.95, 750, 500),
            ('Smirnoff Black Label - 750ml', 'Smirnoff', 'Vodka', 'Botella 750ml', 0.95, 750, 500),
            ('Grey Goose - 750ml', 'Grey Goose', 'Vodka', 'Botella 750ml', 0.95, 750, 500),
            ('Belvedere - 750ml', 'Belvedere', 'Vodka', 'Botella 750ml', 0.95, 750, 500),
        
            # Ginebra (Gin)
            ('Bombay Sapphire - 750ml', 'Bombay Sapphire', 'Ginebra', 'Botella 750ml', 0.94, 750, 500),
            ('Bombay Sapphire - 1L', 'Bombay Sapphire', 'Ginebra', 'Botella 1L', 0.94, 1000, 650),
            ('Tanqueray London Dry - 750ml', 'Tanqueray', 'Ginebra', 'Botella 750ml', 0.94, 750, 500),
            ('Tanqueray No. Ten - 750ml', 'Tanqueray', 'Ginebra', 'Botella 750ml', 0.94, 750, 500),
            ('Beefeater London Dry - 750ml', 'Beefeater', 'Ginebra', 'Botella 750ml', 0.94, 750, 500),
            ('Hendrick\'s Gin - 750ml', 'Hendrick\'s', 'Ginebra', 'Botella 750ml', 0.94, 750, 500),
            ('Gordon\'s London Dry - 750ml', 'Gordon\'s', 'Ginebra', 'Botella 750ml', 0.94, 750, 500),
            ('Gordon\'s London Dry - 1L', 'Gordon\'s', 'Ginebra', 'Botella 1L', 0.94, 1000, 650),
        
            # Ron
            ('Bacardi Superior - 750ml', 'Bacardi', 'Ron', 'Botella 750ml', 0.95, 750, 500),
            ('Bacardi Gold - 750ml', 'Bacardi', 'Ron', 'Botella 750ml', 0.95, 750, 500),
            ('Bacardi 8 años - 750ml', 'Bacardi', 'Ron', 'Botella 750ml', 0.95, 750, 500),
            ('Havana Club Añejo 3 años - 750ml', 'Havana Club', 'Ron', 'Botella 750ml', 0.95, 750, 500),
            ('Havana Club 7 años - 750ml', 'Havana Club', 'Ron', 'Botella 750ml', 0.95, 750, 500),
            ('Captain Morgan Spiced Gold - 750ml', 'Captain Morgan', 'Ron', 'Botella 750ml', 0.95, 750, 500),
            ('Diplomático Reserva Exclusiva - 750ml', 'Diplomático', 'Ron', 'Botella 750ml', 0.95, 750, 500),
            ('Zacapa 23 - 750ml', 'Zacapa', 'Ron', 'Botella 750ml', 0.95, 750, 500),
        
            # Tequila
            ('Jose Cuervo Especial - 750ml', 'Jose Cuervo', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
            ('Jose Cuervo Tradicional - 750ml', 'Jose Cuervo', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
            ('Don Julio Blanco - 750ml', 'Don Julio', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
            ('Don Julio 70 - 750ml', 'Don Julio', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
            ('Don Julio 1942 - 750ml', 'Don Julio', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
            ('Patrón Silver - 750ml', 'Patrón', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
            ('Patrón Añejo - 750ml', 'Patrón', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
            ('Herradura Silver - 750ml', 'Herradura', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
            ('1800 Tequila Silver - 750ml', '1800 Tequila', 'Tequila', 'Botella 750ml', 0.95, 750, 500),
        
            # Coñac/Brandy
            ('Hennessy VS - 750ml', 'Hennessy', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Hennessy VSOP - 750ml', 'Hennessy', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Hennessy XO - 750ml', 'Hennessy', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Rémy Martin VSOP - 750ml', 'Rémy Martin', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Rémy Martin XO - 750ml', 'Rémy Martin', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Courvoisier VS - 750ml', 'Courvoisier', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Courvoisier VSOP - 750ml', 'Courvoisier', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Martell VS - 750ml', 'Martell', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Martell VSOP - 750ml', 'Martell', 'Coñac', 'Botella 750ml', 0.95, 750, 500),
            ('Fundador - 750ml', 'Fundador', 'Brandy', 'Botella 750ml', 0.95, 750, 500),
            ('Torres 10 - 750ml', 'Torres', 'Brandy', 'Botella 750ml', 0.95, 750, 500),
            ('Torres 15 - 750ml', 'Torres', 'Brandy', 'Botella 750ml', 0.95, 750, 500),
        
            # Vermouth
            ('Martini Rosso - 1L', 'Martini', 'Vermouth', 'Botella 1L', 1.04, 1000, 700),
            ('Martini Bianco - 1L', 'Martini', 'Vermouth', 'Botella 1L', 1.04, 1000, 700),
            ('Martini Extra Dry - 1L', 'Martini', 'Vermouth', 'Botella 1L', 1.04, 1000, 700),
            ('Martini Rosso - 750ml', 'Martini', 'Vermouth', 'Botella 750ml', 1.04, 750, 550),
            ('Martini Bianco - 750ml', 'Martini', 'Vermouth', 'Botella 750ml', 1.04, 750, 550),
            ('Martini Extra Dry - 750ml', 'Martini', 'Vermouth', 'Botella 750ml', 1.04, 750, 550),
            ('Cinzano Rosso - 1L', 'Cinzano', 'Vermouth', 'Botella 1L', 1.04, 1000, 700),
            ('Cinzano Bianco - 1L', 'Cinzano', 'Vermouth', 'Botella 1L', 1.04, 1000, 700),
            ('Cinzano Extra Dry - 1L', 'Cinzano', 'Vermouth', 'Botella 1L', 1.04, 1000, 700),
        
            # Licores y otros
            ('Baileys Original Irish Cream - 750ml', 'Baileys', 'Licor', 'Botella 750ml', 1.10, 750, 500),
            ('Jägermeister - 750ml', 'Jägermeister', 'Licor', 'Botella 750ml', 1.10, 750, 500),
            ('Kahlúa - 750ml', 'Kahlúa', 'Licor', 'Botella 750ml', 1.10, 750, 500),
            ('Amaretto Disaronno - 750ml', 'Disaronno', 'Licor', 'Botella 750ml', 1.10, 750, 500),
            ('Cointreau - 750ml', 'Cointreau', 'Licor', 'Botella 750ml', 1.10, 750, 500),
            ('Grand Marnier - 750ml', 'Grand Marnier', 'Licor', 'Botella 750ml', 1.10, 750, 500),
            ('Campari - 750ml', 'Campari', 'Bitter', 'Botella 750ml', 1.10, 750, 500),
            ('Aperol - 750ml', 'Aperol', 'Bitter', 'Botella 750ml', 1.10, 750, 500),
            ('Fernet Branca - 750ml', 'Fernet Branca', 'Bitter', 'Botella 750ml', 1.10, 750, 500),
        
            # Vinos y espumosos (principales)
            ('Moët & Chandon Imperial - 750ml', 'Moët & Chandon', 'Champagne', 'Botella 750ml', 0.99, 750, 1200),
            ('Veuve Clicquot Yellow Label - 750ml', 'Veuve Clicquot', 'Champagne', 'Botella 750ml', 0.99, 750, 1200),
            ('Dom Pérignon - 750ml', 'Dom Pérignon', 'Champagne', 'Botella 750ml', 0.99, 750, 1200),
            ('Freixenet Carta Nevada - 750ml', 'Freixenet', 'Cava', 'Botella 750ml', 0.99, 750, 1200),
            ('Codorníu Clásico - 750ml', 'Codorníu', 'Cava', 'Botella 750ml', 0.99, 750, 1200),
        
            # Presentaciones especiales
            ('Johnnie Walker Blue Label - 1L', 'Johnnie Walker', 'Whisky', 'Botella 1L', 0.94, 1000, 700),
            ('Jack Daniel\'s Old No.7 - 1L', 'Jack Daniel\'s', 'Whisky', 'Botella 1L', 0.94, 1000, 650),
            ('Absolut Vodka - 1.75L', 'Absolut', 'Vodka', 'Botella 1.75L', 0.95, 1750, 900),
            ('Smirnoff Red Label - 1L', 'Smirnoff', 'Vodka', 'Botella 1L', 0.95, 1000, 650),
            ('Bacardi Superior - 1L', 'Bacardi', 'Ron', 'Botella 1L', 0.95, 1000, 650),
            ('Jose Cuervo Especial - 1L', 'Jose Cuervo', 'Tequila', 'Botella 1L', 0.95, 1000, 650),
            ('Hennessy VS - 1L', 'Hennessy', 'Coñac', 'Botella 1L', 0.95, 1000, 650),
        ]

        cursor = self.conn.cursor()

        # Crear tabla si no existe (solo una vez)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS licores_comerciales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            marca TEXT NOT NULL,
            tipo TEXT NOT NULL,
            presentacion TEXT NOT NULL,
            densidad REAL NOT NULL,
            capacidad_ml REAL NOT NULL,
            peso_envase REAL NOT NULL,
            imagen TEXT,
            pais_origen TEXT,
            descripcion TEXT
        )
        ''')

        # Limpiar tabla existente antes de insertar nuevos datos
        cursor.execute('DELETE FROM licores_comerciales')

        # Insertar datos
        cursor.executemany('''
            INSERT INTO licores_comerciales 
            (nombre, marca, tipo, presentacion, densidad, capacidad_ml, peso_envase)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', licores)
        self.conn.commit()
    
    def execute_query(self, query, params=()):
        """Ejecuta una consulta y devuelve el número de filas afectadas y el último ID"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            self.conn.commit()
            last_id = cursor.lastrowid
            return cursor.rowcount, last_id
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error SQLite: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            raise e
        finally:
            cursor.close()
    
    def fetch_all(self, query, params=()):
        """Ejecuta una consulta y devuelve todos los resultados"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error SQLite en fetch_all: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            raise e
        finally:
            cursor.close()
    
    def fetch_one(self, query, params=()):
        """Ejecuta una consulta y devuelve un solo resultado"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Error SQLite en fetch_one: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            raise e
        finally:
            cursor.close()
    
    def create_tables(self):
        cursor = self.conn.cursor()
    
        # Lista de todas las tablas a crear
        tables = [
            # Tabla de configuración
            '''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
            ''',
        
            # Tabla de locales
            '''
            CREATE TABLE IF NOT EXISTS locales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                direccion TEXT,
                telefono TEXT,
                activo INTEGER DEFAULT 1
            )
            ''',
        
            # Tabla de usuarios
            '''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL,
                local_id INTEGER,
                activo INTEGER DEFAULT 1,
                FOREIGN KEY (local_id) REFERENCES locales (id)
            )
            ''',
        
            # Tabla de productos
            '''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                marca TEXT NOT NULL,
                tipo TEXT NOT NULL,
                presentacion TEXT,
                densidad REAL NOT NULL,
                capacidad_ml REAL NOT NULL,
                peso_envase REAL NOT NULL,
                activo INTEGER DEFAULT 1,
                botellas_completas INTEGER DEFAULT 0,
                minimo_inventario REAL DEFAULT 0.2,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (local_id) REFERENCES locales (id)
            )
            ''',
        
            # Tabla de movimientos
            '''
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                cantidad_ml REAL NOT NULL,
                peso_bruto REAL,
                notas TEXT,
                fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos (id),
                FOREIGN KEY (user_id) REFERENCES usuarios (id)
            )
            ''',
        
            # Tabla de licores comerciales
            '''
            CREATE TABLE IF NOT EXISTS licores_comerciales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                marca TEXT NOT NULL,
                tipo TEXT NOT NULL,
                presentacion TEXT NOT NULL,
                densidad REAL NOT NULL,
                capacidad_ml REAL NOT NULL,
                peso_envase REAL NOT NULL
            )
            '''
        ]
    
        # Crear todas las tablas
        for table_sql in tables:
            cursor.execute(table_sql)
    
        self.conn.commit()
    
        # Insertar datos iniciales si las tablas están vacías
        self.insertar_datos_iniciales()    
    
    def insertar_datos_iniciales(self):
        # Asegurarse de que existe la configuración mínima
        if not self.get_config("mes_verificado"):
            self.set_config("mes_verificado", "")
        self.create_admin_user()
        
        # Verificar si ya hay licores comerciales
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM licores_comerciales")
        count = cursor.fetchone()[0]
        if count == 0:
            self.insertar_licores_comerciales()
    
    def close(self):
        if hasattr(self, 'conn'):
            self.conn.close()

# Diccionario para almacenar conexiones por hilo
thread_local = threading.local()

@app.route('/api/debug-licores')
def api_debug_licores():
    """Endpoint de debug para ver licores comerciales"""
    try:
        db = get_db()
        licores = db.fetch_all("SELECT tipo, marca, nombre, presentacion FROM licores_comerciales ORDER BY tipo, marca")
        
        # Agrupar por tipo
        licores_por_tipo = {}
        for tipo, marca, nombre, presentacion in licores:
            if tipo not in licores_por_tipo:
                licores_por_tipo[tipo] = []
            licores_por_tipo[tipo].append(f"{marca} {nombre} - {presentacion}")
        
        return jsonify({
            'success': True,
            'total_licores': len(licores),
            'tipos': list(licores_por_tipo.keys()),
            'licores_por_tipo': licores_por_tipo
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

def get_db():
    """Obtiene o crea una conexión a la base de datos para el hilo actual"""
    if not hasattr(thread_local, 'db'):
        thread_local.db = LicorDB()
    return thread_local.db

@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except:
        try:
            img = Image.new('RGB', (16, 16), color='red')
            draw = ImageDraw.Draw(img)
            draw.rectangle([4, 4, 12, 12], fill='white')
            
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='ICO')
            img_buffer.seek(0)
            
            return send_file(img_buffer, mimetype='image/x-icon')
        except:
            return '', 204
    
@app.route('/debug-favicon')
def debug_favicon():
    import os
    favicon_path = os.path.join(app.static_folder, 'favicon.ico')
    return jsonify({
        'static_folder': app.static_folder,
        'favicon_path': favicon_path,
        'exists': os.path.exists(favicon_path),
        'size': os.path.getsize(favicon_path) if os.path.exists(favicon_path) else 0   
    })
# Manejo de errores
@app.errorhandler(404)
def not_found(error):
    try:
        return render_template('error.html', error=error), 404
    except:
        return jsonify({
            'success': False,
            'error': 'Página no encontrada',
            'message': 'La URL solicitada no existe en el servidor'
        }), 404

@app.errorhandler(500)
def internal_error(error):
    try:
        return render_template('error.html', error=error), 500
    except:
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor',
            'message': 'Ocurrió un error inesperado en el servidor'
        }), 500    

@app.route('/api/recreate-tables')
def recreate_tables():
    """Recrear tablas (solo para desarrollo)"""
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'})
    
    try:
        db = get_db()
        
        # Eliminar tablas existentes
        tables_to_drop = ['movimientos', 'productos', 'usuarios', 'locales', 'configuracion', 'licores_comerciales']
        
        for table in tables_to_drop:
            try:
                db.execute_query(f"DROP TABLE IF EXISTS {table}")
                print(f"Tabla {table} eliminada")
            except Exception as e:
                print(f"Error eliminando tabla {table}: {e}")
        
        # Crear tablas nuevamente
        db.create_tables()
        
        return jsonify({'success': True, 'message': 'Tablas recreadas correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500                    

@app.teardown_appcontext
def close_db(error):
    """Cierra la conexión a la base de datos al final de la request"""
    if hasattr(thread_local, 'db'):
        thread_local.db.close()
        del thread_local.db
        
# Agrega estas rutas después de las otras rutas en app.py

@app.route('/api/test-simple')
def test_simple():
    """Endpoint de prueba muy simple"""
    try:
        return jsonify({'success': True, 'message': 'Test simple funcionando'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug-db')
def debug_db():
    """Endpoint de diagnóstico para la base de datos"""
    try:
        db = get_db()
        
        # Verificar si la tabla productos existe
        tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
        print("Tablas en la base de datos:", tables)
        
        # Verificar estructura de la tabla productos
        columns = []
        if any('productos' in str(table) for table in tables):
            columns = db.fetch_all("PRAGMA table_info(productos)")
            print("Columnas de la tabla productos:", columns)
        
        return jsonify({
            'success': True,
            'tables': [table[0] for table in tables] if tables else [],
            'productos_columns': [{'name': col[1], 'type': col[2]} for col in columns] if columns else []
        })
        
    except Exception as e:
        print(f"Error en debug-db: {e}")
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/debug-paths')
def debug_paths():
    """Verificar rutas de archivos"""
    import os
    from pathlib import Path
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, 'templates')
    db_path = get_db_path()
    
    result = {
        'current_directory': current_dir,
        'templates_directory': templates_dir,
        'templates_exists': os.path.exists(templates_dir),
        'db_path': db_path,
        'db_exists': os.path.exists(db_path),
    }
    
    if os.path.exists(templates_dir):
        result['files_in_templates'] = os.listdir(templates_dir)
    
    return jsonify(result) 

@app.route('/api/fix-missing-column')
def fix_missing_column():
    """Endpoint temporal para agregar la columna faltante"""
    try:
        db = get_db()
        
        # Verificar si la columna presentacion ya existe
        columns = db.fetch_all("PRAGMA table_info(productos)")
        column_names = [col[1] for col in columns]
        
        if 'presentacion' not in column_names:
            # Agregar la columna faltante
            db.execute_query("ALTER TABLE productos ADD COLUMN presentacion TEXT")
            print("Columna 'presentacion' agregada a la tabla productos")
            return jsonify({
                'success': True, 
                'message': 'Columna presentacion agregada correctamente'
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'La columna presentacion ya existe'
            })
            
    except Exception as e:
        print(f"Error al agregar columna: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500       

# Funciones de utilidad
def verificar_bloqueo():
    db = get_db()
    hoy = datetime.now()
    mes_actual = hoy.strftime("%Y-%m")
    
    # Verificar si hay fecha de desbloqueo activa
    fecha_desbloqueo_str = db.get_config("fecha_desbloqueo")
    if fecha_desbloqueo_str:
        try:
            fecha_desbloqueo = datetime.strptime(fecha_desbloqueo_str, '%Y-%m-%d')
            if datetime.now() < fecha_desbloqueo:
                return False  # Aún está desbloqueada
        except:
            pass
            
    # Verificar sistema mensual
    mes_verificado = db.get_config("mes_verificado")
    if mes_verificado != mes_actual:
        clave_ingresada = db.get_config(f"clave_{mes_actual}")
        if not clave_ingresada:
            return True
            
    return False

def obtener_imagen_producto(marca, tipo):
    """Obtiene la URL de la imagen para un producto basado en marca y tipo"""
    # Lógica para generar o obtener imágenes de productos
    base_url = "https://via.placeholder.com/100x200/ECF0F1/2C3E50?text="
    
    if marca and len(marca) >= 2:
        return f"{base_url}{marca[:2].upper()}"
    elif tipo and len(tipo) >= 2:
        return f"{base_url}{tipo[:2].upper()}"
    else:
        return f"{base_url}🍷"
    
@app.route('/api/test-db')
def test_db():
    """Endpoint para probar la conexión a la base de datos"""
    try:
        db = get_db()
        
        # Probar una consulta simple
        result = db.fetch_one("SELECT COUNT(*) FROM productos")
        print(f"Test DB result: {result}")
        
        return jsonify({
            'success': True,
            'message': f'Conexión a BD exitosa. Productos encontrados: {result[0] if result else 0}'
        })
        
    except Exception as e:
        print(f"Error en test-db: {e}")
        import traceback
        return jsonify({
            'success': False,
            'message': f'Error de base de datos: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500    

# Y asegúrate de agregarla al contexto de Jinja2
@app.context_processor
def utility_processor():
    def obtener_imagen_licor(marca, tipo):
        """Obtiene la URL de la imagen para un licor"""
        base_url = "https://via.placeholder.com/100x200/ECF0F1/2C3E50?text="
    
        if marca and len(marca) >= 2:
            return f"{base_url}{marca[:2].upper()}"
        elif tipo and len(tipo) >= 2:
            return f"{base_url}{tipo[:2].upper()}"
        else:
            return f"{base_url}🍷"
    
    return dict(
        obtener_imagen_licor=obtener_imagen_licor,
        obtener_imagen_producto=obtener_imagen_producto
    )

def get_license_info():
    db = get_db()
    hoy = datetime.now()
    fecha_desbloqueo_str = db.get_config("fecha_desbloqueo")
    
    if fecha_desbloqueo_str:
        try:
            fecha_desbloqueo = datetime.strptime(fecha_desbloqueo_str, '%Y-%m-%d')
            dias_restantes = (fecha_desbloqueo - hoy).days
            mensaje = f"Días restantes: {dias_restantes} (hasta {fecha_desbloqueo.strftime('%d/%m/%Y')})"
            estado = 'success' if dias_restantes > 7 else 'warning' if dias_restantes > 0 else 'danger'
        except:
            mensaje = "Licencia vencida"
            estado = 'danger'
    else:
        # Sistema mensual por defecto
        ultimo_dia_mes = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        dias_restantes = (ultimo_dia_mes - hoy).days
        mensaje = f"Licencia vence en {dias_restantes} días ({ultimo_dia_mes.strftime('%d/%m/%Y')})"
        estado = 'success' if dias_restantes > 7 else 'warning' if dias_restantes > 0 else 'danger'
    
    return {'message': mensaje, 'status': estado, 'days_remaining': dias_restantes}

# Rutas de la aplicación
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Verificar si la aplicación está bloqueada
    if verificar_bloqueo():
        return redirect(url_for('desbloqueo'))
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        local_id = data.get('local_id', '')
        
        if not username or not password or not local_id:
            return jsonify({'success': False, 'message': 'Todos los campos son obligatorios'})
        
        try:
            local_id = int(local_id)
        except:
            return jsonify({'success': False, 'message': 'Seleccione un local válido'})
        
        db = get_db()
        
        # Verificar credenciales
        query = """
        SELECT id, nombre, rol 
        FROM usuarios 
        WHERE username = ? AND password = ? AND (local_id = ? OR rol = 'admin') AND activo = 1
        """
        usuario = db.fetch_one(query, (username, password, local_id))
        
        if usuario:
            user_id, nombre, rol = usuario
            
            # Guardar en sesión
            session['user_id'] = user_id
            session['user_name'] = nombre
            session['user_role'] = rol
            session['local_id'] = local_id
            
            # Obtener nombre del local
            local_nombre = db.fetch_one("SELECT nombre FROM locales WHERE id = ?", (local_id,))[0]
            session['local_nombre'] = local_nombre
            
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Credenciales incorrectas o no tiene acceso a este local'})
    
    # GET request - mostrar formulario de login
    db = get_db()
    locales = db.fetch_all("SELECT id, nombre FROM locales WHERE activo = 1 ORDER BY nombre")
    license_info = get_license_info()
    
    return render_template('login.html', 
                         locales=locales, 
                         version=VERSION,
                         license_info=license_info)

@app.route('/desbloqueo', methods=['GET', 'POST'])
def desbloqueo():
    if not verificar_bloqueo():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = request.get_json()
        clave = data.get('clave', '').strip()
        tiempo = data.get('tiempo', '1 mes')
        
        db = get_db()
        mes_actual = datetime.now().strftime("%Y-%m")
        
        # Obtener intentos fallidos
        intentos = int(db.get_config(f"intentos_{mes_actual}", "0"))
        
        if intentos >= 3:
            return jsonify({'success': False, 'message': 'Demasiados intentos fallidos. Contacte al administrador.'})
        
        if clave == CLAVE_MAESTRA:
            # Resetear intentos
            db.set_config(f"intentos_{mes_actual}", "0")
            
            # Determinar tiempo de desbloqueo
            if tiempo == '1 mes':
                dias = 30
            elif tiempo == '3 meses':
                dias = 90
            elif tiempo == '6 meses':
                dias = 180
            elif tiempo == '1 año':
                dias = 365
            else:
                dias = 30
                
            fecha_fin = datetime.now() + timedelta(days=dias)
            
            # Guardar configuración
            db.set_config("fecha_desbloqueo", fecha_fin.strftime('%Y-%m-%d'))
            db.set_config("dias_desbloqueo", str(dias))
            db.set_config("mes_verificado", mes_actual)
            db.set_config(f"clave_{mes_actual}", "1")
            
            return jsonify({'success': True, 'message': f'Aplicación desbloqueada por {tiempo}', 'redirect': url_for('login')})
        else:
            intentos += 1
            db.set_config(f"intentos_{mes_actual}", str(intentos))
            return jsonify({'success': False, 'message': f'Clave incorrecta. Intentos restantes: {3 - intentos}'})
    
    # GET request - mostrar formulario de desbloqueo
    hoy = datetime.now()
    ultimo_dia_mes = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    dias_restantes = (ultimo_dia_mes - hoy).days
    
    return render_template('desbloqueo.html', 
                         dias_restantes=dias_restantes,
                         fecha_vencimiento=ultimo_dia_mes.strftime('%d/%m/%Y'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    # Permitir cambiar de local si es admin
    local_id = session['local_id']
    if 'local_id' in request.args and session.get('user_role') == 'admin':
        try:
            new_local_id = int(request.args['local_id'])
            # Verificar que el local existe
            local = db.fetch_one("SELECT id, nombre FROM locales WHERE id = ?", (new_local_id,))
            if local:
                local_id = new_local_id
                session['local_id'] = local_id
                session['local_nombre'] = local[1]
        except:
            pass
    
    # Obtener todos los locales para el selector (solo admin)
    todos_locales = []
    if session.get('user_role') == 'admin':
        todos_locales = db.fetch_all("SELECT id, nombre, direccion, activo FROM locales ORDER BY nombre")
    
    # Obtener estadísticas principales
    query = """
    SELECT 
        COUNT(*) as total_productos,
        SUM(botellas_completas) as total_botellas,
        SUM(CASE WHEN (COALESCE((SELECT SUM(CASE WHEN tipo = 'entrada' THEN cantidad_ml ELSE -cantidad_ml END) 
            FROM movimientos WHERE producto_id = p.id), 0) / p.capacidad_ml * 100) < 20 THEN 1 ELSE 0 END) as bajos_inventario
    FROM productos p
    WHERE p.activo = 1 AND p.local_id = ?
    """
    
    stats = db.fetch_one(query, (session['local_id'],))
    
    if stats:
        total_productos, total_botellas, bajos_inventario = stats
    else:
        total_productos, total_botellas, bajos_inventario = 0, 0, 0
        
    # Obtener productos para el gráfico - CORREGIDO
    query = """
    SELECT 
        p.id, p.nombre, p.marca, p.tipo, p.botellas_completas, p.activo,
        -- Solo el contenido de la botella actual (sin sumar botellas completas)
        COALESCE((SELECT SUM(cantidad_ml) FROM movimientos WHERE producto_id = p.id), 0) as contenido_actual_ml,
        p.capacidad_ml,
        p.densidad,
        p.peso_envase
    FROM productos p
    WHERE p.local_id = ?
    ORDER BY p.nombre
    """

    productos_data = db.fetch_all(query, (session['local_id'],))
    
    # Preparar datos para el gráfico
    inventario_chart = []
    for prod in productos_data:
        id_prod, nombre, marca, tipo, botellas, activo, contenido_actual_ml, capacidad, densidad, peso_envase = prod
    
        # Asegurar que el contenido actual no sea negativo
        contenido_actual_ml = max(contenido_actual_ml, 0)
    
        # Calcular porcentaje de la botella actual (nunca más del 100%)
        porcentaje = min((contenido_actual_ml / capacidad) * 100, 100) if capacidad > 0 else 0
    
        inventario_chart.append({
            'nombre': f"{nombre} {marca}",
            'porcentaje': porcentaje,
            'estado': 'bajo' if porcentaje < 20 else 'ok' if porcentaje >= 50 else 'medio'
        })
    
    # Obtener productos bajos de inventario - CORREGIDO
    query = """
    SELECT 
        p.nombre, p.marca, p.tipo,
        (p.botellas_completas * p.capacidad_ml) + 
        COALESCE((SELECT SUM(cantidad_ml) FROM movimientos WHERE producto_id = p.id), 0) as total_ml,
        p.capacidad_ml,
        ((p.botellas_completas * p.capacidad_ml) + 
        COALESCE((SELECT SUM(cantidad_ml) FROM movimientos WHERE producto_id = p.id), 0)) / p.capacidad_ml * 100 as porcentaje
    FROM productos p
    WHERE p.activo = 1 AND p.local_id = ? 
    AND (((p.botellas_completas * p.capacidad_ml) + 
        COALESCE((SELECT SUM(cantidad_ml) FROM movimientos WHERE producto_id = p.id), 0)) / p.capacidad_ml * 100) < 20
    AND (((p.botellas_completas * p.capacidad_ml) + 
        COALESCE((SELECT SUM(cantidad_ml) FROM movimientos WHERE producto_id = p.id), 0)) / p.capacidad_ml * 100) >= 0
    ORDER BY porcentaje ASC
    LIMIT 10
    """
    
    productos_bajos = db.fetch_all(query, (session['local_id'],))
    # Obtener últimos movimientos
    query = """
    SELECT 
        m.fecha, p.nombre, m.tipo, m.cantidad_ml, m.notas, u.nombre
    FROM movimientos m
    JOIN productos p ON m.producto_id = p.id
    JOIN usuarios u ON m.user_id = u.id
    WHERE p.local_id = ?
    ORDER BY m.fecha DESC
    LIMIT 10
    """
    
    movimientos_recientes = db.fetch_all(query, (session['local_id'],))
    
    # Generar gráfico de niveles de inventario
    img_buf = generar_grafico_inventario()
    plot_url = base64.b64encode(img_buf.getvalue()).decode('utf8')
    
    # NUEVO: Estadísticas de módulos adicionales
    # Contar movimientos recientes (últimos 7 días)
    movimientos_7dias = db.fetch_one("""
        SELECT COUNT(*) FROM movimientos m
        JOIN productos p ON m.producto_id = p.id
        WHERE p.local_id = ? AND DATE(m.fecha) >= DATE('now', '-7 days')
    """, (session['local_id'],))
    movimientos_7dias = movimientos_7dias[0] if movimientos_7dias else 0
    
    # Contar usuarios activos (solo para admin)
    if session['user_role'] == 'admin':
        total_usuarios_result = db.fetch_one("SELECT COUNT(*) FROM usuarios WHERE activo = 1", ())
        total_usuarios = total_usuarios_result[0] if total_usuarios_result else 0
        
        total_locales_result = db.fetch_one("SELECT COUNT(*) FROM locales WHERE activo = 1", ())
        total_locales = total_locales_result[0] if total_locales_result else 0
    else:
        total_usuarios = 0
        total_locales = 0
    
    # Productos que necesitan atención (inventario bajo)
    productos_bajos_count_result = db.fetch_one("""
        SELECT COUNT(*) FROM productos p
        WHERE p.local_id = ? AND p.activo = 1
        AND (COALESCE((SELECT SUM(CASE WHEN tipo = 'entrada' THEN cantidad_ml ELSE -cantidad_ml END) 
            FROM movimientos WHERE producto_id = p.id), 0) / p.capacidad_ml * 100) < 20
    """, (session['local_id'],))
    productos_bajos_count = productos_bajos_count_result[0] if productos_bajos_count_result else 0
    
    # Movimientos de hoy
    movimientos_hoy_result = db.fetch_one("""
        SELECT COUNT(*) FROM movimientos m
        JOIN productos p ON m.producto_id = p.id
        WHERE p.local_id = ? AND DATE(m.fecha) = DATE('now')
    """, (session['local_id'],))
    movimientos_hoy = movimientos_hoy_result[0] if movimientos_hoy_result else 0
    
    return render_template('dashboard.html', 
                         user_name=session['user_name'],
                         user_role=session['user_role'],
                         local_nombre=session['local_nombre'],
                         total_productos=total_productos,
                         total_botellas=total_botellas,
                         bajos_inventario=bajos_inventario,
                         productos_bajos=productos_bajos,
                         movimientos_recientes=movimientos_recientes,
                         plot_url=plot_url,
                         inventario_chart=inventario_chart,  # Asegúrate de incluir esto
                         total_usuarios=total_usuarios,
                         total_locales=total_locales,
                         movimientos_7dias=movimientos_7dias,
                         productos_bajos_count=productos_bajos_count,
                         movimientos_hoy=movimientos_hoy,
                         todos_locales=todos_locales)
    
@app.route('/api/actualizar-dashboard')
def api_actualizar_dashboard():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    
    # Obtener datos para el gráfico (misma lógica que en dashboard)
    query = """
    SELECT 
        p.nombre, 
        COALESCE((SELECT SUM(CASE WHEN tipo = 'entrada' THEN cantidad_ml ELSE -cantidad_ml END) 
              FROM movimientos WHERE producto_id = p.id), 0) as total_ml,
        p.capacidad_ml
    FROM productos p
    WHERE p.activo = 1 AND p.local_id = ?
    ORDER BY p.nombre
    """
    
    datos = db.fetch_all(query, (session['local_id'],))
    
    # Preparar datos para el gráfico
    inventario_chart = []
    for nombre, total_ml, capacidad in datos:
        porcentaje = (total_ml / capacidad) * 100 if capacidad > 0 else 0
        inventario_chart.append({
            'nombre': nombre,
            'porcentaje': porcentaje
        })
    
    return jsonify({
        'success': True,
        'inventario_chart': inventario_chart
    })    
    
def generar_grafico_inventario():
    db = get_db()
    
    # Obtener datos para el gráfico - CORREGIDO
    query = """
    SELECT 
        p.nombre, 
        -- Solo el contenido de la botella actual
        COALESCE((SELECT SUM(cantidad_ml) FROM movimientos WHERE producto_id = p.id), 0) as contenido_actual_ml,
        p.capacidad_ml,
        p.peso_envase
    FROM productos p
    WHERE p.activo = 1 AND p.local_id = ?
    ORDER BY p.nombre
    """
    
    datos = db.fetch_all(query, (session['local_id'],))
    
    # Crear gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    
    nombres = []
    porcentajes = []
    colores = []
    
    for nombre, contenido_actual_ml, capacidad, peso_envase in datos:
        # Asegurar que el contenido actual no sea negativo
        contenido_actual_ml = max(contenido_actual_ml, 0)
        
        # Calcular porcentaje (nunca más del 100%)
        if capacidad > 0:
            porcentaje = min((contenido_actual_ml / capacidad) * 100, 100)
        else:
            porcentaje = 0
        
        nombres.append(nombre)
        porcentajes.append(porcentaje)
        
        # Determinar color según porcentaje
        if porcentaje == 0:
            colores.append('#777777')  # Gris para vacío
        elif porcentaje < 20:
            colores.append('red')
        elif porcentaje < 50:
            colores.append('orange')
        else:
            colores.append('green')
    
    if nombres:
        y_pos = range(len(nombres))
        bars = ax.barh(y_pos, porcentajes, color=colores)
        
        # Añadir etiquetas
        for i, (bar, porcentaje) in enumerate(zip(bars, porcentajes)):
            if porcentaje == 0:
                ax.text(1, i, "VACÍO", color='white', va='center', ha='left', fontweight='bold')
            elif porcentaje > 0:
                ax.text(porcentaje + 1, i, f"{porcentaje:.1f}%", color='black', va='center')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(nombres)
        ax.set_xlabel('Porcentaje de capacidad (%)')
        ax.set_title('Niveles de Inventario')
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.set_xlim(0, 110)  # Espacio extra para etiquetas
    
    # Guardar gráfico en buffer
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight')
    img_buf.seek(0)
    plt.close(fig)
    
    return img_buf

def obtener_imagen_licor(marca, tipo):
    """Obtiene la URL de la imagen para un licor"""
    # Lógica para generar o obtener imágenes de licores
    # Puedes usar una API externa o imágenes locales
    base_url = "https://via.placeholder.com/100x200/ECF0F1/2C3E50?text="
    
    if marca and len(marca) >= 2:
        return f"{base_url}{marca[:2].upper()}"
    elif tipo and len(tipo) >= 2:
        return f"{base_url}{tipo[:2].upper()}"
    else:
        return f"{base_url}🍷"
    
@app.context_processor
def utility_processor():
    def obtener_imagen_licor(marca, tipo):
        # misma lógica de arriba
        base_url = "https://via.placeholder.com/100x200/ECF0F1/2C3E50?text="
        if marca and len(marca) >= 2:
            return f"{base_url}{marca[:2].upper()}"
        elif tipo and len(tipo) >= 2:
            return f"{base_url}{tipo[:2].upper()}"
        else:
            return f"{base_url}🍷"
    
    return dict(obtener_imagen_licor=obtener_imagen_licor)    

@app.route('/inventario')
def inventario():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    # Obtener todos los productos con su inventario - CORREGIDO
    query = """
    SELECT 
        p.id, p.nombre, p.marca, p.tipo, p.botellas_completas, p.activo,
        -- Solo el contenido de la botella actual (sin sumar botellas completas)
        COALESCE((SELECT SUM(cantidad_ml) FROM movimientos WHERE producto_id = p.id), 0) as contenido_actual_ml,
        p.capacidad_ml,
        p.densidad,
        p.peso_envase
    FROM productos p
    WHERE p.local_id = ?
    ORDER BY p.nombre
    """
    
    productos = db.fetch_all(query, (session['local_id'],))
    
    # Calcular valores derivados - CORREGIDO
    inventario = []
    for prod in productos:
        id_prod, nombre, marca, tipo, botellas, activo, contenido_actual_ml, capacidad, densidad, peso_envase = prod
        
        # Asegurar que el contenido actual no sea negativo
        contenido_actual_ml = max(contenido_actual_ml, 0)
        
        # Calcular el inventario total (botellas completas + contenido actual)
        inventario_total_ml = (botellas * capacidad) + contenido_actual_ml
        
        # Calcular porcentaje de la botella actual (nunca más del 100%)
        porcentaje_botella_actual = min((contenido_actual_ml / capacidad) * 100, 100) if capacidad > 0 else 0
        
        # Calcular porcentaje total del inventario
        porcentaje_total = (inventario_total_ml / capacidad) * 100 if capacidad > 0 else 0
        
        total_oz = inventario_total_ml * ML_A_OZ
        peso_licor = inventario_total_ml * densidad
        
        inventario.append({
            'id': id_prod,
            'nombre': nombre,
            'marca': marca,
            'tipo': tipo,
            'botellas': botellas,
            'activo': activo,
            'total_ml': inventario_total_ml,
            'contenido_actual_ml': contenido_actual_ml,  # Para referencia
            'total_oz': total_oz,
            'peso_licor': peso_licor,
            'porcentaje': porcentaje_botella_actual,  # Porcentaje de la botella actual
            'porcentaje_total': porcentaje_total,     # Porcentaje total del inventario
            'capacidad': capacidad,
            'densidad': densidad,
            'peso_envase': peso_envase,
            'estado': 'bajo' if porcentaje_botella_actual < 20 else 'ok'
        })
    
    return render_template('inventario.html',
                         user_name=session['user_name'],
                         user_role=session['user_role'],
                         local_nombre=session['local_nombre'],
                         inventario=inventario,
                         VERSION=VERSION,
                         now=datetime.now())

@app.route('/api/registrar-peso', methods=['POST'])
def api_registrar_peso():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    data = request.get_json()
    producto_id = data.get('producto_id')
    peso_total = data.get('peso_total')
    
    try:
        peso_total = float(peso_total)
    except ValueError:
        return jsonify({'success': False, 'message': 'Peso inválido'})
    
    # Obtener datos del producto
    query = "SELECT id, densidad, peso_envase, capacidad_ml FROM productos WHERE id = ?"
    producto = db.fetch_one(query, (producto_id,))
    
    if not producto:
        return jsonify({'success': False, 'message': 'Producto no encontrado'})
    
    id_prod, densidad, peso_envase, capacidad = producto
    
    # Manejo especial para peso vacío
    if abs(peso_total - peso_envase) < 0.1:  # Considerar igual si la diferencia es mínima
        volumen_ml = 0.0
        tipo = "ajuste"
        
        # Eliminar todos los movimientos anteriores para este producto
        delete_query = "DELETE FROM movimientos WHERE producto_id = ?"
        db.execute_query(delete_query, (id_prod,))
    else:
        peso_licor = peso_total - peso_envase
        volumen_ml = peso_licor / densidad
        
        # Determinar tipo de movimiento
        ultimo_query = "SELECT cantidad_ml FROM movimientos WHERE producto_id = ? ORDER BY fecha DESC LIMIT 1"
        ultimo_ml = db.fetch_one(ultimo_query, (id_prod,))
        
        if ultimo_ml:
            diferencia = volumen_ml - ultimo_ml[0]
            tipo = "entrada" if diferencia > 0 else "salida"
        else:
            tipo = "entrada"
    
    # CORRECCIÓN: Asegurar que las salidas sean negativas
    if tipo == "salida" and volumen_ml > 0:
        volumen_ml = -volumen_ml
    
    # Insertar movimiento
    query = """
    INSERT INTO movimientos (producto_id, user_id, tipo, cantidad_ml, peso_bruto, notas)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    notas = f"Registro manual. Peso total: {peso_total}g. Volumen calculado: {abs(volumen_ml):.1f}ml"
    db.execute_query(query, (id_prod, session['user_id'], tipo, volumen_ml, peso_total, notas))
    
    return jsonify({'success': True, 'message': 'Peso registrado correctamente'})

@app.route('/api/agregar-botella', methods=['POST'])
def api_agregar_botella():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    data = request.get_json()
    producto_id = data.get('producto_id')
    
    # Obtener datos del producto
    query = "SELECT id, capacidad_ml, botellas_completas FROM productos WHERE id = ?"
    producto = db.fetch_one(query, (producto_id,))
    
    if not producto:
        return jsonify({'success': False, 'message': 'Producto no encontrado'})
    
    id_prod, capacidad, botellas = producto
    
    # Actualizar contador de botellas
    query = "UPDATE productos SET botellas_completas = botellas_completas + 1 WHERE id = ?"
    db.execute_query(query, (id_prod,))
    
    # Registrar movimiento de entrada
    query = """
    INSERT INTO movimientos (producto_id, user_id, tipo, cantidad_ml, notas)
    VALUES (?, ?, ?, ?, ?)
    """
    db.execute_query(query, (id_prod, session['user_id'], 'entrada', capacidad, 'Botella completa agregada'))
    
    return jsonify({'success': True, 'message': 'Botella agregada correctamente'})

@app.route('/api/quitar-botella', methods=['POST'])
def api_quitar_botella():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    data = request.get_json()
    producto_id = data.get('producto_id')
    
    # Obtener datos del producto
    query = "SELECT id, capacidad_ml, botellas_completas FROM productos WHERE id = ?"
    producto = db.fetch_one(query, (producto_id,))
    
    if not producto:
        return jsonify({'success': False, 'message': 'Producto no encontrado'})
    
    id_prod, capacidad, botellas = producto
    
    if botellas <= 0:
        return jsonify({'success': False, 'message': 'No hay botellas completas para quitar'})
    
    # Actualizar contador de botellas
    query = "UPDATE productos SET botellas_completas = botellas_completas - 1 WHERE id = ?"
    db.execute_query(query, (id_prod,))
    
    # CORRECCIÓN: Registrar movimiento de salida como valor negativo
    query = """
    INSERT INTO movimientos (producto_id, user_id, tipo, cantidad_ml, notas)
    VALUES (?, ?, ?, ?, ?)
    """
    db.execute_query(query, (id_prod, session['user_id'], 'salida', -capacidad, 'Botella completa retirada'))
    
    return jsonify({'success': True, 'message': 'Botella retirada correctamente'})

@app.route('/productos')
def productos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    # Obtener producto para edición si se solicita
    editar_id = request.args.get('editar')
    editar_producto = None
    if editar_id:
        try:
            editar_producto = db.fetch_one(
                "SELECT id, nombre, marca, tipo, densidad, capacidad_ml, peso_envase, minimo_inventario, activo FROM productos WHERE id = ? AND local_id = ?", 
                (editar_id, session['local_id'])
            )
            if editar_producto:
                # Convertir a dict para fácil acceso en template
                editar_producto = {
                    'id': editar_producto[0],
                    'nombre': editar_producto[1],
                    'marca': editar_producto[2],
                    'tipo': editar_producto[3],
                    'densidad': editar_producto[4],
                    'capacidad_ml': editar_producto[5],
                    'peso_envase': editar_producto[6],
                    'minimo_inventario': editar_producto[7],
                    'activo': editar_producto[8]
                }
        except Exception as e:
            print(f"Error al obtener producto para edición: {e}")
            editar_producto = None
    
    # Obtener todos los productos
    try:
        productos = db.fetch_all(
            "SELECT id, nombre, marca, tipo, densidad, capacidad_ml, peso_envase, botellas_completas, minimo_inventario, activo FROM productos WHERE local_id = ? ORDER BY nombre",
            (session['local_id'],)
        )
    except Exception as e:
        print(f"Error al obtener productos: {e}")
        productos = []
    
    # Obtener tipos y marcas para los combobox
    try:
        tipos = db.fetch_all("SELECT DISTINCT tipo FROM licores_comerciales ORDER BY tipo") or []
        marcas = db.fetch_all("SELECT DISTINCT marca FROM licores_comerciales ORDER BY marca") or []
        presentaciones = db.fetch_all("SELECT DISTINCT presentacion FROM licores_comerciales ORDER BY presentacion") or []
    except Exception as e:
        print(f"Error al obtener datos de licores comerciales: {e}")
        tipos = []
        marcas = []
        presentaciones = []
    
    return render_template('productos.html',
                         user_name=session['user_name'],
                         user_role=session['user_role'],
                         local_nombre=session['local_nombre'],
                         productos=productos,
                         tipos=[t[0] for t in tipos],
                         marcas=[m[0] for m in marcas],
                         presentaciones=[p[0] for p in presentaciones],
                         editar_producto=editar_producto,
                         VERSION=VERSION,
                         now=datetime.now())
    
@app.route('/api/obtener-licor', methods=['POST'])
def api_obtener_licor():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    data = request.get_json()
    tipo = data.get('tipo')
    marca = data.get('marca')
    presentacion = data.get('presentacion')
    
    if not tipo or not marca or not presentacion:
        return jsonify({'success': False, 'message': 'Faltan parámetros'})
    
    # Obtener datos del licor comercial
    query = """
    SELECT nombre, densidad, capacidad_ml, peso_envase 
    FROM licores_comerciales 
    WHERE tipo = ? AND marca = ? AND presentacion = ?
    LIMIT 1
    """
    
    licor = db.fetch_one(query, (tipo, marca, presentacion))
    
    if licor:
        nombre, densidad, capacidad, peso_envase = licor
        return jsonify({
            'success': True,
            'nombre': nombre,
            'densidad': densidad,
            'capacidad': capacidad,
            'peso_envase': peso_envase
        })
    else:
        return jsonify({'success': False, 'message': 'Licor no encontrado'})

@app.route('/api/licores-comerciales')
def api_licores_comerciales():
    """Obtiene todos los licores comerciales para los selectores"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    try:
        db = get_db()
        licores = db.fetch_all("""
            SELECT nombre, marca, tipo, presentacion, densidad, capacidad_ml, peso_envase
            FROM licores_comerciales 
            ORDER BY tipo, marca, nombre, presentacion
        """)
        
        if licores is None:
            licores = []
        
        # Formatear resultados
        resultados = []
        for licor in licores:
            resultados.append({
                'nombre': licor[0],
                'marca': licor[1],
                'tipo': licor[2],
                'presentacion': licor[3],
                'densidad': float(licor[4]),
                'capacidad_ml': float(licor[5]),
                'peso_envase': float(licor[6])
            })
        
        return jsonify({'success': True, 'licores': resultados})
        
    except Exception as e:
        print(f"Error al obtener licores comerciales: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al cargar datos de licores'})

@app.route('/api/guardar-producto', methods=['POST'])
def api_guardar_producto():
    print("=== INICIO api_guardar-producto ===")
    
    try:
        # Verificar autenticación
        if 'user_id' not in session:
            print("ERROR: Usuario no autenticado")
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        print(f"Usuario autenticado: {session['user_id']}")
        
        # Verificar que es JSON
        if not request.is_json:
            print("ERROR: No es JSON")
            return jsonify({'success': False, 'message': 'Content-Type debe ser application/json'}), 400
        
        data = request.get_json()
        print(f"Datos recibidos: {data}")
        
        # Validar datos básicos
        required_fields = ['nombre', 'marca', 'tipo']
        for field in required_fields:
            if not data.get(field):
                print(f"ERROR: Campo {field} faltante")
                return jsonify({'success': False, 'message': f'Campo {field} es obligatorio'}), 400
        
        # Obtener la instancia de la base de datos
        db = get_db()
        print("Conexión a BD establecida")
        
        # Verificar que el local_id existe en sesión
        local_id = session.get('local_id')
        if not local_id:
            print("ERROR: local_id no encontrado en sesión")
            return jsonify({'success': False, 'message': 'Error de configuración de local'}), 500
        
        print(f"Local ID: {local_id}")
        
        # Construir query básica
        if data.get('producto_id'):
            # Actualizar producto existente
            query = """
            UPDATE productos SET 
                nombre=?, marca=?, tipo=?, presentacion=?, densidad=?, 
                capacidad_ml=?, peso_envase=?, minimo_inventario=?, activo=?
            WHERE id=? AND local_id=?
            """
            params = (
                data['nombre'], data['marca'], data['tipo'], 
                data.get('presentacion', ''), float(data.get('densidad', 0.95)),
                float(data.get('capacidad_ml', 750)), float(data.get('peso_envase', 500)),
                float(data.get('minimo_inventario', 0.2)), int(data.get('activo', 1)),
                data['producto_id'], local_id
            )
            
            print(f"Ejecutando UPDATE: {query}")
            print(f"Parámetros: {params}")
            
            # Ejecutar la consulta
            row_count = db.execute_query(query, params)
            print(f"Producto actualizado. Filas afectadas: {row_count}")
            
            message = 'Producto actualizado correctamente'
        else:
            # Nuevo producto
            query = """
            INSERT INTO productos 
            (local_id, nombre, marca, tipo, presentacion, densidad, capacidad_ml, peso_envase, minimo_inventario, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                local_id, data['nombre'], data['marca'], data['tipo'],
                data.get('presentacion', ''), float(data.get('densidad', 0.95)),
                float(data.get('capacidad_ml', 750)), float(data.get('peso_envase', 500)),
                float(data.get('minimo_inventario', 0.2)), int(data.get('activo', 1))
            )
            
            print(f"Ejecutando INSERT: {query}")
            print(f"Parámetros: {params}")
            
            # Ejecutar la consulta
            row_count = db.execute_query(query, params)
            print(f"Producto creado. Filas afectadas: {row_count}")
            
            message = 'Producto creado correctamente'
        
        return jsonify({
            'success': True, 
            'message': message
        })
        
    except Exception as e:
        print(f"ERROR en api_guardar_producto: {str(e)}")
        import traceback
        error_traceback = traceback.format_exc()
        print(f"TRACEBACK COMPLETO:\n{error_traceback}")
        
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor',
            'error': str(e),
            'traceback': error_traceback
        }), 500

@app.route('/movimientos')
def movimientos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    # Obtener movimientos
    query = """
    SELECT 
        m.fecha, p.nombre, m.tipo, m.cantidad_ml, m.notas, u.nombre
    FROM movimientos m
    JOIN productos p ON m.producto_id = p.id
    JOIN usuarios u ON m.user_id = u.id
    WHERE p.local_id = ?
    ORDER BY m.fecha DESC
    LIMIT 100
    """
    
    movimientos = db.fetch_all(query, (session['local_id'],))
    
    # Obtener productos para el filtro
    productos = db.fetch_all("SELECT id, nombre FROM productos WHERE local_id = ? ORDER BY nombre", (session['local_id'],))
    
    return render_template('movimientos.html',
                         user_name=session['user_name'],
                         user_role=session['user_role'],
                         local_nombre=session['local_nombre'],
                         movimientos=movimientos,
                         productos=productos)

@app.route('/api/filtrar-movimientos', methods=['POST'])
def api_filtrar_movimientos():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    data = request.get_json()
    producto_id = data.get('producto_id')
    tipo = data.get('tipo')
    fecha_desde = data.get('fecha_desde')
    fecha_hasta = data.get('fecha_hasta')
    
    query = """
    SELECT 
        m.fecha, p.nombre, m.tipo, m.cantidad_ml, m.notas, u.nombre
    FROM movimientos m
    JOIN productos p ON m.producto_id = p.id
    JOIN usuarios u ON m.user_id = u.id
    WHERE p.local_id = ?
    """
    
    params = [session['local_id']]
    
    if producto_id and producto_id != 'todos':
        query += " AND p.id = ?"
        params.append(producto_id)
        
    if tipo and tipo != 'todos':
        query += " AND m.tipo = ?"
        params.append(tipo)
        
    if fecha_desde:
        query += " AND DATE(m.fecha) >= ?"
        params.append(fecha_desde)
        
    if fecha_hasta:
        query += " AND DATE(m.fecha) <= ?"
        params.append(fecha_hasta)
    
    query += " ORDER BY m.fecha DESC"
    
    movimientos = db.fetch_all(query, params)
    
    # Formatear resultados
    resultados = []
    for mov in movimientos:
        resultados.append({
            'fecha': mov[0],
            'producto': mov[1],
            'tipo': mov[2],
            'cantidad_ml': mov[3],
            'notas': mov[4],
            'usuario': mov[5]
        })
    
    return jsonify({'success': True, 'movimientos': resultados})

@app.route('/api/exportar-movimientos', methods=['POST'])
def api_exportar_movimientos():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    data = request.get_json()
    producto_id = data.get('producto_id')
    tipo = data.get('tipo')
    fecha_desde = data.get('fecha_desde')
    fecha_hasta = data.get('fecha_hasta')
    
    query = """
    SELECT 
        m.fecha, p.nombre, m.tipo, m.cantidad_ml, m.peso_bruto, m.notas, u.nombre
    FROM movimientos m
    JOIN productos p ON m.producto_id = p.id
    JOIN usuarios u ON m.user_id = u.id
    WHERE p.local_id = ?
    """
    
    params = [session['local_id']]
    
    if producto_id and producto_id != 'todos':
        query += " AND p.id = ?"
        params.append(producto_id)
        
    if tipo and tipo != 'todos':
        query += " AND m.tipo = ?"
        params.append(tipo)
        
    if fecha_desde:
        query += " AND DATE(m.fecha) >= ?"
        params.append(fecha_desde)
        
    if fecha_hasta:
        query += " AND DATE(m.fecha) <= ?"
        params.append(fecha_hasta)
    
    query += " ORDER BY m.fecha DESC"
    
    movimientos = db.fetch_all(query, params)
    
    # Crear DataFrame
    df = pd.DataFrame(movimientos, columns=['Fecha', 'Producto', 'Tipo', 'Cantidad (ml)', 'Peso (g)', 'Notas', 'Usuario'])
    
    # Crear archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Movimientos', index=False)
    
    output.seek(0)
    
    # Devolver archivo
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'movimientos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/registrar-volumen', methods=['POST'])
def api_registrar_volumen():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    data = request.get_json()
    producto_id = data.get('producto_id')
    volumen_ml = data.get('volumen_ml')
    tipo_movimiento = data.get('tipo')  # 'entrada' o 'salida'
    notas = data.get('notas', '')
    
    try:
        volumen_ml = float(volumen_ml)
    except ValueError:
        return jsonify({'success': False, 'message': 'Volumen inválido'})
    
    if tipo_movimiento not in ['entrada', 'salida']:
        return jsonify({'success': False, 'message': 'Tipo de movimiento inválido'})
    
    # Obtener datos del producto
    query = "SELECT id, densidad, peso_envase, capacidad_ml FROM productos WHERE id = ?"
    producto = db.fetch_one(query, (producto_id,))
    
    if not producto:
        return jsonify({'success': False, 'message': 'Producto no encontrado'})
    
    id_prod, densidad, peso_envase, capacidad = producto
    
    # Calcular el peso del líquido
    peso_licor = volumen_ml * densidad
    
    # Calcular el peso total (envase + líquido)
    peso_total = peso_envase + peso_licor
    
    # CORRECCIÓN: Las salidas deben ser valores negativos
    if tipo_movimiento == 'salida':
        cantidad_ml = -abs(volumen_ml)  # Salidas son siempre negativas
    else:
        cantidad_ml = abs(volumen_ml)   # Entradas son siempre positivas
    
    # Insertar movimiento
    query = """
    INSERT INTO movimientos (producto_id, user_id, tipo, cantidad_ml, peso_bruto, notas)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    
    # Notas más descriptivas
    if not notas:
        notas = f"Registro manual. {tipo_movimiento} de {volumen_ml}ml. Peso calculado: {peso_total:.1f}g"
    else:
        notas = f"{notas} ({tipo_movimiento} de {volumen_ml}ml)"
    
    db.execute_query(query, (id_prod, session['user_id'], tipo_movimiento, cantidad_ml, peso_total, notas))
    
    return jsonify({
        'success': True, 
        'message': 'Movimiento registrado correctamente',
        'peso_calculado': peso_total,
        'peso_licor': peso_licor
    })
    
@app.route('/api/obtener-producto/<int:producto_id>')
def api_obtener_producto(producto_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    
    # Obtener producto específico
    query = """
    SELECT id, nombre, marca, tipo, densidad, capacidad_ml, peso_envase, 
           minimo_inventario, activo, botellas_completas
    FROM productos 
    WHERE id = ? AND local_id = ?
    """
    
    producto = db.fetch_one(query, (producto_id, session['local_id']))
    
    if producto:
        return jsonify({
            'success': True,
            'producto': {
                'id': producto[0],
                'nombre': producto[1],
                'marca': producto[2],
                'tipo': producto[3],
                'densidad': producto[4],
                'capacidad_ml': producto[5],
                'peso_envase': producto[6],
                'minimo_inventario': producto[7],
                'activo': producto[8],
                'botellas_completas': producto[9]
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Producto no encontrado'})    
    
@app.route('/api/inventario-actual/<int:producto_id>')
def api_inventario_actual(producto_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    
    # Obtener inventario actual y datos del producto
    query = """
    SELECT 
        p.nombre, p.marca, p.densidad, p.peso_envase, p.capacidad_ml,
        COALESCE((SELECT SUM(cantidad_ml) FROM movimientos WHERE producto_id = p.id), 0) as inventario_actual
    FROM productos p
    WHERE p.id = ? AND p.local_id = ?
    """
    
    producto = db.fetch_one(query, (producto_id, session['local_id']))
    
    if not producto:
        return jsonify({'success': False, 'message': 'Producto no encontrado'})
    
    nombre, marca, densidad, peso_envase, capacidad, inventario_actual = producto
    
    # Calcular pesos
    peso_licor_actual = inventario_actual * densidad
    peso_total_actual = peso_envase + peso_licor_actual
    porcentaje_actual = (inventario_actual / capacidad) * 100 if capacidad > 0 else 0
    
    return jsonify({
        'success': True,
        'producto': {
            'nombre': nombre,
            'marca': marca,
            'inventario_actual_ml': inventario_actual,
            'inventario_actual_oz': inventario_actual * ML_A_OZ,
            'peso_licor_actual': peso_licor_actual,
            'peso_total_actual': peso_total_actual,
            'porcentaje_actual': porcentaje_actual,
            'capacidad_ml': capacidad,
            'densidad': densidad,
            'peso_envase': peso_envase
        }
    })    

@app.route('/reportes')
def reportes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    # Obtener productos para el reporte
    productos = db.fetch_all("SELECT id, nombre FROM productos WHERE local_id = ? ORDER BY nombre", (session['local_id'],))
    
    return render_template('reportes.html',
                         user_name=session['user_name'],
                         user_role=session['user_role'],
                         local_nombre=session['local_nombre'],
                         productos=productos)

@app.route('/api/generar-reporte', methods=['POST'])
def api_generar_reporte():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    db = get_db()
    data = request.get_json()
    producto_id = data.get('producto_id')
    periodo = data.get('periodo', '30')
    
    try:
        periodo = int(periodo)
    except:
        periodo = 30
    
    # Determinar fecha de inicio
    fecha_inicio = (datetime.now() - timedelta(days=periodo)).strftime('%Y-%m-%d')
    
    # Obtener movimientos del período
    query = """
    SELECT 
        DATE(m.fecha) as dia, 
        SUM(CASE WHEN m.tipo = 'entrada' THEN m.cantidad_ml ELSE 0 END) as entradas,
        SUM(CASE WHEN m.tipo = 'salida' THEN m.cantidad_ml ELSE 0 END) as salidas
    FROM movimientos m
    JOIN productos p ON m.producto_id = p.id
    WHERE p.id = ? AND p.local_id = ? AND DATE(m.fecha) >= ?
    GROUP BY DATE(m.fecha)
    ORDER BY DATE(m.fecha)
    """
    
    movimientos = db.fetch_all(query, (producto_id, session['local_id'], fecha_inicio))
    
    # Preparar datos para el gráfico
    fechas = [datetime.strptime(m[0], '%Y-%m-%d').strftime('%d/%m') for m in movimientos]
    entradas = [m[1] for m in movimientos]
    salidas = [m[2] for m in movimientos]
    consumos_netos = [e - s for e, s in zip(entradas, salidas)]
    
    # Obtener nombre del producto
    producto_nombre = db.fetch_one("SELECT nombre FROM productos WHERE id = ?", (producto_id,))[0]
    
    return jsonify({
        'success': True,
        'fechas': fechas,
        'entradas': entradas,
        'salidas': salidas,
        'consumos_netos': consumos_netos,
        'producto_nombre': producto_nombre,
        'periodo': periodo
    })

@app.route('/admin/locales')
def admin_locales():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('dashboard'))
    
    db = get_db()
    
    # Obtener todos los locales
    locales = db.fetch_all("SELECT id, nombre, direccion, telefono, activo FROM locales ORDER BY nombre")
    
    return render_template('admin_locales.html',
                         user_name=session['user_name'],
                         user_role=session['user_role'],
                         local_nombre=session['local_nombre'],
                         locales=locales)

@app.route('/api/guardar-local', methods=['POST'])
def api_guardar_local():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'})
    
    db = get_db()
    data = request.get_json()
    local_id = data.get('local_id')
    nombre = data.get('nombre', '').strip()
    direccion = data.get('direccion', '').strip()
    telefono = data.get('telefono', '').strip()
    activo = data.get('activo', False)
    
    if not nombre:
        return jsonify({'success': False, 'message': 'El nombre del local es obligatorio'})
    
    activo = 1 if activo else 0
    
    # Verificar si es un local nuevo o existente
    if local_id:  # Editar local existente
        query = """
        UPDATE locales 
        SET nombre = ?, direccion = ?, telefono = ?, activo = ?
        WHERE id = ?
        """
        db.execute_query(query, (nombre, direccion, telefono, activo, local_id))
        
        message = "Local actualizado correctamente"
    else:  # Nuevo local
        query = """
        INSERT INTO locales (nombre, direccion, telefono, activo)
        VALUES (?, ?, ?, ?)
        """
        db.execute_query(query, (nombre, direccion, telefono, activo))
        
        message = "Local agregado correctamente"
    
    return jsonify({'success': True, 'message': message})

@app.route('/api/eliminar-local', methods=['POST'])
def api_eliminar_local():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'})
    
    db = get_db()
    data = request.get_json()
    local_id = data.get('local_id')
    
    if not local_id:
        return jsonify({'success': False, 'message': 'ID de local no proporcionado'})
    
    # Verificar si hay productos asociados
    productos = db.fetch_one("SELECT COUNT(*) FROM productos WHERE local_id = ?", (local_id,))[0]
    if productos > 0:
        return jsonify({'success': False, 'message': 'No se puede eliminar un local que tiene productos asociados'})
    
    # Verificar si hay usuarios asociados
    usuarios = db.fetch_one("SELECT COUNT(*) FROM usuarios WHERE local_id = ?", (local_id,))[0]
    if usuarios > 0:
        return jsonify({'success': False, 'message': 'No se puede eliminar un local que tiene usuarios asociados'})
    
    # Eliminar el local
    db.execute_query("DELETE FROM locales WHERE id = ?", (local_id,))
    
    return jsonify({'success': True, 'message': 'Local eliminado correctamente'})

@app.route('/admin/usuarios')
def admin_usuarios():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return redirect(url_for('dashboard'))
    
    db = get_db()
    
    # Obtener todos los usuarios con información de local
    usuarios = db.fetch_all("""
    SELECT u.id, u.username, u.password, u.nombre, u.rol, u.activo, l.nombre 
    FROM usuarios u
    LEFT JOIN locales l ON u.local_id = l.id
    ORDER BY u.nombre
    """)
    
    # Obtener locales para el formulario
    locales = db.fetch_all("SELECT id, nombre FROM locales ORDER BY nombre")
    
    return render_template('admin_usuarios.html',
                         user_name=session['user_name'],
                         user_role=session['user_role'],
                         local_nombre=session['local_nombre'],
                         usuarios=usuarios,
                         locales=locales)

@app.route('/api/guardar-usuario', methods=['POST'])
def api_guardar_usuario():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'})
    
    db = get_db()
    data = request.get_json()
    usuario_id = data.get('usuario_id')
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    nombre = data.get('nombre', '').strip()
    rol = data.get('rol', '').strip()
    local_id = data.get('local_id')
    activo = data.get('activo', False)
    
    if not username or not password or not nombre or not rol:
        return jsonify({'success': False, 'message': 'Usuario, contraseña, nombre y rol son campos obligatorios'})
    
    activo = 1 if activo else 0
    
    # Verificar si es un usuario nuevo o existente
    if usuario_id:  # Editar usuario existente
        query = """
        UPDATE usuarios 
        SET username = ?, password = ?, nombre = ?, rol = ?, local_id = ?, activo = ?
        WHERE id = ?
        """
        db.execute_query(query, (username, password, nombre, rol, local_id, activo, usuario_id))
        
        message = "Usuario actualizado correctamente"
    else:  # Nuevo usuario
        # Verificar si el username ya existe
        existe = db.fetch_one("SELECT id FROM usuarios WHERE username = ?", (username,))
        if existe:
            return jsonify({'success': False, 'message': 'El nombre de usuario ya existe'})
        
        query = """
        INSERT INTO usuarios (username, password, nombre, rol, local_id, activo)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        db.execute_query(query, (username, password, nombre, rol, local_id, activo))
        
        message = "Usuario agregado correctamente"
    
    return jsonify({'success': True, 'message': message})

@app.route('/api/eliminar-usuario', methods=['POST'])
def api_eliminar_usuario():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'})
    
    db = get_db()
    data = request.get_json()
    usuario_id = data.get('usuario_id')
    
    if not usuario_id:
        return jsonify({'success': False, 'message': 'ID de usuario no proporcionado'})
    
    # No permitir eliminar al propio usuario
    if usuario_id == session['user_id']:
        return jsonify({'success': False, 'message': 'No puede eliminarse a sí mismo'})
    
    # Eliminar movimientos asociados primero
    db.execute_query("DELETE FROM movimientos WHERE user_id = ?", (usuario_id,))
    
    # Luego eliminar el usuario
    db.execute_query("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    
    return jsonify({'success': True, 'message': 'Usuario eliminado correctamente'})

@app.route('/api/eliminar-producto', methods=['POST'])
def api_eliminar_producto():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'})
    
    try:
        db = get_db()
        data = request.get_json()
        producto_id = data.get('producto_id')
        
        if not producto_id:
            return jsonify({'success': False, 'message': 'ID de producto no proporcionado'})
        
        # Verificar que el producto pertenece al local del usuario
        producto = db.fetch_one("SELECT id FROM productos WHERE id = ? AND local_id = ?", 
                               (producto_id, session['local_id']))
        
        if not producto:
            return jsonify({'success': False, 'message': 'Producto no encontrado o no tiene permisos'})
        
        # Eliminar movimientos asociados primero
        db.execute_query("DELETE FROM movimientos WHERE producto_id = ?", (producto_id,))
        
        # Eliminar el producto
        db.execute_query("DELETE FROM productos WHERE id = ?", (producto_id,))
        
        return jsonify({'success': True, 'message': 'Producto eliminado correctamente'})
        
    except Exception as e:
        print(f"Error al eliminar producto: {e}")
        return jsonify({'success': False, 'message': f'Error al eliminar producto: {str(e)}'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/license-info')
def api_license_info():
    return jsonify(get_license_info())

# Manejo de errores
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error=error), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error=error), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
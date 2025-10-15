import os
from flask import Flask
from config import Config
# Se importa login_manager desde las extensiones
from .extensions import db, migrate, mail, login_manager 
# Se importa el modelo Usuario
from .models import Cliente, Asistencia, ServicioCliente, Producto, Usuario, Venta, CuadreCaja

# --- Importación de todos los Blueprints de los módulos ---
from .modules.asistencias.routes import asistencias_bp
from .modules.productos.routes import productos_bp
from .modules.ventas.routes import ventas_bp 
from .modules.servicios.routes import servicios_bp
from .modules.pagos.routes import pagos_bp
from .modules.clientes.routes import clientes_bp
from .modules.estadisticas.routes import estadisticas_bp
from .modules.autenticacion.routes import autenticacion_bp 
from .modules.cuadres.routes import cuadres_bp 
from .modules.mensajes_masivos.routes import mensajes_bp 

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Inicialización de extensiones ---
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.init_app(app)

    # --- Configuración de Flask-Login ---
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    login_manager.login_view = 'autenticacion.login'
    login_manager.login_message = "Por favor, inicie sesión para acceder a esta página."
    login_manager.login_message_category = "info"

    # --- Registro de Blueprints ---
    from .main_routes import main_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(clientes_bp, url_prefix='/clientes')
    app.register_blueprint(servicios_bp, url_prefix='/servicios')
    app.register_blueprint(pagos_bp, url_prefix='/pagos')
    app.register_blueprint(asistencias_bp, url_prefix='/asistencias')
    app.register_blueprint(productos_bp, url_prefix='/productos')
    app.register_blueprint(ventas_bp, url_prefix='/ventas')
    app.register_blueprint(estadisticas_bp, url_prefix='/estadisticas')
    app.register_blueprint(autenticacion_bp)
    app.register_blueprint(cuadres_bp, url_prefix='/cuadres')
    app.register_blueprint(mensajes_bp, url_prefix='/mensajes')

    with app.app_context():
        upload_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)

    return app  

# En GYM_App/app.py

import os
from flask import Flask
from config import Config
from GYM_App.extensions import db, migrate, mail 
from GYM_App.models import Cliente, Asistencia, ServicioCliente, Producto, Usuario, Venta, CuadreCaja # Importa todos los modelos necesarios
from flask_login import LoginManager

# --- 1. Importaciones de los Blueprints (Verificar esta sección) ---
from GYM_App.modules.asistencias.routes import asistencias_bp
from GYM_App.modules.productos.routes import productos_bp
from GYM_App.modules.ventas.routes import ventas_bp 
from GYM_App.modules.servicios.routes import servicios_bp
from GYM_App.modules.pagos.routes import pagos_bp
from GYM_App.modules.clientes.routes import clientes_bp
from GYM_App.modules.autenticacion.routes import autenticacion_bp
from GYM_App.main_routes import main_bp
from GYM_App.modules.estadisticas.routes import estadisticas_bp
from GYM_App.modules.cuadres.routes import cuadres_bp # <-- ¡LA IMPORTACIÓN CRUCIAL!

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicialización de extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Inicialización de Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'autenticacion.login'

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # --- 2. Registro de Blueprints (Verificar esta sección) ---
    app.register_blueprint(main_bp)
    app.register_blueprint(autenticacion_bp, url_prefix='/auth')
    app.register_blueprint(clientes_bp, url_prefix='/clientes')
    app.register_blueprint(servicios_bp, url_prefix='/servicios')
    app.register_blueprint(pagos_bp, url_prefix='/pagos')
    app.register_blueprint(asistencias_bp, url_prefix='/asistencias')
    app.register_blueprint(productos_bp, url_prefix='/productos')
    app.register_blueprint(ventas_bp, url_prefix='/ventas')
    app.register_blueprint(estadisticas_bp, url_prefix='/estadisticas')
    app.register_blueprint(cuadres_bp, url_prefix='/cuadres') # <-- ¡EL REGISTRO CRUCIAL!

    # Asegura que la carpeta de subidas existe antes de la primera solicitud
    with app.app_context():
        upload_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)

    return app
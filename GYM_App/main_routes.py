from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
# Importa los modelos que necesitarás
from GYM_App.models import Producto 

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required # Protege la ruta principal
def index():
    # Esta es tu página principal para usuarios logueados
    return redirect(url_for('estadisticas.dashboard'))

@main_bp.route('/productos-publicos')
def ver_productos():
    """
    Vista pública para mostrar todos los productos. No requiere inicio de sesión.
    """
    # Si el usuario ya está logueado, llévalo a la vista de admin de productos
    if current_user.is_authenticated:
        return redirect(url_for('productos.listar_productos'))
        
    productos = Producto.query.all()
    # Reutilizamos la plantilla login.html, indicando que queremos ver los productos
    return render_template('autenticacion/login.html', page='productos', productos=productos)

@main_bp.route('/asistencia-publica')
def tomar_asistencia():
    """
    Vista pública para que los clientes registren su asistencia. No requiere inicio de sesión.
    """
    # Si el usuario ya está logueado, llévalo a la vista de admin de asistencias
    if current_user.is_authenticated:
        return redirect(url_for('asistencias.index'))

    # Reutilizamos la plantilla login.html, indicando que queremos ver la asistencia
    return render_template('autenticacion/login.html', page='asistencia')
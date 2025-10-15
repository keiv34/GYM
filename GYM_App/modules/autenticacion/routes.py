from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from GYM_App.models import Usuario, Rol
from GYM_App.extensions import db

autenticacion_bp = Blueprint('autenticacion', __name__, url_prefix='/auth', template_folder='templates')

@autenticacion_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()
        
        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    
    # Le decimos a la plantilla que muestre la sección 'login'
    return render_template('autenticacion/login.html', page='login')

# --- El resto de tus rutas de autenticación (registro, logout) se mantienen igual ---

@autenticacion_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    roles = Rol.query.all()
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario')
        password = request.form.get('password')
        rol_nombre = request.form.get('rol')

        if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
            flash('El nombre de usuario ya existe.', 'danger')
            return render_template('autenticacion/registro.html', roles=roles) 
        
        rol = Rol.query.filter_by(nombre=rol_nombre).first()
        if not rol:
            flash('El rol especificado no existe.', 'danger')
            return render_template('autenticacion/registro.html', roles=roles)

        hashed_password = generate_password_hash(password)
        nuevo_usuario = Usuario(nombre_usuario=nombre_usuario, password_hash=hashed_password, rol=rol)
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('autenticacion.login'))

    return render_template('autenticacion/registro.html', roles=roles)

@autenticacion_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('autenticacion.login'))
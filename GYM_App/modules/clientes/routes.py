from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, flash
from GYM_App.extensions import db
from GYM_App.models import Cliente, ServicioCliente, Servicio
from datetime import datetime
import os
import secrets
from PIL import Image
from werkzeug.utils import secure_filename

clientes_bp = Blueprint("clientes", __name__, template_folder="../../templates/clientes")

# La carpeta de subida se unifica aquí
UPLOAD_FOLDER = 'uploads/fotos_perfil'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    picture_path = os.path.join(current_app.root_path, 'static', UPLOAD_FOLDER, picture_fn)

    output_size = (200, 200)
    try:
        i = Image.open(form_picture)
        i.thumbnail(output_size)
        i.save(picture_path)
    except Exception as e:
        flash(f"Error al procesar la imagen: {str(e)}", "danger")
        return None

    return os.path.join(UPLOAD_FOLDER, picture_fn).replace('\\', '/')

def delete_picture(picture_filename):
    picture_path = os.path.join(current_app.root_path, 'static', picture_filename)
    if os.path.exists(picture_path):
        os.remove(picture_path)

@clientes_bp.route("/")
def listar_clientes():
    return render_template("listado.html")

@clientes_bp.route("/api/clientes")
def get_clientes_api():
    clientes = Cliente.query.all()
    clientes_data = []
    for cliente in clientes:
        servicio_activo = ServicioCliente.query.filter_by(cliente_id=cliente.id, estatus=True).first()
        estatus = 'Activo' if servicio_activo else 'Inactivo'

        clientes_data.append({
            'id': cliente.id,
            'nombre': cliente.nombre,
            'email': cliente.email,
            'estatus': estatus,
            'url_ver': url_for('clientes.get_cliente_info', id=cliente.id),
            'url_editar': url_for('clientes.editar_cliente', id=cliente.id),
            'url_eliminar': url_for('clientes.eliminar_cliente', id=cliente.id)
        })
    return jsonify(clientes_data)

# ... (importaciones y demás código)

@clientes_bp.route("/crear", methods=["GET", "POST"])
def crear_cliente():
    success_message = None
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        direccion = request.form["direccion"]
        telefono = request.form["telefono"]
        telefono_emergencia = request.form["telefono_emergencia"]
        edad = request.form["edad"]
        sexo = request.form.get("sexo")  # Obtener el valor del campo 'sexo'

        # Validaciones del lado del servidor
        if not all([nombre, email, telefono, sexo]): # Añadimos 'sexo' a la validación
            flash("Por favor, complete los campos obligatorios: Nombre, Email, Teléfono y Sexo.", "danger")
            return render_template("crear.html", cliente=request.form)

        if Cliente.query.filter_by(email=email).first():
            flash("Ya existe un cliente con este correo electrónico. Por favor, use uno diferente.", "danger")
            return render_template("crear.html", cliente=request.form)

        foto_perfil_url = None
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    foto_perfil_url = save_picture(file)
                    if not foto_perfil_url:
                        return render_template("crear.html", cliente=request.form)
                else:
                    flash("Formato de imagen no permitido.", "danger")
                    return render_template("crear.html", cliente=request.form)

        try:
            edad_int = int(edad) if edad else None
        except ValueError:
            flash("La edad debe ser un número válido.", "danger")
            return render_template("crear.html", cliente=request.form)

        nuevo_cliente = Cliente(
            nombre=nombre,
            email=email,
            direccion=direccion,
            telefono=telefono,
            telefono_emergencia=telefono_emergencia,
            edad=edad_int,
            sexo=sexo, # Aquí se asigna el valor del sexo al objeto Cliente
            foto_perfil=foto_perfil_url
        )
        
        try:
            db.session.add(nuevo_cliente)
            db.session.commit()
            success_message = "Cliente creado con éxito!"
            return render_template("crear.html", success_message=success_message)
        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar el cliente: {str(e)}", "danger")
            return render_template("crear.html", cliente=request.form)
    
    return render_template("crear.html")

@clientes_bp.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    if request.method == "POST":
        # Validaciones del lado del servidor
        if not all([request.form.get("nombre"), request.form.get("email"), request.form.get("telefono")]):
            flash("Por favor, complete los campos obligatorios: Nombre, Email y Teléfono.", "danger")
            return redirect(url_for('clientes.editar_cliente', id=id))
        
        # Validar si el nuevo email ya existe en otro cliente
        if request.form["email"] != cliente.email and Cliente.query.filter_by(email=request.form["email"]).first():
            flash("Ya existe otro cliente con este correo electrónico. Por favor, use uno diferente.", "danger")
            return redirect(url_for('clientes.editar_cliente', id=id))

        cliente.nombre = request.form["nombre"]
        cliente.email = request.form["email"]
        cliente.direccion = request.form["direccion"]
        cliente.telefono = request.form["telefono"]
        cliente.telefono_emergencia = request.form["telefono_emergencia"]
        
        try:
            cliente.edad = int(request.form["edad"]) if request.form["edad"] else None
        except ValueError:
            flash("La edad debe ser un número válido.", "danger")
            return redirect(url_for('clientes.editar_cliente', id=id))
            
        if 'foto_perfil' in request.files and request.files['foto_perfil'].filename != '':
            file = request.files['foto_perfil']
            if file and allowed_file(file.filename):
                if cliente.foto_perfil:
                    delete_picture(cliente.foto_perfil)
                
                foto_perfil_url = save_picture(file)
                if not foto_perfil_url:
                    return redirect(url_for('clientes.editar_cliente', id=id))

                cliente.foto_perfil = foto_perfil_url
            else:
                flash("Formato de imagen no permitido.", "danger")
                return redirect(url_for('clientes.editar_cliente', id=id))
        
        try:
            db.session.commit()
            flash("Cliente actualizado con éxito!", "success")
            return redirect(url_for("clientes.listar_clientes"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el cliente: {str(e)}", "danger")
            return redirect(url_for('clientes.editar_cliente', id=id))
    
    return render_template("editar.html", cliente=cliente)

@clientes_bp.route("/eliminar/<int:id>", methods=["POST"])
def eliminar_cliente(id):
    try:
        cliente = Cliente.query.get_or_404(id)
        if cliente.foto_perfil:
            delete_picture(cliente.foto_perfil)
            
        db.session.delete(cliente)
        db.session.commit()
        flash("Cliente eliminado con éxito!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el cliente: {str(e)}", "danger")
    
    return redirect(url_for("clientes.listar_clientes"))

@clientes_bp.route("/api/info/<int:id>")
def get_cliente_info(id):
    cliente = Cliente.query.get_or_404(id)
    
    servicio_actual = ServicioCliente.query.filter(
        ServicioCliente.cliente_id == cliente.id,
        ServicioCliente.estatus == True
    ).first()

    historial_servicios = ServicioCliente.query.filter_by(cliente_id=cliente.id).order_by(ServicioCliente.fecha_inicio.desc()).all()
    
    historial_list = []
    for servicio_cliente in historial_servicios:
        historial_list.append({
            'nombre': servicio_cliente.servicio.nombre,
            'fecha_inicio': servicio_cliente.fecha_inicio.strftime("%Y-%m-%d"),
            'fecha_fin': servicio_cliente.fecha_fin.strftime("%Y-%m-%d") if servicio_cliente.fecha_fin else 'No aplica',
            'estatus': 'Activo' if servicio_cliente.estatus else 'Inactivo'
        })
    
    servicio_activo_data = {}
    if servicio_actual:
        servicio_activo_data = {
            'nombre_servicio': servicio_actual.servicio.nombre,
            'tipo_servicio': servicio_actual.servicio.tipo_servicio,
            'fecha_fin': servicio_actual.fecha_fin.strftime("%Y-%m-%d") if servicio_actual.fecha_fin else 'No aplica'
        }

    cliente_data = {
        'id': cliente.id,
        'nombre': cliente.nombre,
        'email': cliente.email,
        'direccion': cliente.direccion,
        'telefono': cliente.telefono,
        'telefono_emergencia': cliente.telefono_emergencia,
        'edad': cliente.edad,
        'foto_perfil': url_for('static', filename=cliente.foto_perfil) if cliente.foto_perfil else None,
        'fecha_registro': cliente.fecha_registro.strftime("%Y-%m-%d %H:%M:%S") if cliente.fecha_registro else 'No disponible',
        'estatus': 'Activo' if servicio_actual else 'Inactivo',
        'servicio_actual': servicio_activo_data,
        'historial': historial_list
    }
    
    return jsonify(cliente_data)

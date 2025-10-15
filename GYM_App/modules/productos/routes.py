import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from GYM_App.extensions import db
from GYM_App.models import Producto

productos_bp = Blueprint("productos", __name__, template_folder="../../templates/productos")

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@productos_bp.route("/")
def listar_productos():
    productos = Producto.query.all()
    return render_template("listar_productos.html", productos=productos)

@productos_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo_producto():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        precio = request.form.get("precio")
        stock = request.form.get("stock")
        imagen = request.files.get("imagen")

        if not nombre or not precio or not stock:
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("productos.nuevo_producto"))

        try:
            precio = float(precio)
            stock = int(stock)
            if precio <= 0 or stock < 0:
                flash("Precio y stock deben ser valores positivos.", "danger")
                return redirect(url_for("productos.nuevo_producto"))
        except (ValueError, TypeError):
            flash("Precio y stock deben ser números válidos.", "danger")
            return redirect(url_for("productos.nuevo_producto"))

        producto_existente = Producto.query.filter_by(nombre=nombre).first()
        if producto_existente:
            flash(f"El producto '{nombre}' ya existe.", "danger")
            return redirect(url_for("productos.nuevo_producto"))

        imagen_url = None
        if imagen and imagen.filename != '':
            if not allowed_file(imagen.filename):
                flash("Formato de imagen no permitido. Usa .png, .jpg, .jpeg o .gif.", "danger")
                return redirect(url_for("productos.nuevo_producto"))
            
            filename = secure_filename(imagen.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'productos')
            
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            filepath = os.path.join(upload_folder, filename)
            imagen.save(filepath)
            imagen_url = os.path.join('uploads', 'productos', filename).replace('\\', '/')
            
        nuevo_producto = Producto(nombre=nombre, precio=precio, stock=stock, imagen_url=imagen_url)
        db.session.add(nuevo_producto)
        db.session.commit()

        flash("Producto agregado exitosamente.", "success")
        return redirect(url_for("productos.listar_productos"))

    return render_template("nuevo_producto.html")

# NUEVA RUTA: Editar un producto
@productos_bp.route("/editar/<int:producto_id>", methods=["GET", "POST"])
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    if request.method == "POST":
        nombre = request.form.get("nombre")
        precio = request.form.get("precio")
        stock = request.form.get("stock")
        imagen = request.files.get("imagen")

        if not nombre or not precio or not stock:
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("productos.editar_producto", producto_id=producto_id))

        try:
            precio = float(precio)
            stock = int(stock)
            if precio <= 0 or stock < 0:
                flash("Precio y stock deben ser valores positivos.", "danger")
                return redirect(url_for("productos.editar_producto", producto_id=producto_id))
        except (ValueError, TypeError):
            flash("Precio y stock deben ser números válidos.", "danger")
            return redirect(url_for("productos.editar_producto", producto_id=producto_id))

        # Verificar si el nuevo nombre ya existe en otro producto
        producto_existente = Producto.query.filter_by(nombre=nombre).first()
        if producto_existente and producto_existente.id != producto.id:
            flash(f"El nombre de producto '{nombre}' ya existe.", "danger")
            return redirect(url_for("productos.editar_producto", producto_id=producto_id))

        producto.nombre = nombre
        producto.precio = precio
        producto.stock = stock

        if imagen and imagen.filename != '':
            if not allowed_file(imagen.filename):
                flash("Formato de imagen no permitido.", "danger")
                return redirect(url_for("productos.editar_producto", producto_id=producto_id))
            
            if producto.imagen_url:
                old_filepath = os.path.join(current_app.root_path, 'static', producto.imagen_url)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)

            filename = secure_filename(imagen.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'productos')
            filepath = os.path.join(upload_folder, filename)
            imagen.save(filepath)
            producto.imagen_url = os.path.join('uploads', 'productos', filename).replace('\\', '/')
            
        db.session.commit()
        flash("Producto actualizado exitosamente.", "success")
        return redirect(url_for("productos.listar_productos"))

    return render_template("editar_producto.html", producto=producto)

@productos_bp.route("/eliminar/<int:producto_id>", methods=["POST"])
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    # 1. Eliminar la imagen asociada si existe
    if producto.imagen_url:
        filepath = os.path.join(current_app.root_path, 'static', producto.imagen_url)
        if os.path.exists(filepath):
            os.remove(filepath)

    # 2. Eliminar el producto. 
    # La base de datos ahora establecerá a NULL las referencias en DetalleVenta.
    db.session.delete(producto)
    
    try:
        db.session.commit()
        flash("Producto eliminado exitosamente. El historial de ventas (detalle_venta) fue conservado.", "success")
    except Exception as e:
        db.session.rollback()
        # Esto atraparía cualquier otro error de BD no cubierto por la FK.
        flash(f"Error al eliminar el producto. Consulta los logs para más detalles.", "danger")
    
    return redirect(url_for("productos.listar_productos"))
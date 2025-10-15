# GYM_App/models.py
from GYM_App.extensions import db
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import func 
from sqlalchemy.types import Numeric # Asegúrate de importar Numeric

# ---- ROLES Y USUARIOS ----
class Rol(db.Model):
    __tablename__ = 'rol'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    usuarios = db.relationship('Usuario', backref='rol', lazy=True)


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario' # <-- La tabla real es 'usuario' (singular)
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)

    def get_id(self):
        return str(self.id)


class Cliente(db.Model):
    __tablename__ = 'cliente'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    telefono_emergencia = db.Column(db.String(20))
    edad = db.Column(db.Integer)
    sexo = db.Column(db.String(20))
    foto_perfil = db.Column(db.String(255), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación sin cascada, pero habilitando passive_deletes
    servicios = db.relationship(
        'ServicioCliente',
        backref='cliente',
        lazy=True,
        passive_deletes=True
    )
    asistencias = db.relationship(
        'Asistencia',
        backref='cliente',
        lazy=True,
        passive_deletes=True
    )


# ---- SERVICIOS ----
class Servicio(db.Model):
    __tablename__ = 'servicio'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_servicio = db.Column(db.String(50), nullable=False)
    costo = db.Column(db.Float, nullable=False)
    servicios_cliente = db.relationship('ServicioCliente', backref='servicio', lazy=True)


# ---- SERVICIOS DEL CLIENTE (Membresías) ----
class ServicioCliente(db.Model):
    __tablename__ = 'servicio_cliente'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('cliente.id', ondelete="SET NULL"),
        nullable=True
    )
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicio.id'), nullable=False)
    fecha_inicio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    estatus = db.Column(db.Boolean, default=True)
    costo_servicio = db.Column(db.Float, nullable=False)
    costo_inscripcion = db.Column(db.Float, default=0)
    # 🚨 NUEVO CAMPO: Método de pago para el Cuadre
    metodo_pago = db.Column(db.String(50), nullable=False, default='Efectivo')


# ---- ASISTENCIAS ----
class Asistencia(db.Model):
    __tablename__ = 'asistencia'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('cliente.id', ondelete="SET NULL"),
        nullable=True
    )
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


# ---- PRODUCTOS ----
class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen_url = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Producto {self.nombre}>'


# ---- VENTAS ----
class Venta(db.Model):
    __tablename__ = 'venta'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total = db.Column(db.Float, nullable=False)
    # 🚨 NUEVO CAMPO: Método de pago para el Cuadre
    metodo_pago = db.Column(db.String(50), nullable=False, default='Efectivo')
    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True, cascade="all, delete-orphan")


# ---- DETALLES DE VENTA ----

class DetalleVenta(db.Model):
    __tablename__ = 'detalle_venta'
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    
    producto_id = db.Column(
        db.Integer, 
        db.ForeignKey('productos.id', ondelete='SET NULL'), 
        nullable=True 
    )
    
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)

    producto = db.relationship('Producto', backref=db.backref('detalles_venta', lazy=True))

# ---- CUADRES DE CAJA (NUEVA CLASE) ----
class CuadreCaja(db.Model):
    __tablename__ = 'cuadre_caja'
    id = db.Column(db.Integer, primary_key=True)

    # El campo datetime.utcnow lo usaremos para marcar el fin del periodo
    fecha_cierre = db.Column(db.DateTime, default=datetime.utcnow) 
    
    # Montos reportados por el sistema para el periodo:
    ventas_efectivo_sistema = db.Column(db.Numeric(10, 2), nullable=False)
    ventas_tarjeta_sistema = db.Column(db.Numeric(10, 2), nullable=False)
    ventas_total_sistema = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Monto contado físicamente por el cajero (Solo efectivo)
    monto_contado_efectivo = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Resultado del cuadre
    diferencia = db.Column(db.Numeric(10, 2), nullable=False) # Faltante (negativo) o Sobrante (positivo)
    
    # Quien realizó el cuadre
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario = db.relationship('Usuario', backref='cuadres_realizados')

    def __repr__(self):
        return f"CuadreCaja(ID: {self.id}, Cierre: {self.fecha_cierre}, Dif: {self.diferencia})"
    

class MensajeMasivo(db.Model):
    """Modelo para registrar el historial de mensajes de correo masivos enviados."""
    __tablename__ = 'mensajes_masivos'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha_envio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    asunto = db.Column(db.String(150), nullable=False)
    cuerpo_resumen = db.Column(db.String(300), nullable=False) # Resumen del cuerpo
    destinatario_filtro = db.Column(db.String(50), nullable=False) # Ej: 'activos', 'todos'
    total_enviados = db.Column(db.Integer, nullable=False)
    
    # 🚨 CORRECCIÓN CLAVE: 'usuario.id' en lugar de 'usuarios.id'
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) 
    
    # Relación con el usuario que lo envió
    usuario = db.relationship('Usuario', backref=db.backref('mensajes_enviados', lazy=True))

    def __repr__(self):
        return f"MensajeMasivo('{self.asunto}', '{self.fecha_envio}')"
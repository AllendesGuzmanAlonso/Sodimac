from app.src.database.database import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum  # Cambia a usar enum de Python para definir los enumerados
from sqlalchemy import Enum  # SQLAlchemy Enum para la base de datos


# Define la enumeración para los estados de la herramienta
class EstadoHerramientaEnum(enum.Enum):
    DISPONIBLE = "Disponible"
    RESERVADA = "Reservada"
    EN_REPARACION = "En reparación"


# Define la enumeración para los roles de usuario
class RolEnum(enum.Enum):
    USUARIO = "Usuario"
    ADMINISTRADOR = "Administrador"


# Define la enumeración para el estado del arriendo
class EstadoArriendoEnum(enum.Enum):
    EN_PROCESO = "En proceso"
    FINALIZADO = "Finalizado"


# Este modelo representa las herramientas disponibles en el sistema.
class Herramienta(db.Model):
    __tablename__ = "herramientas"
    id_herramienta = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(50), nullable=False)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    estado = db.Column(
        Enum(EstadoHerramientaEnum),  # Utiliza Enum de SQLAlchemy
        nullable=False,
        default=EstadoHerramientaEnum.DISPONIBLE,
    )
    cantidad_disponible = db.Column(db.Integer, nullable=False)
    sucursal_id = db.Column(
        db.Integer, db.ForeignKey("sucursales.id_sucursal"), nullable=False
    )
    sucursal = db.relationship("Sucursal", back_populates="herramientas")


# Este modelo representa las sucursales donde las herramientas están ubicadas.
class Sucursal(db.Model):
    __tablename__ = "sucursales"
    id_sucursal = db.Column(db.Integer, primary_key=True)
    nombre_sucursal = db.Column(db.String(100), nullable=False)
    ubicacion = db.Column(db.String(200), nullable=False)
    herramientas = db.relationship("Herramienta", back_populates="sucursal")


# Este modelo representa a los usuarios que utilizan el sistema.
class Usuario(db.Model):
    __tablename__ = "usuarios"
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(Enum(RolEnum), nullable=False, default=RolEnum.USUARIO)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# Este modelo representa los arriendos realizados por los usuarios.
class ReporteArriendo(db.Model):
    __tablename__ = "reporte_arriendos"
    id_arriendo = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(
        db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False
    )
    id_herramienta = db.Column(
        db.Integer, db.ForeignKey("herramientas.id_herramienta"), nullable=False
    )
    fecha_inicio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    estado_arriendo = db.Column(
        Enum(EstadoArriendoEnum),
        nullable=False,
        default=EstadoArriendoEnum.EN_PROCESO,
    )
    usuario = db.relationship("Usuario", backref="arriendos")
    herramienta = db.relationship("Herramienta", backref="arriendos")


# Este modelo representa las transacciones realizadas con las herramientas.
class Transaccion(db.Model):
    __tablename__ = "transacciones"
    id_transaccion = db.Column(db.Integer, primary_key=True)
    id_herramienta = db.Column(
        db.Integer, db.ForeignKey("herramientas.id_herramienta"), nullable=False
    )
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cantidad = db.Column(
        db.Integer, nullable=False, default=1
    )  # Cantidad de herramientas involucradas en la transacción
    sucursal_origen = db.Column(
        db.Integer, db.ForeignKey("sucursales.id_sucursal"), nullable=True
    )
    sucursal_destino = db.Column(
        db.Integer, db.ForeignKey("sucursales.id_sucursal"), nullable=True
    )
    estado = db.Column(db.Enum(EstadoHerramientaEnum), nullable=False)

    herramienta = db.relationship("Herramienta", backref="transacciones")


# Este es un modelo intermedio que sirve para manejar la relación de muchos a muchos entre herramientas y sucursales.
class HerramientaSucursal(db.Model):
    __tablename__ = "herramienta_sucursal"
    id = db.Column(db.Integer, primary_key=True)
    herramienta_id = db.Column(
        db.Integer, db.ForeignKey("herramientas.id_herramienta"), nullable=False
    )
    sucursal_id = db.Column(
        db.Integer, db.ForeignKey("sucursales.id_sucursal"), nullable=False
    )
    cantidad_disponible = db.Column(db.Integer, nullable=False)
    herramienta = db.relationship("Herramienta", backref="sucursal_asignaciones")
    sucursal = db.relationship("Sucursal", backref="herramienta_asignaciones")

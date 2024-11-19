from app.src.database.database import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum  # Cambia a usar enum de Python para definir los enumerados
from sqlalchemy import Enum  # SQLAlchemy Enum para la base de datos


# Enumeración para los estados de la herramienta
class EstadoHerramientaEnum(enum.Enum):
    Disponible = "Disponible"
    RESERVADA = "Reservada"
    EN_REPARACION = "En reparación"


# Enumeración para los roles de usuario
class RolEnum(enum.Enum):
    Usuario = "Usuario"
    Administrador = "Administrador"


# Enumeración para el estado del arriendo
class EstadoArriendoEnum(enum.Enum):
    EN_PROCESO = "En proceso"
    FINALIZADO = "Finalizado"


# Modelo Herramienta: representa las herramientas disponibles en el sistema
class Herramienta(db.Model):
    __tablename__ = "herramientas"
    id_herramienta = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(50), nullable=False)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    estado = db.Column(
        Enum(EstadoHerramientaEnum),
        nullable=False,
        default=EstadoHerramientaEnum.Disponible,
    )
    cantidad_disponible = db.Column(db.Integer, nullable=False)

    # Relación con sucursales a través del modelo intermedio HerramientaSucursal
    sucursal_asignaciones = db.relationship(
        "HerramientaSucursal", back_populates="herramienta"
    )

    # Relación directa con la sucursal (campo sucursal_id para compatibilidad con sistemas existentes)
    sucursal_id = db.Column(
        db.Integer, db.ForeignKey("sucursales.id_sucursal"), nullable=True
    )
    sucursal = db.relationship("Sucursal", back_populates="herramientas")


# Modelo Sucursal: representa las sucursales donde se almacenan herramientas
class Sucursal(db.Model):
    __tablename__ = "sucursales"
    id_sucursal = db.Column(db.Integer, primary_key=True)
    nombre_sucursal = db.Column(db.String(100), nullable=False)
    ubicacion = db.Column(db.String(200), nullable=False)

    # Relación con herramientas a través del modelo intermedio HerramientaSucursal
    herramienta_asignaciones = db.relationship(
        "HerramientaSucursal", back_populates="sucursal"
    )

    # Relación directa con herramientas (para herramientas individuales con sucursal fija)
    herramientas = db.relationship("Herramienta", back_populates="sucursal")


# Modelo Usuario: representa los usuarios del sistema
class Usuario(db.Model):
    __tablename__ = "usuarios"
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(Enum(RolEnum), nullable=False, default=RolEnum.Usuario)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        """Genera un hash para la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña coincide con el hash almacenado."""
        return check_password_hash(self.password_hash, password)


# Modelo ReporteArriendo: representa arriendos realizados por usuarios
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


# Modelo Transaccion: representa las transacciones de herramientas
class Transaccion(db.Model):
    __tablename__ = "transacciones"
    id_transaccion = db.Column(db.Integer, primary_key=True)
    id_herramienta = db.Column(
        db.Integer, db.ForeignKey("herramientas.id_herramienta"), nullable=False
    )
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    sucursal_origen = db.Column(
        db.Integer, db.ForeignKey("sucursales.id_sucursal"), nullable=False
    )
    estado = db.Column(Enum(EstadoHerramientaEnum), nullable=False)

    herramienta = db.relationship("Herramienta", backref="transacciones")
    sucursal = db.relationship("Sucursal", backref="transacciones_origen")


# Modelo HerramientaSucursal: modelo intermedio para manejar relación muchos a muchos
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

    # Relaciones con herramientas y sucursales
    herramienta = db.relationship("Herramienta", back_populates="sucursal_asignaciones")
    sucursal = db.relationship("Sucursal", back_populates="herramienta_asignaciones")

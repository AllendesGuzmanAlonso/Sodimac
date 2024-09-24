from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Enum


class EstadoHerramientaEnum(Enum):
    DISPONIBLE = "Disponible"
    RESERVADA = "Reservada"
    EN_REPARACION = "En reparación"


# Define la enumeración para los roles de usuario
class RolEnum(Enum):
    USUARIO = "Usuario"
    ADMINISTRADOR = "Administrador"


# Define la enumeración para el estado del arriendo
class EstadoArriendoEnum(Enum):
    EN_PROCESO = "En proceso"
    FINALIZADO = "Finalizado"


class Herramienta(db.Model):
    __tablename__ = "herramientas"
    id_herramienta = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(50), nullable=False)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    estado = db.Column(
        db.Enum(EstadoHerramientaEnum),
        nullable=False,
        default=EstadoHerramientaEnum.DISPONIBLE,
    )
    cantidad_disponible = db.Column(db.Integer, nullable=False)
    sucursal_id = db.Column(
        db.Integer, db.ForeignKey("sucursales.id_sucursal"), nullable=False
    )
    sucursal = db.relationship("Sucursal", back_populates="herramientas")


class Sucursal(db.Model):
    __tablename__ = "sucursales"
    id_sucursal = db.Column(db.Integer, primary_key=True)
    nombre_sucursal = db.Column(db.String(100), nullable=False)
    ubicacion = db.Column(db.String(200), nullable=False)
    herramientas = db.relationship("Herramienta", back_populates="sucursal")


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.Enum(RolEnum), nullable=False, default=RolEnum.USUARIO)
    password_hash = db.Column(db.String(128), nullable=False)

    # Función para establecer la contraseña de manera segura
    def set_password(self, password):
        """
        Toma la contraseña en texto plano y genera un hash seguro
        El hash generado se almacena en la variable self.password_hash
        Esto permite almacenar la contraseña de forma segura, ya que el hash
        es una representación encriptada de la contraseña original.
        """
        self.password_hash = generate_password_hash(password)

    # Función para verificar la contraseña
    def check_password(self, password):
        """
        Compara la contraseña en texto plano ingresada con el hash almacenado
        Utiliza check_password_hash para determinar si la contraseña es correcta
        Retorna True si el hash de la contraseña ingresada coincide con el hash almacenado,
        lo que indica que la contraseña es válida, o False en caso contrario.
        """
        return check_password_hash(self.password_hash, password)


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
        db.Enum(EstadoArriendoEnum),
        nullable=False,
        default=EstadoArriendoEnum.EN_PROCESO,
    )
    usuario = db.relationship("Usuario", backref="arriendos")
    herramienta = db.relationship("Herramienta", backref="arriendos")
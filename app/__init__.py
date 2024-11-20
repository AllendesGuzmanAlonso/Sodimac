import os
from flask import Flask
from flask_mail import Mail  # Importar Flask-Mail
from app.src.database.database import db, migrate  # Importar las extensiones

# Inicializar Flask-Mail
mail = Mail()

def create_app():
    app = Flask(__name__)

    # Establecer la clave secreta para proteger las sesiones
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "8b1ac95e69492bdb3ad740420f3a1498"
    )

    # Configuración de la base de datos MariaDB
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql://root:Proyectorental@localhost:3307/Multirental"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Desactiva las advertencias

    # Configuración de Flask-Mail
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USE_SSL"] = False
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "tu_correo@gmail.com")  # Cambia a tu correo
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "tu_contraseña")  # Cambia a tu contraseña
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "tu_correo@gmail.com")  # Cambia al remitente predeterminado

    # Inicializar las extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)  # Inicializar Flask-Mail

    # Importar modelos
    # Importamos aquí para evitar importaciones circulares
    with app.app_context():
        from app.src.models.models import (
            Herramienta,
            Sucursal,
            Usuario,
            ReporteArriendo,
            Transaccion,
            HerramientaSucursal,
        )

    # Registrar los Blueprints
    from app.src.routes.main_routes import main_bp

    app.register_blueprint(main_bp)

    return app

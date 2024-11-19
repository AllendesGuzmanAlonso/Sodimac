import os
from flask import Flask
from app.src.database.database import db, migrate  # Importar las extensiones


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

    # Inicializar las extensiones
    db.init_app(app)
    migrate.init_app(app, db)

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

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.src.models.models import (
    Herramienta,
    Sucursal,
    Usuario,
    ReporteArriendo,
    Transaccion,
    HerramientaSucursal,
)

main_bp = Blueprint("main_bp", __name__)


# Ruta de login aceptando tanto GET como POST
@main_bp.route("/")
def login():
    return render_template("login.html")


@main_bp.route("/home")
def home():
    search_query = request.args.get("search")

    if search_query:
        herramientas = Herramienta.query.filter(
            Herramienta.nombre.ilike(f"%{search_query}%")
        ).all()
    else:
        herramientas = Herramienta.query.all()

    return render_template("home.html", herramientas=herramientas)


@main_bp.route("/registroHerramientas")
def registroHerramientas():
    return render_template("registroHerramientas.html")


@main_bp.route("/transacciones")
def transacciones():
    return render_template("transacciones.html")


@main_bp.route("/reportes")
def reportes():
    return render_template("reportes.html")

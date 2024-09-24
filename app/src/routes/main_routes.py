from flask import Blueprint, render_template, request

main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/home')
def home():
    return render_template('home.html')

# Ruta de login aceptando tanto GET como POST
@main_bp.route('/login')
def login():
    return render_template('login.html')

@main_bp.route('/login2')
def login2():
    return render_template('login2.html')

@main_bp.route('/registro-herramientas')
def registroHerramientas():
    return render_template('registro-herramientas.html')

@main_bp.route('/transacciones')
def transacciones():
    return render_template('transacciones.html')

@main_bp.route('/reportes')
def reportes():
    return render_template('reportes.html')


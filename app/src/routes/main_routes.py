from flask import Blueprint, render_template, request

main_bp = Blueprint('main_bp', __name__)


@main_bp.route('/')
def home():
    return render_template('home.html')

# Ruta de login aceptando tanto GET como POST
@main_bp.route('/login')
def login():
    return render_template('login.html')



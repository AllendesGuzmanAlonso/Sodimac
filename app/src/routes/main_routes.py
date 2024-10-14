from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.src.models.models import (
    Herramienta,
    Sucursal,
    Usuario,
    ReporteArriendo,
    Transaccion,
    HerramientaSucursal,
    db,
    EstadoHerramientaEnum,
)
from werkzeug.security import check_password_hash, generate_password_hash
from app.src.utils.decorators import login_required, admin_required

main_bp = Blueprint("main_bp", __name__)


# Ruta de login aceptando tanto GET como POST
@main_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo")
        password = request.form.get("password")
        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            # Almacenar la información del usuario en la sesión
            session["usuario_id"] = usuario.id_usuario
            session["rol"] = usuario.rol.value  # Guardamos el rol (Usuario o Administrador)
            session["nombre_usuario"] = usuario.nombre
            flash(f"Bienvenido, {usuario.nombre}")
            return redirect(url_for("main_bp.home"))
        else:
            flash("Correo o contraseña incorrectos")

    return render_template("login.html")


@main_bp.route("/home")
@login_required
def home():
    search_query = request.args.get("search")

    if search_query:
        herramientas = Herramienta.query.filter(
            Herramienta.nombre.ilike(f"%{search_query}%")
        ).all()
    else:
        herramientas = Herramienta.query.all()

    return render_template("home.html", herramientas=herramientas)


# Ruta para registrar herramientas
@main_bp.route("/registroHerramientas", methods=["GET", "POST"])
@login_required
def registroHerramientas():
    # Obtener todas las sucursales disponibles para mostrarlas en el formulario
    sucursales = Sucursal.query.all()

    if request.method == "POST":
        # Obtener los datos del formulario
        nombre = request.form.get("nombre")
        marca = request.form.get("marca")
        codigo = request.form.get("codigo")
        sucursal_id = request.form.get("sucursal")
        stock = request.form.get("stock")

        # Validar que los campos no estén vacíos
        if not nombre or not marca or not codigo or not sucursal_id or not stock:
            flash("Todos los campos son obligatorios", "danger")
            return render_template("registroHerramientas.html", sucursales=sucursales)

        # Verificar si ya existe una herramienta con ese código
        herramienta_existente = Herramienta.query.filter_by(codigo=codigo).first()
        if herramienta_existente:
            flash("Ya existe una herramienta con ese código", "danger")
            return render_template("registroHerramientas.html", sucursales=sucursales)

        # Crear una nueva herramienta
        nueva_herramienta = Herramienta(
            nombre=nombre,
            marca=marca,
            codigo=codigo,
            cantidad_disponible=stock,
            sucursal_id=sucursal_id,
        )

        # Guardar la nueva herramienta en la base de datos
        db.session.add(nueva_herramienta)
        db.session.commit()

        flash("Herramienta registrada exitosamente", "success")
        return redirect(url_for("main_bp.registroHerramientas"))

    # Si es un GET, renderizar el formulario
    return render_template("registroHerramientas.html", sucursales=sucursales)


@main_bp.route("/transacciones/<int:id_herramienta>", methods=["GET", "POST"])
@login_required
def transacciones(id_herramienta):
    # Obtener la herramienta seleccionada
    herramienta = Herramienta.query.get_or_404(id_herramienta)

    # Obtener el stock de la herramienta en las diferentes sucursales
    stock_sucursales = HerramientaSucursal.query.filter_by(
        herramienta_id=id_herramienta
    ).all()

    if request.method == "POST":
        # Obtener los datos del formulario
        codigo = request.form.get("codigo")
        estado = request.form.get("estado")  # El estado seleccionado

        # Actualizar el estado de la herramienta seleccionada
        herramienta.estado = estado
        db.session.commit()

        # Crear una nueva transacción sin tipo, solo registramos el cambio
        nueva_transaccion = Transaccion(
            id_herramienta=herramienta.id_herramienta,
            cantidad=1,  # Cantidad predeterminada de 1 para cada transacción
            sucursal_origen=None,  # No estamos seleccionando una sucursal de origen
            sucursal_destino=herramienta.sucursal_id,  # La sucursal donde se hace la transacción
        )
        db.session.add(nueva_transaccion)
        db.session.commit()

        # Redireccionar después de guardar
        return redirect(url_for("main_bp.transacciones", id_herramienta=id_herramienta))

    return render_template(
        "transacciones.html",
        herramienta=herramienta,
        stock_sucursales=stock_sucursales,
        EstadoHerramientaEnum=EstadoHerramientaEnum,
    )

#Logout
@main_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()  # Limpiar todos los datos de la sesión
    flash("Sesión cerrada con éxito.")
    return redirect(url_for("main_bp.login"))

# Ruta para manejar error 404
@main_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

#REPORTES
@main_bp.route("/reportes")
@login_required
def reportes():
    return render_template("reportes.html")

#Crear sucursales
@main_bp.route('/sucursales/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_sucursal():
    if request.method == 'POST':
        nombre = request.form['nombre_sucursal']
        ubicacion = request.form['ubicacion']
        nueva_sucursal = Sucursal(nombre_sucursal=nombre, ubicacion=ubicacion)
        db.session.add(nueva_sucursal)
        db.session.commit()
        flash('Sucursal creada correctamente')
        return redirect(url_for('main_bp.listar_sucursales'))
    return render_template('crear_sucursal.html')

#Listar usuarios
@main_bp.route('/usuarios', methods=['GET'])
@login_required
@admin_required
def listar_usuarios():
    # Obtener todos los usuarios de la base de datos
    usuarios = Usuario.query.all()
    return render_template('listar_usuarios.html', usuarios=usuarios)

#Listar sucursales
@main_bp.route('/sucursales', methods=['GET'])
@login_required
def listar_sucursales():
    # Obtener todas las sucursales de la base de datos
    sucursales = Sucursal.query.all()
    return render_template('listar_sucursales.html', sucursales=sucursales)

#Crear Usuario
@main_bp.route('/usuarios/crear', methods=['GET', 'POST'])
@admin_required
def crear_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        rol = request.form['rol']  # El administrador selecciona el rol del usuario
        password = request.form['password']

        # Validar si ya existe un usuario con ese correo
        usuario_existente = Usuario.query.filter_by(correo=correo).first()
        if usuario_existente:
            flash('Ya existe un usuario con ese correo', 'danger')
            return redirect(url_for('main_bp.crear_usuario'))

        # Crear el nuevo usuario con el hash de la contraseña
        nuevo_usuario = Usuario(
            nombre=nombre, 
            correo=correo, 
            rol=rol, 
            password_hash=generate_password_hash(password)
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('main_bp.listar_usuarios'))  # Después de crear, listar usuarios

    return render_template('crear_usuario.html')

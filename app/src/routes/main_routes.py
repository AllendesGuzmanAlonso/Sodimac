from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
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
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask_mail import Message, Mail
import csv
import io
from flask import send_file, Response
import pandas as pd
import pytz


main_bp = Blueprint("main_bp", __name__)

# Configuración de Flask-Mail
mail = Mail()
s = URLSafeTimedSerializer("your-secret-key")  # Cambia "your-secret-key" por una clave secreta real


# Ruta de login aceptando tanto GET como POST
@main_bp.route("/", methods=["GET", "POST"])
def login():
    """Maneja la autenticación de usuarios con selección de sucursal."""
    if request.method == "POST":
        correo = request.form.get("correo")
        password = request.form.get("password")
        sucursal_id = request.form.get("sucursal")

        if not sucursal_id:
            flash("Por favor, selecciona una sucursal.", "warning")
            return render_template("login.html", sucursales=Sucursal.query.all())

        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            session["usuario_id"] = usuario.id_usuario
            session["rol"] = usuario.rol.value
            session["nombre_usuario"] = usuario.nombre
            session["sucursal_id"] = sucursal_id
            session["nombre_sucursal"] = Sucursal.query.get(sucursal_id).nombre_sucursal

            flash(f"Bienvenido, {usuario.nombre}, Sucursal: {session['nombre_sucursal']}")
            return redirect(url_for("main_bp.home"))
        else:
            flash("Correo o contraseña incorrectos", "danger")
            print("Contraseña incorrecta o usuario no encontrado")

    sucursales = Sucursal.query.all()
    return render_template("login.html", sucursales=sucursales)

# Ruta de recuperación de contraseña unificada
@main_bp.route("/recuperar_contrasena", methods=["GET", "POST"])
def recuperar_contrasena():
    """Maneja la recuperación de contraseña en un solo flujo."""
    if request.method == "POST":
        correo = request.form.get("correo")
        nueva_password = request.form.get("nueva_password")
        confirmar_password = request.form.get("confirmar_password")

        if nueva_password and confirmar_password:
            if nueva_password != confirmar_password:
                flash("Las contraseñas no coinciden.", "danger")
                return render_template("recuperar_contrasena.html", correo=correo)

            usuario = Usuario.query.filter_by(correo=correo).first()
            if usuario:
                usuario.password_hash = generate_password_hash(nueva_password)
                db.session.commit()
                flash("Contraseña actualizada con éxito. Ahora puedes iniciar sesión.", "success")
                return redirect(url_for("main_bp.login"))
            else:
                flash("El correo no está registrado.", "danger")
        elif correo:
            usuario = Usuario.query.filter_by(correo=correo).first()
            if usuario:
                flash("Por favor, ingresa la nueva contraseña.", "info")
                return render_template("recuperar_contrasena.html", correo=correo)
            else:
                flash("El correo no está registrado.", "danger")

    return render_template("recuperar_contrasena.html")


@main_bp.route("/home", methods=["GET"])
@login_required
def home():
    """Página de inicio donde se listan las herramientas con búsqueda y paginación por sucursal seleccionada en el login."""
    # Obtener la sucursal seleccionada desde la sesión
    sucursal_id = session.get("sucursal_id")

    # Verificar que haya una sucursal seleccionada
    if not sucursal_id:
        flash("Por favor selecciona una sucursal antes de continuar.", "warning")
        return redirect(url_for("main_bp.login"))

    # Obtener parámetros de búsqueda y página desde la URL
    search_query = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)

    # Construir la consulta base con el filtro de sucursal
    query = Herramienta.query.filter(Herramienta.sucursal_id == sucursal_id)

    # Filtro por búsqueda de nombre de herramienta
    if search_query:
        query = query.filter(Herramienta.nombre.ilike(f"%{search_query}%"))

    # Agregar paginación (10 herramientas por página)
    herramientas = query.paginate(page=page, per_page=10)

    # Obtener información de la sucursal activa para mostrarla en la plantilla
    sucursal = Sucursal.query.get(sucursal_id)

    # Renderizar el template con las herramientas y la sucursal activa
    return render_template(
        "home.html",
        herramientas=herramientas,
        search_query=search_query,
        nombre_sucursal=sucursal.nombre_sucursal,
    )




# Ruta para registrar herramientas
@main_bp.route("/registroHerramientas", methods=["GET", "POST"])
@login_required
def registroHerramientas():
    """Registro de una nueva herramienta en el sistema."""
    # Obtener todas las sucursales disponibles para mostrarlas en el formulario
    sucursales = Sucursal.query.all()

    if request.method == "POST":
        # Obtener los datos del formulario
        nombre = request.form.get("nombre")
        marca = request.form.get("marca")
        codigo = request.form.get("codigo")
        sucursal_id = request.form.get("sucursal")
        stock = request.form.get("stock")
        stock_total = request.form.get("stock_total")

        # Validar que los campos no estén vacíos
        if not nombre or not marca or not codigo or not sucursal_id or not stock or not stock_total:
            flash("Todos los campos son obligatorios", "danger")
            return render_template("registroHerramientas.html", sucursales=sucursales)

        # Validar que el stock total sea un número positivo
        try:
            stock = int(stock)
            stock_total = int(stock_total)
            if stock < 0 or stock_total < 0:
                raise ValueError
        except ValueError:
            flash("El stock y el stock total deben ser números positivos", "danger")
            return render_template("registroHerramientas.html", sucursales=sucursales)

        # Validar que el stock inicial no supere el stock total
        if stock > stock_total:
            flash("El stock inicial no puede ser mayor al stock total", "danger")
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
            stock_total=stock_total,
            sucursal_id=sucursal_id,
        )

        # Guardar la nueva herramienta en la base de datos
        db.session.add(nueva_herramienta)
        db.session.commit()

        flash("Herramienta registrada exitosamente", "success")
        return redirect(url_for("main_bp.registroHerramientas"))

    # Si es un GET, renderizar el formulario
    return render_template("registroHerramientas.html", sucursales=sucursales)



# Transacciones
# Ruta para la página de transacciones
@main_bp.route("/transacciones/<int:id_herramienta>", methods=["GET", "POST"])
@login_required
def transacciones(id_herramienta):
    """Gestiona las transacciones de herramientas."""
    herramienta = Herramienta.query.get_or_404(id_herramienta)
    sucursal_actual_id = session.get("sucursal_id")
    sucursal_actual = Sucursal.query.get_or_404(sucursal_actual_id)

    herramienta_sucursal_actual = HerramientaSucursal.query.filter_by(
        herramienta_id=id_herramienta,
        sucursal_id=sucursal_actual_id
    ).first()

    # Crear un registro inicial si no existe
    if not herramienta_sucursal_actual:
        herramienta_sucursal_actual = HerramientaSucursal(
            herramienta_id=id_herramienta,
            sucursal_id=sucursal_actual_id,
            cantidad_disponible=0
        )
        db.session.add(herramienta_sucursal_actual)
        db.session.commit()

    # Obtener stock en otras sucursales
    stock_sucursales = HerramientaSucursal.query.filter(
        HerramientaSucursal.herramienta_id == id_herramienta,
        HerramientaSucursal.sucursal_id != sucursal_actual_id
    ).join(Sucursal).all()

    if request.method == "POST":
        estado = request.form.get("estado")
        cantidad = int(request.form.get("cantidad", 0))

        # Validación de cantidad ingresada
        if cantidad <= 0:
            return jsonify({"error": "La cantidad debe ser mayor a 0."}), 400

        if estado == EstadoHerramientaEnum.Disponible.value:
            # Validar que no se exceda el stock total registrado
            if herramienta_sucursal_actual.cantidad_disponible + cantidad > herramienta.stock_total:
                return jsonify({"error": f"No puedes exceder el stock total permitido: {herramienta.stock_total}"}), 400
            herramienta_sucursal_actual.cantidad_disponible += cantidad

        elif estado in [EstadoHerramientaEnum.EN_REPARACION.value, EstadoHerramientaEnum.RESERVADA.value]:
            if herramienta_sucursal_actual.cantidad_disponible >= cantidad:
                herramienta_sucursal_actual.cantidad_disponible -= cantidad
            else:
                return jsonify({"error": "No hay suficiente stock disponible para esta acción."}), 400

        nueva_transaccion = Transaccion(
            id_herramienta=id_herramienta,
            fecha=db.func.now(),
            cantidad=cantidad,
            sucursal_origen=sucursal_actual_id,
            estado=estado
        )
        db.session.add(nueva_transaccion)
        db.session.commit()

        # Respuesta exitosa con stock actualizado
        return jsonify({
            "message": "Transacción registrada con éxito.",
            "stock_local": herramienta_sucursal_actual.cantidad_disponible,
            "stock_sucursales": [
                {
                    "sucursal": {"id": stock.sucursal.id_sucursal, "nombre_sucursal": stock.sucursal.nombre_sucursal},
                    "cantidad_disponible": stock.cantidad_disponible
                } for stock in stock_sucursales
            ]
        }), 200

    return render_template(
        "transacciones.html",
        herramienta=herramienta,
        sucursal_actual=sucursal_actual,
        stock_local=herramienta_sucursal_actual.cantidad_disponible,
        stock_sucursales=stock_sucursales,
        estados=EstadoHerramientaEnum
    )


# Ver transacciones
@main_bp.route("/ver_transacciones", methods=["GET"])
@login_required
def ver_transacciones():
    """Muestra todas las transacciones registradas en el sistema."""
    transacciones = Transaccion.query.all()

    # Definir la zona horaria de Chile
    tz = pytz.timezone("America/Santiago")

    return render_template("ver_transacciones.html", transacciones=transacciones, tz=tz)


# Logout
@main_bp.route("/logout", methods=["POST"])
def logout():
    """Cierra la sesión del usuario actual."""
    session.clear()  # Limpiar todos los datos de la sesión
    flash("Sesión cerrada con éxito.")
    return redirect(url_for("main_bp.login"))


# Ruta para manejar error 404
@main_bp.app_errorhandler(404)
def page_not_found(e):
    """Muestra una página personalizada para el error 404."""
    return render_template("404.html"), 404


# Listar usuarios
@main_bp.route("/usuarios", methods=["GET"])
@login_required
@admin_required
def listar_usuarios():
    """Lista todos los usuarios registrados en el sistema (solo accesible por administradores)."""
    # Obtener todos los usuarios de la base de datos
    usuarios = Usuario.query.all()
    return render_template("listar_usuarios.html", usuarios=usuarios)


# Listar sucursales
@main_bp.route("/sucursales", methods=["GET"])
@login_required
def listar_sucursales():
    """Permite a un administrador crear un nuevo usuario en el sistema."""
    # Obtener todas las sucursales de la base de datos
    sucursales = Sucursal.query.all()
    return render_template("listar_sucursales.html", sucursales=sucursales)


# Crear Usuario
@main_bp.route("/usuarios/crear", methods=["GET", "POST"])
@admin_required
def crear_usuario():
    """
    Crea un nuevo usuario en el sistema. Accesible solo para administradores.

    - Método GET: Renderiza el formulario para ingresar los datos del nuevo usuario.
    - Método POST:
        - Recibe el nombre, correo, rol, y contraseña desde el formulario.
        - Verifica si el correo ya está registrado.
        - Si no existe, crea el usuario con un hash de la contraseña y guarda en la base de datos.
        - Redirige al listado de usuarios y muestra un mensaje de éxito.
    """
    if request.method == "POST":
        nombre = request.form["nombre"]
        correo = request.form["correo"]
        rol = request.form["rol"]
        password = request.form["password"]

        usuario_existente = Usuario.query.filter_by(correo=correo).first()
        if usuario_existente:
            flash("Ya existe un usuario con ese correo", "danger")
            return redirect(url_for("main_bp.crear_usuario"))

        nuevo_usuario = Usuario(
            nombre=nombre,
            correo=correo,
            rol=rol,
            password_hash=generate_password_hash(password),
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash("Usuario creado correctamente", "success")
        return redirect(url_for("main_bp.listar_usuarios"))

    return render_template("crear_usuario.html")


# Crear Sucursal
@main_bp.route("/sucursales/crear", methods=["GET", "POST"])
@login_required
@admin_required
def crear_sucursal():
    """
    Crea una nueva sucursal en el sistema. Requiere autenticación y rol de administrador.

    - Método GET: Renderiza el formulario para ingresar los datos de la nueva sucursal.
    - Método POST:
        - Recibe el nombre y ubicación desde el formulario.
        - Valida que ambos campos no estén vacíos.
        - Crea la sucursal y la guarda en la base de datos.
        - Redirige al listado de sucursales y muestra un mensaje de éxito.
    """
    if request.method == "POST":
        nombre = request.form.get("nombre_sucursal")
        ubicacion = request.form.get("ubicacion")

        if not nombre or not ubicacion:
            flash("Todos los campos son obligatorios.", "danger")
            return render_template("crear_sucursal.html")

        nueva_sucursal = Sucursal(nombre_sucursal=nombre, ubicacion=ubicacion)
        db.session.add(nueva_sucursal)
        db.session.commit()
        flash("Sucursal creada correctamente", "success")
        return redirect(url_for("main_bp.listar_sucursales"))

    return render_template("crear_sucursal.html")


# Listar herramientas para eliminar
@main_bp.route("/herramientas/eliminar", methods=["GET"])
@login_required
@admin_required
def listar_herramientas_para_eliminar():
    """
    Lista todas las herramientas en el sistema para que puedan ser seleccionadas y eliminadas.
    Requiere autenticación y rol de administrador.
    """
    herramientas = Herramienta.query.all()
    return render_template("eliminar_herramienta.html", herramientas=herramientas)


# Eliminar Herramienta
@main_bp.route("/herramientas/eliminar/<int:id_herramienta>", methods=["POST"])
@login_required
@admin_required
def eliminar_herramienta(id_herramienta):
    """
    Elimina una herramienta específica del sistema.
    Requiere autenticación y rol de administrador.

    - Busca la herramienta por su ID.
    - La elimina de la base de datos.
    - Muestra un mensaje de confirmación y redirige a la lista de herramientas para eliminar.
    """
    herramienta = Herramienta.query.get_or_404(id_herramienta)
    db.session.delete(herramienta)
    db.session.commit()
    flash("Herramienta eliminada con éxito", "success")
    return redirect(url_for("main_bp.listar_herramientas_para_eliminar"))


# Reportes
@main_bp.route("/reportes")
@login_required
def reportes():
    """
    Genera un reporte que lista todas las herramientas junto con la sucursal, cantidad disponible,
    y el número total de transacciones asociadas. Requiere autenticación.

    - Consulta la base de datos para obtener las herramientas, sucursales, y total de transacciones.
    - Renderiza el reporte en una plantilla HTML.
    """
    herramientas = (
        db.session.query(
            Herramienta.nombre,
            Sucursal.nombre_sucursal,
            Herramienta.cantidad_disponible,
            db.func.count(Transaccion.id_transaccion).label("total_transacciones"),
        )
        .join(Sucursal, Herramienta.sucursal_id == Sucursal.id_sucursal)
        .outerjoin(
            Transaccion, Herramienta.id_herramienta == Transaccion.id_herramienta
        )
        .group_by(Herramienta.id_herramienta, Sucursal.id_sucursal)
        .all()
    )

    return render_template("reportes.html", herramientas=herramientas)


# Descargar reporte en CSV
@main_bp.route("/reportes/csv")
@login_required
def descargar_csv():
    """
    Genera y permite la descarga de un reporte en formato CSV.
    Requiere autenticación.

    - Consulta las herramientas, sucursales y transacciones.
    - Crea un archivo CSV en memoria.
    - Añade encabezados y datos.
    - Envía el archivo como una respuesta de descarga.
    """
    herramientas = (
        db.session.query(
            Herramienta.nombre,
            Sucursal.nombre_sucursal,
            Herramienta.cantidad_disponible,
            db.func.count(Transaccion.id_transaccion).label("total_transacciones"),
        )
        .join(Sucursal, Herramienta.sucursal_id == Sucursal.id_sucursal)
        .outerjoin(
            Transaccion, Herramienta.id_herramienta == Transaccion.id_herramienta
        )
        .group_by(Herramienta.id_herramienta, Sucursal.id_sucursal)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Nombre Herramienta", "Sucursal", "Stock Actual", "Total Transacciones"]
    )

    for herramienta in herramientas:
        writer.writerow(
            [
                herramienta.nombre,
                herramienta.nombre_sucursal,
                herramienta.cantidad_disponible,
                herramienta.total_transacciones,
            ]
        )

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte.csv"},
    )


# Descargar reporte en Excel
@main_bp.route("/reportes/excel")
@login_required
def descargar_excel():
    """
    Genera y permite la descarga de un reporte en formato Excel.
    Requiere autenticación.

    - Consulta las herramientas, sucursales y transacciones.
    - Crea un archivo Excel en memoria usando Pandas.
    - Añade los datos y los organiza en una hoja de cálculo.
    - Envía el archivo como una respuesta de descarga.
    """
    herramientas = (
        db.session.query(
            Herramienta.nombre,
            Sucursal.nombre_sucursal,
            Herramienta.cantidad_disponible,
            db.func.count(Transaccion.id_transaccion).label("total_transacciones"),
        )
        .join(Sucursal, Herramienta.sucursal_id == Sucursal.id_sucursal)
        .outerjoin(
            Transaccion, Herramienta.id_herramienta == Transaccion.id_herramienta
        )
        .group_by(Herramienta.id_herramienta, Sucursal.id_sucursal)
        .all()
    )

    df = pd.DataFrame(
        {
            "Nombre Herramienta": [h.nombre for h in herramientas],
            "Sucursal": [h.nombre_sucursal for h in herramientas],
            "Stock Actual": [h.cantidad_disponible for h in herramientas],
            "Total Transacciones": [h.total_transacciones for h in herramientas],
        }
    )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")

    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="reporte.xlsx",
    )


# Eliminar Sucursal
@main_bp.route("/sucursales/eliminar/<int:id_sucursal>", methods=["POST"])
@login_required
@admin_required
def eliminar_sucursal(id_sucursal):
    """
    Elimina una sucursal específica del sistema.
    Requiere autenticación y rol de administrador.

    - Busca la sucursal por su ID.
    - Intenta eliminar la sucursal de la base de datos.
    - Si ocurre un error, realiza rollback y muestra el error.
    - Muestra un mensaje de éxito si se elimina exitosamente.
    """
    sucursal = Sucursal.query.get_or_404(id_sucursal)

    try:
        db.session.delete(sucursal)
        db.session.commit()
        flash("Sucursal eliminada exitosamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la sucursal: {str(e)}", "danger")

    return redirect(url_for("main_bp.listar_sucursales"))


# Listar Sucursales para Eliminar
@main_bp.route("/sucursales/eliminar", methods=["GET"])
@login_required
@admin_required
def listar_para_eliminar_sucursales():
    """
    Lista todas las sucursales en el sistema para que puedan ser seleccionadas y eliminadas.
    Requiere autenticación y rol de administrador.
    """
    sucursales = Sucursal.query.all()
    return render_template("eliminar_sucursal.html", sucursales=sucursales)

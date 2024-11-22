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
import csv
import io
from flask import send_file, Response
import pandas as pd
import pytz
from datetime import datetime

main_bp = Blueprint("main_bp", __name__)


# Ruta de login aceptando tanto GET como POST
@main_bp.route("/", methods=["GET", "POST"])
def login():
    """Maneja la autenticación de usuarios."""
    if request.method == "POST":
        # Obtener el correo, la contraseña y la sucursal ingresados
        correo = request.form.get("correo")
        password = request.form.get("password")
        sucursal_id = request.form.get("sucursal")

        # Validar que todos los campos estén completos
        if not sucursal_id:
            flash("Por favor, selecciona una sucursal.", "warning")
            return render_template("login.html", sucursales=Sucursal.query.all())

        # Buscar al usuario en la base de datos por el correo
        usuario = Usuario.query.filter_by(correo=correo).first()

        # Verificar si el usuario existe y la contraseña es correcta
        if usuario and check_password_hash(usuario.password_hash, password):
            # Si todo está bien, almacenar los datos del usuario y la sucursal en la sesión
            session["usuario_id"] = usuario.id_usuario
            session["rol"] = usuario.rol.value
            session["nombre_usuario"] = usuario.nombre
            session["sucursal_id"] = sucursal_id  # Almacena la sucursal seleccionada
            session["nombre_sucursal"] = Sucursal.query.get(sucursal_id).nombre_sucursal

            flash(
                f"Bienvenido, {usuario.nombre}, Sucursal: {session['nombre_sucursal']}"
            )  # Mensaje de éxito
            return redirect(url_for("main_bp.home"))  # Redirigir al home
        else:
            # Si las credenciales son incorrectas
            flash("Correo o contraseña incorrectos", "danger")
            print(
                "Contraseña incorrecta o usuario no encontrado"
            )  # Mensaje para depuración

    # Si es un GET, cargar las sucursales para mostrarlas en el formulario
    sucursales = Sucursal.query.all()
    return render_template("login.html", sucursales=sucursales)


@main_bp.route("/home")
@login_required
def home():
    sucursal_id = session.get("sucursal_id")
    search_query = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    # Construir la consulta base para herramientas en la sucursal activa
    query = (
        db.session.query(Herramienta)
        .join(HerramientaSucursal, Herramienta.id_herramienta == HerramientaSucursal.herramienta_id)
        .filter(
            HerramientaSucursal.sucursal_id == sucursal_id,
            HerramientaSucursal.cantidad_disponible > 0,  # Solo herramientas con stock
        )
    )

    # Agregar búsqueda por nombre o código si se proporciona un query
    if search_query:
        query = query.filter(
            db.or_(
                Herramienta.nombre.ilike(f"%{search_query}%"),
                Herramienta.codigo.ilike(f"%{search_query}%"),
            )
        )

    # Paginación
    herramientas = query.paginate(page=page, per_page=10)

    return render_template(
        "home.html",
        herramientas=herramientas,
        search_query=search_query,
        nombre_sucursal=session.get("nombre_sucursal"),
    )



# Ruta para registrar herramientas
@main_bp.route("/registroHerramientas", methods=["GET", "POST"])
@login_required
def registroHerramientas():
    """Ruta para registrar una nueva herramienta."""
    if request.method == "POST":
        # Obtener datos del formulario
        nombre = request.form.get("nombre")
        marca = request.form.get("marca")
        codigo = request.form.get("codigo")
        cantidad_disponible = request.form.get("cantidad_disponible")

        # Validar que todos los campos estén completos
        if not nombre or not marca or not codigo or not cantidad_disponible:
            flash("Todos los campos son obligatorios", "danger")
            return render_template("registroHerramientas.html")

        # Obtener la sucursal activa desde la sesión
        sucursal_id = session.get("sucursal_id")
        if not sucursal_id:
            flash("Error: No se pudo identificar la sucursal activa.", "danger")
            return redirect(url_for("main_bp.home"))

        try:
            # Crear la herramienta en la base de datos
            nueva_herramienta = Herramienta(
                nombre=nombre,
                marca=marca,
                codigo=codigo
            )
            db.session.add(nueva_herramienta)
            db.session.commit()

            # Asociar la herramienta a la sucursal con la cantidad disponible
            nueva_asociacion = HerramientaSucursal(
                herramienta_id=nueva_herramienta.id_herramienta,
                sucursal_id=sucursal_id,
                cantidad_disponible=int(cantidad_disponible)
            )
            db.session.add(nueva_asociacion)
            db.session.commit()

            flash("Herramienta registrada con éxito.", "success")
            return redirect(url_for("main_bp.home"))
        except Exception as e:
            db.session.rollback()
            print("Error al registrar la herramienta:", e)
            flash("Ocurrió un error al registrar la herramienta.", "danger")
            return render_template("registroHerramientas.html")

    return render_template("registroHerramientas.html")


# Transacciones
@main_bp.route("/transacciones/<int:herramienta_id>", methods=["GET", "POST"])
def transacciones(herramienta_id):
    herramienta = Herramienta.query.get_or_404(herramienta_id)
    sucursal_id = session.get("sucursal_id")
    
    # Calcular stock agrupado por sucursal y nombre de herramienta
    stocks = (
        db.session.query(
            Sucursal.nombre_sucursal,
            db.func.sum(HerramientaSucursal.cantidad_disponible).label("cantidad_disponible")
        )
        .join(HerramientaSucursal, Sucursal.id_sucursal == HerramientaSucursal.sucursal_id)
        .join(Herramienta, Herramienta.id_herramienta == HerramientaSucursal.herramienta_id)
        .filter(Herramienta.nombre == herramienta.nombre)  # Agrupar por nombre
        .group_by(Sucursal.id_sucursal)
        .all()
    )

    if request.method == "POST":
        estado = request.form.get("estado")
        herramienta_sucursal = HerramientaSucursal.query.filter_by(
            herramienta_id=herramienta_id, sucursal_id=sucursal_id
        ).first()

        # Validar que la herramienta existe en la sucursal
        if not herramienta_sucursal:
            flash("La herramienta no está registrada en esta sucursal.", "danger")
            return redirect(url_for("main_bp.home"))

        # Lógica de estados y stock
        if estado in ["Reservada", "En Mantenimiento"]:
            if herramienta_sucursal.cantidad_disponible > 0:
                herramienta_sucursal.cantidad_disponible -= 1
                db.session.commit()
                flash("Estado actualizado y stock ajustado.", "success")
            else:
                flash("No hay stock suficiente para cambiar el estado.", "danger")
                return redirect(
                    url_for("main_bp.transacciones", herramienta_id=herramienta_id)
                )
        elif estado == "Disponible":
            herramienta_sucursal.cantidad_disponible += 1
            db.session.commit()
            flash("Estado actualizado a Disponible.", "success")

        return redirect(url_for("main_bp.transacciones", herramienta_id=herramienta_id))

    return render_template(
        "transacciones.html",
        herramienta=herramienta,
        stocks=stocks,
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


@main_bp.route("/herramientas/eliminar", methods=["GET", "POST"])
@login_required
@admin_required
def eliminar_herramienta():
    herramientas = Herramienta.query.all()  # Lista actualizada de herramientas

    if request.method == "POST":
        try:
            id_herramienta = request.form.get("id_herramienta")
            herramienta = Herramienta.query.get_or_404(id_herramienta)

            # Elimina dependencias
            HerramientaSucursal.query.filter_by(herramienta_id=id_herramienta).delete()
            Transaccion.query.filter_by(id_herramienta=id_herramienta).delete()

            db.session.delete(herramienta)
            db.session.commit()

            flash("Herramienta eliminada con éxito", "success")

            # Redirigir al mismo endpoint después de eliminar
            return redirect(url_for("main_bp.eliminar_herramienta"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ocurrió un error al eliminar la herramienta: {str(e)}", "danger")

    return render_template("eliminar_herramienta.html", herramientas=herramientas)


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
    try:
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
    except Exception as e:
        flash(f"Error al generar el reporte en Excel: {str(e)}", "danger")
        return redirect(url_for("main_bp.reportes"))


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


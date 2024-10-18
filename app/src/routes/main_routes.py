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

main_bp = Blueprint("main_bp", __name__)


# Ruta de login aceptando tanto GET como POST
@main_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Obtener el correo y la contraseña ingresados
        correo = request.form.get("correo")
        password = request.form.get("password")

        # Buscar al usuario en la base de datos por el correo
        usuario = Usuario.query.filter_by(correo=correo).first()

        # Verificar si el usuario existe y la contraseña es correcta
        if usuario and check_password_hash(usuario.password_hash, password):
            # Si todo está bien, almacenar los datos del usuario en la sesión
            session["usuario_id"] = usuario.id_usuario
            session["rol"] = usuario.rol.value
            session["nombre_usuario"] = usuario.nombre

            flash(f"Bienvenido, {usuario.nombre}")  # Mensaje de éxito
            return redirect(url_for("main_bp.home"))  # Redirigir al home
        else:
            # Si las credenciales son incorrectas
            flash("Correo o contraseña incorrectos", "danger")
            print("Contraseña incorrecta o usuario no encontrado")  # Mensaje para depuración

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

#Transacciones
@main_bp.route("/transacciones/<int:id_herramienta>", methods=["GET", "POST"])
@login_required
def transacciones(id_herramienta):
    # Obtener la herramienta seleccionada
    herramienta = Herramienta.query.get_or_404(id_herramienta)

    # Modificar esta línea para obtener todas las sucursales que tienen la herramienta (con el mismo código o diferente)
    stock_sucursales = HerramientaSucursal.query.filter_by(herramienta_id=herramienta.id_herramienta).all()

    if request.method == "POST":
        # Obtener los datos del formulario
        estado = request.form.get("estado")
        sucursal_origen = request.form.get("sucursal_origen")

        if not estado or not sucursal_origen:
            flash("Debe seleccionar un estado y una sucursal de origen.", "danger")
            return redirect(url_for('main_bp.transacciones', id_herramienta=id_herramienta))

        # Obtener el stock de la herramienta en la sucursal seleccionada
        herramienta_sucursal = HerramientaSucursal.query.filter_by(
            herramienta_id=herramienta.id_herramienta, sucursal_id=sucursal_origen
        ).first()

        if not herramienta_sucursal:
            flash("La herramienta no está disponible en la sucursal seleccionada.", "danger")
            return redirect(url_for('main_bp.transacciones', id_herramienta=id_herramienta))

        # Actualizar el stock según el estado de la herramienta
        if estado == "Reservada" or estado == "En Reparación":
            if herramienta_sucursal.cantidad_disponible > 0:
                herramienta_sucursal.cantidad_disponible -= 1
            else:
                flash("No hay stock disponible para esta herramienta.", "danger")
                return redirect(url_for('main_bp.transacciones', id_herramienta=id_herramienta))
        elif estado == "Disponible":
            herramienta_sucursal.cantidad_disponible += 1

        # Guardar el estado de la herramienta
        herramienta.estado = estado
        db.session.commit()

        # Crear una nueva transacción
        nueva_transaccion = Transaccion(
            id_herramienta=herramienta.id_herramienta,
            cantidad=1,
            sucursal_origen=sucursal_origen,
            estado=estado
        )
        db.session.add(nueva_transaccion)
        db.session.commit()

        flash("Transacción registrada con éxito", "success")
        return redirect(url_for("main_bp.transacciones", id_herramienta=id_herramienta))

    # Renderizar la página de transacciones
    return render_template(
        "transacciones.html",
        herramienta=herramienta,
        stock_sucursales=stock_sucursales,  # Pasar los datos de las sucursales con stock disponible
        EstadoHerramientaEnum=EstadoHerramientaEnum
    )

#Ver transacciones
@main_bp.route("/ver_transacciones", methods=["GET"])
@login_required
def ver_transacciones():
    transacciones = Transaccion.query.all()

    # Definir la zona horaria de Chile
    tz = pytz.timezone("America/Santiago")

    return render_template('ver_transacciones.html', transacciones=transacciones, tz=tz)

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

@main_bp.route('/sucursales/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_sucursal():
    if request.method == 'POST':
        nombre = request.form.get('nombre_sucursal')
        ubicacion = request.form.get('ubicacion')
        
        if not nombre or not ubicacion:
            flash("Todos los campos son obligatorios.", "danger")
            return render_template('crear_sucursal.html')

        nueva_sucursal = Sucursal(nombre_sucursal=nombre, ubicacion=ubicacion)
        db.session.add(nueva_sucursal)
        db.session.commit()
        flash('Sucursal creada correctamente', 'success')
        return redirect(url_for('main_bp.listar_sucursales'))
    
    return render_template('crear_sucursal.html')

# Ruta para listar herramientas a eliminar
@main_bp.route('/herramientas/eliminar', methods=['GET'])
@login_required
@admin_required
def listar_herramientas_para_eliminar():
    herramientas = Herramienta.query.all()  # Obtener todas las herramientas
    return render_template('eliminar_herramienta.html', herramientas=herramientas)

# Ruta para eliminar una herramienta
@main_bp.route('/herramientas/eliminar/<int:id_herramienta>', methods=['POST'])
@login_required
@admin_required
def eliminar_herramienta(id_herramienta):
    herramienta = Herramienta.query.get_or_404(id_herramienta)  # Obtener la herramienta por ID
    db.session.delete(herramienta)  # Eliminar la herramienta de la base de datos
    db.session.commit()
    flash('Herramienta eliminada con éxito', 'success')  # Mensaje flash para confirmar la eliminación
    return redirect(url_for('main_bp.listar_herramientas_para_eliminar'))

#REPORTES
@main_bp.route("/reportes")
@login_required
def reportes():
    # Obtener todas las herramientas y sus sucursales
    herramientas = db.session.query(
        Herramienta.nombre,
        Sucursal.nombre_sucursal,
        Herramienta.cantidad_disponible,
        db.func.count(Transaccion.id_transaccion).label("total_transacciones")
    ).join(Sucursal, Herramienta.sucursal_id == Sucursal.id_sucursal) \
     .outerjoin(Transaccion, Herramienta.id_herramienta == Transaccion.id_herramienta) \
     .group_by(Herramienta.id_herramienta, Sucursal.id_sucursal) \
     .all()

    return render_template("reportes.html", herramientas=herramientas)


# Ruta para descargar el reporte en CSV
@main_bp.route("/reportes/csv")
@login_required
def descargar_csv():
    # Obtener las herramientas y transacciones
    herramientas = db.session.query(
        Herramienta.nombre,
        Sucursal.nombre_sucursal,
        Herramienta.cantidad_disponible,
        db.func.count(Transaccion.id_transaccion).label("total_transacciones")
    ).join(Sucursal, Herramienta.sucursal_id == Sucursal.id_sucursal) \
     .outerjoin(Transaccion, Herramienta.id_herramienta == Transaccion.id_herramienta) \
     .group_by(Herramienta.id_herramienta, Sucursal.id_sucursal) \
     .all()

    # Crear el CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nombre Herramienta", "Sucursal", "Stock Actual", "Total Transacciones"])

    for herramienta in herramientas:
        writer.writerow([herramienta.nombre, herramienta.nombre_sucursal, herramienta.cantidad_disponible, herramienta.total_transacciones])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=reporte.csv"})

# Ruta para descargar el reporte en Excel
@main_bp.route("/reportes/excel")
@login_required
def descargar_excel():
    # Obtener las herramientas y transacciones
    herramientas = db.session.query(
        Herramienta.nombre,
        Sucursal.nombre_sucursal,
        Herramienta.cantidad_disponible,
        db.func.count(Transaccion.id_transaccion).label("total_transacciones")
    ).join(Sucursal, Herramienta.sucursal_id == Sucursal.id_sucursal) \
     .outerjoin(Transaccion, Herramienta.id_herramienta == Transaccion.id_herramienta) \
     .group_by(Herramienta.id_herramienta, Sucursal.id_sucursal) \
     .all()

    # Crear un DataFrame con Pandas
    df = pd.DataFrame({
        "Nombre Herramienta": [h.nombre for h in herramientas],
        "Sucursal": [h.nombre_sucursal for h in herramientas],
        "Stock Actual": [h.cantidad_disponible for h in herramientas],
        "Total Transacciones": [h.total_transacciones for h in herramientas]
    })

    # Guardar el DataFrame en un archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")

    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="reporte.xlsx")

@main_bp.route('/sucursales/eliminar/<int:id_sucursal>', methods=['POST'])
@login_required
@admin_required
def eliminar_sucursal(id_sucursal):
    # Obtener la sucursal por su ID
    sucursal = Sucursal.query.get_or_404(id_sucursal)

    try:
        # Eliminar la sucursal
        db.session.delete(sucursal)
        db.session.commit()
        flash('Sucursal eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la sucursal: {str(e)}', 'danger')

    # Redireccionar a la página de listar sucursales
    return redirect(url_for('main_bp.listar_sucursales'))

# Ruta para listar las sucursales para eliminarlas
@main_bp.route('/sucursales/eliminar', methods=['GET'])
@login_required
@admin_required
def listar_para_eliminar_sucursales():
    # Obtener todas las sucursales para mostrarlas en la página
    sucursales = Sucursal.query.all()
    return render_template('eliminar_sucursal.html', sucursales=sucursales)




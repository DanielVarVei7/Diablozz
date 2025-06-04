from flask import Flask, render_template, request, redirect, session, url_for, flash, make_response
from functools import wraps
from fpdf import FPDF
from config.conexion import conexion

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'


# ------------------ Autenticación ------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contraseña = request.form.get('contraseña')

        if usuario == 'admin' and contraseña == '1234':
            session['usuario'] = usuario
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))


# ------------------ Clientes ------------------

def obtener_clientes():
    try:
        with conexion.cursor() as cursor:
            cursor.execute('SELECT * FROM tbcliente')
            return cursor.fetchall()
    except Exception as e:
        flash(f'Error al obtener clientes: {e}', 'danger')
        return []


@app.route('/')
@login_required
def index():
    clientes = obtener_clientes()
    return render_template('registrar.html', mensaje='Clientes Registrados', clientes=clientes)


@app.route('/buscar')
@login_required
def buscar():
    texto = request.args.get('txtbuscar', '').strip()
    if not texto:
        flash('Debes escribir algo para buscar.', 'warning')
        return redirect(url_for('index'))

    try:
        with conexion.cursor() as cursor:
            query = """
                SELECT id_cliente, nombre, nit FROM tbcliente
                WHERE nombre LIKE %s OR nit LIKE %s
            """
            like = f"%{texto}%"
            cursor.execute(query, (like, like))
            clientes = cursor.fetchall()
    except Exception as e:
        flash(f'Error al buscar: {e}', 'danger')
        return redirect(url_for('index'))

    mensaje = f'Resultados para: "{texto}"'
    return render_template('registrar.html', clientes=clientes, mensaje=mensaje)


@app.route('/insertar', methods=['POST'])
@login_required
def insertar():
    nombre = request.form.get('txtnombre')
    nit = request.form.get('txtnit')

    if not nombre or not nit:
        flash('Nombre y NIT son obligatorios', 'warning')
        return redirect(url_for('index'))

    try:
        with conexion.cursor() as cursor:
            sql = "INSERT INTO tbcliente (nombre, nit) VALUES (%s, %s)"
            cursor.execute(sql, (nombre, nit))
        conexion.commit()
        flash('Cliente registrado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al insertar cliente: {e}', 'danger')

    return redirect(url_for('index'))


@app.route('/actualizar/<int:id>')
@login_required
def actualizar(id):
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM tbcliente WHERE id_cliente = %s", (id,))
            cliente = cursor.fetchone()
        if not cliente:
            flash('Cliente no encontrado', 'danger')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error al obtener cliente: {e}', 'danger')
        return redirect(url_for('index'))

    return render_template('actualizar.html', datos=cliente)


@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    try:
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM tbcliente WHERE id_cliente = %s", (id,))
        conexion.commit()
        flash('Cliente eliminado correctamente', 'info')
    except Exception as e:
        flash(f'Error al eliminar cliente: {e}', 'danger')

    return redirect(url_for('index'))



catalogo_albumes = [
    {'id': 1, 'nombre': 'Álbum: HAUTE COUTURE', 'artista': 'MiSaMo', 'precio': 30.00},
    {'id': 2, 'nombre': 'Song: Baby Good Night', 'artista': 'GD&TOP', 'precio': 14.99},
    {'id': 3, 'nombre': 'Song: TESYODAY', 'artista': 'NCT, NCT U', 'precio': 14.99},
    {'id': 4, 'nombre': 'Álbum: GOLDEN', 'artista': 'Jung Kook', 'precio': 40.00},
    {'id': 5, 'nombre': 'Song: Its Up to You', 'artista': 'Moon Sujin', 'precio': 20.00},
    {'id': 6, 'nombre': 'Song: I AM SHAMPOO', 'artista': 'BIBi', 'precio': 14.99},
    {'id': 7, 'nombre': 'Song: Eighteen', 'artista': 'Seiko Matsuda', 'precio': 9.99},
    {'id': 8, 'nombre': 'Song: After LIKE', 'artista': 'IVE', 'precio': 12.00},
]


@app.route('/comprar/<int:id>')
@login_required
def comprar(id):
    carrito = session.get('carrito', [])
    return render_template('catalogo.html', catalogo=catalogo_albumes, carrito=carrito, id_cliente=id)


@app.route('/agregar_carrito', methods=['POST'])
@login_required
def agregar_carrito():
    id_album = int(request.form.get('id'))
    album = next((a for a in catalogo_albumes if a['id'] == id_album), None)
    if album:
        carrito = session.get('carrito', [])
        carrito.append(album)
        session['carrito'] = carrito
    return redirect(request.referrer)


@app.route('/quitar_carrito', methods=['POST'])
@login_required
def quitar_carrito():
    id_album = int(request.form.get('id'))
    carrito = session.get('carrito', [])
    session['carrito'] = [a for a in carrito if a['id'] != id_album]
    return redirect(request.referrer)


@app.route('/vercompras/<int:id>')
@login_required
def vercompras(id):
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM tbcompra WHERE id_cliente = %s", (id,))
            datos = cursor.fetchall()
        return render_template('vercompras.html', datos=datos)
    except Exception as e:
        flash(f'Error al obtener compras: {e}', 'danger')
        return redirect(url_for('index'))


@app.route('/reporte/<int:id>')
@login_required
def generar_pdf(id):
    try:
        with conexion.cursor() as cursor:
            sql = """
                SELECT c.nombre, c.nit, co.producto, co.cantidad, co.costo
                FROM tbcompra co
                INNER JOIN tbcliente c ON co.id_cliente = c.id_cliente
                WHERE co.id_cliente = %s
            """
            cursor.execute(sql, (id,))
            datos = cursor.fetchall()
    except Exception as e:
        return f"Error al generar reporte: {e}", 500

    if not datos:
        return "No se encontraron compras para este cliente", 404

    nombre_cliente, nit_cliente = datos[0][0], datos[0][1]

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="REPORTE DE COMPRAS", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Cliente: {nombre_cliente}", ln=True)
    pdf.cell(200, 5, txt=f"NIT: {nit_cliente}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 10, "Producto", 1)
    pdf.cell(30, 10, "Cantidad", 1)
    pdf.cell(30, 10, "Costo", 1)
    pdf.cell(40, 10, "Total", 1)
    pdf.ln()

    pdf.set_font("Arial", '', 10)
    for _, _, producto, cantidad, costo in datos:
        total = float(cantidad) * float(costo)
        pdf.cell(60, 10, str(producto), 1)
        pdf.cell(30, 10, str(cantidad), 1)
        pdf.cell(30, 10, f"{costo:.2f}", 1)
        pdf.cell(40, 10, f"{total:.2f}", 1)
        pdf.ln()

    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=reporte_compras.pdf'
    return response


if __name__ == '__main__':
    app.run(debug=True)

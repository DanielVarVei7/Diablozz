from config.conexion import conexion
from flask import Flask, render_template, request, redirect, session, url_for, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'  # Necesario para sesiones

# Decorador para proteger rutas que requieren autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Obtener todos los clientes
def obtener_clientes():
    with conexion.cursor() as cursor:
        cursor.execute('SELECT * FROM tbcliente')
        return cursor.fetchall()

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


@app.route('/')
@login_required
def index():
    clientes = obtener_clientes()
    mensaje = "Bienvenidos a la página de ventas"
    return render_template('registrar.html', mensaje=mensaje, clientes=clientes)

@app.route('/insertar', methods=['POST'])
@login_required
def insertar():
    nombre = request.form.get('txtnombre')
    nit = request.form.get('txtnit')

    if not nombre or not nit:
        flash('Nombre y NIT son obligatorios', 'warning')
        return redirect(url_for('index'))

    with conexion.cursor() as cursor:
        sql = "INSERT INTO tbcliente (nombre, nit) VALUES (%s, %s)"
        cursor.execute(sql, (nombre, nit))
    conexion.commit()

    flash('Registro insertado exitosamente', 'success')
    return redirect(url_for('index'))

@app.route('/actualizar/<int:id>')
@login_required
def actualizar(id):
    with conexion.cursor() as cursor:
        cursor.execute("SELECT * FROM tbcliente WHERE id_cliente = %s", (id,))
        cliente = cursor.fetchone()
    
    if not cliente:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('index'))

    return render_template('actualizar.html', datos=cliente)

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    with conexion.cursor() as cursor:
        cursor.execute("DELETE FROM tbcliente WHERE id_cliente = %s", (id,))
    conexion.commit()

    flash('Cliente eliminado correctamente', 'info')
    return redirect(url_for('index'))

@app.route('/comprar/<int:id>')
@login_required
def comprar(id):
    mensaje = f"Página de compra para el cliente con ID {id}"
    return render_template('comprar.html', mensaje=mensaje, id_cliente=id)

if __name__ == '__main__':
    app.run(debug=True)

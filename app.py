from flask import Flask, render_template, request, redirect, session, url_for, flash, make_response
from functools import wraps
from fpdf import FPDF
from config.conexion import conexion
import logging

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura_cambiar_en_produccion'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Debes iniciar sesión para acceder', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        contraseña = request.form.get('contraseña', '').strip()
        
        # Validación básica
        if not usuario or not contraseña:
            flash('Usuario y contraseña son obligatorios', 'warning')
            return render_template('login.html')
            
        # TODO: Implementar hash de contraseñas y validación en BD
        if usuario == 'admin' and contraseña == '1234':
            session['usuario'] = usuario
            flash(f'Bienvenido {usuario}', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    usuario = session.get('usuario', 'Usuario')
    session.clear()  # Limpiar toda la sesión
    flash(f'Hasta luego {usuario}', 'info')
    return redirect(url_for('login'))


def ejecutar_consulta(query, params=None, fetch=True):
    """
    Función centralizada para ejecutar consultas de manera segura
    """
    try:
        with conexion.cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            conexion.commit()
            return True
    except Exception as e:
        logger.error(f"Error en consulta DB: {e}")
        conexion.rollback()
        raise e

def obtener_clientes():
    """Obtener todos los clientes de la base de datos"""
    try:
        return ejecutar_consulta('SELECT * FROM tbcliente ORDER BY nombre')
    except Exception as e:
        flash(f'Error al obtener clientes: {str(e)}', 'danger')
        return []

def obtener_cliente_por_id(id_cliente):
    """Obtener un cliente específico por ID"""
    try:
        resultado = ejecutar_consulta(
            "SELECT * FROM tbcliente WHERE id_cliente = %s", 
            (id_cliente,)
        )
        return resultado[0] if resultado else None
    except Exception as e:
        logger.error(f"Error al obtener cliente {id_cliente}: {e}")
        return None


@app.route('/')
@login_required
def index():
    clientes = obtener_clientes()
    return render_template('registrar.html', 
                         mensaje='Clientes Registrados', 
                         clientes=clientes)

@app.route('/buscar')
@login_required
def buscar():
    texto = request.args.get('txtbuscar', '').strip()
    
    if not texto:
        flash('Debes escribir algo para buscar.', 'warning')
        return redirect(url_for('index'))

    try:
        query = """
            SELECT id_cliente, nombre, nit 
            FROM tbcliente 
            WHERE LOWER(nombre) LIKE LOWER(%s) OR nit LIKE %s
            ORDER BY nombre
        """
        like_texto = f"%{texto}%"
        clientes = ejecutar_consulta(query, (like_texto, like_texto))
        
        if not clientes:
            flash(f'No se encontraron resultados para: "{texto}"', 'info')
            
    except Exception as e:
        flash(f'Error al buscar: {str(e)}', 'danger')
        return redirect(url_for('index'))

    mensaje = f'Resultados para: "{texto}" ({len(clientes)} encontrados)'
    return render_template('registrar.html', 
                         clientes=clientes, 
                         mensaje=mensaje)

@app.route('/insertar', methods=['POST'])
@login_required
def insertar():
    nombre = request.form.get('txtnombre', '').strip()
    nit = request.form.get('txtnit', '').strip()

    # Validaciones
    if not nombre or not nit:
        flash('Nombre y NIT son obligatorios', 'warning')
        return redirect(url_for('index'))
    
    if len(nombre) < 2:
        flash('El nombre debe tener al menos 2 caracteres', 'warning')
        return redirect(url_for('index'))

    try:
        # Verificar si el NIT ya existe
        existe = ejecutar_consulta(
            "SELECT COUNT(*) as count FROM tbcliente WHERE nit = %s", 
            (nit,)
        )
        
        if existe and existe[0]['count'] > 0:
            flash(f'Ya existe un cliente con el NIT: {nit}', 'warning')
            return redirect(url_for('index'))
        
        # Insertar nuevo cliente
        ejecutar_consulta(
            "INSERT INTO tbcliente (nombre, nit) VALUES (%s, %s)", 
            (nombre, nit), 
            fetch=False
        )
        
        flash(f'Cliente "{nombre}" registrado exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al insertar cliente: {str(e)}', 'danger')

    return redirect(url_for('index'))

@app.route('/actualizar/<int:id>')
@login_required
def actualizar(id):
    cliente = obtener_cliente_por_id(id)
    
    if not cliente:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('index'))

    return render_template('actualizar.html', datos=cliente)

@app.route('/actualizar_cliente', methods=['POST'])
@login_required
def actualizar_cliente():
    """Nueva ruta para procesar la actualización"""
    id_cliente = request.form.get('id_cliente')
    nombre = request.form.get('txtnombre', '').strip()
    nit = request.form.get('txtnit', '').strip()

    if not all([id_cliente, nombre, nit]):
        flash('Todos los campos son obligatorios', 'warning')
        return redirect(url_for('index'))

    try:
        # Verificar que el cliente existe
        cliente_actual = obtener_cliente_por_id(id_cliente)
        if not cliente_actual:
            flash('Cliente no encontrado', 'danger')
            return redirect(url_for('index'))

        # Verificar NIT duplicado (excepto el actual)
        existe = ejecutar_consulta(
            "SELECT COUNT(*) as count FROM tbcliente WHERE nit = %s AND id_cliente != %s", 
            (nit, id_cliente)
        )
        
        if existe and existe[0]['count'] > 0:
            flash(f'Ya existe otro cliente con el NIT: {nit}', 'warning')
            return redirect(url_for('actualizar', id=id_cliente))

        # Actualizar cliente
        ejecutar_consulta(
            "UPDATE tbcliente SET nombre = %s, nit = %s WHERE id_cliente = %s",
            (nombre, nit, id_cliente),
            fetch=False
        )
        
        flash(f'Cliente "{nombre}" actualizado correctamente', 'success')
        
    except Exception as e:
        flash(f'Error al actualizar cliente: {str(e)}', 'danger')

    return redirect(url_for('index'))

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    try:
        # Verificar que el cliente existe
        cliente = obtener_cliente_por_id(id)
        if not cliente:
            flash('Cliente no encontrado', 'danger')
            return redirect(url_for('index'))

        # Verificar si tiene compras asociadas
        compras = ejecutar_consulta(
            "SELECT COUNT(*) as count FROM tbcompra WHERE id_cliente = %s", 
            (id,)
        )
        
        if compras and compras[0]['count'] > 0:
            flash('No se puede eliminar el cliente porque tiene compras registradas', 'warning')
            return redirect(url_for('index'))

        # Eliminar cliente
        ejecutar_consulta(
            "DELETE FROM tbcliente WHERE id_cliente = %s", 
            (id,), 
            fetch=False
        )
        
        flash(f'Cliente "{cliente["nombre"]}" eliminado correctamente', 'info')
        
    except Exception as e:
        flash(f'Error al eliminar cliente: {str(e)}', 'danger')

    return redirect(url_for('index'))

# ------------------ Catálogo de Álbumes ------------------

CATALOGO_ALBUMES = [
    {'id': 1, 'nombre': 'Álbum: HAUTE COUTURE', 'artista': 'MiSaMo', 'precio': 30.00, 'stock': 10},
    {'id': 2, 'nombre': 'Song: Baby Good Night', 'artista': 'GD&TOP', 'precio': 14.99, 'stock': 5},
    {'id': 3, 'nombre': 'Álbum: Formula of Love', 'artista': 'TWICE', 'precio': 25.00, 'stock': 8},
    {'id': 4, 'nombre': 'Song: Dynamite', 'artista': 'BTS', 'precio': 12.99, 'stock': 15},
    {'id': 5, 'nombre': 'Álbum: The Album', 'artista': 'BLACKPINK', 'precio': 28.00, 'stock': 7},
    {'id': 5, 'nombre': 'Song: FXXk IT ', 'artista': 'BIGBANG', 'precio': 20.00, 'stock': 10},
    {'id': 5, 'nombre': 'Song: LETS NOT FALL IN LOVE ', 'artista': 'BIGBANG', 'precio': 20.00, 'stock': 2},
]

def obtener_album_por_id(id_album):
    """Obtener álbum por ID"""
    return next((a for a in CATALOGO_ALBUMES if a['id'] == id_album), None)

@app.route('/comprar/<int:id>')
@login_required
def comprar(id):
    # Verificar que el cliente existe
    cliente = obtener_cliente_por_id(id)
    if not cliente:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('index'))

    carrito = session.get('carrito', [])
    total_carrito = sum(item['precio'] * item.get('cantidad', 1) for item in carrito)
    
    return render_template('catalogo.html', 
                         catalogo=CATALOGO_ALBUMES, 
                         carrito=carrito,
                         total_carrito=total_carrito,
                         cliente=cliente)

@app.route('/agregar_carrito', methods=['POST'])
@login_required
def agregar_carrito():
    id_album = int(request.form.get('id'))
    cantidad = int(request.form.get('cantidad', 1))
    
    album = obtener_album_por_id(id_album)
    if not album:
        flash('Álbum no encontrado', 'danger')
        return redirect(request.referrer or url_for('index'))
    
    if cantidad > album['stock']:
        flash(f'Solo hay {album["stock"]} unidades disponibles', 'warning')
        return redirect(request.referrer)

    carrito = session.get('carrito', [])
    
    # Buscar si el álbum ya está en el carrito
    item_existente = next((item for item in carrito if item['id'] == id_album), None)
    
    if item_existente:
        nueva_cantidad = item_existente.get('cantidad', 1) + cantidad
        if nueva_cantidad > album['stock']:
            flash(f'No hay suficiente stock. Máximo: {album["stock"]}', 'warning')
        else:
            item_existente['cantidad'] = nueva_cantidad
            flash(f'Cantidad actualizada para "{album["nombre"]}"', 'success')
    else:
        album_carrito = album.copy()
        album_carrito['cantidad'] = cantidad
        carrito.append(album_carrito)
        flash(f'"{album["nombre"]}" agregado al carrito', 'success')
    
    session['carrito'] = carrito
    return redirect(request.referrer or url_for('index'))

@app.route('/quitar_carrito', methods=['POST'])
@login_required
def quitar_carrito():
    id_album = int(request.form.get('id'))
    carrito = session.get('carrito', [])
    
    # Encontrar el nombre del álbum antes de eliminarlo
    album_eliminado = next((a for a in carrito if a['id'] == id_album), None)
    
    session['carrito'] = [a for a in carrito if a['id'] != id_album]
    
    if album_eliminado:
        flash(f'"{album_eliminado["nombre"]}" eliminado del carrito', 'info')
    
    return redirect(request.referrer or url_for('index'))

@app.route('/limpiar_carrito')
@login_required
def limpiar_carrito():
    """Nueva función para limpiar todo el carrito"""
    session['carrito'] = []
    flash('Carrito vaciado completamente', 'info')
    return redirect(request.referrer or url_for('index'))

@app.route('/finalizar_compra/<int:id_cliente>', methods=['POST'])
@login_required
def finalizar_compra(id_cliente):
    """Nueva función para procesar la compra"""
    carrito = session.get('carrito', [])
    
    if not carrito:
        flash('El carrito está vacío', 'warning')
        return redirect(url_for('comprar', id=id_cliente))

    try:
        # Procesar cada item del carrito
        for item in carrito:
            ejecutar_consulta(
                "INSERT INTO tbcompra (id_cliente, producto, cantidad, costo) VALUES (%s, %s, %s, %s)",
                (id_cliente, f"{item['nombre']} - {item['artista']}", 
                 item.get('cantidad', 1), item['precio']),
                fetch=False
            )
        
        # Limpiar carrito después de la compra
        session['carrito'] = []
        flash('Compra realizada exitosamente', 'success')
        
    except Exception as e:
        flash(f'Error al procesar la compra: {str(e)}', 'danger')
    
    return redirect(url_for('vercompras', id=id_cliente))

# ------------------ Compras ------------------

@app.route('/vercompras/<int:id>')
@login_required
def vercompras(id):
    cliente = obtener_cliente_por_id(id)
    if not cliente:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('index'))

    try:
        compras = ejecutar_consulta(
            "SELECT * FROM tbcompra WHERE id_cliente = %s ORDER BY id_compra DESC", 
            (id,)
        )
        
        # Calcular total de compras
        total_compras = sum(float(compra['cantidad']) * float(compra['costo']) 
                          for compra in compras)
        
        return render_template('vercompras.html', 
                             datos=compras, 
                             cliente=cliente,
                             total_compras=total_compras)
                             
    except Exception as e:
        flash(f'Error al obtener compras: {str(e)}', 'danger')
        return redirect(url_for('index'))

# ------------------ Reportes PDF ------------------

@app.route('/reporte/<int:id>')
@login_required
def generar_pdf(id):
    try:
        # Consulta mejorada con JOIN
        sql = """
            SELECT c.nombre, c.nit, co.producto, co.cantidad, co.costo, co.id_compra
            FROM tbcompra co
            INNER JOIN tbcliente c ON co.id_cliente = c.id_cliente
            WHERE co.id_cliente = %s
            ORDER BY co.id_compra DESC
        """
        datos = ejecutar_consulta(sql, (id,))
        
    except Exception as e:
        logger.error(f"Error al generar reporte para cliente {id}: {e}")
        return f"Error al generar reporte: {str(e)}", 500

    if not datos:
        return "No se encontraron compras para este cliente", 404

    nombre_cliente, nit_cliente = datos[0]['nombre'], datos[0]['nit']

    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, "REPORTE DE COMPRAS", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Cliente: {nombre_cliente}", ln=True)
    pdf.cell(0, 10, f"NIT: {nit_cliente}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(10, 10, "#", 1, 0, 'C')
    pdf.cell(80, 10, "Producto", 1, 0, 'C')
    pdf.cell(25, 10, "Cantidad", 1, 0, 'C')
    pdf.cell(25, 10, "Precio Unit.", 1, 0, 'C')
    pdf.cell(25, 10, "Total", 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Arial", '', 9)
    total_general = 0
    
    for i, compra in enumerate(datos, 1):
        cantidad = float(compra['cantidad'])
        costo = float(compra['costo'])
        total_linea = cantidad * costo
        total_general += total_linea
        
        pdf.cell(10, 8, str(i), 1, 0, 'C')
        pdf.cell(80, 8, str(compra['producto'])[:40], 1)  
        pdf.cell(25, 8, str(int(cantidad)), 1, 0, 'C')
        pdf.cell(25, 8, f"${costo:.2f}", 1, 0, 'R')
        pdf.cell(25, 8, f"${total_linea:.2f}", 1, 0, 'R')
        pdf.ln()

    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "TOTAL GENERAL:", 0, 0, 'R')
    pdf.cell(25, 10, f"${total_general:.2f}", 1, 0, 'R')

    try:
        pdf_output = pdf.output(dest='S')
        response = make_response(pdf_output)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=reporte_{nombre_cliente.replace(" ", "_")}.pdf'
        return response
    except Exception as e:
        logger.error(f"Error al generar PDF: {e}")
        return f"Error al generar PDF: {str(e)}", 500


@app.errorhandler(404)
def page_not_found(e):
    flash('Página no encontrada', 'warning')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    flash('Error interno del servidor', 'danger')
    return redirect(url_for('index'))

@app.route('/usuarios')
def usuarios():
    return render_template('usuarios.html')

if __name__ == '__main__':
    logger.info("Iniciando aplicación Flask...")
    app.run(debug=True, host='0.0.0.0', port=5000)


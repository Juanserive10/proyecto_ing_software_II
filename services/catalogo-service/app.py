import csv
import io
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flasgger import Swagger
from openpyxl import load_workbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [catalogo-service] %(levelname)s: %(message)s")
logger = logging.getLogger("catalogo-service")

app = Flask(__name__)
CORS(app)


@app.before_request
def start_request_trace():
    g.start_time = time.perf_counter()
    g.request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())


@app.after_request
def log_request_trace(response):
    ms = round((time.perf_counter() - getattr(g, "start_time", time.perf_counter())) * 1000, 1)
    req_id = getattr(g, "request_id", "-")
    response.headers["X-Request-Id"] = req_id
    logger.info("request_id=%s method=%s path=%s status=%s ms=%s", req_id, request.method, request.path, response.status_code, ms)
    return response

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///catalogo.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SWAGGER"] = {
    "title": "Distribuidora Andina - Catálogo API",
    "uiversion": 3,
    "version": "1.0.0",
    "description": "Microservicio de Productos, Categorías, Búsqueda e Importación Excel/CSV (RF01, RF02, RF12, RF17)",
}

db = SQLAlchemy(app)
swagger = Swagger(app)


# ==================== MODELOS (ER: Base de datos Catálogo) ====================
class Categoria(db.Model):
    __tablename__ = "categoria"
    id_categoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_categoria_padre = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    subcategorias = db.relationship(
        "Categoria",
        backref=db.backref("padre", remote_side=[id_categoria]),
        lazy=True,
    )

    def to_dict(self):
        return {
            "id_categoria": self.id_categoria,
            "id_categoria_padre": self.id_categoria_padre,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "activo": self.activo,
        }


class Producto(db.Model):
    __tablename__ = "producto"
    id_producto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_categoria = db.Column(db.Integer, db.ForeignKey("categoria.id_categoria"), nullable=False)
    codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(160), nullable=False, index=True)
    descripcion = db.Column(db.String(500), nullable=True)
    unidad_medida = db.Column(db.String(40), nullable=False, default="UNIDAD")
    precio_venta = db.Column(db.Numeric(12, 2), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    categoria = db.relationship("Categoria", backref="productos", lazy=True)

    def to_dict(self):
        return {
            "id_producto": self.id_producto,
            "id_categoria": self.id_categoria,
            "categoria_nombre": self.categoria.nombre if self.categoria else None,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "unidad_medida": self.unidad_medida,
            "precio_venta": float(self.precio_venta),
            "activo": self.activo,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }


class Importacion(db.Model):
    __tablename__ = "importacion"
    id_importacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, nullable=False, default=1)
    nombre_archivo = db.Column(db.String(200), nullable=False)
    formato = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(30), nullable=False, default="PROCESADO")
    total_filas = db.Column(db.Integer, nullable=False, default=0)
    filas_validas = db.Column(db.Integer, nullable=False, default=0)
    filas_error = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    detalles = db.relationship("DetalleImportacion", backref="importacion", lazy=True)

    def to_dict(self, include_details=False):
        data = {
            "id_importacion": self.id_importacion,
            "id_usuario": self.id_usuario,
            "nombre_archivo": self.nombre_archivo,
            "formato": self.formato,
            "estado": self.estado,
            "total_filas": self.total_filas,
            "filas_validas": self.filas_validas,
            "filas_error": self.filas_error,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if include_details:
            data["detalles"] = [d.to_dict() for d in self.detalles]
        return data


class DetalleImportacion(db.Model):
    __tablename__ = "detalle_importacion"
    id_detalle = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_importacion = db.Column(db.Integer, db.ForeignKey("importacion.id_importacion"), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey("producto.id_producto"), nullable=True)
    numero_fila = db.Column(db.Integer, nullable=False)
    codigo_fuente = db.Column(db.String(60), nullable=True)
    estado = db.Column(db.String(20), nullable=False)
    mensaje_error = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id_detalle": self.id_detalle,
            "id_importacion": self.id_importacion,
            "id_producto": self.id_producto,
            "numero_fila": self.numero_fila,
            "codigo_fuente": self.codigo_fuente,
            "estado": self.estado,
            "mensaje_error": self.mensaje_error,
        }


# ==================== SEED INICIAL (Ferretería Distribuidora Andina) ====================
def seed_data():
    if Categoria.query.count() == 0:
        c1 = Categoria(nombre="Herramientas Eléctricas", descripcion="Taladros, pulidoras, sierras y atornilladores")
        c2 = Categoria(nombre="Herramientas Manuales", descripcion="Martillos, llaves, alicates y destornilladores")
        c3 = Categoria(nombre="Tornillería y Fijaciones", descripcion="Tornillos, chazos, pernos y tuercas")
        c4 = Categoria(nombre="Pinturas y Acabados", descripcion="Vinilos, esmaltes, rodillos y brochas")
        c5 = Categoria(nombre="Plomería y Tubería", descripcion="Tubos PVC, válvulas, codos y selladores")
        db.session.add_all([c1, c2, c3, c4, c5])
        db.session.commit()

        sub = Categoria(
            id_categoria_padre=c1.id_categoria,
            nombre="Taladros y Rotomartillos",
            descripcion="Subcategoría especializada en perforación",
        )
        db.session.add(sub)
        db.session.commit()

    if Producto.query.count() == 0:
        cats = {c.nombre: c.id_categoria for c in Categoria.query.all()}
        productos = [
            Producto(id_categoria=cats["Herramientas Eléctricas"], codigo="FER-001", nombre="Taladro Percutor 750W 1/2\"", descripcion="Taladro percutor industrial velocidad variable", unidad_medida="UNIDAD", precio_venta=Decimal("245000.00")),
            Producto(id_categoria=cats["Herramientas Eléctricas"], codigo="FER-002", nombre="Pulidora Angular 4-1/2\" 850W", descripcion="Esmeriladora angular con guarda protectora", unidad_medida="UNIDAD", precio_venta=Decimal("189000.00")),
            Producto(id_categoria=cats["Herramientas Manuales"], codigo="FER-003", nombre="Martillo Carpintero 16oz Fibra", descripcion="Mango ergonómico en fibra de vidrio antideslizante", unidad_medida="UNIDAD", precio_venta=Decimal("32500.00")),
            Producto(id_categoria=cats["Herramientas Manuales"], codigo="FER-004", nombre="Juego Destornilladores Pro x8", descripcion="Puntas imantadas estrella y pala en cromo vanadio", unidad_medida="JUEGO", precio_venta=Decimal("48000.00")),
            Producto(id_categoria=cats["Herramientas Manuales"], codigo="FER-005", nombre="Llave Expansiva 10\" Cromada", descripcion="Acero forjado con escala milimétrica grabada", unidad_medida="UNIDAD", precio_venta=Decimal("41000.00")),
            Producto(id_categoria=cats["Tornillería y Fijaciones"], codigo="FER-006", nombre="Caja Tornillo Drywall 1\" x1000", descripcion="Tornillo fosfatado punta aguda para drywall", unidad_medida="CAJA", precio_venta=Decimal("29500.00")),
            Producto(id_categoria=cats["Tornillería y Fijaciones"], codigo="FER-007", nombre="Chazo Plástico 1/4\" Bolsa x100", descripcion="Anclaje de expansión para muro sólido", unidad_medida="BOLSA", precio_venta=Decimal("12000.00")),
            Producto(id_categoria=cats["Pinturas y Acabados"], codigo="FER-008", nombre="Pintura Vinilo Tipo 1 Blanco 1 Galón", descripcion="Alta lavabilidad y cubrimiento para interiores", unidad_medida="GALON", precio_venta=Decimal("78500.00")),
            Producto(id_categoria=cats["Pinturas y Acabados"], codigo="FER-009", nombre="Rodillo Felpa 9\" Antigota", descripcion="Incluye maneral metálico reforzado", unidad_medida="UNIDAD", precio_venta=Decimal("19800.00")),
            Producto(id_categoria=cats["Plomería y Tubería"], codigo="FER-010", nombre="Tubo PVC Presión 1/2\" x 6m", descripcion="Tubería sanitaria/presión norma NTC", unidad_medida="UNIDAD", precio_venta=Decimal("18400.00")),
        ]
        db.session.add_all(productos)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()


# ==================== ENDPOINTS ====================
@app.get("/health")
def health():
    """Estado de salud del microservicio de Catálogo
    ---
    responses:
      200:
        description: Servicio activo
    """
    return jsonify({"service": "catalogo-service", "status": "ok"}), 200


# --- Categorías (RF02) ---
@app.get("/categories")
def list_categories():
    """Listar categorías y subcategorías (RF02)
    ---
    responses:
      200:
        description: Lista de categorías
    """
    solo_activas = request.args.get("activo")
    query = Categoria.query
    if solo_activas is not None:
        query = query.filter_by(activo=solo_activas.lower() == "true")
    return jsonify([c.to_dict() for c in query.order_by(Categoria.id_categoria.asc()).all()]), 200


@app.post("/categories")
def create_category():
    """Crear categoría o subcategoría (RF02)
    ---
    responses:
      201:
        description: Categoría creada
    """
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre de la categoría es obligatorio"}), 400
    cat = Categoria(
        nombre=nombre,
        descripcion=data.get("descripcion"),
        id_categoria_padre=data.get("id_categoria_padre"),
        activo=bool(data.get("activo", True)),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@app.put("/categories/<int:id_categoria>")
def update_category(id_categoria):
    """Actualizar categoría (RF02)
    ---
    responses:
      200:
        description: Categoría actualizada
    """
    cat = Categoria.query.get(id_categoria)
    if not cat:
        return jsonify({"error": "Categoría no encontrada"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("nombre", "descripcion", "id_categoria_padre", "activo"):
        if field in data:
            setattr(cat, field, data[field])
    db.session.commit()
    return jsonify(cat.to_dict()), 200


@app.delete("/categories/<int:id_categoria>")
def delete_category(id_categoria):
    """Dar de baja lógica una categoría (RF02)
    ---
    responses:
      200:
        description: Categoría desactivada
    """
    cat = Categoria.query.get(id_categoria)
    if not cat:
        return jsonify({"error": "Categoría no encontrada"}), 404
    cat.activo = False
    db.session.commit()
    return jsonify({"message": "Categoría desactivada", "categoria": cat.to_dict()}), 200


# --- Productos (RF01, RF12) ---
@app.get("/products")
def list_products():
    """Buscar y filtrar productos por nombre, código o categoría (RF01, RF12)
    ---
    parameters:
      - name: q
        in: query
        type: string
      - name: codigo
        in: query
        type: string
      - name: id_categoria
        in: query
        type: integer
    responses:
      200:
        description: Lista de productos
    """
    q = (request.args.get("q") or "").strip()
    codigo = (request.args.get("codigo") or "").strip()
    id_categoria = request.args.get("id_categoria", type=int)
    activo = request.args.get("activo")

    query = Producto.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Producto.nombre.ilike(like), Producto.codigo.ilike(like), Producto.descripcion.ilike(like))
        )
    if codigo:
        query = query.filter(Producto.codigo.ilike(f"%{codigo}%"))
    if id_categoria:
        query = query.filter_by(id_categoria=id_categoria)
    if activo is not None:
        query = query.filter_by(activo=activo.lower() == "true")

    productos = query.order_by(Producto.id_producto.asc()).all()
    return jsonify([p.to_dict() for p in productos]), 200


@app.get("/products/<int:id_producto>")
def get_product(id_producto):
    """Consultar un producto por ID (RF01)
    ---
    responses:
      200:
        description: Detalle del producto
      404:
        description: Producto no encontrado
    """
    prod = Producto.query.get(id_producto)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    return jsonify(prod.to_dict()), 200


@app.post("/products")
def create_product():
    """Crear un nuevo producto (RF01)
    ---
    responses:
      201:
        description: Producto creado
    """
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip().upper()
    nombre = (data.get("nombre") or "").strip()
    id_categoria = data.get("id_categoria")
    precio_venta = data.get("precio_venta")

    if not codigo or not nombre or not id_categoria or precio_venta is None:
        return jsonify({"error": "codigo, nombre, id_categoria y precio_venta son obligatorios"}), 400
    if Producto.query.filter_by(codigo=codigo).first():
        return jsonify({"error": f"Ya existe un producto con código {codigo}"}), 409
    if not Categoria.query.get(id_categoria):
        return jsonify({"error": "Categoría no encontrada"}), 404

    try:
        precio = Decimal(str(precio_venta))
        if precio < 0:
            raise InvalidOperation()
    except InvalidOperation:
        return jsonify({"error": "precio_venta debe ser un número mayor o igual a 0"}), 400

    prod = Producto(
        id_categoria=id_categoria,
        codigo=codigo,
        nombre=nombre,
        descripcion=data.get("descripcion", ""),
        unidad_medida=(data.get("unidad_medida") or "UNIDAD").upper(),
        precio_venta=precio,
        activo=bool(data.get("activo", True)),
    )
    db.session.add(prod)
    db.session.commit()
    return jsonify(prod.to_dict()), 201


@app.put("/products/<int:id_producto>")
def update_product(id_producto):
    """Actualizar un producto existente (RF01)
    ---
    responses:
      200:
        description: Producto actualizado
    """
    prod = Producto.query.get(id_producto)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    data = request.get_json(silent=True) or {}
    if "codigo" in data:
        new_code = data["codigo"].strip().upper()
        existing = Producto.query.filter_by(codigo=new_code).first()
        if existing and existing.id_producto != id_producto:
            return jsonify({"error": f"El código {new_code} ya está en uso"}), 409
        prod.codigo = new_code
    if "nombre" in data:
        prod.nombre = data["nombre"].strip()
    if "descripcion" in data:
        prod.descripcion = data["descripcion"]
    if "unidad_medida" in data:
        prod.unidad_medida = data["unidad_medida"].upper()
    if "id_categoria" in data:
        if not Categoria.query.get(data["id_categoria"]):
            return jsonify({"error": "Categoría no encontrada"}), 404
        prod.id_categoria = data["id_categoria"]
    if "precio_venta" in data:
        prod.precio_venta = Decimal(str(data["precio_venta"]))
    if "activo" in data:
        prod.activo = bool(data["activo"])
    db.session.commit()
    return jsonify(prod.to_dict()), 200


@app.delete("/products/<int:id_producto>")
def delete_product(id_producto):
    """Dar de baja lógica un producto (RF01)
    ---
    responses:
      200:
        description: Producto dado de baja
    """
    prod = Producto.query.get(id_producto)
    if not prod:
        return jsonify({"error": "Producto no encontrado"}), 404
    prod.activo = False
    db.session.commit()
    return jsonify({"message": "Producto dado de baja", "producto": prod.to_dict()}), 200


# --- Importación Excel/CSV (RF17) ---
@app.post("/products/import")
def import_products():
    """Importar productos desde archivo CSV o Excel (.xlsx) con validación fila por fila (RF17)
    ---
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
      - name: id_usuario
        in: formData
        type: integer
    responses:
      201:
        description: Resultado detallado de la importación
    """
    if "file" not in request.files:
        return jsonify({"error": "Debe adjuntar un archivo en el campo 'file'"}), 400

    file = request.files["file"]
    filename = file.filename or "importacion.csv"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"
    id_usuario = int(request.form.get("id_usuario", 1))

    rows = []
    try:
        if ext == "csv":
            content = file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
        elif ext in ("xlsx", "xlsm"):
            wb = load_workbook(io.BytesIO(file.read()), read_only=True)
            ws = wb.active
            raw_rows = list(ws.iter_rows(values_only=True))
            if raw_rows:
                headers = [str(h).strip().lower() if h is not None else "" for h in raw_rows[0]]
                for r in raw_rows[1:]:
                    rows.append({headers[i]: (r[i] if i < len(r) else None) for i in range(len(headers))})
        else:
            return jsonify({"error": "Formato no soportado. Use .csv o .xlsx"}), 400
    except Exception as exc:
        return jsonify({"error": f"Error leyendo el archivo: {exc}"}), 400

    imp = Importacion(
        id_usuario=id_usuario,
        nombre_archivo=filename,
        formato=ext.upper(),
        estado="EN_PROCESO",
        total_filas=len(rows),
    )
    db.session.add(imp)
    db.session.flush()

    validas = 0
    errores = 0
    default_cat = Categoria.query.first()

    for idx, row in enumerate(rows, start=2):
        norm = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
        codigo = str(norm.get("codigo") or "").strip().upper()
        nombre = str(norm.get("nombre") or "").strip()
        precio_raw = norm.get("precio_venta") or norm.get("precio")
        unidad = str(norm.get("unidad_medida") or "UNIDAD").strip().upper()
        desc = str(norm.get("descripcion") or "").strip()
        cat_raw = norm.get("id_categoria") or norm.get("categoria")

        error_msg = None
        prod_id = None

        if not codigo:
            error_msg = "Falta el campo 'codigo'"
        elif not nombre:
            error_msg = "Falta el campo 'nombre'"
        else:
            try:
                precio = Decimal(str(precio_raw))
                if precio < 0:
                    error_msg = "El precio no puede ser negativo"
            except (InvalidOperation, TypeError):
                error_msg = f"Precio inválido: {precio_raw}"

        cat_obj = None
        if not error_msg:
            if cat_raw is not None and str(cat_raw).strip() != "":
                if str(cat_raw).isdigit():
                    cat_obj = Categoria.query.get(int(cat_raw))
                else:
                    cat_obj = Categoria.query.filter(Categoria.nombre.ilike(str(cat_raw).strip())).first()
            if not cat_obj:
                cat_obj = default_cat

        if not error_msg:
            existing = Producto.query.filter_by(codigo=codigo).first()
            if existing:
                existing.nombre = nombre
                existing.descripcion = desc or existing.descripcion
                existing.unidad_medida = unidad
                existing.precio_venta = precio
                existing.id_categoria = cat_obj.id_categoria
                existing.activo = True
                prod_id = existing.id_producto
            else:
                nuevo = Producto(
                    id_categoria=cat_obj.id_categoria,
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=desc,
                    unidad_medida=unidad,
                    precio_venta=precio,
                    activo=True,
                )
                db.session.add(nuevo)
                db.session.flush()
                prod_id = nuevo.id_producto
            validas += 1
            estado_fila = "VALIDA"
        else:
            errores += 1
            estado_fila = "ERROR"

        db.session.add(
            DetalleImportacion(
                id_importacion=imp.id_importacion,
                id_producto=prod_id,
                numero_fila=idx,
                codigo_fuente=codigo or None,
                estado=estado_fila,
                mensaje_error=error_msg,
            )
        )

    imp.filas_validas = validas
    imp.filas_error = errores
    imp.estado = "COMPLETADO" if errores == 0 else ("PARCIAL" if validas > 0 else "FALLIDO")
    db.session.commit()

    return jsonify(imp.to_dict(include_details=True)), 201


@app.get("/imports")
def list_imports():
    """Listar historial de importaciones (RF17)
    ---
    responses:
      200:
        description: Historial de importaciones
    """
    imps = Importacion.query.order_by(Importacion.creado_en.desc()).all()
    return jsonify([i.to_dict() for i in imps]), 200


@app.get("/imports/<int:id_importacion>")
@app.get("/products/import/<int:id_importacion>")
def get_import(id_importacion):
    """Consultar detalle de una importación (RF17)
    ---
    responses:
      200:
        description: Detalle de importación
    """
    imp = Importacion.query.get(id_importacion)
    if not imp:
        return jsonify({"error": "Importación no encontrada"}), 404
    return jsonify(imp.to_dict(include_details=True)), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5002")), debug=True)

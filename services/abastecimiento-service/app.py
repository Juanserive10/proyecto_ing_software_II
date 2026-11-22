import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import requests
from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flasgger import Swagger
from sqlalchemy.orm import selectinload

logging.basicConfig(level=logging.INFO, format="%(asctime)s [abastecimiento-service] %(levelname)s: %(message)s")
logger = logging.getLogger("abastecimiento-service")

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
    "DATABASE_URL", "sqlite:///abastecimiento.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["INVENTARIO_URL"] = os.getenv("INVENTARIO_URL", "http://inventario-service:5003")
app.config["SWAGGER"] = {
    "title": "Distribuidora Andina - Abastecimiento API",
    "uiversion": 3,
    "version": "1.0.0",
    "description": "Microservicio de Proveedores, Órdenes de Compra y Recepción de Mercancía (RF03, RF06)",
}

db = SQLAlchemy(app)
swagger = Swagger(app)


# ==================== MODELOS (ER: Base de datos Abastecimiento) ====================
class Proveedor(db.Model):
    __tablename__ = "proveedor"
    id_proveedor = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identificacion = db.Column(db.String(40), unique=True, nullable=False, index=True)
    razon_social = db.Column(db.String(160), nullable=False)
    contacto = db.Column(db.String(120), nullable=True)
    correo = db.Column(db.String(150), nullable=True)
    telefono = db.Column(db.String(40), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            "id_proveedor": self.id_proveedor,
            "identificacion": self.identificacion,
            "razon_social": self.razon_social,
            "contacto": self.contacto,
            "correo": self.correo,
            "telefono": self.telefono,
            "activo": self.activo,
        }


class ProveedorProducto(db.Model):
    __tablename__ = "proveedor_producto"
    id_asociacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_proveedor = db.Column(db.Integer, db.ForeignKey("proveedor.id_proveedor"), nullable=False)
    id_producto = db.Column(db.Integer, nullable=False)
    codigo_proveedor = db.Column(db.String(60), nullable=True)
    costo_referencia = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    activo = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            "id_asociacion": self.id_asociacion,
            "id_proveedor": self.id_proveedor,
            "id_producto": self.id_producto,
            "codigo_proveedor": self.codigo_proveedor,
            "costo_referencia": float(self.costo_referencia),
            "activo": self.activo,
        }


class OrdenCompra(db.Model):
    __tablename__ = "orden_compra"
    id_orden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_proveedor = db.Column(db.Integer, db.ForeignKey("proveedor.id_proveedor"), nullable=False)
    id_usuario = db.Column(db.Integer, nullable=False, default=1)
    numero = db.Column(db.String(40), unique=True, nullable=False, index=True)
    estado = db.Column(db.String(30), nullable=False, default="EMITIDA")  # EMITIDA | PARCIAL | RECIBIDA | CANCELADA
    fecha_emision = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    total_estimado = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0.00"))

    proveedor = db.relationship("Proveedor", backref="ordenes", lazy=True)
    detalles = db.relationship("DetalleOrden", backref="orden", lazy=True, cascade="all, delete-orphan")
    recepciones = db.relationship("Recepcion", backref="orden", lazy=True)

    def to_dict(self, include_details=True):
        data = {
            "id_orden": self.id_orden,
            "id_proveedor": self.id_proveedor,
            "proveedor_nombre": self.proveedor.razon_social if self.proveedor else None,
            "id_usuario": self.id_usuario,
            "numero": self.numero,
            "estado": self.estado,
            "fecha_emision": self.fecha_emision.isoformat() if self.fecha_emision else None,
            "total_estimado": float(self.total_estimado),
        }
        if include_details:
            data["detalles"] = [d.to_dict() for d in self.detalles]
            data["recepciones"] = [r.to_dict() for r in self.recepciones]
        return data


class DetalleOrden(db.Model):
    __tablename__ = "detalle_orden"
    id_detalle_orden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_orden = db.Column(db.Integer, db.ForeignKey("orden_compra.id_orden"), nullable=False)
    id_producto = db.Column(db.Integer, nullable=False)
    cantidad_pedida = db.Column(db.Numeric(12, 2), nullable=False)
    costo_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)

    def to_dict(self):
        return {
            "id_detalle_orden": self.id_detalle_orden,
            "id_orden": self.id_orden,
            "id_producto": self.id_producto,
            "cantidad_pedida": float(self.cantidad_pedida),
            "costo_unitario": float(self.costo_unitario),
            "subtotal": float(self.subtotal),
        }


class Recepcion(db.Model):
    __tablename__ = "recepcion"
    id_recepcion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_orden = db.Column(db.Integer, db.ForeignKey("orden_compra.id_orden"), nullable=False)
    id_bodega = db.Column(db.Integer, nullable=False)
    id_usuario = db.Column(db.Integer, nullable=False, default=1)
    estado = db.Column(db.String(30), nullable=False, default="PENDIENTE")  # PENDIENTE | CONFIRMADA | RECHAZADA
    clave_idempotencia = db.Column(db.String(120), unique=True, nullable=True)
    recibido_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    detalles = db.relationship("DetalleRecepcion", backref="recepcion", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id_recepcion": self.id_recepcion,
            "id_orden": self.id_orden,
            "id_bodega": self.id_bodega,
            "id_usuario": self.id_usuario,
            "estado": self.estado,
            "clave_idempotencia": self.clave_idempotencia,
            "recibido_en": self.recibido_en.isoformat() if self.recibido_en else None,
            "detalles": [d.to_dict() for d in self.detalles],
        }


class DetalleRecepcion(db.Model):
    __tablename__ = "detalle_recepcion"
    id_detalle_recepcion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_recepcion = db.Column(db.Integer, db.ForeignKey("recepcion.id_recepcion"), nullable=False)
    id_detalle_orden = db.Column(db.Integer, db.ForeignKey("detalle_orden.id_detalle_orden"), nullable=False)
    cantidad_recibida = db.Column(db.Numeric(12, 2), nullable=False)
    condicion = db.Column(db.String(30), nullable=False, default="BUENO")

    def to_dict(self):
        return {
            "id_detalle_recepcion": self.id_detalle_recepcion,
            "id_recepcion": self.id_recepcion,
            "id_detalle_orden": self.id_detalle_orden,
            "cantidad_recibida": float(self.cantidad_recibida),
            "condicion": self.condicion,
        }


# ==================== SEED INICIAL ====================
def seed_data():
    if Proveedor.query.count() == 0:
        p1 = Proveedor(identificacion="NIT-900412345-1", razon_social="Ferretería Mayorista del Eje S.A.S.", contacto="Carlos Morales", correo="ventas@mayoristaeje.co", telefono="3104556789")
        p2 = Proveedor(identificacion="NIT-890123789-4", razon_social="Herramientas Industriales Andinas S.A.", contacto="Andrea López", correo="pedidos@herramientasandinas.co", telefono="3158901234")
        p3 = Proveedor(identificacion="NIT-901678234-2", razon_social="Pinturas y Tuberías de Colombia Ltda.", contacto="Jorge Ramírez", correo="comercial@pintubcol.co", telefono="3207654321")
        db.session.add_all([p1, p2, p3])
        db.session.commit()

        asocs = [
            ProveedorProducto(id_proveedor=p2.id_proveedor, id_producto=1, codigo_proveedor="HIA-TAL-750", costo_referencia=Decimal("185000.00")),
            ProveedorProducto(id_proveedor=p2.id_proveedor, id_producto=2, codigo_proveedor="HIA-PUL-850", costo_referencia=Decimal("140000.00")),
            ProveedorProducto(id_proveedor=p1.id_proveedor, id_producto=3, codigo_proveedor="FME-MAR-16", costo_referencia=Decimal("22000.00")),
            ProveedorProducto(id_proveedor=p1.id_proveedor, id_producto=6, codigo_proveedor="FME-TOR-1000", costo_referencia=Decimal("19500.00")),
            ProveedorProducto(id_proveedor=p3.id_proveedor, id_producto=8, codigo_proveedor="PTC-VIN-1G", costo_referencia=Decimal("58000.00")),
            ProveedorProducto(id_proveedor=p3.id_proveedor, id_producto=10, codigo_proveedor="PTC-PVC-05", costo_referencia=Decimal("12500.00")),
        ]
        db.session.add_all(asocs)

        oc = OrdenCompra(
            id_proveedor=p2.id_proveedor,
            id_usuario=1,
            numero="OC-2026-0001",
            estado="EMITIDA",
            total_estimado=Decimal("3250000.00"),
        )
        db.session.add(oc)
        db.session.flush()
        db.session.add_all([
            DetalleOrden(id_orden=oc.id_orden, id_producto=1, cantidad_pedida=Decimal("10"), costo_unitario=Decimal("185000.00"), subtotal=Decimal("1850000.00")),
            DetalleOrden(id_orden=oc.id_orden, id_producto=2, cantidad_pedida=Decimal("10"), costo_unitario=Decimal("140000.00"), subtotal=Decimal("1400000.00")),
        ])
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()


# ==================== ENDPOINTS ====================
@app.get("/health")
def health():
    """Estado de salud del microservicio de Abastecimiento
    ---
    responses:
      200:
        description: Servicio activo
    """
    return jsonify({"service": "abastecimiento-service", "status": "ok"}), 200


# --- Proveedores (RF03) ---
@app.get("/suppliers")
def list_suppliers():
    """Listar proveedores (RF03)
    ---
    responses:
      200:
        description: Lista de proveedores
    """
    return jsonify([p.to_dict() for p in Proveedor.query.order_by(Proveedor.id_proveedor.asc()).all()]), 200


@app.post("/suppliers")
def create_supplier():
    """Crear proveedor (RF03)
    ---
    responses:
      201:
        description: Proveedor creado
    """
    data = request.get_json(silent=True) or {}
    ident = (data.get("identificacion") or "").strip().upper()
    razon = (data.get("razon_social") or "").strip()
    if not ident or not razon:
        return jsonify({"error": "identificacion y razon_social son obligatorios"}), 400
    if Proveedor.query.filter_by(identificacion=ident).first():
        return jsonify({"error": f"Ya existe un proveedor con identificación {ident}"}), 409

    prov = Proveedor(
        identificacion=ident,
        razon_social=razon,
        contacto=data.get("contacto"),
        correo=data.get("correo"),
        telefono=data.get("telefono"),
        activo=bool(data.get("activo", True)),
    )
    db.session.add(prov)
    db.session.commit()
    return jsonify(prov.to_dict()), 201


@app.put("/suppliers/<int:id_proveedor>")
def update_supplier(id_proveedor):
    """Actualizar proveedor (RF03)
    ---
    responses:
      200:
        description: Proveedor actualizado
    """
    prov = Proveedor.query.get(id_proveedor)
    if not prov:
        return jsonify({"error": "Proveedor no encontrado"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("razon_social", "contacto", "correo", "telefono", "activo"):
        if field in data:
            setattr(prov, field, data[field])
    db.session.commit()
    return jsonify(prov.to_dict()), 200


@app.delete("/suppliers/<int:id_proveedor>")
def delete_supplier(id_proveedor):
    """Desactivar proveedor (RF03)
    ---
    responses:
      200:
        description: Proveedor desactivado
    """
    prov = Proveedor.query.get(id_proveedor)
    if not prov:
        return jsonify({"error": "Proveedor no encontrado"}), 404
    prov.activo = False
    db.session.commit()
    return jsonify({"message": "Proveedor desactivado", "proveedor": prov.to_dict()}), 200


@app.get("/suppliers/<int:id_proveedor>/products")
def list_supplier_products(id_proveedor):
    """Listar productos asociados a un proveedor (RF03)
    ---
    responses:
      200:
        description: Asociaciones proveedor-producto
    """
    asocs = ProveedorProducto.query.filter_by(id_proveedor=id_proveedor).all()
    return jsonify([a.to_dict() for a in asocs]), 200


@app.post("/suppliers/<int:id_proveedor>/products")
def associate_supplier_product(id_proveedor):
    """Asociar producto a proveedor (RF03)
    ---
    responses:
      201:
        description: Asociación creada
    """
    if not Proveedor.query.get(id_proveedor):
        return jsonify({"error": "Proveedor no encontrado"}), 404
    data = request.get_json(silent=True) or {}
    if not data.get("id_producto"):
        return jsonify({"error": "id_producto es obligatorio"}), 400
    asoc = ProveedorProducto(
        id_proveedor=id_proveedor,
        id_producto=int(data["id_producto"]),
        codigo_proveedor=data.get("codigo_proveedor"),
        costo_referencia=Decimal(str(data.get("costo_referencia", 0))),
        activo=True,
    )
    db.session.add(asoc)
    db.session.commit()
    return jsonify(asoc.to_dict()), 201


# --- Órdenes de Compra (RF06) ---
@app.get("/purchase-orders")
def list_purchase_orders():
    """Listar órdenes de compra (RF06)
    ---
    responses:
      200:
        description: Lista de órdenes de compra
    """
    limit = min(max(request.args.get("limit", default=100, type=int), 1), 1000)
    ordenes = (
        OrdenCompra.query.options(
            selectinload(OrdenCompra.proveedor),
            selectinload(OrdenCompra.detalles),
            selectinload(OrdenCompra.recepciones).selectinload(Recepcion.detalles),
        )
        .order_by(OrdenCompra.fecha_emision.desc(), OrdenCompra.id_orden.desc())
        .limit(limit)
        .all()
    )
    return jsonify([o.to_dict(include_details=True) for o in ordenes]), 200


@app.get("/purchase-orders/<int:id_orden>")
def get_purchase_order(id_orden):
    """Consultar orden de compra por ID (RF06)
    ---
    responses:
      200:
        description: Detalle de orden de compra
    """
    oc = OrdenCompra.query.get(id_orden)
    if not oc:
        return jsonify({"error": "Orden de compra no encontrada"}), 404
    return jsonify(oc.to_dict(include_details=True)), 200


@app.post("/purchase-orders")
def create_purchase_order():
    """Crear orden de compra a proveedor (RF06)
    ---
    responses:
      201:
        description: Orden de compra creada
    """
    data = request.get_json(silent=True) or {}
    id_proveedor = data.get("id_proveedor")
    items = data.get("items") or []
    if not id_proveedor or not items:
        return jsonify({"error": "id_proveedor e items son obligatorios"}), 400
    if not Proveedor.query.get(id_proveedor):
        return jsonify({"error": "Proveedor no encontrado"}), 404

    custom_numero = data.get("numero")

    oc = OrdenCompra(
        id_proveedor=id_proveedor,
        id_usuario=int(data.get("id_usuario", 1)),
        numero=custom_numero or f"TMP-{uuid.uuid4().hex[:12]}",
        estado="EMITIDA",
        total_estimado=Decimal("0.00"),
    )
    db.session.add(oc)
    db.session.flush()
    if not custom_numero:
        oc.numero = f"OC-2026-{oc.id_orden:04d}"

    total = Decimal("0.00")
    for item in items:
        cant = Decimal(str(item["cantidad_pedida"]))
        costo = Decimal(str(item["costo_unitario"]))
        sub = cant * costo
        total += sub
        db.session.add(
            DetalleOrden(
                id_orden=oc.id_orden,
                id_producto=int(item["id_producto"]),
                cantidad_pedida=cant,
                costo_unitario=costo,
                subtotal=sub,
            )
        )
    oc.total_estimado = total
    db.session.commit()
    return jsonify(oc.to_dict(include_details=True)), 201


@app.patch("/purchase-orders/<int:id_orden>")
def update_purchase_order_status(id_orden):
    """Actualizar estado de una orden de compra (RF06)
    ---
    responses:
      200:
        description: Estado actualizado
    """
    oc = OrdenCompra.query.get(id_orden)
    if not oc:
        return jsonify({"error": "Orden de compra no encontrada"}), 404
    data = request.get_json(silent=True) or {}
    nuevo_estado = (data.get("estado") or "").strip().upper()
    if nuevo_estado not in ("EMITIDA", "PARCIAL", "RECIBIDA", "CANCELADA"):
        return jsonify({"error": "estado inválido"}), 400
    if oc.estado == "RECIBIDA" and nuevo_estado == "CANCELADA":
        return jsonify({"error": "No se puede cancelar una orden ya recibida"}), 400
    oc.estado = nuevo_estado
    db.session.commit()
    return jsonify(oc.to_dict(include_details=True)), 200


@app.post("/purchase-orders/<int:id_orden>/receipts")
def receive_purchase_order(id_orden):
    """Registrar recepción (parcial o total) de una orden de compra y notificar entrada a Inventario (RF06)
    ---
    responses:
      201:
        description: Recepción confirmada en Inventario
      502:
        description: Error al comunicar entrada con Inventario
    """
    oc = OrdenCompra.query.get(id_orden)
    if not oc:
        return jsonify({"error": "Orden de compra no encontrada"}), 404
    if oc.estado == "CANCELADA":
        return jsonify({"error": "No se puede recibir mercancía de una orden cancelada"}), 400

    data = request.get_json(silent=True) or {}
    id_bodega = data.get("id_bodega")
    items = data.get("items") or []
    id_usuario = int(data.get("id_usuario", 1))
    idem_key = data.get("clave_idempotencia") or f"REC-{id_orden}-{uuid.uuid4().hex[:10]}"

    if not id_bodega or not items:
        return jsonify({"error": "id_bodega e items son obligatorios"}), 400

    existing_rec = Recepcion.query.filter_by(clave_idempotencia=idem_key).first()
    if existing_rec:
        return jsonify({"idempotent": True, "recepcion": existing_rec.to_dict()}), 200

    # Crear recepción en estado PENDIENTE
    rec = Recepcion(
        id_orden=oc.id_orden,
        id_bodega=int(id_bodega),
        id_usuario=id_usuario,
        estado="PENDIENTE",
        clave_idempotencia=idem_key,
    )
    db.session.add(rec)
    db.session.flush()

    detalles_orden_map = {d.id_detalle_orden: d for d in oc.detalles}
    movimientos_para_enviar = []

    for item in items:
        id_det = item.get("id_detalle_orden")
        det_orden = detalles_orden_map.get(id_det)
        if not det_orden and item.get("id_producto"):
            det_orden = next((d for d in oc.detalles if d.id_producto == int(item["id_producto"])), None)
        if not det_orden:
            db.session.rollback()
            return jsonify({"error": f"Detalle de orden no válido: {item}"}), 400

        cant_rec = Decimal(str(item["cantidad_recibida"]))
        if cant_rec <= 0:
            db.session.rollback()
            return jsonify({"error": "cantidad_recibida debe ser mayor a 0"}), 400

        db.session.add(
            DetalleRecepcion(
                id_recepcion=rec.id_recepcion,
                id_detalle_orden=det_orden.id_detalle_orden,
                cantidad_recibida=cant_rec,
                condicion=(item.get("condicion") or "BUENO").upper(),
            )
        )
        movimientos_para_enviar.append((det_orden.id_producto, cant_rec, det_orden.costo_unitario))

    db.session.commit()

    # Flujo síncrono Abastecimiento -> Inventario (ENTRADA)
    inv_url = app.config["INVENTARIO_URL"].rstrip("/")
    req_headers = {"X-Request-Id": getattr(g, "request_id", str(uuid.uuid4()))}
    inventario_responses = []
    try:
        for idx, (id_prod, cant_rec, costo_u) in enumerate(movimientos_para_enviar):
            resp = requests.post(
                f"{inv_url}/inventory/movements",
                json={
                    "tipo": "ENTRADA",
                    "id_producto": id_prod,
                    "cantidad": float(cant_rec),
                    "id_bodega_destino": int(id_bodega),
                    "id_usuario": id_usuario,
                    "tipo_referencia": "RECEPCION_OC",
                    "id_referencia": rec.id_recepcion,
                    "clave_idempotencia": f"{idem_key}-ITEM-{idx}",
                    "precio_referencia": float(costo_u),
                },
                headers=req_headers,
                timeout=8,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Inventario rechazó entrada: {resp.status_code} {resp.text}")
            inventario_responses.append(resp.json())
    except Exception as exc:
        rec.estado = "RECHAZADA"
        db.session.commit()
        return jsonify({
            "error": "No se pudo confirmar la entrada en el microservicio de Inventario",
            "detail": str(exc),
            "recepcion": rec.to_dict(),
        }), 502

    # Solo queda CONFIRMADA si Inventario confirmó todas las entradas
    rec.estado = "CONFIRMADA"

    # Recalcular estado de la orden de compra (PARCIAL vs RECIBIDA)
    recibido_por_det = {}
    for r in oc.recepciones:
        if r.estado == "CONFIRMADA":
            for dr in r.detalles:
                recibido_por_det[dr.id_detalle_orden] = recibido_por_det.get(dr.id_detalle_orden, Decimal("0")) + Decimal(dr.cantidad_recibida)

    completa = all(recibido_por_det.get(d.id_detalle_orden, Decimal("0")) >= Decimal(d.cantidad_pedida) for d in oc.detalles)
    oc.estado = "RECIBIDA" if completa else "PARCIAL"
    db.session.commit()

    return jsonify({
        "recepcion": rec.to_dict(),
        "orden_estado": oc.estado,
        "inventario_confirmaciones": inventario_responses,
    }), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5004")), debug=True)

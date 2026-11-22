import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import httpx
import pika
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, selectinload, Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ventas-service] %(levelname)s: %(message)s")
logger = logging.getLogger("ventas-service")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ventas.db")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario-service:5003").rstrip("/")
CATALOGO_URL = os.getenv("CATALOGO_URL", "http://catalogo-service:5002").rstrip("/")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "andina.events")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=20, max_overflow=30, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
http_client = httpx.Client(timeout=8.0, limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))


# ==================== MODELOS (ER: Base de datos Ventas) ====================
class Venta(Base):
    __tablename__ = "venta"
    id_venta = Column(Integer, primary_key=True, autoincrement=True)
    id_bodega = Column(Integer, nullable=False, index=True)
    id_usuario = Column(Integer, nullable=False, default=1, index=True)
    numero = Column(String(40), unique=True, nullable=False, index=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    estado = Column(String(30), nullable=False, default="PENDIENTE")  # PENDIENTE | CONFIRMADA | RECHAZADA
    metodo_pago = Column(String(40), nullable=False, default="EFECTIVO")  # EFECTIVO | TRANSFERENCIA | TARJETA
    subtotal = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    clave_idempotencia = Column(String(120), unique=True, nullable=True, index=True)

    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")


class DetalleVenta(Base):
    __tablename__ = "detalle_venta"
    id_detalle_venta = Column(Integer, primary_key=True, autoincrement=True)
    id_venta = Column(Integer, ForeignKey("venta.id_venta"), nullable=False)
    id_producto = Column(Integer, nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(14, 2), nullable=False)

    venta = relationship("Venta", back_populates="detalles")


# ==================== SCHEMAS PYDANTIC ====================
class VentaItemCreate(BaseModel):
    id_producto: int
    cantidad: Decimal = Field(..., gt=0)
    precio_unitario: Optional[Decimal] = Field(None, ge=0)


class VentaCreate(BaseModel):
    id_bodega: int = 1
    id_usuario: int = 1
    metodo_pago: str = Field("EFECTIVO", description="EFECTIVO, TRANSFERENCIA o TARJETA")
    clave_idempotencia: Optional[str] = None
    items: List[VentaItemCreate] = Field(..., min_length=1)


# ==================== RABBITMQ PUBLISHER ====================
def publish_event(routing_key: str, payload: dict):
    if not RABBITMQ_URL:
        return
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        params.socket_timeout = 2
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=json.dumps(payload, default=str),
            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
        )
        connection.close()
        logger.info("Evento publicado [%s]: %s", routing_key, payload)
    except Exception as exc:
        logger.warning("No se pudo publicar evento RabbitMQ (%s): %s", routing_key, exc)


# ==================== APP ====================
app = FastAPI(
    title="Distribuidora Andina - Ventas API",
    version="1.0.0",
    description="Registro de ventas operativas, descuento automático de stock e historial (RF15, RF16)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = req_id
    started = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - started) * 1000, 1)
    response.headers["X-Request-Id"] = req_id
    logger.info("request_id=%s method=%s path=%s status=%s ms=%s", req_id, request.method, request.url.path, response.status_code, ms)
    return response


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)


def iso_utc(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def serialize_venta(v: Venta):
    return {
        "id_venta": v.id_venta,
        "id_bodega": v.id_bodega,
        "id_usuario": v.id_usuario,
        "numero": v.numero,
        "fecha": iso_utc(v.fecha),
        "estado": v.estado,
        "metodo_pago": v.metodo_pago,
        "subtotal": float(v.subtotal),
        "total": float(v.total),
        "clave_idempotencia": v.clave_idempotencia,
        "detalles": [
            {
                "id_detalle_venta": d.id_detalle_venta,
                "id_producto": d.id_producto,
                "cantidad": float(d.cantidad),
                "precio_unitario": float(d.precio_unitario),
                "subtotal": float(d.subtotal),
            }
            for d in v.detalles
        ],
    }


@app.get("/health")
def health():
    return {"service": "ventas-service", "status": "ok"}


@app.get("/sales")
def list_sales(
    id_usuario: Optional[int] = Query(None),
    metodo_pago: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Venta).options(selectinload(Venta.detalles))
    if id_usuario is not None:
        query = query.filter(Venta.id_usuario == id_usuario)
    if metodo_pago:
        query = query.filter(Venta.metodo_pago == metodo_pago.upper())
    if estado:
        query = query.filter(Venta.estado == estado.upper())
    if fecha_desde:
        query = query.filter(Venta.fecha >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        query = query.filter(Venta.fecha <= datetime.fromisoformat(fecha_hasta))

    ventas = query.order_by(Venta.fecha.desc(), Venta.id_venta.desc()).limit(limit).all()
    return [serialize_venta(v) for v in ventas]


@app.get("/sales/{id_venta}")
def get_sale(id_venta: int, db: Session = Depends(get_db)):
    v = db.query(Venta).filter_by(id_venta=id_venta).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return serialize_venta(v)


@app.post("/sales", status_code=201)
def create_sale(payload: VentaCreate, request: Request, db: Session = Depends(get_db)):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    trace_headers = {"X-Request-Id": req_id}
    idem_key = payload.clave_idempotencia or f"VTA-{uuid.uuid4().hex[:12]}"
    existing = db.query(Venta).filter_by(clave_idempotencia=idem_key).first()
    if existing:
        return {"idempotent": True, "venta": serialize_venta(existing)}

    # 1. Resolver precios desde Catálogo si no fueron enviados
    resolved_items = []
    for item in payload.items:
        precio = item.precio_unitario
        if precio is None:
            try:
                r = http_client.get(f"{CATALOGO_URL}/products/{item.id_producto}", headers=trace_headers)
                if r.status_code != 200:
                    raise HTTPException(status_code=404, detail=f"Producto {item.id_producto} no encontrado en Catálogo")
                precio = Decimal(str(r.json()["precio_venta"]))
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Error consultando Catálogo: {exc}")
        resolved_items.append((item.id_producto, item.cantidad, precio))

    # 2. Registrar Venta en estado PENDIENTE (numero derivado de PK autoincremental para evitar colisiones concurrentes)
    subtotal = sum(cant * prec for _, cant, prec in resolved_items)

    venta = Venta(
        id_bodega=payload.id_bodega,
        id_usuario=payload.id_usuario,
        numero=f"TMP-{uuid.uuid4().hex[:12]}",
        estado="PENDIENTE",
        metodo_pago=payload.metodo_pago.upper(),
        subtotal=subtotal,
        total=subtotal,
        clave_idempotencia=idem_key,
    )
    db.add(venta)
    db.flush()
    venta.numero = f"VTA-2026-{venta.id_venta:05d}"

    for id_prod, cant, prec in resolved_items:
        db.add(
            DetalleVenta(
                id_venta=venta.id_venta,
                id_producto=id_prod,
                cantidad=cant,
                precio_unitario=prec,
                subtotal=cant * prec,
            )
        )
    db.commit()
    db.refresh(venta)

    # 3. Flujo síncrono Ventas -> Inventario (SALIDA por cada ítem con compensación Saga si alguno falla)
    descontados = []
    try:
        for idx, (id_prod, cant, prec) in enumerate(resolved_items):
            resp = http_client.post(
                f"{INVENTARIO_URL}/inventory/movements",
                headers=trace_headers,
                json={
                    "tipo": "SALIDA",
                    "id_producto": id_prod,
                    "cantidad": float(cant),
                    "id_bodega_origen": payload.id_bodega,
                    "id_usuario": payload.id_usuario,
                    "tipo_referencia": "VENTA",
                    "id_referencia": venta.id_venta,
                    "clave_idempotencia": f"{idem_key}-ITEM-{idx}",
                    "precio_referencia": float(prec),
                },
            )
            if resp.status_code not in (200, 201):
                detail_msg = resp.json().get("detail", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                raise RuntimeError(f"Stock/Inventario rechazó producto {id_prod}: {detail_msg}")
            descontados.append((idx, id_prod, cant, prec))
    except Exception as exc:
        # Compensación (Saga): devolver al stock los ítems que sí alcanzaron a descontarse
        for idx, id_prod, cant, prec in descontados:
            try:
                http_client.post(
                    f"{INVENTARIO_URL}/inventory/movements",
                    headers=trace_headers,
                    json={
                        "tipo": "ENTRADA",
                        "id_producto": id_prod,
                        "cantidad": float(cant),
                        "id_bodega_destino": payload.id_bodega,
                        "id_usuario": payload.id_usuario,
                        "tipo_referencia": "COMPENSACION_VENTA",
                        "id_referencia": venta.id_venta,
                        "clave_idempotencia": f"{idem_key}-COMP-{idx}",
                        "precio_referencia": float(prec),
                    },
                )
            except Exception as comp_exc:
                logger.error("Error en compensación de inventario para venta %s: %s", venta.id_venta, comp_exc)

        venta.estado = "RECHAZADA"
        db.commit()
        raise HTTPException(
            status_code=409,
            detail={
                "message": "La venta fue rechazada porque Inventario no pudo descontar las existencias",
                "reason": str(exc),
                "venta": serialize_venta(venta),
            },
        )

    # 4. Confirmar venta y publicar evento asíncrono hacia Reportes
    venta.estado = "CONFIRMADA"
    db.commit()
    db.refresh(venta)

    publish_event(
        "sales.confirmed",
        {
            "id_venta": venta.id_venta,
            "numero": venta.numero,
            "id_bodega": venta.id_bodega,
            "id_usuario": venta.id_usuario,
            "metodo_pago": venta.metodo_pago,
            "total": float(venta.total),
            "fecha": venta.fecha.isoformat(),
            "items": [
                {
                    "id_producto": d.id_producto,
                    "cantidad": float(d.cantidad),
                    "precio_unitario": float(d.precio_unitario),
                    "subtotal": float(d.subtotal),
                }
                for d in venta.detalles
            ],
        },
    )

    return {"venta": serialize_venta(venta)}

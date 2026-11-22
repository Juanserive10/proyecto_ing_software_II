import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import pika
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, declarative_base, Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [inventario-service] %(levelname)s: %(message)s")
logger = logging.getLogger("inventario-service")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inventario.db")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "andina.events")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==================== MODELOS (ER: Base de datos Inventario) ====================
class Bodega(Base):
    __tablename__ = "bodega"
    id_bodega = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(40), unique=True, nullable=False, index=True)
    nombre = Column(String(120), nullable=False)
    ubicacion = Column(String(200), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)


class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = (UniqueConstraint("id_bodega", "id_producto", name="uq_stock_bodega_producto"),)

    id_stock = Column(Integer, primary_key=True, autoincrement=True)
    id_bodega = Column(Integer, ForeignKey("bodega.id_bodega"), nullable=False, index=True)
    id_producto = Column(Integer, nullable=False, index=True)
    cantidad_disponible = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    cantidad_no_vendible = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    version = Column(Integer, nullable=False, default=1)
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Movimiento(Base):
    __tablename__ = "movimiento"
    id_movimiento = Column(Integer, primary_key=True, autoincrement=True)
    id_bodega_origen = Column(Integer, ForeignKey("bodega.id_bodega"), nullable=True)
    id_bodega_destino = Column(Integer, ForeignKey("bodega.id_bodega"), nullable=True)
    id_producto = Column(Integer, nullable=False, index=True)
    id_usuario = Column(Integer, nullable=False, default=1)
    tipo = Column(String(40), nullable=False, index=True)
    cantidad = Column(Numeric(12, 2), nullable=False)
    tipo_referencia = Column(String(50), nullable=True)
    id_referencia = Column(Integer, nullable=True)
    clave_idempotencia = Column(String(120), unique=True, nullable=True, index=True)
    ocurrido_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class Devolucion(Base):
    __tablename__ = "devolucion"
    id_devolucion = Column(Integer, primary_key=True, autoincrement=True)
    id_bodega = Column(Integer, ForeignKey("bodega.id_bodega"), nullable=False)
    id_movimiento = Column(Integer, ForeignKey("movimiento.id_movimiento"), nullable=False)
    id_producto = Column(Integer, nullable=False)
    id_usuario = Column(Integer, nullable=False, default=1)
    origen = Column(String(30), nullable=False)  # CLIENTE | PROVEEDOR
    referencia_externa = Column(Integer, nullable=True)
    cantidad = Column(Numeric(12, 2), nullable=False)
    condicion = Column(String(30), nullable=False, default="BUENO")  # BUENO | DANADO
    motivo = Column(String(255), nullable=True)
    estado = Column(String(30), nullable=False, default="COMPLETADA")
    registrado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ==================== SCHEMAS PYDANTIC ====================
class BodegaCreate(BaseModel):
    codigo: str = Field(..., min_length=2, max_length=40)
    nombre: str = Field(..., min_length=2, max_length=120)
    ubicacion: Optional[str] = None
    activo: bool = True


class BodegaUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=2, max_length=40)
    nombre: Optional[str] = Field(None, min_length=2, max_length=120)
    ubicacion: Optional[str] = None
    activo: Optional[bool] = None


class MovimientoCreate(BaseModel):
    tipo: str = Field(..., description="ENTRADA, SALIDA, AJUSTE_POSITIVO, AJUSTE_NEGATIVO")
    id_producto: int
    cantidad: Decimal = Field(..., gt=0)
    id_bodega_origen: Optional[int] = None
    id_bodega_destino: Optional[int] = None
    id_usuario: int = 1
    tipo_referencia: Optional[str] = "MANUAL"
    id_referencia: Optional[int] = None
    clave_idempotencia: Optional[str] = None
    precio_referencia: Optional[Decimal] = None


class TrasladoCreate(BaseModel):
    id_bodega_origen: int
    id_bodega_destino: int
    id_producto: int
    cantidad: Decimal = Field(..., gt=0)
    id_usuario: int = 1
    clave_idempotencia: Optional[str] = None


class DevolucionCreate(BaseModel):
    origen: str = Field(..., description="CLIENTE o PROVEEDOR")
    id_bodega: int
    id_producto: int
    cantidad: Decimal = Field(..., gt=0)
    condicion: str = Field("BUENO", description="BUENO o DANADO")
    motivo: Optional[str] = None
    referencia_externa: Optional[int] = None
    id_usuario: int = 1
    clave_idempotencia: Optional[str] = None


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


# ==================== APP & SEED ====================
app = FastAPI(
    title="Distribuidora Andina - Inventario y Almacenes API",
    version="1.0.0",
    description="Control de stock por bodega, Kardex, traslados y devoluciones (RF04, RF05, RF10, RF13)",
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


def seed_data():
    db = SessionLocal()
    try:
        if db.query(Bodega).count() == 0:
            b1 = Bodega(codigo="BOD-01", nombre="Bodega Principal Manizales", ubicacion="Zona Industrial Maltería, Manizales", activo=True)
            b2 = Bodega(codigo="BOD-02", nombre="Punto de Almacenamiento Norte", ubicacion="Av. Santander #45-12, Manizales", activo=True)
            db.add_all([b1, b2])
            db.commit()
            db.refresh(b1)
            db.refresh(b2)

            # Stock inicial realista para los 10 productos del catálogo semilla
            initial_stocks = [
                (b1.id_bodega, 1, 18), (b2.id_bodega, 1, 6),
                (b1.id_bodega, 2, 14), (b2.id_bodega, 2, 5),
                (b1.id_bodega, 3, 45), (b2.id_bodega, 3, 12),
                (b1.id_bodega, 4, 30), (b2.id_bodega, 4, 8),
                (b1.id_bodega, 5, 25), (b2.id_bodega, 5, 7),
                (b1.id_bodega, 6, 60), (b2.id_bodega, 6, 15),
                (b1.id_bodega, 7, 80), (b2.id_bodega, 7, 20),
                (b1.id_bodega, 8, 22), (b2.id_bodega, 8, 4),
                (b1.id_bodega, 9, 35), (b2.id_bodega, 9, 9),
                (b1.id_bodega, 10, 50), (b2.id_bodega, 10, 14),
            ]
            for id_bod, id_prod, cant in initial_stocks:
                db.add(Stock(id_bodega=id_bod, id_producto=id_prod, cantidad_disponible=Decimal(str(cant)), cantidad_no_vendible=Decimal("0")))
                db.add(
                    Movimiento(
                        id_bodega_destino=id_bod,
                        id_producto=id_prod,
                        id_usuario=1,
                        tipo="ENTRADA",
                        cantidad=Decimal(str(cant)),
                        tipo_referencia="INVENTARIO_INICIAL",
                        id_referencia=0,
                    )
                )
            db.commit()
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
seed_data()


def get_or_create_stock(db: Session, id_bodega: int, id_producto: int, lock: bool = True) -> Stock:
    q = db.query(Stock).filter_by(id_bodega=id_bodega, id_producto=id_producto)
    if lock and not DATABASE_URL.startswith("sqlite"):
        q = q.with_for_update()
    stock = q.first()
    if not stock:
        try:
            with db.begin_nested():
                stock = Stock(
                    id_bodega=id_bodega,
                    id_producto=id_producto,
                    cantidad_disponible=Decimal("0.00"),
                    cantidad_no_vendible=Decimal("0.00"),
                    version=1,
                )
                db.add(stock)
                db.flush()
        except IntegrityError:
            q = db.query(Stock).filter_by(id_bodega=id_bodega, id_producto=id_producto)
            if lock and not DATABASE_URL.startswith("sqlite"):
                q = q.with_for_update()
            stock = q.first()
    return stock


def serialize_stock(s: Stock, bodega_map: dict):
    b = bodega_map.get(s.id_bodega)
    return {
        "id_stock": s.id_stock,
        "id_bodega": s.id_bodega,
        "bodega_codigo": b.codigo if b else None,
        "bodega_nombre": b.nombre if b else None,
        "id_producto": s.id_producto,
        "cantidad_disponible": float(s.cantidad_disponible),
        "cantidad_no_vendible": float(s.cantidad_no_vendible),
        "version": s.version,
        "actualizado_en": s.actualizado_en.isoformat() if s.actualizado_en else None,
    }


def serialize_mov(m: Movimiento):
    return {
        "id_movimiento": m.id_movimiento,
        "id_bodega_origen": m.id_bodega_origen,
        "id_bodega_destino": m.id_bodega_destino,
        "id_producto": m.id_producto,
        "id_usuario": m.id_usuario,
        "tipo": m.tipo,
        "cantidad": float(m.cantidad),
        "tipo_referencia": m.tipo_referencia,
        "id_referencia": m.id_referencia,
        "clave_idempotencia": m.clave_idempotencia,
        "ocurrido_en": m.ocurrido_en.isoformat() if m.ocurrido_en else None,
    }


# ==================== ENDPOINTS ====================
@app.get("/health")
def health():
    return {"service": "inventario-service", "status": "ok"}


@app.get("/warehouses")
def list_warehouses(db: Session = Depends(get_db)):
    bodegas = db.query(Bodega).order_by(Bodega.id_bodega.asc()).all()
    return [
        {
            "id_bodega": b.id_bodega,
            "codigo": b.codigo,
            "nombre": b.nombre,
            "ubicacion": b.ubicacion,
            "activo": b.activo,
        }
        for b in bodegas
    ]


@app.post("/warehouses", status_code=201)
def create_warehouse(payload: BodegaCreate, db: Session = Depends(get_db)):
    code = payload.codigo.strip().upper()
    if db.query(Bodega).filter_by(codigo=code).first():
        raise HTTPException(status_code=409, detail=f"Ya existe una bodega con código {code}")
    b = Bodega(codigo=code, nombre=payload.nombre.strip(), ubicacion=payload.ubicacion, activo=payload.activo)
    db.add(b)
    db.commit()
    db.refresh(b)
    return {
        "id_bodega": b.id_bodega,
        "codigo": b.codigo,
        "nombre": b.nombre,
        "ubicacion": b.ubicacion,
        "activo": b.activo,
    }


@app.get("/warehouses/{id_bodega}")
def get_warehouse(id_bodega: int, db: Session = Depends(get_db)):
    b = db.query(Bodega).get(id_bodega)
    if not b:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    return {
        "id_bodega": b.id_bodega,
        "codigo": b.codigo,
        "nombre": b.nombre,
        "ubicacion": b.ubicacion,
        "activo": b.activo,
    }


@app.patch("/warehouses/{id_bodega}")
def update_warehouse(id_bodega: int, payload: BodegaUpdate, db: Session = Depends(get_db)):
    b = db.query(Bodega).get(id_bodega)
    if not b:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    if payload.codigo is not None:
        code = payload.codigo.strip().upper()
        existing = db.query(Bodega).filter_by(codigo=code).first()
        if existing and existing.id_bodega != id_bodega:
            raise HTTPException(status_code=409, detail=f"Ya existe una bodega con código {code}")
        b.codigo = code
    if payload.nombre is not None:
        b.nombre = payload.nombre.strip()
    if payload.ubicacion is not None:
        b.ubicacion = payload.ubicacion
    if payload.activo is not None:
        b.activo = payload.activo
    db.commit()
    db.refresh(b)
    return {
        "id_bodega": b.id_bodega,
        "codigo": b.codigo,
        "nombre": b.nombre,
        "ubicacion": b.ubicacion,
        "activo": b.activo,
    }


@app.get("/inventory/stock")
def list_stock(
    id_producto: Optional[int] = Query(None),
    id_bodega: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Stock)
    if id_producto is not None:
        query = query.filter(Stock.id_producto == id_producto)
    if id_bodega is not None:
        query = query.filter(Stock.id_bodega == id_bodega)
    stocks = query.order_by(Stock.id_bodega.asc(), Stock.id_producto.asc()).all()
    bodega_map = {b.id_bodega: b for b in db.query(Bodega).all()}
    return [serialize_stock(s, bodega_map) for s in stocks]


@app.get("/inventory/movements")
def list_movements(
    id_producto: Optional[int] = Query(None),
    id_bodega: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Movimiento)
    if id_producto is not None:
        query = query.filter(Movimiento.id_producto == id_producto)
    if id_bodega is not None:
        query = query.filter((Movimiento.id_bodega_origen == id_bodega) | (Movimiento.id_bodega_destino == id_bodega))
    if tipo:
        query = query.filter(Movimiento.tipo == tipo.upper())
    movs = query.order_by(Movimiento.ocurrido_en.desc(), Movimiento.id_movimiento.desc()).limit(limit).all()
    return [serialize_mov(m) for m in movs]


@app.post("/inventory/movements", status_code=201)
def create_movement(payload: MovimientoCreate, db: Session = Depends(get_db)):
    tipo = payload.tipo.upper()
    if tipo not in ("ENTRADA", "SALIDA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO"):
        raise HTTPException(status_code=400, detail="tipo debe ser ENTRADA, SALIDA, AJUSTE_POSITIVO o AJUSTE_NEGATIVO")

    # Idempotencia
    if payload.clave_idempotencia:
        existing = db.query(Movimiento).filter_by(clave_idempotencia=payload.clave_idempotencia).first()
        if existing:
            return {"idempotent": True, "movimiento": serialize_mov(existing)}

    if tipo in ("ENTRADA", "AJUSTE_POSITIVO"):
        if not payload.id_bodega_destino:
            raise HTTPException(status_code=400, detail=f"{tipo} requiere id_bodega_destino")
        if not db.query(Bodega).get(payload.id_bodega_destino):
            raise HTTPException(status_code=404, detail="Bodega destino no encontrada")
        stock = get_or_create_stock(db, payload.id_bodega_destino, payload.id_producto)
        stock.cantidad_disponible = Decimal(stock.cantidad_disponible) + payload.cantidad
        stock.version += 1
        stock.actualizado_en = datetime.now(timezone.utc)
        target_bodega = payload.id_bodega_destino
    else:
        if not payload.id_bodega_origen:
            raise HTTPException(status_code=400, detail=f"{tipo} requiere id_bodega_origen")
        if not db.query(Bodega).get(payload.id_bodega_origen):
            raise HTTPException(status_code=404, detail="Bodega origen no encontrada")
        stock = get_or_create_stock(db, payload.id_bodega_origen, payload.id_producto)
        if Decimal(stock.cantidad_disponible) < payload.cantidad:
            raise HTTPException(
                status_code=409,
                detail=f"Stock insuficiente en bodega {payload.id_bodega_origen} para producto {payload.id_producto}. Disponible: {float(stock.cantidad_disponible)}, solicitado: {float(payload.cantidad)}",
            )
        stock.cantidad_disponible = Decimal(stock.cantidad_disponible) - payload.cantidad
        stock.version += 1
        stock.actualizado_en = datetime.now(timezone.utc)
        target_bodega = payload.id_bodega_origen

    mov = Movimiento(
        id_bodega_origen=payload.id_bodega_origen if tipo in ("SALIDA", "AJUSTE_NEGATIVO") else None,
        id_bodega_destino=payload.id_bodega_destino if tipo in ("ENTRADA", "AJUSTE_POSITIVO") else None,
        id_producto=payload.id_producto,
        id_usuario=payload.id_usuario,
        tipo=tipo,
        cantidad=payload.cantidad,
        tipo_referencia=payload.tipo_referencia,
        id_referencia=payload.id_referencia,
        clave_idempotencia=payload.clave_idempotencia,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    db.refresh(stock)

    event_data = {
        "id_movimiento": mov.id_movimiento,
        "id_producto": mov.id_producto,
        "id_bodega": target_bodega,
        "tipo": mov.tipo,
        "cantidad": float(mov.cantidad),
        "cantidad_disponible": float(stock.cantidad_disponible),
        "version": stock.version,
        "precio_referencia": float(payload.precio_referencia) if payload.precio_referencia is not None else None,
        "ocurrido_en": mov.ocurrido_en.isoformat(),
    }
    publish_event("inventory.stock.updated", event_data)
    publish_event("inventory.movement.created", event_data)

    return {
        "movimiento": serialize_mov(mov),
        "stock_actual": float(stock.cantidad_disponible),
        "version": stock.version,
    }


@app.post("/inventory/transfers", status_code=201)
def create_transfer(payload: TrasladoCreate, db: Session = Depends(get_db)):
    if payload.id_bodega_origen == payload.id_bodega_destino:
        raise HTTPException(status_code=400, detail="La bodega de origen y destino deben ser diferentes")
    if not db.query(Bodega).get(payload.id_bodega_origen) or not db.query(Bodega).get(payload.id_bodega_destino):
        raise HTTPException(status_code=404, detail="Bodega origen o destino no encontrada")

    if payload.clave_idempotencia:
        existing = db.query(Movimiento).filter_by(clave_idempotencia=payload.clave_idempotencia).first()
        if existing:
            return {"idempotent": True, "movimiento": serialize_mov(existing)}

    # Bloquear filas de stock en orden determinístico por id_bodega para evitar deadlocks
    if payload.id_bodega_origen < payload.id_bodega_destino:
        stock_origen = get_or_create_stock(db, payload.id_bodega_origen, payload.id_producto)
        stock_destino = get_or_create_stock(db, payload.id_bodega_destino, payload.id_producto)
    else:
        stock_destino = get_or_create_stock(db, payload.id_bodega_destino, payload.id_producto)
        stock_origen = get_or_create_stock(db, payload.id_bodega_origen, payload.id_producto)

    if Decimal(stock_origen.cantidad_disponible) < payload.cantidad:
        raise HTTPException(
            status_code=409,
            detail=f"Stock insuficiente en bodega origen ({float(stock_origen.cantidad_disponible)} disponible)",
        )

    now = datetime.now(timezone.utc)
    stock_origen.cantidad_disponible = Decimal(stock_origen.cantidad_disponible) - payload.cantidad
    stock_origen.version += 1
    stock_origen.actualizado_en = now

    stock_destino.cantidad_disponible = Decimal(stock_destino.cantidad_disponible) + payload.cantidad
    stock_destino.version += 1
    stock_destino.actualizado_en = now

    mov = Movimiento(
        id_bodega_origen=payload.id_bodega_origen,
        id_bodega_destino=payload.id_bodega_destino,
        id_producto=payload.id_producto,
        id_usuario=payload.id_usuario,
        tipo="TRASLADO",
        cantidad=payload.cantidad,
        tipo_referencia="TRASLADO_INTERNO",
        clave_idempotencia=payload.clave_idempotencia,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)

    for bod_id, st_obj, mov_tipo in [
        (payload.id_bodega_origen, stock_origen, "SALIDA"),
        (payload.id_bodega_destino, stock_destino, "ENTRADA"),
    ]:
        ev = {
            "id_movimiento": mov.id_movimiento,
            "id_producto": mov.id_producto,
            "id_bodega": bod_id,
            "tipo": mov_tipo,
            "cantidad": float(mov.cantidad),
            "cantidad_disponible": float(st_obj.cantidad_disponible),
            "version": st_obj.version,
            "ocurrido_en": mov.ocurrido_en.isoformat(),
        }
        publish_event("inventory.stock.updated", ev)
        publish_event("inventory.movement.created", ev)

    return {
        "movimiento": serialize_mov(mov),
        "stock_origen": float(stock_origen.cantidad_disponible),
        "stock_destino": float(stock_destino.cantidad_disponible),
    }


@app.get("/inventory/returns")
def list_returns(db: Session = Depends(get_db)):
    devs = db.query(Devolucion).order_by(Devolucion.registrado_en.desc()).all()
    return [
        {
            "id_devolucion": d.id_devolucion,
            "id_bodega": d.id_bodega,
            "id_movimiento": d.id_movimiento,
            "id_producto": d.id_producto,
            "id_usuario": d.id_usuario,
            "origen": d.origen,
            "referencia_externa": d.referencia_externa,
            "cantidad": float(d.cantidad),
            "condicion": d.condicion,
            "motivo": d.motivo,
            "estado": d.estado,
            "registrado_en": d.registrado_en.isoformat() if d.registrado_en else None,
        }
        for d in devs
    ]


@app.post("/inventory/returns", status_code=201)
def create_return(payload: DevolucionCreate, db: Session = Depends(get_db)):
    origen = payload.origen.upper()
    condicion = payload.condicion.upper()
    if origen not in ("CLIENTE", "PROVEEDOR"):
        raise HTTPException(status_code=400, detail="origen debe ser CLIENTE o PROVEEDOR")
    if not db.query(Bodega).get(payload.id_bodega):
        raise HTTPException(status_code=404, detail="Bodega no encontrada")

    stock = get_or_create_stock(db, payload.id_bodega, payload.id_producto)
    now = datetime.now(timezone.utc)

    if origen == "CLIENTE":
        tipo_mov = "DEVOLUCION_CLIENTE"
        if condicion == "BUENO":
            stock.cantidad_disponible = Decimal(stock.cantidad_disponible) + payload.cantidad
        else:
            stock.cantidad_no_vendible = Decimal(stock.cantidad_no_vendible) + payload.cantidad
        bodega_origen, bodega_destino = None, payload.id_bodega
    else:
        tipo_mov = "DEVOLUCION_PROVEEDOR"
        if Decimal(stock.cantidad_disponible) < payload.cantidad:
            raise HTTPException(status_code=409, detail="Stock disponible insuficiente para devolver al proveedor")
        stock.cantidad_disponible = Decimal(stock.cantidad_disponible) - payload.cantidad
        bodega_origen, bodega_destino = payload.id_bodega, None

    stock.version += 1
    stock.actualizado_en = now

    mov = Movimiento(
        id_bodega_origen=bodega_origen,
        id_bodega_destino=bodega_destino,
        id_producto=payload.id_producto,
        id_usuario=payload.id_usuario,
        tipo=tipo_mov,
        cantidad=payload.cantidad,
        tipo_referencia=f"DEVOLUCION_{origen}",
        id_referencia=payload.referencia_externa,
        clave_idempotencia=payload.clave_idempotencia,
    )
    db.add(mov)
    db.flush()

    dev = Devolucion(
        id_bodega=payload.id_bodega,
        id_movimiento=mov.id_movimiento,
        id_producto=payload.id_producto,
        id_usuario=payload.id_usuario,
        origen=origen,
        referencia_externa=payload.referencia_externa,
        cantidad=payload.cantidad,
        condicion=condicion,
        motivo=payload.motivo,
        estado="COMPLETADA",
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)

    ev = {
        "id_movimiento": mov.id_movimiento,
        "id_producto": mov.id_producto,
        "id_bodega": payload.id_bodega,
        "tipo": "ENTRADA" if origen == "CLIENTE" else "SALIDA",
        "cantidad": float(mov.cantidad),
        "cantidad_disponible": float(stock.cantidad_disponible),
        "version": stock.version,
        "ocurrido_en": mov.ocurrido_en.isoformat(),
    }
    publish_event("inventory.stock.updated", ev)
    publish_event("inventory.movement.created", ev)

    return {
        "id_devolucion": dev.id_devolucion,
        "id_movimiento": mov.id_movimiento,
        "origen": dev.origen,
        "condicion": dev.condicion,
        "stock_disponible": float(stock.cantidad_disponible),
        "stock_no_vendible": float(stock.cantidad_no_vendible),
    }

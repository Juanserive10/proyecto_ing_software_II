import json
import logging
import os
import threading
import time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
import pika
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [reportes-service] %(levelname)s: %(message)s")
logger = logging.getLogger("reportes-service")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reportes.db")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "andina.events")
QUEUE_NAME = os.getenv("RABBITMQ_QUEUE", "reportes.events.queue")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario-service:5003").rstrip("/")
CATALOGO_URL = os.getenv("CATALOGO_URL", "http://catalogo-service:5002").rstrip("/")
VENTAS_URL = os.getenv("VENTAS_URL", "http://ventas-service:5005").rstrip("/")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==================== MODELOS (ER: Base de datos Reportes) ====================
class Umbral(Base):
    __tablename__ = "umbral"
    id_umbral = Column(Integer, primary_key=True, autoincrement=True)
    id_producto = Column(Integer, nullable=False, index=True)
    id_bodega = Column(Integer, nullable=False, index=True)
    cantidad_minima = Column(Numeric(12, 2), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Alerta(Base):
    __tablename__ = "alerta"
    id_alerta = Column(Integer, primary_key=True, autoincrement=True)
    id_umbral = Column(Integer, ForeignKey("umbral.id_umbral"), nullable=False)
    saldo_observado = Column(Numeric(12, 2), nullable=False)
    estado = Column(String(30), nullable=False, default="ACTIVA")  # ACTIVA | ATENDIDA
    id_evento_origen = Column(Integer, nullable=True)
    generada_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    atendida_en = Column(DateTime, nullable=True)

    umbral = relationship("Umbral", backref="alertas")


class ResumenStock(Base):
    __tablename__ = "resumen_stock"
    id_resumen_stock = Column(Integer, primary_key=True, autoincrement=True)
    id_producto = Column(Integer, nullable=False, index=True)
    id_bodega = Column(Integer, nullable=False, index=True)
    cantidad_disponible = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    valor_estimado = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    version_fuente = Column(String(40), nullable=True)


class ResumenMovimiento(Base):
    __tablename__ = "resumen_movimiento"
    id_resumen_mov = Column(Integer, primary_key=True, autoincrement=True)
    id_producto = Column(Integer, nullable=False, index=True)
    id_bodega = Column(Integer, nullable=False, index=True)
    periodo_inicio = Column(Date, nullable=False)
    periodo_fin = Column(Date, nullable=False)
    entradas = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    salidas = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    rotacion = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ResumenVenta(Base):
    __tablename__ = "resumen_venta"
    id_resumen_venta = Column(Integer, primary_key=True, autoincrement=True)
    id_producto = Column(Integer, nullable=False, index=True)
    periodo_inicio = Column(Date, nullable=False)
    periodo_fin = Column(Date, nullable=False)
    unidades_vendidas = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    ingreso = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ==================== SCHEMAS PYDANTIC ====================
class UmbralCreate(BaseModel):
    id_producto: int
    id_bodega: int
    cantidad_minima: Decimal = Field(..., ge=0)
    activo: bool = True


# ==================== LÓGICA DE EVENTOS ====================
def current_month_range():
    today = date.today()
    first = today.replace(day=1)
    if today.month == 12:
        last = today.replace(day=31)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
        last = date.fromordinal(next_month.toordinal() - 1)
    return first, last


def evaluate_threshold(db: Session, id_producto: int, id_bodega: int, saldo: Decimal, id_evento: Optional[int] = None):
    umbral = db.query(Umbral).filter_by(id_producto=id_producto, id_bodega=id_bodega, activo=True).first()
    if not umbral:
        return
    if saldo <= Decimal(umbral.cantidad_minima):
        # Evitar duplicar alerta activa para el mismo umbral
        active = db.query(Alerta).filter_by(id_umbral=umbral.id_umbral, estado="ACTIVA").first()
        if active:
            active.saldo_observado = saldo
            active.id_evento_origen = id_evento
        else:
            db.add(
                Alerta(
                    id_umbral=umbral.id_umbral,
                    saldo_observado=saldo,
                    estado="ACTIVA",
                    id_evento_origen=id_evento,
                )
            )
    else:
        # Si ya se repuso stock por encima del umbral, marcar alertas activas como atendidas
        actives = db.query(Alerta).filter_by(id_umbral=umbral.id_umbral, estado="ACTIVA").all()
        now = datetime.now(timezone.utc)
        for a in actives:
            a.estado = "ATENDIDA"
            a.atendida_en = now


def handle_event(routing_key: str, data: dict):
    db = SessionLocal()
    try:
        p_ini, p_fin = current_month_range()
        now = datetime.now(timezone.utc)

        if routing_key == "inventory.stock.updated":
            id_prod = int(data["id_producto"])
            id_bod = int(data["id_bodega"])
            cant = Decimal(str(data["cantidad_disponible"]))
            precio = Decimal(str(data.get("precio_referencia") or 0))
            res = db.query(ResumenStock).filter_by(id_producto=id_prod, id_bodega=id_bod).first()
            if not res:
                res = ResumenStock(
                    id_producto=id_prod,
                    id_bodega=id_bod,
                    cantidad_disponible=cant,
                    valor_estimado=cant * precio,
                    version_fuente=str(data.get("version", "")),
                    actualizado_en=now,
                )
                db.add(res)
            else:
                unit_val = precio if precio > 0 else (
                    Decimal(res.valor_estimado) / Decimal(res.cantidad_disponible)
                    if Decimal(res.cantidad_disponible) > 0
                    else Decimal("0")
                )
                res.cantidad_disponible = cant
                if unit_val > 0:
                    res.valor_estimado = cant * unit_val
                res.version_fuente = str(data.get("version", ""))
                res.actualizado_en = now

            evaluate_threshold(db, id_prod, id_bod, cant, data.get("id_movimiento"))
            db.commit()

        elif routing_key == "inventory.movement.created":
            id_prod = int(data["id_producto"])
            id_bod = int(data["id_bodega"])
            tipo = str(data.get("tipo", "")).upper()
            cant = Decimal(str(data["cantidad"]))

            rm = (
                db.query(ResumenMovimiento)
                .filter_by(id_producto=id_prod, id_bodega=id_bod, periodo_inicio=p_ini, periodo_fin=p_fin)
                .first()
            )
            if not rm:
                rm = ResumenMovimiento(
                    id_producto=id_prod,
                    id_bodega=id_bod,
                    periodo_inicio=p_ini,
                    periodo_fin=p_fin,
                    entradas=Decimal("0"),
                    salidas=Decimal("0"),
                    rotacion=Decimal("0"),
                )
                db.add(rm)
                db.flush()

            if tipo in ("ENTRADA", "AJUSTE_POSITIVO", "DEVOLUCION_CLIENTE"):
                rm.entradas = Decimal(rm.entradas) + cant
            else:
                rm.salidas = Decimal(rm.salidas) + cant

            base_rot = Decimal(rm.entradas) if Decimal(rm.entradas) > 0 else Decimal("1")
            rm.rotacion = (Decimal(rm.salidas) / base_rot).quantize(Decimal("0.0001"))
            rm.actualizado_en = now
            db.commit()

        elif routing_key == "sales.confirmed":
            for item in data.get("items", []):
                id_prod = int(item["id_producto"])
                cant = Decimal(str(item["cantidad"]))
                sub = Decimal(str(item["subtotal"]))
                rv = (
                    db.query(ResumenVenta)
                    .filter_by(id_producto=id_prod, periodo_inicio=p_ini, periodo_fin=p_fin)
                    .first()
                )
                if not rv:
                    rv = ResumenVenta(
                        id_producto=id_prod,
                        periodo_inicio=p_ini,
                        periodo_fin=p_fin,
                        unidades_vendidas=cant,
                        ingreso=sub,
                        actualizado_en=now,
                    )
                    db.add(rv)
                else:
                    rv.unidades_vendidas = Decimal(rv.unidades_vendidas) + cant
                    rv.ingreso = Decimal(rv.ingreso) + sub
                    rv.actualizado_en = now
            db.commit()
    except Exception as exc:
        logger.error("Error procesando evento %s: %s", routing_key, exc)
        db.rollback()
    finally:
        db.close()


def rabbitmq_consumer_loop():
    if not RABBITMQ_URL:
        logger.info("RABBITMQ_URL no configurada; consumidor en modo espera.")
        return
    while True:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key="inventory.#")
            channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key="sales.#")

            def callback(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode("utf-8"))
                    handle_event(method.routing_key, payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as exc:
                    logger.error("Error en callback RabbitMQ: %s", exc)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            logger.info("Consumidor RabbitMQ conectado en cola '%s'", QUEUE_NAME)
            channel.start_consuming()
        except Exception as exc:
            logger.warning("RabbitMQ no disponible aún (%s). Reintentando en 5s...", exc)
            time.sleep(5)


# ==================== APP & SEED ====================
app = FastAPI(
    title="Distribuidora Andina - Reportes y Alertas API",
    version="1.0.0",
    description="Alertas de stock mínimo, reportes operativos y dashboard de indicadores (RF09, RF11, RF14)",
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
        if db.query(Umbral).count() == 0:
            # Umbrales por defecto para bodegas 1 y 2
            umbrales = [
                Umbral(id_producto=1, id_bodega=1, cantidad_minima=Decimal("10")),
                Umbral(id_producto=1, id_bodega=2, cantidad_minima=Decimal("8")),
                Umbral(id_producto=2, id_bodega=1, cantidad_minima=Decimal("10")),
                Umbral(id_producto=2, id_bodega=2, cantidad_minima=Decimal("6")),
                Umbral(id_producto=3, id_bodega=1, cantidad_minima=Decimal("15")),
                Umbral(id_producto=8, id_bodega=2, cantidad_minima=Decimal("5")),
                Umbral(id_producto=10, id_bodega=1, cantidad_minima=Decimal("20")),
            ]
            db.add_all(umbrales)
            db.commit()
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
seed_data()

if RABBITMQ_URL:
    t = threading.Thread(target=rabbitmq_consumer_loop, daemon=True)
    t.start()


# ==================== ENDPOINTS ====================
@app.get("/health")
def health():
    return {"service": "reportes-service", "status": "ok", "rabbitmq_enabled": bool(RABBITMQ_URL)}


@app.post("/reports/sync")
def sync_from_services(db: Session = Depends(get_db)):
    """Sincroniza los modelos de lectura de Reportes consultando Catálogo, Inventario y Ventas."""
    now = datetime.now(timezone.utc)
    p_ini, p_fin = current_month_range()
    synced = {"stocks": 0, "ventas": 0, "alertas_evaluadas": 0}

    with httpx.Client(timeout=8.0) as client:
        precios = {}
        try:
            r_cat = client.get(f"{CATALOGO_URL}/products")
            if r_cat.status_code == 200:
                for p in r_cat.json():
                    precios[int(p["id_producto"])] = Decimal(str(p["precio_venta"]))
        except Exception as exc:
            logger.warning("No se pudo leer Catálogo en sync: %s", exc)

        try:
            r_inv = client.get(f"{INVENTARIO_URL}/inventory/stock")
            if r_inv.status_code == 200:
                for s in r_inv.json():
                    id_prod = int(s["id_producto"])
                    id_bod = int(s["id_bodega"])
                    cant = Decimal(str(s["cantidad_disponible"]))
                    val = cant * precios.get(id_prod, Decimal("0"))

                    res = db.query(ResumenStock).filter_by(id_producto=id_prod, id_bodega=id_bod).first()
                    if not res:
                        db.add(
                            ResumenStock(
                                id_producto=id_prod,
                                id_bodega=id_bod,
                                cantidad_disponible=cant,
                                valor_estimado=val,
                                version_fuente=str(s.get("version", "")),
                                actualizado_en=now,
                            )
                        )
                    else:
                        res.cantidad_disponible = cant
                        res.valor_estimado = val
                        res.version_fuente = str(s.get("version", ""))
                        res.actualizado_en = now

                    evaluate_threshold(db, id_prod, id_bod, cant)
                    synced["stocks"] += 1
                    synced["alertas_evaluadas"] += 1
        except Exception as exc:
            logger.warning("No se pudo leer Inventario en sync: %s", exc)

        try:
            r_vta = client.get(f"{VENTAS_URL}/sales", params={"estado": "CONFIRMADA", "limit": 1000})
            if r_vta.status_code == 200:
                agg = {}
                for v in r_vta.json():
                    for d in v.get("detalles", []):
                        pid = int(d["id_producto"])
                        u, ing = agg.get(pid, (Decimal("0"), Decimal("0")))
                        agg[pid] = (u + Decimal(str(d["cantidad"])), ing + Decimal(str(d["subtotal"])))
                for pid, (u, ing) in agg.items():
                    rv = db.query(ResumenVenta).filter_by(id_producto=pid, periodo_inicio=p_ini, periodo_fin=p_fin).first()
                    if not rv:
                        db.add(ResumenVenta(id_producto=pid, periodo_inicio=p_ini, periodo_fin=p_fin, unidades_vendidas=u, ingreso=ing, actualizado_en=now))
                    else:
                        rv.unidades_vendidas = u
                        rv.ingreso = ing
                        rv.actualizado_en = now
                    synced["ventas"] += 1
        except Exception as exc:
            logger.warning("No se pudo leer Ventas en sync: %s", exc)

        try:
            r_mov = client.get(f"{INVENTARIO_URL}/inventory/movements", params={"limit": 500})
            if r_mov.status_code == 200:
                mov_agg = {}
                for m in r_mov.json():
                    occ_str = (m.get("ocurrido_en") or "")[:10]
                    if occ_str:
                        occ_d = date.fromisoformat(occ_str)
                        if not (p_ini <= occ_d <= p_fin):
                            continue
                    pid = int(m["id_producto"])
                    cant = Decimal(str(m["cantidad"]))
                    tipo = str(m.get("tipo", "")).upper()
                    if tipo == "TRASLADO":
                        pairs = [
                            (m.get("id_bodega_origen"), Decimal("0"), cant),
                            (m.get("id_bodega_destino"), cant, Decimal("0")),
                        ]
                    elif tipo in ("ENTRADA", "AJUSTE_POSITIVO", "DEVOLUCION_CLIENTE"):
                        pairs = [(m.get("id_bodega_destino"), cant, Decimal("0"))]
                    else:
                        pairs = [(m.get("id_bodega_origen"), Decimal("0"), cant)]

                    for bid, ent, sal in pairs:
                        if not bid:
                            continue
                        prev_e, prev_s = mov_agg.get((pid, int(bid)), (Decimal("0"), Decimal("0")))
                        mov_agg[(pid, int(bid))] = (prev_e + ent, prev_s + sal)

                for (pid, bid), (ent, sal) in mov_agg.items():
                    base_rot = ent if ent > 0 else Decimal("1")
                    rot = (sal / base_rot).quantize(Decimal("0.0001"))
                    rm = db.query(ResumenMovimiento).filter_by(
                        id_producto=pid, id_bodega=bid, periodo_inicio=p_ini, periodo_fin=p_fin
                    ).first()
                    if not rm:
                        db.add(ResumenMovimiento(
                            id_producto=pid, id_bodega=bid, periodo_inicio=p_ini, periodo_fin=p_fin,
                            entradas=ent, salidas=sal, rotacion=rot, actualizado_en=now,
                        ))
                    else:
                        rm.entradas = ent
                        rm.salidas = sal
                        rm.rotacion = rot
                        rm.actualizado_en = now
        except Exception as exc:
            logger.warning("No se pudo leer Movimientos en sync: %s", exc)

    db.commit()
    return {"message": "Sincronización completada", "synced": synced}


@app.get("/reports/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    stocks = db.query(ResumenStock).all()
    ventas = db.query(ResumenVenta).all()
    alertas_activas = db.query(Alerta).filter_by(estado="ACTIVA").count()
    movs = db.query(ResumenMovimiento).all()

    valor_total_inventario = sum(float(s.valor_estimado) for s in stocks)
    unidades_totales = sum(float(s.cantidad_disponible) for s in stocks)
    quiebres_stock = sum(1 for s in stocks if float(s.cantidad_disponible) <= 0)
    ingresos_periodo = sum(float(v.ingreso) for v in ventas)
    unidades_vendidas = sum(float(v.unidades_vendidas) for v in ventas)
    rotacion_promedio = (
        sum(float(m.rotacion) for m in movs) / len(movs) if movs else 0.0
    )

    top_vendidos = sorted(ventas, key=lambda v: float(v.unidades_vendidas), reverse=True)[:5]

    return {
        "valor_total_inventario": round(valor_total_inventario, 2),
        "unidades_totales_stock": round(unidades_totales, 2),
        "quiebres_stock": quiebres_stock,
        "alertas_activas": alertas_activas,
        "ingresos_periodo": round(ingresos_periodo, 2),
        "unidades_vendidas": round(unidades_vendidas, 2),
        "rotacion_promedio": round(rotacion_promedio, 4),
        "top_productos_vendidos": [
            {
                "id_producto": v.id_producto,
                "unidades_vendidas": float(v.unidades_vendidas),
                "ingreso": float(v.ingreso),
            }
            for v in top_vendidos
        ],
    }


@app.get("/reports/inventory")
def report_inventory(id_bodega: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(ResumenStock)
    if id_bodega is not None:
        q = q.filter(ResumenStock.id_bodega == id_bodega)
    rows = q.order_by(ResumenStock.id_bodega.asc(), ResumenStock.id_producto.asc()).all()
    return [
        {
            "id_resumen_stock": r.id_resumen_stock,
            "id_producto": r.id_producto,
            "id_bodega": r.id_bodega,
            "cantidad_disponible": float(r.cantidad_disponible),
            "valor_estimado": float(r.valor_estimado),
            "version_fuente": r.version_fuente,
            "actualizado_en": r.actualizado_en.isoformat() if r.actualizado_en else None,
        }
        for r in rows
    ]


@app.get("/reports/sales")
def report_sales(db: Session = Depends(get_db)):
    rows = db.query(ResumenVenta).order_by(ResumenVenta.ingreso.desc()).all()
    return [
        {
            "id_resumen_venta": r.id_resumen_venta,
            "id_producto": r.id_producto,
            "periodo_inicio": r.periodo_inicio.isoformat(),
            "periodo_fin": r.periodo_fin.isoformat(),
            "unidades_vendidas": float(r.unidades_vendidas),
            "ingreso": float(r.ingreso),
            "actualizado_en": r.actualizado_en.isoformat() if r.actualizado_en else None,
        }
        for r in rows
    ]


@app.get("/reports/movements")
def report_movements(db: Session = Depends(get_db)):
    rows = db.query(ResumenMovimiento).order_by(ResumenMovimiento.rotacion.desc()).all()
    return [
        {
            "id_resumen_mov": r.id_resumen_mov,
            "id_producto": r.id_producto,
            "id_bodega": r.id_bodega,
            "periodo_inicio": r.periodo_inicio.isoformat(),
            "periodo_fin": r.periodo_fin.isoformat(),
            "entradas": float(r.entradas),
            "salidas": float(r.salidas),
            "rotacion": float(r.rotacion),
            "actualizado_en": r.actualizado_en.isoformat() if r.actualizado_en else None,
        }
        for r in rows
    ]


# --- Umbrales y Alertas (RF09) ---
@app.get("/thresholds")
def list_thresholds(db: Session = Depends(get_db)):
    rows = db.query(Umbral).order_by(Umbral.id_umbral.asc()).all()
    return [
        {
            "id_umbral": u.id_umbral,
            "id_producto": u.id_producto,
            "id_bodega": u.id_bodega,
            "cantidad_minima": float(u.cantidad_minima),
            "activo": u.activo,
            "actualizado_en": u.actualizado_en.isoformat() if u.actualizado_en else None,
        }
        for u in rows
    ]


@app.post("/thresholds", status_code=201)
def create_or_update_threshold(payload: UmbralCreate, db: Session = Depends(get_db)):
    u = db.query(Umbral).filter_by(id_producto=payload.id_producto, id_bodega=payload.id_bodega).first()
    if u:
        u.cantidad_minima = payload.cantidad_minima
        u.activo = payload.activo
        u.actualizado_en = datetime.now(timezone.utc)
    else:
        u = Umbral(
            id_producto=payload.id_producto,
            id_bodega=payload.id_bodega,
            cantidad_minima=payload.cantidad_minima,
            activo=payload.activo,
        )
        db.add(u)
    db.commit()
    db.refresh(u)

    # Re-evaluar si ya existe resumen de stock
    rs = db.query(ResumenStock).filter_by(id_producto=u.id_producto, id_bodega=u.id_bodega).first()
    if rs:
        evaluate_threshold(db, u.id_producto, u.id_bodega, Decimal(rs.cantidad_disponible))
        db.commit()

    return {
        "id_umbral": u.id_umbral,
        "id_producto": u.id_producto,
        "id_bodega": u.id_bodega,
        "cantidad_minima": float(u.cantidad_minima),
        "activo": u.activo,
    }


@app.get("/alerts")
def list_alerts(estado: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Alerta)
    if estado:
        q = q.filter(Alerta.estado == estado.upper())
    rows = q.order_by(Alerta.generada_en.desc()).all()
    return [
        {
            "id_alerta": a.id_alerta,
            "id_umbral": a.id_umbral,
            "id_producto": a.umbral.id_producto if a.umbral else None,
            "id_bodega": a.umbral.id_bodega if a.umbral else None,
            "cantidad_minima": float(a.umbral.cantidad_minima) if a.umbral else None,
            "saldo_observado": float(a.saldo_observado),
            "estado": a.estado,
            "id_evento_origen": a.id_evento_origen,
            "generada_en": a.generada_en.isoformat() if a.generada_en else None,
            "atendida_en": a.atendida_en.isoformat() if a.atendida_en else None,
        }
        for a in rows
    ]


@app.post("/alerts/{id_alerta}/ack")
@app.post("/alerts/{id_alerta}/acknowledge")
def acknowledge_alert(id_alerta: int, db: Session = Depends(get_db)):
    a = db.query(Alerta).filter_by(id_alerta=id_alerta).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    a.estado = "ATENDIDA"
    a.atendida_en = datetime.now(timezone.utc)
    db.commit()
    return {"id_alerta": a.id_alerta, "estado": a.estado, "atendida_en": a.atendida_en.isoformat()}

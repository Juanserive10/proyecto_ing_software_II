import os
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from functools import wraps

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flasgger import Swagger
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///usuarios.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "andina-jwt-super-secret-2026")
app.config["JWT_EXP_HOURS"] = int(os.getenv("JWT_EXP_HOURS", "12"))
app.config["SWAGGER"] = {
    "title": "Distribuidora Andina - Usuarios y Seguridad API",
    "uiversion": 3,
    "version": "1.0.0",
    "description": "Microservicio de Identidad, Roles y Autenticación JWT (RF07, RF08, RNF07)",
}

db = SQLAlchemy(app)
swagger = Swagger(app)

# Lista simple de tokens revocados en memoria (logout)
REVOKED_TOKENS = set()


# ==================== MODELOS (ER: Base de datos Identidad) ====================
class Rol(db.Model):
    __tablename__ = "rol"
    id_rol = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(60), unique=True, nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    permisos = db.Column(db.String(500), nullable=False, default="read")

    def to_dict(self):
        return {
            "id_rol": self.id_rol,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "activo": self.activo,
            "permisos": self.permisos.split(",") if self.permisos else [],
        }


class Usuario(db.Model):
    __tablename__ = "usuario"
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_rol = db.Column(db.Integer, db.ForeignKey("rol.id_rol"), nullable=False)
    correo = db.Column(db.String(150), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="ACTIVO")
    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ultimo_acceso_en = db.Column(db.DateTime, nullable=True)

    rol = db.relationship("Rol", backref="usuarios", lazy=True)

    def to_dict(self):
        return {
            "id_usuario": self.id_usuario,
            "id_rol": self.id_rol,
            "rol": self.rol.nombre if self.rol else None,
            "permisos": self.rol.permisos.split(",") if self.rol and self.rol.permisos else [],
            "correo": self.correo,
            "nombre": self.nombre,
            "estado": self.estado,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "ultimo_acceso_en": self.ultimo_acceso_en.isoformat() if self.ultimo_acceso_en else None,
        }


class RecuperacionClave(db.Model):
    __tablename__ = "recuperacion_clave"
    id_recuperacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=False)
    token_hash = db.Column(db.String(128), nullable=False, index=True)
    vence_en = db.Column(db.DateTime, nullable=False)
    usado_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# ==================== UTILIDADES JWT ====================
def create_token(usuario: Usuario) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id_usuario),
        "id_usuario": usuario.id_usuario,
        "correo": usuario.correo,
        "nombre": usuario.nombre,
        "rol": usuario.rol.nombre if usuario.rol else "OPERADOR_BODEGA",
        "permisos": usuario.rol.permisos.split(",") if usuario.rol and usuario.rol.permisos else [],
        "iat": now,
        "exp": now + timedelta(hours=app.config["JWT_EXP_HOURS"]),
    }
    return jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")


def decode_token(token: str):
    if token in REVOKED_TOKENS:
        return None
    try:
        return jwt.decode(token, app.config["JWT_SECRET"], algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Token Bearer requerido"}), 401
        token = header.split(" ", 1)[1].strip()
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Token inválido o expirado"}), 401
        request.jwt_payload = payload
        request.raw_token = token
        return f(*args, **kwargs)
    return wrapper


# ==================== SEED INICIAL ====================
def seed_data():
    if Rol.query.count() == 0:
        roles = [
            Rol(
                nombre="ADMINISTRADOR",
                descripcion="Acceso total al sistema, usuarios, catálogo, inventario, compras, ventas y reportes",
                activo=True,
                permisos="all,users,catalog,inventory,procurement,sales,reports",
            ),
            Rol(
                nombre="OPERADOR_BODEGA",
                descripcion="Control de stock, entradas, salidas, traslados, devoluciones y recepción de compras",
                activo=True,
                permisos="catalog:read,inventory,procurement:receive,reports:read",
            ),
            Rol(
                nombre="VENDEDOR",
                descripcion="Registro de ventas, consulta de catálogo y consulta de disponibilidad",
                activo=True,
                permisos="catalog:read,inventory:read,sales,reports:read",
            ),
        ]
        db.session.add_all(roles)
        db.session.commit()

    if Usuario.query.count() == 0:
        rol_admin = Rol.query.filter_by(nombre="ADMINISTRADOR").first()
        rol_bodega = Rol.query.filter_by(nombre="OPERADOR_BODEGA").first()
        rol_vendedor = Rol.query.filter_by(nombre="VENDEDOR").first()

        usuarios = [
            Usuario(
                id_rol=rol_admin.id_rol,
                correo="admin@andina.com",
                nombre="Juan Sebastián Rivera (Admin)",
                contrasena_hash=generate_password_hash("Admin123*"),
                estado="ACTIVO",
            ),
            Usuario(
                id_rol=rol_bodega.id_rol,
                correo="bodega@andina.com",
                nombre="Cristian Bermúdez (Bodega)",
                contrasena_hash=generate_password_hash("Bodega123*"),
                estado="ACTIVO",
            ),
            Usuario(
                id_rol=rol_vendedor.id_rol,
                correo="ventas@andina.com",
                nombre="Laura Gómez (Vendedora)",
                contrasena_hash=generate_password_hash("Ventas123*"),
                estado="ACTIVO",
            ),
        ]
        db.session.add_all(usuarios)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()


# ==================== ENDPOINTS ====================
@app.get("/health")
def health():
    """Estado de salud del microservicio
    ---
    responses:
      200:
        description: Servicio activo
    """
    return jsonify({"service": "usuarios-service", "status": "ok"}), 200


@app.post("/auth/login")
def login():
    """Iniciar sesión y obtener JWT (RF08)
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [correo, contrasena]
          properties:
            correo: {type: string, example: admin@andina.com}
            contrasena: {type: string, example: Admin123*}
    responses:
      200:
        description: Inicio de sesión exitoso
      401:
        description: Credenciales inválidas
    """
    data = request.get_json(silent=True) or {}
    correo = (data.get("correo") or data.get("email") or "").strip().lower()
    contrasena = data.get("contrasena") or data.get("password") or ""

    usuario = Usuario.query.filter_by(correo=correo).first()
    if not usuario or not check_password_hash(usuario.contrasena_hash, contrasena):
        return jsonify({"error": "Credenciales inválidas"}), 401
    if usuario.estado != "ACTIVO":
        return jsonify({"error": "Usuario inactivo o bloqueado"}), 403

    usuario.ultimo_acceso_en = datetime.now(timezone.utc)
    db.session.commit()

    token = create_token(usuario)
    return jsonify({"access_token": token, "token_type": "Bearer", "usuario": usuario.to_dict()}), 200


@app.post("/auth/register")
def register():
    """Registrar nuevo usuario (RF07, RF08)
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [correo, nombre, contrasena]
          properties:
            correo: {type: string}
            nombre: {type: string}
            contrasena: {type: string}
            id_rol: {type: integer, default: 2}
    responses:
      201:
        description: Usuario registrado
    """
    data = request.get_json(silent=True) or {}
    correo = (data.get("correo") or "").strip().lower()
    nombre = (data.get("nombre") or "").strip()
    contrasena = data.get("contrasena") or ""
    id_rol = data.get("id_rol")

    if not correo or not nombre or len(contrasena) < 6:
        return jsonify({"error": "correo, nombre y contrasena (mín. 6 caracteres) son obligatorios"}), 400
    if Usuario.query.filter_by(correo=correo).first():
        return jsonify({"error": "El correo ya está registrado"}), 409

    rol = Rol.query.get(id_rol) if id_rol else Rol.query.filter_by(nombre="OPERADOR_BODEGA").first()
    if not rol:
        return jsonify({"error": "Rol no encontrado"}), 404

    usuario = Usuario(
        id_rol=rol.id_rol,
        correo=correo,
        nombre=nombre,
        contrasena_hash=generate_password_hash(contrasena),
        estado="ACTIVO",
    )
    db.session.add(usuario)
    db.session.commit()

    token = create_token(usuario)
    return jsonify({"usuario": usuario.to_dict(), "access_token": token}), 201


@app.post("/auth/logout")
@auth_required
def logout():
    """Cerrar sesión revocando el JWT actual (RF08)
    ---
    responses:
      200:
        description: Sesión cerrada
    """
    REVOKED_TOKENS.add(request.raw_token)
    return jsonify({"message": "Sesión cerrada correctamente"}), 200


@app.get("/auth/me")
@auth_required
def me():
    """Consultar perfil del usuario autenticado
    ---
    responses:
      200:
        description: Perfil del usuario
    """
    usuario = Usuario.query.get(request.jwt_payload["id_usuario"])
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(usuario.to_dict()), 200


@app.post("/auth/verify")
def verify():
    """Validar token JWT (utilizado por el API Gateway o servicios internos)
    ---
    responses:
      200:
        description: Token válido
      401:
        description: Token inválido
    """
    header = request.headers.get("Authorization", "")
    token = header.split(" ", 1)[1].strip() if header.startswith("Bearer ") else (request.get_json(silent=True) or {}).get("token", "")
    payload = decode_token(token)
    if not payload:
        return jsonify({"valid": False, "error": "Token inválido o expirado"}), 401
    return jsonify({"valid": True, "payload": payload}), 200


@app.post("/auth/change-password")
@auth_required
def change_password():
    """Cambiar contraseña del usuario autenticado (RF08)
    ---
    responses:
      200:
        description: Contraseña actualizada
    """
    data = request.get_json(silent=True) or {}
    actual = data.get("contrasena_actual", "")
    nueva = data.get("contrasena_nueva", "")
    if len(nueva) < 6:
        return jsonify({"error": "La nueva contraseña debe tener al menos 6 caracteres"}), 400

    usuario = Usuario.query.get(request.jwt_payload["id_usuario"])
    if not usuario or not check_password_hash(usuario.contrasena_hash, actual):
        return jsonify({"error": "Contraseña actual incorrecta"}), 400

    usuario.contrasena_hash = generate_password_hash(nueva)
    db.session.commit()
    return jsonify({"message": "Contraseña actualizada correctamente"}), 200


@app.post("/auth/forgot-password")
def forgot_password():
    """Generar token de recuperación de contraseña (RF08)
    ---
    responses:
      200:
        description: Token de recuperación generado
    """
    data = request.get_json(silent=True) or {}
    correo = (data.get("correo") or "").strip().lower()
    usuario = Usuario.query.filter_by(correo=correo).first()
    if not usuario:
        return jsonify({"message": "Si el correo existe, se generó el token de recuperación"}), 200

    raw_token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    rec = RecuperacionClave(
        id_usuario=usuario.id_usuario,
        token_hash=token_hash,
        vence_en=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.session.add(rec)
    db.session.commit()
    return jsonify({
        "message": "Token de recuperación generado (entorno demo)",
        "reset_token": raw_token,
        "vence_en": rec.vence_en.isoformat(),
    }), 200


@app.post("/auth/reset-password")
def reset_password():
    """Restablecer contraseña usando token de recuperación (RF08)
    ---
    responses:
      200:
        description: Contraseña restablecida
    """
    data = request.get_json(silent=True) or {}
    raw_token = data.get("token", "")
    nueva = data.get("contrasena_nueva", "")
    if not raw_token or len(nueva) < 6:
        return jsonify({"error": "Token y contrasena_nueva (mín. 6 caracteres) son obligatorios"}), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    rec = RecuperacionClave.query.filter_by(token_hash=token_hash, usado_en=None).first()
    now = datetime.now(timezone.utc)
    if not rec:
        return jsonify({"error": "Token inválido o ya utilizado"}), 400

    vence = rec.vence_en.replace(tzinfo=timezone.utc) if rec.vence_en.tzinfo is None else rec.vence_en
    if vence < now:
        return jsonify({"error": "Token expirado"}), 400

    usuario = Usuario.query.get(rec.id_usuario)
    usuario.contrasena_hash = generate_password_hash(nueva)
    rec.usado_en = now
    db.session.commit()
    return jsonify({"message": "Contraseña restablecida correctamente"}), 200


@app.get("/roles")
def list_roles():
    """Listar roles disponibles (RF07)
    ---
    responses:
      200:
        description: Lista de roles
    """
    roles = Rol.query.all()
    return jsonify([r.to_dict() for r in roles]), 200


@app.get("/users")
def list_users():
    """Listar todos los usuarios (RF07)
    ---
    responses:
      200:
        description: Lista de usuarios
    """
    usuarios = Usuario.query.order_by(Usuario.id_usuario.asc()).all()
    return jsonify([u.to_dict() for u in usuarios]), 200


@app.get("/users/<int:id_usuario>")
def get_user(id_usuario):
    """Obtener un usuario por ID (RF07)
    ---
    responses:
      200:
        description: Datos del usuario
      404:
        description: No encontrado
    """
    usuario = Usuario.query.get(id_usuario)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(usuario.to_dict()), 200


@app.put("/users/<int:id_usuario>")
def update_user(id_usuario):
    """Actualizar datos, rol o estado de un usuario (RF07)
    ---
    responses:
      200:
        description: Usuario actualizado
    """
    usuario = Usuario.query.get(id_usuario)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    data = request.get_json(silent=True) or {}
    if "nombre" in data:
        usuario.nombre = data["nombre"].strip()
    if "estado" in data:
        usuario.estado = data["estado"].upper()
    if "id_rol" in data:
        rol = Rol.query.get(data["id_rol"])
        if not rol:
            return jsonify({"error": "Rol no encontrado"}), 404
        usuario.id_rol = rol.id_rol
    db.session.commit()
    return jsonify(usuario.to_dict()), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")), debug=True)

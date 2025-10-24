from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet, MultiFernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User
import pytest

# Configuración de hashing de contraseñas
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=2,
    argon2__memory_cost=102400,
    argon2__parallelism=8,
)

# OAuth2 con soporte para JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Fernet para encriptar credenciales
class FernetVault:
    def __init__(self, keys: list[bytes]):
        """
        Inicializa el vault con rotación de claves.
        Primera clave = actual para encriptar.
        Resto de claves = anteriores para decriptar.
        """
        if not keys:
            raise ValueError("Al menos una clave Fernet es requerida")
        self.fernet = MultiFernet([Fernet(k) for k in keys])
        self._primary = Fernet(keys[0])

    def encrypt(self, data: str) -> str:
        """Encripta usando la clave primaria"""
        return self._primary.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decripta usando todas las claves disponibles"""
        return self.fernet.decrypt(token.encode()).decode()

    def rotate(self, token: str) -> str:
        """Rota un token a la clave primaria"""
        return self.fernet.rotate(token.encode()).decode()

# Instancia global de FernetVault
vault = FernetVault([settings.FERNET_KEY.encode()])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_token(
    subject: str, 
    expires_delta: timedelta,
    scope: str = "access",
    secret_key: str = settings.SECRET_KEY
) -> str:
    """Crea un token JWT con claims estándar"""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "scope": scope,
        "iat": now,
        "exp": now + expires_delta,
        "nbf": now,
    }
    return jwt.encode(claims, secret_key, settings.JWT_ALGORITHM)

def create_access_token(subject: str) -> str:
    return create_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

def create_refresh_token(subject: str) -> str:
    return create_token(
        subject=subject,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        scope="refresh",
        secret_key=settings.REFRESH_SECRET_KEY
    )

def decode_token(
    token: str,
    secret_key: str = settings.SECRET_KEY,
    verify_exp: bool = True
) -> dict:
    try:
        return jwt.decode(
            token,
            secret_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": verify_exp}
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    if not current_user.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=43200  # 30 días

def test_password_hash():
    password = "secretpassword123"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_access_token():
    email = "test@example.com"
    token = create_access_token(email)
    payload = decode_token(token)
    assert payload["sub"] == email
    assert payload["scope"] == "access"

def test_refresh_token():
    email = "test@example.com"
    token = create_refresh_token(email)
    payload = decode_token(
        token, 
        secret_key=settings.REFRESH_SECRET_KEY
    )
    assert payload["sub"] == email
    assert payload["scope"] == "refresh"

def test_token_expiration():
    email = "test@example.com"
    token = create_token(
        subject=email,
        expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(HTTPException):
        decode_token(token)

def test_fernet_vault():
    secret = "mysecret123"
    encrypted = vault.encrypt(secret)
    assert encrypted != secret
    decrypted = vault.decrypt(encrypted)
    assert decrypted == secret

    # Test rotación
    rotated = vault.rotate(encrypted)
    assert vault.decrypt(rotated) == secret

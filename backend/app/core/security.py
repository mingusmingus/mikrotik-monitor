from datetime import datetime, timedelta, timezone
from jose import jwt
from argon2 import PasswordHasher
from argon2.low_level import Type
from cryptography.fernet import Fernet
from app.core.config import settings

# Password hashing (Argon2id)
ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
    hash_len=32,
    type=Type.ID,
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, plain)
        return True
    except Exception:
        return False

# JWT
def _create_token(sub: str, minutes: int, token_type: str):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "type": token_type,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALG)

def create_access_token(sub: str) -> str:
    return _create_token(sub, settings.ACCESS_TOKEN_EXPIRE_MINUTES, "access")

def create_refresh_token(sub: str) -> str:
    return _create_token(sub, settings.REFRESH_TOKEN_EXPIRE_MINUTES, "refresh")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALG])

# Fernet (encryption for device credentials)
fernet = Fernet(settings.FERNET_KEY.encode() if isinstance(settings.FERNET_KEY, str) else settings.FERNET_KEY)

def encrypt_secret(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt_secret(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()

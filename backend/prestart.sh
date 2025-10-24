#!/usr/bin/env bash
set -e

# Esperar DB
echo "Esperando PostgreSQL..."
python - <<'PY'
import time, psycopg2, os
for _ in range(30):
    try:
        psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB","mikromon"),
            user=os.getenv("POSTGRES_USER","mikromon"),
            password=os.getenv("POSTGRES_PASSWORD","changeme"),
            host=os.getenv("POSTGRES_HOST","db"),
            port=int(os.getenv("POSTGRES_PORT","5432")),
        )
        print("DB lista")
        break
    except Exception as e:
        print("DB no lista, reintento...", e)
        time.sleep(2)
else:
    raise SystemExit("No se pudo conectar a la DB")
PY

# Migraciones
alembic upgrade head

# Bootstrap de planes y admin si no existen (simple)
python - <<'PY'
import os
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.db.models import Plan, User
from app.core.security import hash_password

db: Session = SessionLocal()
plans = {
    "BASICMAAT": (5, 19.99, "Plan básico con hasta 5 dispositivos"),
    "INTERMAAT": (15, 39.99, "Plan intermedio con hasta 15 dispositivos"), 
    "PROMAAT": (0, 79.99, "Plan profesional con dispositivos ilimitados")
}
for name,(maxd, price, desc) in plans.items():
    if not db.query(Plan).filter(Plan.nombre == name).first():
        db.add(Plan(nombre=name, max_equipos=maxd, precio=price, descripcion=desc))
db.commit()

email = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
pwd = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
name = os.getenv("BOOTSTRAP_ADMIN_NAME","Admin")
if email and pwd:
    if not db.query(User).filter(User.email == email).first():
        pro = db.query(Plan).filter(Plan.nombre=="PROMAAT").first()
        db.add(User(email=email, password=hash_password(pwd), nombre=name, plan_id=pro.id if pro else None, activo=True))
        db.commit()
db.close()
print("Bootstrap OK")
PY

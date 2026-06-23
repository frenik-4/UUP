import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine, SessionLocal
from app.config import settings
from app.routers import auth, personal, kurser, avdelningar, perioder, installningar, regler

app = FastAPI(title="UUP — Universitetsbemanningssystem", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(personal.router)
app.include_router(kurser.router)
app.include_router(avdelningar.router)
app.include_router(perioder.router)
app.include_router(installningar.router)
app.include_router(regler.router)


def _migrate(engine):
    """Lägg till nya kolumner till befintliga tabeller utan att förstöra data."""
    stmts = [
        "ALTER TABLE personer ADD COLUMN IF NOT EXISTS personnummer VARCHAR(13)",
        "ALTER TABLE personer ADD COLUMN IF NOT EXISTS kompetenser TEXT",
        "ALTER TABLE kursbelaggningar ADD COLUMN IF NOT EXISTS belaggning_start DATE",
        "ALTER TABLE kursbelaggningar ADD COLUMN IF NOT EXISTS belaggning_slut DATE",
        "ALTER TABLE anvandar_roller ADD COLUMN IF NOT EXISTS amnesomrade VARCHAR(200)",
        "ALTER TABLE uppdrag ADD COLUMN IF NOT EXISTS start_datum DATE",
        "ALTER TABLE uppdrag ADD COLUMN IF NOT EXISTS slut_datum DATE",
        "ALTER TABLE uppdrag ADD COLUMN IF NOT EXISTS godkand BOOLEAN DEFAULT TRUE",
        # Sätt amnesomrade på befintliga STR-användare baserat på person.amnesomrade
        """UPDATE anvandar_roller ar SET amnesomrade = (
            SELECT p.amnesomrade FROM personer p
            JOIN anvandare u ON u.person_id = p.id
            WHERE u.id = ar.anvandare_id
        ) WHERE ar.roll = 'str_roll' AND ar.amnesomrade IS NULL""",
        # Ny enum-värden
        "ALTER TYPE userroll ADD VALUE IF NOT EXISTS 'controller'",
        # Nya kolumner på uppdrag
        "ALTER TABLE uppdrag ADD COLUMN IF NOT EXISTS projekt_kategori VARCHAR(100)",
        "ALTER TABLE uppdrag ADD COLUMN IF NOT EXISTS ekonom_person_id INTEGER REFERENCES personer(id)",
        # Notering-fält på frånvaro (för äldre DB utan kolumnen)
        "ALTER TABLE franvaro ADD COLUMN IF NOT EXISTS notering TEXT",
        # Semester-typ i frånvaro-enum
        "ALTER TYPE franvarotyp ADD VALUE IF NOT EXISTS 'semester'",
        # Procent- och schablon-fält på frånvaro
        "ALTER TABLE franvaro ADD COLUMN IF NOT EXISTS pct_av_heltid INTEGER",
        "ALTER TABLE franvaro ADD COLUMN IF NOT EXISTS is_schablonsemester BOOLEAN NOT NULL DEFAULT FALSE",
    ]
    with engine.connect() as conn:
        for s in stmts:
            try:
                conn.execute(text(s))
                conn.commit()
            except Exception as e:
                print(f"Migration note: {e}")


@app.on_event("startup")
def startup():
    # Vänta på att databasen är redo (max 30s)
    for _ in range(30):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception:
            time.sleep(1)

    _migrate(engine)
    Base.metadata.create_all(bind=engine)

    if settings.seed_on_start:
        from app.seed import seed
        db = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()


@app.get("/health")
def health():
    return {"status": "ok"}

from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.core import Kurs, Kursbelaggning, Person, AssignmentStatus
from app.schemas.core import KursListOut, KursDetailOut, BelaggningCreate, BelaggningOut, BelaggningGranska
from app.routers.auth import get_current_user
from app.services.calculations import validera_belaggning

router = APIRouter(prefix="/kurser", tags=["kurser"])


def _kurs_stats(db: Session) -> dict[int, dict]:
    """Returnerar {kurs_id: {godkand: h, begard: h}} för alla kurser."""
    rows = db.query(
        Kursbelaggning.kurs_id,
        Kursbelaggning.status,
        func.sum(Kursbelaggning.timmar).label("total")
    ).group_by(Kursbelaggning.kurs_id, Kursbelaggning.status).all()
    result: dict[int, dict] = {}
    for kurs_id, status, total in rows:
        if kurs_id not in result:
            result[kurs_id] = {"godkand": Decimal("0"), "begard": Decimal("0")}
        if status == AssignmentStatus.godkand:
            result[kurs_id]["godkand"] = total or Decimal("0")
        elif status == AssignmentStatus.begard:
            result[kurs_id]["begard"] = total or Decimal("0")
    return result


def _load_kurs(db: Session, kurs_id: int) -> Kurs:
    k = (db.query(Kurs)
         .options(
             selectinload(Kurs.timtyper),
             selectinload(Kurs.belaggningar).selectinload(Kursbelaggning.person).selectinload(Person.avdelning),
         )
         .filter(Kurs.id == kurs_id)
         .first())
    if not k:
        raise HTTPException(404, "Kurs finns inte")
    return k


@router.get("", response_model=list[KursListOut])
def lista_kurser(period_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Kurs)
    if period_id:
        q = q.filter(Kurs.period_id == period_id)
    stats = _kurs_stats(db)
    result = []
    for k in q.order_by(Kurs.kod).all():
        out = KursListOut.model_validate(k)
        s = stats.get(k.id, {})
        out.bemannat_godkand = s.get("godkand", Decimal("0"))
        out.bemannat_begard = s.get("begard", Decimal("0"))
        result.append(out)
    return result


@router.get("/{kurs_id}", response_model=KursDetailOut)
def hamta_kurs(kurs_id: int, db: Session = Depends(get_db)):
    return KursDetailOut.model_validate(_load_kurs(db, kurs_id))


@router.post("/belaggningar", response_model=BelaggningOut, status_code=201)
def skapa_belaggning(
    body: BelaggningCreate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = None
    if authorization and authorization.startswith("Bearer "):
        try:
            user = get_current_user(authorization[7:], db)
        except Exception:
            pass

    kurs = db.get(Kurs, body.kurs_id)
    if not kurs:
        raise HTTPException(404, "Kurs finns inte")

    person = (db.query(Person)
              .options(selectinload(Person.anstallningar), selectinload(Person.franvaro),
                       selectinload(Person.uppdrag), selectinload(Person.kursbelaggningar))
              .filter(Person.id == body.person_id).first())
    if not person:
        raise HTTPException(404, "Person finns inte")

    fel = validera_belaggning(person, 2026, body.timmar, db)
    blocking = [f for f in fel if f["typ"] == "fel"]
    if blocking:
        raise HTTPException(422, detail=blocking)

    kb = Kursbelaggning(
        kurs_id=body.kurs_id,
        person_id=body.person_id,
        timmar=body.timmar,
        timtyp=body.timtyp,
        status=body.status,
        belaggning_start=body.belaggning_start,
        belaggning_slut=body.belaggning_slut,
        begard_av=user,
        begard_vid=datetime.utcnow() if user else None,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return BelaggningOut.model_validate(
        db.query(Kursbelaggning)
        .options(selectinload(Kursbelaggning.person).selectinload(Person.avdelning))
        .filter(Kursbelaggning.id == kb.id).first()
    )


@router.patch("/belaggningar/{kb_id}/status", response_model=BelaggningOut)
def granska_belaggning(
    kb_id: int,
    body: BelaggningGranska,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    kb = db.get(Kursbelaggning, kb_id)
    if not kb:
        raise HTTPException(404, "Beläggning finns inte")
    if body.status not in (AssignmentStatus.godkand, AssignmentStatus.nekad):
        raise HTTPException(422, "Status måste vara godkand eller nekad")

    user = None
    if authorization and authorization.startswith("Bearer "):
        try:
            user = get_current_user(authorization[7:], db)
        except Exception:
            pass

    kb.status = body.status
    kb.granskad_av = user
    kb.granskad_vid = datetime.utcnow()
    kb.gransknings_kommentar = body.kommentar
    db.commit()
    db.refresh(kb)
    return BelaggningOut.model_validate(
        db.query(Kursbelaggning)
        .options(selectinload(Kursbelaggning.person).selectinload(Person.avdelning))
        .filter(Kursbelaggning.id == kb.id).first()
    )


@router.delete("/belaggningar/{kb_id}", status_code=204)
def ta_bort_belaggning(kb_id: int, db: Session = Depends(get_db)):
    kb = db.get(Kursbelaggning, kb_id)
    if not kb:
        raise HTTPException(404, "Beläggning finns inte")
    db.delete(kb)
    db.commit()

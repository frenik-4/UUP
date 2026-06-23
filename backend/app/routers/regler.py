from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.database import get_db
from app.models.core import ReduktionsRegel, ReduktionsTriggerTyp, ReduktionsEffektTyp
from app.schemas.core import ReduktionsRegelOut, ReduktionsRegelCreate, ReduktionsRegelUpdate

router = APIRouter(prefix="/regler", tags=["regler"])


@router.get("", response_model=list[ReduktionsRegelOut])
def lista_regler(db: Session = Depends(get_db)):
    return db.query(ReduktionsRegel).order_by(ReduktionsRegel.id).all()


@router.post("", response_model=ReduktionsRegelOut, status_code=201)
def skapa_regel(body: ReduktionsRegelCreate, db: Session = Depends(get_db)):
    r = ReduktionsRegel(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.patch("/{regel_id}", response_model=ReduktionsRegelOut)
def uppdatera_regel(regel_id: int, body: ReduktionsRegelUpdate, db: Session = Depends(get_db)):
    r = db.query(ReduktionsRegel).filter(ReduktionsRegel.id == regel_id).first()
    if not r:
        raise HTTPException(404, "Regel finns inte")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{regel_id}", status_code=204)
def ta_bort_regel(regel_id: int, db: Session = Depends(get_db)):
    r = db.query(ReduktionsRegel).filter(ReduktionsRegel.id == regel_id).first()
    if not r:
        raise HTTPException(404, "Regel finns inte")
    db.delete(r)
    db.commit()

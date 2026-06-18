from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date

from app.database import get_db
from app.models.core import Planeringsperiod, PlaneringsperiodTyp

router = APIRouter(prefix="/perioder", tags=["perioder"])


class PeriodOut(BaseModel):
    id: int
    namn: str
    typ: PlaneringsperiodTyp
    start_datum: date
    slut_datum: date
    aktiv: bool
    model_config = {"from_attributes": True}


@router.get("", response_model=list[PeriodOut])
def lista_perioder(db: Session = Depends(get_db)):
    return [PeriodOut.model_validate(p) for p in
            db.query(Planeringsperiod).order_by(Planeringsperiod.start_datum.desc()).all()]

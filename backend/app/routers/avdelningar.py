from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Avdelning
from app.schemas.core import AvdelningOut

router = APIRouter(prefix="/avdelningar", tags=["avdelningar"])


@router.get("", response_model=list[AvdelningOut])
def lista_avdelningar(db: Session = Depends(get_db)):
    return [AvdelningOut.model_validate(a) for a in db.query(Avdelning).filter(Avdelning.aktiv == True).order_by(Avdelning.namn).all()]

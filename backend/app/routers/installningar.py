from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Installning
from app.schemas.core import InstallningOut, InstallningBatchUpdate

router = APIRouter(prefix="/installningar", tags=["installningar"])


@router.get("", response_model=list[InstallningOut])
def hamta_installningar(db: Session = Depends(get_db)):
    return db.query(Installning).order_by(Installning.key).all()


@router.put("", response_model=list[InstallningOut])
def uppdatera_installningar(body: InstallningBatchUpdate, db: Session = Depends(get_db)):
    for key, value in body.updates.items():
        inst = db.get(Installning, key)
        if inst:
            inst.value = str(value)
        else:
            raise HTTPException(400, f"Okänd inställningsnyckel: {key}")
    db.commit()
    return db.query(Installning).order_by(Installning.key).all()

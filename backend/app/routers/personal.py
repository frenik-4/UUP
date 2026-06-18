from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.core import Person, PersonKategori, PersonKategoriTyp
from app.schemas.core import PersonListOut, PersonDetailOut, TidskontoDel, ValideringsResultat
from app.services.calculations import berakna_tidskonto, validera_belaggning

router = APIRouter(prefix="/personal", tags=["personal"])


def _load_person(db: Session, person_id: int) -> Person:
    p = (db.query(Person)
         .options(
             selectinload(Person.avdelning),
             selectinload(Person.anstallningar),
             selectinload(Person.franvaro),
             selectinload(Person.uppdrag),
             selectinload(Person.kursbelaggningar),
             selectinload(Person.anvandare),
         )
         .filter(Person.id == person_id)
         .first())
    if not p:
        raise HTTPException(status_code=404, detail="Person finns inte")
    return p


@router.get("", response_model=list[PersonListOut])
def lista_personal(
    avdelning_id: int | None = None,
    kategori: PersonKategori | None = None,
    kategori_typ: PersonKategoriTyp | None = None,
    inkl_inaktiva: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Person).options(selectinload(Person.avdelning))
    if not inkl_inaktiva:
        q = q.filter(Person.aktiv == True)
    if avdelning_id:
        q = q.filter(Person.avdelning_id == avdelning_id)
    if kategori:
        q = q.filter(Person.personalkategori == kategori)
    if kategori_typ:
        q = q.filter(Person.kategori_typ == kategori_typ)
    return [PersonListOut.model_validate(p) for p in q.order_by(Person.namn).all()]


@router.get("/{person_id}", response_model=PersonDetailOut)
def hamta_person(person_id: int, db: Session = Depends(get_db)):
    return PersonDetailOut.model_validate(_load_person(db, person_id))


@router.get("/{person_id}/tidskonto", response_model=TidskontoDel)
def tidskonto(person_id: int, ar: int = 2026, db: Session = Depends(get_db)):
    p = _load_person(db, person_id)
    konto = berakna_tidskonto(p, ar, db)
    return TidskontoDel(
        person_id=konto.person_id,
        planeringsår=konto.planeringsår,
        brutto_timmar=konto.brutto_timmar,
        semester_timmar=konto.semester_timmar,
        heltidsbas=konto.heltidsbas,
        tjanstgoringspct=konto.tjanstgoringspct,
        justerad_heltidsbas=konto.justerad_heltidsbas,
        franvaro_timmar=konto.franvaro_timmar,
        netto_bemanningsbar=konto.netto_bemanningsbar,
        fok_pct=konto.fok_pct,
        fok_timmar=konto.fok_timmar,
        kollegialt_pct=konto.kollegialt_pct,
        kollegialt_timmar=konto.kollegialt_timmar,
        uppdrag_timmar_totalt=konto.uppdrag_timmar_totalt,
        uppdrag_detaljer=konto.uppdrag_detaljer,
        tillganglig_undervisning=konto.tillganglig_undervisning,
        undervisning_godkand=konto.undervisning_godkand,
        undervisning_begard=konto.undervisning_begard,
        undervisning_utkast=konto.undervisning_utkast,
        undervisning_totalt_planerad=konto.undervisning_totalt_planerad,
        aterstaar=konto.aterstaar,
        aterstaar_inkl_begard=konto.aterstaar_inkl_begard,
        belaggningspct=konto.belaggningspct,
    )


@router.get("/{person_id}/validera", response_model=ValideringsResultat)
def validera(
    person_id: int,
    timmar: Decimal,
    ar: int = 2026,
    exkludera_belaggning_id: int | None = None,
    db: Session = Depends(get_db),
):
    p = _load_person(db, person_id)
    fel = validera_belaggning(p, ar, timmar, db, exkludera_belaggning_id)
    konto = berakna_tidskonto(p, ar, db)
    return ValideringsResultat(
        fel=fel,
        tidskonto=TidskontoDel(
            person_id=konto.person_id, planeringsår=konto.planeringsår,
            brutto_timmar=konto.brutto_timmar, semester_timmar=konto.semester_timmar,
            heltidsbas=konto.heltidsbas, tjanstgoringspct=konto.tjanstgoringspct,
            justerad_heltidsbas=konto.justerad_heltidsbas,
            franvaro_timmar=konto.franvaro_timmar, netto_bemanningsbar=konto.netto_bemanningsbar,
            fok_pct=konto.fok_pct, fok_timmar=konto.fok_timmar,
            kollegialt_pct=konto.kollegialt_pct, kollegialt_timmar=konto.kollegialt_timmar,
            uppdrag_timmar_totalt=konto.uppdrag_timmar_totalt,
            uppdrag_detaljer=konto.uppdrag_detaljer,
            tillganglig_undervisning=konto.tillganglig_undervisning,
            undervisning_godkand=konto.undervisning_godkand,
            undervisning_begard=konto.undervisning_begard,
            undervisning_utkast=konto.undervisning_utkast,
            undervisning_totalt_planerad=konto.undervisning_totalt_planerad,
            aterstaar=konto.aterstaar, aterstaar_inkl_begard=konto.aterstaar_inkl_begard,
            belaggningspct=konto.belaggningspct,
        )
    )

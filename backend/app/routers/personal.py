from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.core import Person, PersonKategori, PersonKategoriTyp, Kursbelaggning, Kurs, Planeringsperiod
from app.schemas.core import PersonListOut, PersonDetailOut, TidskontoDel, ValideringsResultat, KapacitetOut, PersonBelaggningOut
from app.services.calculations import berakna_tidskonto, validera_belaggning

router = APIRouter(prefix="/personal", tags=["personal"])


def _full_load(db: Session):
    return (db.query(Person)
            .options(
                selectinload(Person.avdelning),
                selectinload(Person.anstallningar),
                selectinload(Person.franvaro),
                selectinload(Person.uppdrag),
                selectinload(Person.kursbelaggningar),
            ))


@router.get("/kapacitet", response_model=list[KapacitetOut])
def kapacitet(ar: int = 2026, avdelning_id: int | None = None, db: Session = Depends(get_db)):
    q = _full_load(db).filter(Person.aktiv == True)
    if avdelning_id:
        q = q.filter(Person.avdelning_id == avdelning_id)
    result = []
    for p in q.order_by(Person.namn).all():
        k = berakna_tidskonto(p, ar, db)
        result.append(KapacitetOut(
            person_id=p.id, namn=p.namn, initialer=p.initialer,
            titel_display=p.titel_display, titel_typ=p.titel_typ,
            avdelning_id=p.avdelning_id,
            avdelning_namn=p.avdelning.namn if p.avdelning else None,
            personalkategori=p.personalkategori, kategori_typ=p.kategori_typ,
            netto_bemanningsbar=float(k.netto_bemanningsbar),
            tillganglig_undervisning=float(k.tillganglig_undervisning),
            undervisning_godkand=float(k.undervisning_godkand),
            undervisning_begard=float(k.undervisning_begard),
            aterstaar=float(k.aterstaar),
            aterstaar_inkl_begard=float(k.aterstaar_inkl_begard),
            belaggningspct=float(k.belaggningspct),
        ))
    return result


def _load_person(db: Session, person_id: int) -> Person:
    p = (_full_load(db)
         .options(selectinload(Person.anvandare))
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


@router.get("/{person_id}/belaggningar", response_model=list[PersonBelaggningOut])
def person_belaggningar(person_id: int, ar: int | None = None, db: Session = Depends(get_db)):
    _load_person(db, person_id)
    q = (db.query(Kursbelaggning)
         .options(selectinload(Kursbelaggning.kurs))
         .filter(Kursbelaggning.person_id == person_id))
    if ar:
        q = q.join(Kurs, Kursbelaggning.kurs_id == Kurs.id)\
             .join(Planeringsperiod, Kurs.period_id == Planeringsperiod.id)\
             .filter(extract('year', Planeringsperiod.start_datum) == ar)
    return q.order_by(Kursbelaggning.status).all()


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

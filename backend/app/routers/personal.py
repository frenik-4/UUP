from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.core import Person, PersonKategori, PersonKategoriTyp, Kursbelaggning, Kurs, Planeringsperiod, Anstallning, Uppdrag, Franvaro
from app.schemas.core import (PersonListOut, PersonDetailOut, TidskontoDel, ValideringsResultat,
                               KapacitetOut, PersonBelaggningOut, PersonUpdate, AnstallningOut,
                               AnstallningUpdate, AnstallningCreate, UppdragOut, UppdragCreate,
                               FranvaroOut, FranvaroCreate)
from app.services.calculations import berakna_tidskonto, validera_belaggning

router = APIRouter(prefix="/personal", tags=["personal"])


def _full_load(db: Session):
    return (db.query(Person)
            .options(
                selectinload(Person.avdelning),
                selectinload(Person.anstallningar),
                selectinload(Person.franvaro),
                selectinload(Person.uppdrag),
                selectinload(Person.kursbelaggningar)
                    .selectinload(Kursbelaggning.kurs)
                    .selectinload(Kurs.period),
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


@router.patch("/{person_id}", response_model=PersonDetailOut)
def uppdatera_person(person_id: int, body: PersonUpdate, db: Session = Depends(get_db)):
    p = _load_person(db, person_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    return PersonDetailOut.model_validate(_load_person(db, person_id))


@router.post("/{person_id}/anstallning", response_model=AnstallningOut, status_code=201)
def skapa_anstallning(person_id: int, body: AnstallningCreate, db: Session = Depends(get_db)):
    _load_person(db, person_id)
    anst = Anstallning(person_id=person_id, **body.model_dump())
    db.add(anst)
    db.commit()
    db.refresh(anst)
    return AnstallningOut.model_validate(anst)


@router.patch("/{person_id}/anstallning/{anst_id}", response_model=AnstallningOut)
def uppdatera_anstallning(person_id: int, anst_id: int, body: AnstallningUpdate, db: Session = Depends(get_db)):
    anst = db.query(Anstallning).filter(Anstallning.id == anst_id, Anstallning.person_id == person_id).first()
    if not anst:
        raise HTTPException(404, "Anställning finns inte")
    data = body.model_dump(exclude_unset=True)
    if data.pop("clear_fok_override", False):
        anst.fok_pct_override = None
    if data.pop("clear_kollegialt_override", False):
        anst.kollegialt_pct_override = None
    for field, value in data.items():
        setattr(anst, field, value)
    db.commit()
    db.refresh(anst)
    return AnstallningOut.model_validate(anst)


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
        from datetime import date as _d
        q = q.join(Kurs, Kursbelaggning.kurs_id == Kurs.id)\
             .join(Planeringsperiod, Kurs.period_id == Planeringsperiod.id)\
             .filter(
                 Planeringsperiod.start_datum <= _d(ar, 12, 31),
                 Planeringsperiod.slut_datum >= _d(ar, 1, 1),
             )
    return q.order_by(Kursbelaggning.status).all()


@router.get("/uppdrag/katalog")
def lista_uppdrag_katalog(db: Session = Depends(get_db)):
    """Returnerar alla unika uppdragsnamn + vanligaste typ (för autocomplete)."""
    rows = db.query(Uppdrag.namn, Uppdrag.typ).order_by(Uppdrag.namn).all()
    seen: dict[str, str] = {}
    for namn, typ in rows:
        if namn not in seen:
            seen[namn] = typ
    return [{"namn": n, "typ": t} for n, t in seen.items()]


@router.post("/{person_id}/uppdrag", response_model=UppdragOut, status_code=201)
def skapa_uppdrag(person_id: int, body: UppdragCreate, db: Session = Depends(get_db)):
    _load_person(db, person_id)
    u = Uppdrag(person_id=person_id, **body.model_dump())
    db.add(u)
    db.commit()
    db.refresh(u)
    return UppdragOut.model_validate(u)


@router.delete("/{person_id}/uppdrag/{uppdrag_id}", status_code=204)
def ta_bort_uppdrag(person_id: int, uppdrag_id: int, db: Session = Depends(get_db)):
    u = db.query(Uppdrag).filter(Uppdrag.id == uppdrag_id, Uppdrag.person_id == person_id).first()
    if not u:
        raise HTTPException(404, "Uppdrag finns inte")
    db.delete(u)
    db.commit()


@router.post("/{person_id}/franvaro", response_model=FranvaroOut, status_code=201)
def skapa_franvaro(person_id: int, body: FranvaroCreate, db: Session = Depends(get_db)):
    _load_person(db, person_id)
    f = Franvaro(person_id=person_id, **body.model_dump())
    db.add(f)
    db.commit()
    db.refresh(f)
    return FranvaroOut.model_validate(f)


@router.delete("/{person_id}/franvaro/{franvaro_id}", status_code=204)
def ta_bort_franvaro(person_id: int, franvaro_id: int, db: Session = Depends(get_db)):
    f = db.query(Franvaro).filter(Franvaro.id == franvaro_id, Franvaro.person_id == person_id).first()
    if not f:
        raise HTTPException(404, "Frånvaro finns inte")
    db.delete(f)
    db.commit()


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

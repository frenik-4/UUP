from datetime import date as _date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.core import (Person, PersonKategori, PersonKategoriTyp, Kursbelaggning,
                              Kurs, Planeringsperiod, Anstallning, Uppdrag, Franvaro, FranvaroTyp)
from app.schemas.core import (PersonListOut, PersonDetailOut, TidskontoDel, ValideringsResultat,
                               KapacitetOut, PersonBelaggningOut, PersonUpdate, AnstallningOut,
                               AnstallningUpdate, AnstallningCreate, UppdragOut, UppdragCreate,
                               FranvaroOut, FranvaroCreate, UppdragUpdate, SchablonsemesterIn)
from app.services.calculations import berakna_tidskonto, validera_belaggning
from app.utils.holidays import (svenska_rodadagar, count_working_days,
                                 semesterdagar_for_alder, berakna_slutdatum,
                                 fodelsear_fran_personnummer)

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


@router.get("/franvaro/alla")
def alla_franvaro(ar: int | None = None, db: Session = Depends(get_db)):
    """Returnerar alla frånvaroposter med person-info, valfritt filtrerat på år."""
    q = db.query(Franvaro).options(
        selectinload(Franvaro.person).selectinload(Person.avdelning)
    )
    if ar:
        q = q.filter(Franvaro.planeringsår == ar)
    rows = q.order_by(Franvaro.start_datum.desc()).all()
    return [{
        "id": f.id,
        "person_id": f.person_id,
        "person_namn": f.person.namn if f.person else "",
        "person_initialer": f.person.initialer if f.person else "",
        "avdelning_namn": f.person.avdelning.kortnamn if f.person and f.person.avdelning else None,
        "typ": f.typ,
        "timmar": float(f.timmar),
        "pct_av_heltid": f.pct_av_heltid,
        "is_schablonsemester": f.is_schablonsemester,
        "start_datum": str(f.start_datum),
        "slut_datum": str(f.slut_datum),
        "planeringsår": f.planeringsår,
        "notering": f.notering,
    } for f in rows]


@router.post("/franvaro/schablonsemester", status_code=201)
def rulla_ut_schablonsemester(body: SchablonsemesterIn, db: Session = Depends(get_db)):
    """Skapar schablonsemesterposter för all aktiv personal baserat på ålder och Villkorsavtalet-T."""
    rodadagar = svenska_rodadagar(body.start_datum.year)
    # Lägg till röda dagar från eventuellt angränsande år om slut faller i nästa år
    rodadagar |= svenska_rodadagar(body.start_datum.year + 1)

    personal = (db.query(Person)
                .options(selectinload(Person.anstallningar))
                .filter(Person.aktiv == True)
                .all())

    skapade = 0
    for person in personal:
        # Hitta gällande anstallning (obligatorisk)
        anst = _hitta_anstallning(person, body.planeringsår)
        if not anst:
            continue

        # Födelseår från personnummer — fallback 31 dagar om det inte kan parsas
        fodelsear = fodelsear_fran_personnummer(person.personnummer)
        dagar = semesterdagar_for_alder(fodelsear, body.planeringsår) if fodelsear else 31
        slut = berakna_slutdatum(body.start_datum, dagar, rodadagar)
        timmar_per_dag = Decimal(str(anst.brutto_timmar)) / Decimal("260")
        timmar = (Decimal(str(dagar)) * timmar_per_dag).quantize(Decimal("0.01"))

        f = Franvaro(
            person_id=person.id,
            typ=FranvaroTyp.semester,
            timmar=timmar,
            pct_av_heltid=100,
            start_datum=body.start_datum,
            slut_datum=slut,
            planeringsår=body.planeringsår,
            notering=f"Schablonsemester {body.planeringsår} ({dagar} dagar)",
            is_schablonsemester=True,
        )
        db.add(f)
        skapade += 1

    db.commit()
    return {"skapade": skapade}


@router.delete("/franvaro/schablonsemester/{ar}", status_code=200)
def aterta_schablonsemester(ar: int, db: Session = Depends(get_db)):
    """Tar bort alla schablonsemesterposter för ett år (individuella justeringar rörs ej)."""
    rows = db.query(Franvaro).filter(
        Franvaro.planeringsår == ar,
        Franvaro.is_schablonsemester == True,
    ).all()
    antal = len(rows)
    for f in rows:
        db.delete(f)
    db.commit()
    return {"borttagna": antal}


@router.get("/uppdrag/projekt")
def lista_projekt(ar: int | None = None, kategori: str | None = None, db: Session = Depends(get_db)):
    """Returnerar uppdrag som har projekt_kategori satt (forskningsprojekt m.m.)."""
    q = db.query(Uppdrag).options(
        selectinload(Uppdrag.person).selectinload(Person.avdelning),
        selectinload(Uppdrag.ekonom),
    ).filter(Uppdrag.projekt_kategori != None)
    if ar:
        q = q.filter(Uppdrag.planeringsår == ar)
    if kategori:
        q = q.filter(Uppdrag.projekt_kategori == kategori)
    rows = q.order_by(Uppdrag.namn).all()
    return [{
        "id": u.id,
        "namn": u.namn,
        "projekt_kategori": u.projekt_kategori,
        "typ": u.typ,
        "varde": float(u.varde),
        "planeringsår": u.planeringsår,
        "godkand": u.godkand,
        "notering": u.notering,
        "person_id": u.person_id,
        "person_namn": u.person.namn if u.person else "",
        "person_initialer": u.person.initialer if u.person else "",
        "avdelning_namn": u.person.avdelning.kortnamn if u.person and u.person.avdelning else None,
        "ekonom_person_id": u.ekonom_person_id,
        "ekonom_namn": u.ekonom.namn if u.ekonom else None,
        "ekonom_initialer": u.ekonom.initialer if u.ekonom else None,
    } for u in rows]


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


@router.patch("/{person_id}/uppdrag/{uppdrag_id}", response_model=UppdragOut)
def uppdatera_uppdrag(person_id: int, uppdrag_id: int, body: UppdragUpdate, db: Session = Depends(get_db)):
    u = db.query(Uppdrag).filter(Uppdrag.id == uppdrag_id, Uppdrag.person_id == person_id).first()
    if not u:
        raise HTTPException(404, "Uppdrag finns inte")
    data = body.model_dump(exclude_unset=True)
    if data.pop("clear_ekonom", False):
        u.ekonom_person_id = None
    for field, value in data.items():
        setattr(u, field, value)
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


def _hitta_anstallning(person: Person, ar: int) -> Anstallning | None:
    target = _date(ar, 7, 1)
    giltiga = [a for a in person.anstallningar
               if a.giltig_fran <= target and (a.giltig_till is None or a.giltig_till >= target)]
    return giltiga[0] if giltiga else (person.anstallningar[0] if person.anstallningar else None)


@router.post("/{person_id}/franvaro", response_model=FranvaroOut, status_code=201)
def skapa_franvaro(person_id: int, body: FranvaroCreate, db: Session = Depends(get_db)):
    p = _load_person(db, person_id)
    data = body.model_dump()

    # Beräkna timmar från pct_av_heltid eller semester (alltid 100%)
    pct = body.pct_av_heltid or (100 if body.typ == FranvaroTyp.semester else None)
    if pct and (body.timmar == 0 or body.timmar is None):
        anst = _hitta_anstallning(p, body.planeringsår)
        if anst:
            rodadagar = svenska_rodadagar(body.start_datum.year)
            arbets_dagar = count_working_days(body.start_datum, body.slut_datum, rodadagar)
            timmar_per_dag = Decimal(str(anst.brutto_timmar)) / Decimal("260")
            data["timmar"] = (Decimal(str(arbets_dagar)) * timmar_per_dag * Decimal(str(pct)) / 100).quantize(Decimal("0.01"))
        data["pct_av_heltid"] = pct

    f = Franvaro(person_id=person_id, **data)
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

"""
Tidsberäkningsmotor för tjänstgöringsplaner.

Beräkningskedja:
  brutto_timmar - semester_timmar = heltidsbas
  heltidsbas × (tjanstgoringspct / 100) = justerad_heltidsbas
  justerad_heltidsbas - franvaro_timmar = netto_bemanningsbar

  FOK = netto_bemanningsbar × fok_pct
  Kollegialt = netto_bemanningsbar × kollegialt_pct

  Uppdrag typ 1 (pct_heltid): justerad_heltidsbas × (varde / 100)
  Uppdrag typ 2 (pct_bemanningsbar): netto_bemanningsbar × (varde / 100)
  Uppdrag typ 3 (fasta_timmar): varde

  tillganglig_undervisning = netto_bemanningsbar - fok - kollegialt - uppdrag
"""

from decimal import Decimal
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.core import (
    Person, Anstallning, Franvaro, Uppdrag, Kursbelaggning,
    UppdragTyp, AssignmentStatus, TitelTyp
)


DEFAULT_FOK_PCT = {
    TitelTyp.professor: Decimal("27"),
    TitelTyp.docent: Decimal("27"),
    TitelTyp.lektor: Decimal("18"),
    TitelTyp.adjunkt: Decimal("10"),
    TitelTyp.doktorand: Decimal("0"),
    TitelTyp.forskare: Decimal("0"),
    TitelTyp.forskarassistent: Decimal("0"),
    TitelTyp.provutvecklare: Decimal("0"),
    TitelTyp.annan: Decimal("0"),
}
DEFAULT_KOLLEGIALT_PCT = Decimal("5")


@dataclass
class Tidskonto:
    """Fullständig tidsanalys för en person under ett planeringsår."""
    person_id: int
    planeringsår: int

    brutto_timmar: Decimal = Decimal("0")
    semester_timmar: Decimal = Decimal("0")
    heltidsbas: Decimal = Decimal("0")
    tjanstgoringspct: Decimal = Decimal("100")
    justerad_heltidsbas: Decimal = Decimal("0")
    franvaro_timmar: Decimal = Decimal("0")
    netto_bemanningsbar: Decimal = Decimal("0")

    fok_pct: Decimal = Decimal("0")
    fok_timmar: Decimal = Decimal("0")
    kollegialt_pct: Decimal = Decimal("0")
    kollegialt_timmar: Decimal = Decimal("0")

    uppdrag_detaljer: list = field(default_factory=list)
    uppdrag_timmar_totalt: Decimal = Decimal("0")

    tillganglig_undervisning: Decimal = Decimal("0")

    undervisning_godkand: Decimal = Decimal("0")
    undervisning_begard: Decimal = Decimal("0")
    undervisning_utkast: Decimal = Decimal("0")
    undervisning_totalt_planerad: Decimal = Decimal("0")

    @property
    def aterstaar(self) -> Decimal:
        return self.tillganglig_undervisning - self.undervisning_godkand

    @property
    def aterstaar_inkl_begard(self) -> Decimal:
        return self.tillganglig_undervisning - self.undervisning_godkand - self.undervisning_begard

    @property
    def belaggningspct(self) -> Decimal:
        if self.tillganglig_undervisning == 0:
            return Decimal("0")
        return (self.undervisning_godkand / self.tillganglig_undervisning * 100).quantize(Decimal("0.1"))


def berakna_tidskonto(
    person: Person,
    planeringsår: int,
    db: Session,
    global_fok_overrides: dict | None = None,
    global_kollegialt_pct: Decimal | None = None,
) -> Tidskonto:
    konto = Tidskonto(person_id=person.id, planeringsår=planeringsår)

    # Hämta gällande anställning
    anst = _gallande_anstallning(person, planeringsår)
    if not anst:
        return konto

    konto.brutto_timmar = Decimal(str(anst.brutto_timmar))
    konto.semester_timmar = Decimal(str(anst.semester_timmar))
    konto.tjanstgoringspct = Decimal(str(anst.tjanstgoringspct))
    konto.heltidsbas = konto.brutto_timmar - konto.semester_timmar
    konto.justerad_heltidsbas = (konto.heltidsbas * konto.tjanstgoringspct / 100).quantize(Decimal("0.01"))

    # Frånvaro
    franvaro = [f for f in person.franvaro if f.planeringsår == planeringsår]
    konto.franvaro_timmar = sum(Decimal(str(f.timmar)) for f in franvaro)
    konto.netto_bemanningsbar = max(Decimal("0"), konto.justerad_heltidsbas - konto.franvaro_timmar)

    # FOK
    if anst.fok_pct_override is not None:
        konto.fok_pct = Decimal(str(anst.fok_pct_override))
    elif global_fok_overrides and person.titel_typ in global_fok_overrides:
        konto.fok_pct = global_fok_overrides[person.titel_typ]
    else:
        konto.fok_pct = DEFAULT_FOK_PCT.get(person.titel_typ, Decimal("0"))
    konto.fok_timmar = (konto.netto_bemanningsbar * konto.fok_pct / 100).quantize(Decimal("0.01"))

    # Kollegialt
    if anst.kollegialt_pct_override is not None:
        konto.kollegialt_pct = Decimal(str(anst.kollegialt_pct_override))
    else:
        konto.kollegialt_pct = global_kollegialt_pct or DEFAULT_KOLLEGIALT_PCT
    konto.kollegialt_timmar = (konto.netto_bemanningsbar * konto.kollegialt_pct / 100).quantize(Decimal("0.01"))

    # Uppdrag
    uppdrag_list = [u for u in person.uppdrag if u.planeringsår == planeringsår]
    totalt_uppdrag = Decimal("0")
    for u in uppdrag_list:
        v = Decimal(str(u.varde))
        if u.typ == UppdragTyp.pct_heltid:
            timmar = (konto.justerad_heltidsbas * v / 100).quantize(Decimal("0.01"))
        elif u.typ == UppdragTyp.pct_bemanningsbar:
            timmar = (konto.netto_bemanningsbar * v / 100).quantize(Decimal("0.01"))
        else:  # fasta_timmar
            timmar = v
        # Prorate pct-typer om exakta datum är satta
        if u.start_datum and u.slut_datum and u.typ != UppdragTyp.fasta_timmar:
            from datetime import date as _date
            year_start = _date(planeringsår, 1, 1)
            year_end = _date(planeringsår, 12, 31)
            eff_start = max(u.start_datum, year_start)
            eff_end = min(u.slut_datum, year_end)
            if eff_end >= eff_start:
                year_days = (year_end - year_start).days + 1
                uppdrag_days = (eff_end - eff_start).days + 1
                timmar = (timmar * Decimal(str(uppdrag_days)) / Decimal(str(year_days))).quantize(Decimal("0.01"))
            else:
                timmar = Decimal("0")
        konto.uppdrag_detaljer.append({"id": u.id, "namn": u.namn, "typ": u.typ, "timmar": timmar,
                                        "start_datum": str(u.start_datum) if u.start_datum else None,
                                        "slut_datum": str(u.slut_datum) if u.slut_datum else None})
        totalt_uppdrag += timmar
    konto.uppdrag_timmar_totalt = totalt_uppdrag

    konto.tillganglig_undervisning = max(
        Decimal("0"),
        konto.netto_bemanningsbar - konto.fok_timmar - konto.kollegialt_timmar - konto.uppdrag_timmar_totalt
    )

    # Kursbeläggningar
    for kb in person.kursbelaggningar:
        # Filtrera på år via kursens period (approximation)
        t = Decimal(str(kb.timmar))
        if kb.status == AssignmentStatus.godkand:
            konto.undervisning_godkand += t
        elif kb.status == AssignmentStatus.begard:
            konto.undervisning_begard += t
        elif kb.status == AssignmentStatus.utkast:
            konto.undervisning_utkast += t
    konto.undervisning_totalt_planerad = (
        konto.undervisning_godkand + konto.undervisning_begard + konto.undervisning_utkast
    )

    return konto


def validera_belaggning(
    person: Person,
    planeringsår: int,
    nya_timmar: Decimal,
    db: Session,
    exkludera_belaggning_id: int | None = None,
) -> list[dict]:
    """Returnerar lista med fel/varningar. Tom lista = ok."""
    konto = berakna_tidskonto(person, planeringsår, db)
    fel = []

    tillgangligt = konto.aterstaar_inkl_begard
    if exkludera_belaggning_id:
        # Räkna om utan den exkluderade beläggningen
        for kb in person.kursbelaggningar:
            if kb.id == exkludera_belaggning_id:
                if kb.status == AssignmentStatus.godkand:
                    tillgangligt += Decimal(str(kb.timmar))
                elif kb.status == AssignmentStatus.begard:
                    tillgangligt += Decimal(str(kb.timmar))

    if person.titel_typ == TitelTyp.doktorand:
        max_undervisning = konto.netto_bemanningsbar * Decimal("0.20")
        if konto.undervisning_godkand + konto.undervisning_begard + nya_timmar > max_undervisning:
            fel.append({
                "typ": "fel",
                "kod": "doktorand_max_20pct",
                "meddelande": f"Doktorander får max 20% institutionell tjänst ({max_undervisning:.0f}h). "
                              f"Redan planerat: {konto.undervisning_godkand + konto.undervisning_begard:.0f}h."
            })

    if nya_timmar > tillgangligt:
        fel.append({
            "typ": "fel",
            "kod": "overtid",
            "meddelande": f"Övertid: {nya_timmar:.0f}h begärt men bara {tillgangligt:.0f}h tillgängligt."
        })
    elif nya_timmar > tillgangligt * Decimal("0.9"):
        fel.append({
            "typ": "varning",
            "kod": "nara_tak",
            "meddelande": f"Nära tak: {tillgangligt - nya_timmar:.0f}h återstår efter tilldelning."
        })

    return fel


def _gallande_anstallning(person: Person, ar: int) -> Anstallning | None:
    target = date(ar, 7, 1)  # mitten av planeringsåret som approximation
    giltiga = [
        a for a in person.anstallningar
        if a.giltig_fran <= target and (a.giltig_till is None or a.giltig_till >= target)
    ]
    return giltiga[0] if giltiga else (person.anstallningar[0] if person.anstallningar else None)


from datetime import date

from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.core import (
    PersonKategori, PersonKategoriTyp, TitelTyp, UppdragTyp,
    AssignmentStatus, KurstimTyp, UserRoll, FranvaroTyp
)


class AvdelningOut(BaseModel):
    id: int
    namn: str
    kortnamn: str | None
    model_config = {"from_attributes": True}


class AnstallningOut(BaseModel):
    id: int
    tjanstgoringspct: Decimal
    brutto_timmar: int
    semester_timmar: int
    fok_pct_override: Decimal | None
    kollegialt_pct_override: Decimal | None
    giltig_fran: date
    giltig_till: date | None
    model_config = {"from_attributes": True}


class PersonListOut(BaseModel):
    id: int
    namn: str
    initialer: str
    titel_typ: TitelTyp | None
    titel_display: str | None
    amnesomrade: str | None
    personalkategori: PersonKategori
    kategori_typ: PersonKategoriTyp
    fran_organisation: str | None
    avdelning: AvdelningOut | None
    aktiv: bool
    model_config = {"from_attributes": True}


class UppdragOut(BaseModel):
    id: int
    namn: str
    typ: UppdragTyp
    varde: Decimal
    planeringsår: int
    period: str | None
    notering: str | None
    model_config = {"from_attributes": True}


class FranvaroOut(BaseModel):
    id: int
    typ: FranvaroTyp
    timmar: Decimal
    start_datum: date
    slut_datum: date
    planeringsår: int
    model_config = {"from_attributes": True}


class TidskontoDel(BaseModel):
    """Detaljerad tidsanalys för en person."""
    person_id: int
    planeringsår: int
    brutto_timmar: Decimal
    semester_timmar: Decimal
    heltidsbas: Decimal
    tjanstgoringspct: Decimal
    justerad_heltidsbas: Decimal
    franvaro_timmar: Decimal
    netto_bemanningsbar: Decimal
    fok_pct: Decimal
    fok_timmar: Decimal
    kollegialt_pct: Decimal
    kollegialt_timmar: Decimal
    uppdrag_timmar_totalt: Decimal
    uppdrag_detaljer: list
    tillganglig_undervisning: Decimal
    undervisning_godkand: Decimal
    undervisning_begard: Decimal
    undervisning_utkast: Decimal
    undervisning_totalt_planerad: Decimal
    aterstaar: Decimal
    aterstaar_inkl_begard: Decimal
    belaggningspct: Decimal


class PersonDetailOut(PersonListOut):
    anstallningar: list[AnstallningOut]
    uppdrag: list[UppdragOut]
    franvaro: list[FranvaroOut]


class KursListOut(BaseModel):
    id: int
    kod: str
    namn: str
    hp: Decimal
    niva: str | None
    amnesomrade: str | None
    period_id: int
    studenter: int | None
    budget_timmar: Decimal | None
    bemannat_godkand: Decimal = Decimal("0")
    bemannat_begard: Decimal = Decimal("0")
    model_config = {"from_attributes": True}


class KapacitetOut(BaseModel):
    person_id: int
    namn: str
    initialer: str
    titel_display: str | None
    titel_typ: TitelTyp | None
    avdelning_id: int | None
    avdelning_namn: str | None
    personalkategori: PersonKategori
    kategori_typ: PersonKategoriTyp
    netto_bemanningsbar: float
    tillganglig_undervisning: float
    undervisning_godkand: float
    undervisning_begard: float
    aterstaar: float
    aterstaar_inkl_begard: float
    belaggningspct: float


class KurstimTypOut(BaseModel):
    id: int
    timtyp: KurstimTyp
    timmar: Decimal
    model_config = {"from_attributes": True}


class BelaggningOut(BaseModel):
    id: int
    kurs_id: int
    person_id: int
    person: PersonListOut
    timtyp: KurstimTyp | None
    timmar: Decimal
    status: AssignmentStatus
    begard_av_id: int | None
    begard_vid: datetime | None
    granskad_av_id: int | None
    granskad_vid: datetime | None
    gransknings_kommentar: str | None
    model_config = {"from_attributes": True}


class KursDetailOut(KursListOut):
    timtyper: list[KurstimTypOut]
    belaggningar: list[BelaggningOut]


class BelaggningCreate(BaseModel):
    kurs_id: int
    person_id: int
    timmar: Decimal
    timtyp: KurstimTyp | None = None
    status: AssignmentStatus = AssignmentStatus.utkast


class BelaggningGranska(BaseModel):
    status: AssignmentStatus  # godkand eller nekad
    kommentar: str | None = None


class KursMiniOut(BaseModel):
    id: int
    kod: str
    namn: str
    hp: Decimal
    period_id: int
    budget_timmar: Decimal | None
    model_config = {"from_attributes": True}


class PersonBelaggningOut(BaseModel):
    id: int
    kurs: KursMiniOut
    timtyp: KurstimTyp | None
    timmar: Decimal
    status: AssignmentStatus
    begard_vid: datetime | None
    granskad_vid: datetime | None
    gransknings_kommentar: str | None
    model_config = {"from_attributes": True}


class ValideringsResultat(BaseModel):
    fel: list[dict]
    tidskonto: TidskontoDel


class AnvandarRollOut(BaseModel):
    roll: UserRoll
    avdelning: AvdelningOut | None
    model_config = {"from_attributes": True}


class AnvandareOut(BaseModel):
    id: int
    epost: str
    namn: str
    person_id: int | None
    roller: list[AnvandarRollOut]
    model_config = {"from_attributes": True}


class LoginIn(BaseModel):
    epost: str
    losenord: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    anvandare: AnvandareOut

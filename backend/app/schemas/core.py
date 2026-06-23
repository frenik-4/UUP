from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.core import (
    PersonKategori, PersonKategoriTyp, TitelTyp, UppdragTyp,
    AssignmentStatus, KurstimTyp, UserRoll, FranvaroTyp,
    ReduktionsTriggerTyp, ReduktionsEffektTyp
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
    personnummer: str | None = None
    kompetenser: str | None = None
    personalkategori: PersonKategori
    kategori_typ: PersonKategoriTyp
    fran_organisation: str | None
    avdelning: AvdelningOut | None
    aktiv: bool
    model_config = {"from_attributes": True}


class EkonomMiniOut(BaseModel):
    id: int
    namn: str
    initialer: str
    model_config = {"from_attributes": True}


class UppdragOut(BaseModel):
    id: int
    namn: str
    typ: UppdragTyp
    varde: Decimal
    planeringsår: int
    start_datum: date | None = None
    slut_datum: date | None = None
    godkand: bool = True
    notering: str | None = None
    projekt_kategori: str | None = None
    ekonom_person_id: int | None = None
    ekonom: EkonomMiniOut | None = None
    model_config = {"from_attributes": True}


class FranvaroOut(BaseModel):
    id: int
    typ: FranvaroTyp
    timmar: Decimal
    pct_av_heltid: int | None = None
    start_datum: date
    slut_datum: date
    planeringsår: int
    notering: str | None = None
    is_schablonsemester: bool = False
    model_config = {"from_attributes": True}


class FranvaroCreate(BaseModel):
    typ: FranvaroTyp
    timmar: Decimal = Decimal("0")
    pct_av_heltid: int | None = None
    start_datum: date
    slut_datum: date
    planeringsår: int
    notering: str | None = None
    is_schablonsemester: bool = False


class SchablonsemesterIn(BaseModel):
    planeringsår: int
    start_datum: date


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
    anvandare: "AnvandareOut | None" = None


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
    belaggning_start: date | None = None
    belaggning_slut: date | None = None
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
    belaggning_start: date | None = None
    belaggning_slut: date | None = None


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
    belaggning_start: date | None = None
    belaggning_slut: date | None = None
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
    amnesomrade: str | None = None
    model_config = {"from_attributes": True}


class AnvandareOut(BaseModel):
    id: int
    epost: str
    namn: str
    person_id: int | None
    roller: list[AnvandarRollOut]
    model_config = {"from_attributes": True}


class PersonUpdate(BaseModel):
    namn: str | None = None
    initialer: str | None = None
    titel_typ: TitelTyp | None = None
    titel_display: str | None = None
    amnesomrade: str | None = None
    personnummer: str | None = None
    kompetenser: str | None = None
    personalkategori: PersonKategori | None = None
    kategori_typ: PersonKategoriTyp | None = None
    fran_organisation: str | None = None
    avdelning_id: int | None = None
    aktiv: bool | None = None


class UppdragCreate(BaseModel):
    namn: str
    typ: UppdragTyp
    varde: Decimal
    planeringsår: int
    start_datum: date | None = None
    slut_datum: date | None = None
    godkand: bool = True
    notering: str | None = None


class AnstallningUpdate(BaseModel):
    tjanstgoringspct: Decimal | None = None
    brutto_timmar: int | None = None
    semester_timmar: int | None = None
    fok_pct_override: Decimal | None = None
    kollegialt_pct_override: Decimal | None = None
    giltig_fran: date | None = None
    giltig_till: date | None = None
    clear_fok_override: bool = False
    clear_kollegialt_override: bool = False


class AnstallningCreate(BaseModel):
    tjanstgoringspct: Decimal = Decimal("100")
    brutto_timmar: int = 1975
    semester_timmar: int = 275
    fok_pct_override: Decimal | None = None
    kollegialt_pct_override: Decimal | None = None
    giltig_fran: date
    giltig_till: date | None = None


class InstallningOut(BaseModel):
    key: str
    value: str
    beskrivning: str | None
    model_config = {"from_attributes": True}


class InstallningBatchUpdate(BaseModel):
    updates: dict[str, str]


class UppdragUpdate(BaseModel):
    namn: str | None = None
    projekt_kategori: str | None = None
    ekonom_person_id: int | None = None
    clear_ekonom: bool = False


class ReduktionsRegelOut(BaseModel):
    id: int
    namn: str
    trigger_typ: ReduktionsTriggerTyp
    trigger_varde: str
    effekt_typ: ReduktionsEffektTyp
    effekt_varde: Decimal
    aktiv: bool
    beskrivning: str | None = None
    model_config = {"from_attributes": True}


class ReduktionsRegelCreate(BaseModel):
    namn: str
    trigger_typ: ReduktionsTriggerTyp
    trigger_varde: str
    effekt_typ: ReduktionsEffektTyp
    effekt_varde: Decimal
    aktiv: bool = True
    beskrivning: str | None = None


class ReduktionsRegelUpdate(BaseModel):
    namn: str | None = None
    trigger_typ: ReduktionsTriggerTyp | None = None
    trigger_varde: str | None = None
    effekt_typ: ReduktionsEffektTyp | None = None
    effekt_varde: Decimal | None = None
    aktiv: bool | None = None
    beskrivning: str | None = None


class LoginIn(BaseModel):
    epost: str
    losenord: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    anvandare: AnvandareOut

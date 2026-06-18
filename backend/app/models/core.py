from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric,
    String, Text, Enum as SAEnum, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class PersonKategori(str, enum.Enum):
    undervisande = "undervisande"           # Undervisande personal (enl AO)
    annan_uf = "annan_uf"                   # Annan undervisande o forskande personal
    forskarstuderande = "forskarstuderande" # Doktorander
    administrativ = "administrativ"         # Administrativ personal
    teknisk = "teknisk"                     # Teknisk personal
    skolavtal = "skolavtal"                 # Skolavtal

class PersonKategoriTyp(str, enum.Enum):
    anstalld = "anstalld"
    extern = "extern"
    inlanad = "inlanad"

class TitelTyp(str, enum.Enum):
    professor = "professor"
    docent = "docent"                       # Universitetslektor med docentkompetens
    lektor = "lektor"                       # Universitetslektor
    adjunkt = "adjunkt"                     # Universitetsadjunkt
    doktorand = "doktorand"
    forskare = "forskare"
    forskarassistent = "forskarassistent"
    provutvecklare = "provutvecklare"
    annan = "annan"

class UppdragTyp(str, enum.Enum):
    pct_heltid = "pct_heltid"              # % av heltidsbas (1700h × tjänstgr%)
    pct_bemanningsbar = "pct_bemanningsbar" # % av netto bemanningsbar
    fasta_timmar = "fasta_timmar"           # Fast antal timmar

class PlaneringsperiodTyp(str, enum.Enum):
    termin = "termin"
    kalenderar = "kalenderar"

class KurstimTyp(str, enum.Enum):
    forelasning = "forelasning"
    seminarium = "seminarium"
    examination = "examination"
    handledning = "handledning"
    ovrigt = "ovrigt"

class AssignmentStatus(str, enum.Enum):
    utkast = "utkast"       # STR håller på
    begard = "begard"       # STR har skickat till AVDC
    godkand = "godkand"     # AVDC har sagt ja
    nekad = "nekad"         # AVDC har nekat

class FranvaroTyp(str, enum.Enum):
    sjukdom = "sjukdom"
    foraldraledighet = "foraldraledighet"
    tjanstledighet = "tjanstledighet"
    vab = "vab"
    konferens = "konferens"
    ovrigt = "ovrigt"

class UserRoll(str, enum.Enum):
    sysadmin = "sysadmin"
    prefekt = "prefekt"
    avdc = "avdc"
    str_roll = "str_roll"
    ekonom = "ekonom"
    larare = "larare"
    hr = "hr"


# ── Globala inställningar ────────────────────────────────────────────────────

class Installning(Base):
    __tablename__ = "installningar"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))
    beskrivning: Mapped[str | None] = mapped_column(Text)
    uppdaterad: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


# ── Organisationsstruktur ────────────────────────────────────────────────────

class Avdelning(Base):
    __tablename__ = "avdelningar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namn: Mapped[str] = mapped_column(String(200))
    kortnamn: Mapped[str | None] = mapped_column(String(20))
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)

    personer: Mapped[list["Person"]] = relationship("Person", back_populates="avdelning")
    roller: Mapped[list["AnvandarRoll"]] = relationship("AnvandarRoll", back_populates="avdelning")


# ── Personal ─────────────────────────────────────────────────────────────────

class Person(Base):
    __tablename__ = "personer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namn: Mapped[str] = mapped_column(String(200))
    initialer: Mapped[str] = mapped_column(String(5))
    titel_typ: Mapped[TitelTyp | None] = mapped_column(SAEnum(TitelTyp))
    titel_display: Mapped[str | None] = mapped_column(String(100))  # fritext t.ex. "Universitetslektor"
    amnesomrade: Mapped[str | None] = mapped_column(String(200))
    personalkategori: Mapped[PersonKategori] = mapped_column(SAEnum(PersonKategori))
    kategori_typ: Mapped[PersonKategoriTyp] = mapped_column(SAEnum(PersonKategoriTyp), default=PersonKategoriTyp.anstalld)
    fran_organisation: Mapped[str | None] = mapped_column(String(200))  # för externa/inlånade
    avdelning_id: Mapped[int | None] = mapped_column(ForeignKey("avdelningar.id"))
    ansvarig_chef_id: Mapped[int | None] = mapped_column(ForeignKey("anvandare.id"))  # för externa/inlånade
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    skapad: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    avdelning: Mapped["Avdelning | None"] = relationship("Avdelning", back_populates="personer")
    ansvarig_chef: Mapped["Anvandare | None"] = relationship("Anvandare", foreign_keys=[ansvarig_chef_id])
    anstallningar: Mapped[list["Anstallning"]] = relationship("Anstallning", back_populates="person", order_by="Anstallning.giltig_fran.desc()")
    franvaro: Mapped[list["Franvaro"]] = relationship("Franvaro", back_populates="person")
    uppdrag: Mapped[list["Uppdrag"]] = relationship("Uppdrag", back_populates="person")
    kursbelaggningar: Mapped[list["Kursbelaggning"]] = relationship("Kursbelaggning", back_populates="person")
    anvandare: Mapped["Anvandare | None"] = relationship("Anvandare", back_populates="person", foreign_keys="Anvandare.person_id")


class Anstallning(Base):
    """En persons anställningsvillkor under en period."""
    __tablename__ = "anstallningar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("personer.id"))
    tjanstgoringspct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100)  # 0-100
    brutto_timmar: Mapped[int] = mapped_column(Integer, default=1975)   # t.ex. 1975
    semester_timmar: Mapped[int] = mapped_column(Integer, default=275)  # t.ex. 275
    fok_pct_override: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # null = använd global inställning
    kollegialt_pct_override: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    giltig_fran: Mapped[date] = mapped_column(Date)
    giltig_till: Mapped[date | None] = mapped_column(Date)

    person: Mapped["Person"] = relationship("Person", back_populates="anstallningar")


class Franvaro(Base):
    __tablename__ = "franvaro"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("personer.id"))
    typ: Mapped[FranvaroTyp] = mapped_column(SAEnum(FranvaroTyp))
    timmar: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    start_datum: Mapped[date] = mapped_column(Date)
    slut_datum: Mapped[date] = mapped_column(Date)
    planeringsår: Mapped[int] = mapped_column(Integer)
    notering: Mapped[str | None] = mapped_column(Text)

    person: Mapped["Person"] = relationship("Person", back_populates="franvaro")


class Uppdrag(Base):
    """Projekt/förtroendeuppdrag som belastar en persons tid."""
    __tablename__ = "uppdrag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("personer.id"))
    namn: Mapped[str] = mapped_column(String(300))
    typ: Mapped[UppdragTyp] = mapped_column(SAEnum(UppdragTyp))
    varde: Mapped[Decimal] = mapped_column(Numeric(8, 2))  # % eller timmar beroende på typ
    planeringsår: Mapped[int] = mapped_column(Integer)
    period: Mapped[str | None] = mapped_column(String(20))  # "HT", "VT", eller null för hela året
    notering: Mapped[str | None] = mapped_column(Text)

    person: Mapped["Person"] = relationship("Person", back_populates="uppdrag")


# ── Kurser ───────────────────────────────────────────────────────────────────

class Planeringsperiod(Base):
    __tablename__ = "planeringsperioder"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namn: Mapped[str] = mapped_column(String(50))   # "HT 2025", "2025"
    typ: Mapped[PlaneringsperiodTyp] = mapped_column(SAEnum(PlaneringsperiodTyp))
    start_datum: Mapped[date] = mapped_column(Date)
    slut_datum: Mapped[date] = mapped_column(Date)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)

    kurser: Mapped[list["Kurs"]] = relationship("Kurs", back_populates="period")


class Kurs(Base):
    __tablename__ = "kurser"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kod: Mapped[str] = mapped_column(String(20))
    namn: Mapped[str] = mapped_column(String(300))
    hp: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    niva: Mapped[str | None] = mapped_column(String(50))        # grund/avancerad/forskar
    amnesomrade: Mapped[str | None] = mapped_column(String(200))
    period_id: Mapped[int] = mapped_column(ForeignKey("planeringsperioder.id"))
    studenter: Mapped[int | None] = mapped_column(Integer)
    budget_timmar: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    primary_str_id: Mapped[int | None] = mapped_column(ForeignKey("anvandare.id"))
    notering: Mapped[str | None] = mapped_column(Text)

    period: Mapped["Planeringsperiod"] = relationship("Planeringsperiod", back_populates="kurser")
    primary_str: Mapped["Anvandare | None"] = relationship("Anvandare", foreign_keys=[primary_str_id])
    timtyper: Mapped[list["KursTidfordelning"]] = relationship("KursTidfordelning", back_populates="kurs", cascade="all, delete-orphan")
    belaggningar: Mapped[list["Kursbelaggning"]] = relationship("Kursbelaggning", back_populates="kurs")


class KursTidfordelning(Base):
    """Fördelning av en kurs budgettimmar på typ (föreläsning, seminarium etc.)."""
    __tablename__ = "kurs_tidfordelning"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kurs_id: Mapped[int] = mapped_column(ForeignKey("kurser.id"))
    timtyp: Mapped[KurstimTyp] = mapped_column(SAEnum(KurstimTyp))
    timmar: Mapped[Decimal] = mapped_column(Numeric(8, 2))

    kurs: Mapped["Kurs"] = relationship("Kurs", back_populates="timtyper")


class Kursbelaggning(Base):
    """Koppling person ↔ kurs med timmar och godkännandeflöde."""
    __tablename__ = "kursbelaggningar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kurs_id: Mapped[int] = mapped_column(ForeignKey("kurser.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("personer.id"))
    timtyp: Mapped[KurstimTyp | None] = mapped_column(SAEnum(KurstimTyp))  # null = generell
    timmar: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    status: Mapped[AssignmentStatus] = mapped_column(SAEnum(AssignmentStatus), default=AssignmentStatus.utkast)
    begard_av_id: Mapped[int | None] = mapped_column(ForeignKey("anvandare.id"))
    begard_vid: Mapped[datetime | None] = mapped_column(DateTime)
    granskad_av_id: Mapped[int | None] = mapped_column(ForeignKey("anvandare.id"))
    granskad_vid: Mapped[datetime | None] = mapped_column(DateTime)
    gransknings_kommentar: Mapped[str | None] = mapped_column(Text)

    kurs: Mapped["Kurs"] = relationship("Kurs", back_populates="belaggningar")
    person: Mapped["Person"] = relationship("Person", back_populates="kursbelaggningar")
    begard_av: Mapped["Anvandare | None"] = relationship("Anvandare", foreign_keys=[begard_av_id])
    granskad_av: Mapped["Anvandare | None"] = relationship("Anvandare", foreign_keys=[granskad_av_id])


# ── Användare och roller ──────────────────────────────────────────────────────

class Anvandare(Base):
    __tablename__ = "anvandare"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    epost: Mapped[str] = mapped_column(String(200), unique=True)
    namn: Mapped[str] = mapped_column(String(200))
    losenord_hash: Mapped[str] = mapped_column(String(200))
    person_id: Mapped[int | None] = mapped_column(ForeignKey("personer.id"))
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    skapad: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    person: Mapped["Person | None"] = relationship("Person", back_populates="anvandare", foreign_keys=[person_id])
    roller: Mapped[list["AnvandarRoll"]] = relationship("AnvandarRoll", back_populates="anvandare")


class AnvandarRoll(Base):
    """En användares roll, med valfri koppling till avdelning (scope)."""
    __tablename__ = "anvandar_roller"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anvandare_id: Mapped[int] = mapped_column(ForeignKey("anvandare.id"))
    roll: Mapped[UserRoll] = mapped_column(SAEnum(UserRoll))
    avdelning_id: Mapped[int | None] = mapped_column(ForeignKey("avdelningar.id"))  # scope för avdc

    anvandare: Mapped["Anvandare"] = relationship("Anvandare", back_populates="roller")
    avdelning: Mapped["Avdelning | None"] = relationship("Avdelning", back_populates="roller")

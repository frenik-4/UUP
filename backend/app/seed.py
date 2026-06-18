"""Seed-data med anonymiserade mock-personer baserade på IPS-strukturen."""
from datetime import date
from decimal import Decimal
import bcrypt as _bcrypt
from sqlalchemy.orm import Session

from app.models.core import (
    Installning, Avdelning, Person, Anstallning, Uppdrag, Franvaro,
    Kurs, KursTidfordelning, Kursbelaggning, Planeringsperiod,
    Anvandare, AnvandarRoll,
    PersonKategori, PersonKategoriTyp, TitelTyp, UppdragTyp,
    PlaneringsperiodTyp, KurstimTyp, AssignmentStatus, UserRoll, FranvaroTyp
)

def _hash(pw: str) -> str:
    return _bcrypt.hashpw(pw.encode(), _bcrypt.gensalt()).decode()


def seed(db: Session):
    if db.query(Avdelning).count() > 0:
        return  # redan seedat

    # ── Inställningar ──────────────────────────────────────────────────────
    installningar = [
        Installning(key="fok_pct_professor", value="27", beskrivning="FOK% för professor"),
        Installning(key="fok_pct_docent", value="27", beskrivning="FOK% för docent"),
        Installning(key="fok_pct_lektor", value="18", beskrivning="FOK% för lektor"),
        Installning(key="fok_pct_adjunkt", value="10", beskrivning="FOK% för adjunkt"),
        Installning(key="kollegialt_pct", value="5", beskrivning="Kollegial tid % (alla)"),
        Installning(key="brutto_timmar_35d", value="1975", beskrivning="Bruttotimmar vid 35 semesterdagar"),
        Installning(key="brutto_timmar_31d", value="1732", beskrivning="Bruttotimmar vid 31 semesterdagar"),
        Installning(key="brutto_timmar_28d", value="1756", beskrivning="Bruttotimmar vid 28 semesterdagar"),
    ]
    db.add_all(installningar)
    db.flush()

    # ── Avdelningar ────────────────────────────────────────────────────────
    avd_ped = Avdelning(namn="Pedagogik och Didaktik", kortnamn="PD")
    avd_spe = Avdelning(namn="Specialpedagogik", kortnamn="SP")
    avd_spr = Avdelning(namn="Språk och Bedömning", kortnamn="SB")
    avd_utb = Avdelning(namn="Utbildningsutveckling", kortnamn="UU")
    avd_for = Avdelning(namn="Forskarutbildning", kortnamn="FU")
    avd_adm = Avdelning(namn="Administration", kortnamn="ADM")
    db.add_all([avd_ped, avd_spe, avd_spr, avd_utb, avd_for, avd_adm])
    db.flush()

    # ── Planeringsperioder ─────────────────────────────────────────────────
    ht25 = Planeringsperiod(namn="HT 2025", typ=PlaneringsperiodTyp.termin,
                            start_datum=date(2025, 8, 25), slut_datum=date(2026, 1, 19), aktiv=True)
    vt26 = Planeringsperiod(namn="VT 2026", typ=PlaneringsperiodTyp.termin,
                            start_datum=date(2026, 1, 20), slut_datum=date(2026, 6, 7), aktiv=True)
    ar25 = Planeringsperiod(namn="2025", typ=PlaneringsperiodTyp.kalenderar,
                            start_datum=date(2025, 1, 1), slut_datum=date(2025, 12, 31), aktiv=True)
    ar26 = Planeringsperiod(namn="2026", typ=PlaneringsperiodTyp.kalenderar,
                            start_datum=date(2026, 1, 1), slut_datum=date(2026, 12, 31), aktiv=True)
    db.add_all([ht25, vt26, ar25, ar26])
    db.flush()

    # ── Hjälpfunktion ──────────────────────────────────────────────────────
    def person(namn, init, titel_typ, titel_display, kat, avd, pct=100, brutto=1975, sem=275,
               fok_ov=None, koll_ov=None, ktyp=PersonKategoriTyp.anstalld, fran_org=None, amne=None):
        p = Person(
            namn=namn, initialer=init, titel_typ=titel_typ, titel_display=titel_display,
            personalkategori=kat, kategori_typ=ktyp,
            fran_organisation=fran_org, avdelning=avd, amnesomrade=amne
        )
        db.add(p)
        db.flush()
        a = Anstallning(
            person=p, tjanstgoringspct=Decimal(str(pct)),
            brutto_timmar=brutto, semester_timmar=sem,
            fok_pct_override=Decimal(str(fok_ov)) if fok_ov is not None else None,
            kollegialt_pct_override=Decimal(str(koll_ov)) if koll_ov is not None else None,
            giltig_fran=date(2025, 1, 1)
        )
        db.add(a)
        return p

    # ── Personal: Pedagogik och Didaktik ──────────────────────────────────
    p_bergstrom  = person("Erik Bergström", "EB", TitelTyp.professor, "Professor",
                          PersonKategori.undervisande, avd_ped, amne="Pedagogik")
    p_lindqvist  = person("Anna Lindqvist", "AL", TitelTyp.docent, "Universitetslektor",
                          PersonKategori.undervisande, avd_ped, amne="Pedagogik")
    p_hansson    = person("Lars Hansson", "LH", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_ped, amne="Pedagogik")
    p_svensson   = person("Maria Svensson", "MS", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_ped, amne="Didaktik")
    p_nyman      = person("Johan Nyman", "JN", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_ped, amne="Pedagogik")
    p_ekberg     = person("Lena Ekberg", "LE", TitelTyp.adjunkt, "Universitetsadjunkt",
                          PersonKategori.undervisande, avd_ped, amne="Pedagogik", brutto=1756, sem=248)
    p_holm       = person("Peter Holm", "PH", TitelTyp.adjunkt, "Universitetsadjunkt",
                          PersonKategori.undervisande, avd_ped, amne="Didaktik")
    p_carlsson   = person("Sara Carlsson", "SC", TitelTyp.adjunkt, "Universitetsadjunkt",
                          PersonKategori.undervisande, avd_ped, pct=80, amne="Pedagogik")
    p_lundberg   = person("Mikael Lundberg", "ML", TitelTyp.doktorand, "Doktorand",
                          PersonKategori.forskarstuderande, avd_for, amne="Pedagogik")

    # ── Personal: Specialpedagogik ─────────────────────────────────────────
    p_nilsson    = person("Karin Nilsson", "KN", TitelTyp.professor, "Professor",
                          PersonKategori.undervisande, avd_spe, amne="Specialpedagogik")
    p_petersson  = person("Anders Petersson", "AP", TitelTyp.docent, "Universitetslektor",
                          PersonKategori.undervisande, avd_spe, amne="Specialpedagogik")
    p_olsson     = person("Helena Olsson", "HO", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_spe, amne="Specialpedagogik")
    p_lindgren   = person("Thomas Lindgren", "TL", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_spe, amne="Specialpedagogik", brutto=1756, sem=248)
    p_johansson  = person("Eva Johansson", "EJ", TitelTyp.adjunkt, "Universitetsadjunkt",
                          PersonKategori.undervisande, avd_spe, amne="Specialpedagogik")
    p_magnusson  = person("Ulf Magnusson", "UM", TitelTyp.adjunkt, "Universitetsadjunkt",
                          PersonKategori.undervisande, avd_spe, pct=50, amne="Specialpedagogik")
    p_gustafsson = person("Britta Gustafsson", "BG", TitelTyp.doktorand, "Doktorand",
                          PersonKategori.forskarstuderande, avd_for, amne="Specialpedagogik")
    p_persson    = person("David Persson", "DP", TitelTyp.doktorand, "Doktorand",
                          PersonKategori.forskarstuderande, avd_for, amne="Specialpedagogik")

    # ── Personal: Språk och Bedömning ─────────────────────────────────────
    p_stromberg  = person("Lisa Strömberg", "LS", TitelTyp.professor, "Professor",
                          PersonKategori.undervisande, avd_spr, amne="Språkpedagogik")
    p_bjork      = person("Martin Björk", "MB", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_spr, amne="Språkpedagogik")
    p_wallin     = person("Cecilia Wallin", "CW", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_spr, amne="Bedömning")
    p_hedlund    = person("Fredrik Hedlund", "FH", TitelTyp.adjunkt, "Universitetsadjunkt",
                          PersonKategori.undervisande, avd_spr, amne="Språkpedagogik")
    p_engstrom   = person("Annika Engström", "AE", TitelTyp.provutvecklare, "Provutvecklare",
                          PersonKategori.annan_uf, avd_spr)
    p_lund       = person("Per Lund", "PL", TitelTyp.provutvecklare, "Provutvecklare",
                          PersonKategori.annan_uf, avd_spr, pct=25)
    p_fransson   = person("Maja Fransson", "MF", TitelTyp.doktorand, "Doktorand",
                          PersonKategori.forskarstuderande, avd_for, amne="Språkpedagogik")

    # ── Personal: Utbildningsutveckling ───────────────────────────────────
    p_eliasson   = person("Gunnar Eliasson", "GE", TitelTyp.professor, "Professor",
                          PersonKategori.undervisande, avd_utb, amne="Utbildningsledarskap")
    p_jonsson    = person("Pia Jonsson", "PJ", TitelTyp.docent, "Universitetslektor",
                          PersonKategori.undervisande, avd_utb, amne="Utbildningsledarskap")
    p_lindstrom  = person("Niklas Lindström", "NL", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_utb, amne="Utbildningsledarskap")
    p_axelsson   = person("Ingrid Axelsson", "IA", TitelTyp.lektor, "Universitetslektor",
                          PersonKategori.undervisande, avd_utb, pct=80, amne="Utbildningsutveckling")
    p_sandberg   = person("Robert Sandberg", "RS", TitelTyp.adjunkt, "Universitetsadjunkt",
                          PersonKategori.undervisande, avd_utb, amne="Utbildningsledarskap")
    p_molander   = person("Susanne Molander", "SM", TitelTyp.adjunkt, "Universitetsadjunkt",
                          PersonKategori.undervisande, avd_utb, amne="Utbildningsutveckling")
    p_isaksson   = person("Henrik Isaksson", "HI", TitelTyp.doktorand, "Doktorand",
                          PersonKategori.forskarstuderande, avd_for, amne="Utbildningsledarskap")
    p_martensson = person("Sofia Mårtensson", "SoM", TitelTyp.doktorand, "Doktorand",
                          PersonKategori.forskarstuderande, avd_for, amne="Utbildningsutveckling")

    # ── Externa / inlånade ────────────────────────────────────────────────
    p_ext1 = person("Joakim Lindelöf", "JL", TitelTyp.lektor, "Universitetslektor",
                    PersonKategori.undervisande, None, pct=0,
                    ktyp=PersonKategoriTyp.inlanad, fran_org="Inst. för pedagogik, kommunikation och lärande",
                    amne="Pedagogik")
    p_ext2 = person("Rebecka Thorén", "RT", TitelTyp.adjunkt, "Universitetsadjunkt",
                    PersonKategori.undervisande, None, pct=0,
                    ktyp=PersonKategoriTyp.extern, fran_org="Förvaltningshögskolan",
                    amne="Samhällsvetenskap")

    # ── Administration ────────────────────────────────────────────────────
    p_adm1 = person("Christina Åberg", "CÅ", TitelTyp.annan, "Administrativ chef",
                    PersonKategori.administrativ, avd_adm)
    p_adm2 = person("Jonas Lindahl", "JLi", TitelTyp.annan, "Ekonomicontroller",
                    PersonKategori.administrativ, avd_adm)
    p_adm3 = person("Monica Björklund", "MBj", TitelTyp.annan, "Studievägledare",
                    PersonKategori.administrativ, avd_adm)

    db.flush()

    # ── Uppdrag ───────────────────────────────────────────────────────────
    db.add_all([
        Uppdrag(person=p_bergstrom, namn="Vice prefekt forskning", typ=UppdragTyp.pct_heltid,
                varde=Decimal("20"), planeringsår=2026),
        Uppdrag(person=p_nilsson, namn="Prefekt", typ=UppdragTyp.pct_heltid,
                varde=Decimal("50"), planeringsår=2026),
        Uppdrag(person=p_lindqvist, namn="Studierektor grundutbildning", typ=UppdragTyp.pct_heltid,
                varde=Decimal("20"), planeringsår=2026),
        Uppdrag(person=p_stromberg, namn="Forskningsprojekt STINT", typ=UppdragTyp.pct_bemanningsbar,
                varde=Decimal("30"), planeringsår=2026),
        Uppdrag(person=p_eliasson, namn="Extern bedömning VR", typ=UppdragTyp.fasta_timmar,
                varde=Decimal("80"), planeringsår=2026),
        Uppdrag(person=p_wallin, namn="Nationellt provuppdrag", typ=UppdragTyp.fasta_timmar,
                varde=Decimal("200"), planeringsår=2026),
        Uppdrag(person=p_carlsson, namn="Programansvar", typ=UppdragTyp.pct_heltid,
                varde=Decimal("10"), planeringsår=2026),
    ])

    # ── Frånvaro ──────────────────────────────────────────────────────────
    db.add_all([
        Franvaro(person=p_magnusson, typ=FranvaroTyp.sjukdom, timmar=Decimal("120"),
                 start_datum=date(2026, 2, 1), slut_datum=date(2026, 4, 30), planeringsår=2026),
        Franvaro(person=p_axelsson, typ=FranvaroTyp.tjanstledighet, timmar=Decimal("200"),
                 start_datum=date(2026, 1, 1), slut_datum=date(2026, 6, 30), planeringsår=2026),
    ])

    # ── Kurser HT 2025 ─────────────────────────────────────────────────────
    def kurs(kod, namn, hp, amne, studenter, budget, period, str_user=None):
        k = Kurs(kod=kod, namn=namn, hp=Decimal(str(hp)), niva="grund",
                 amnesomrade=amne, period=period, studenter=studenter,
                 budget_timmar=Decimal(str(budget)))
        db.add(k)
        return k

    k1  = kurs("PED101", "Introduktion till pedagogik", 7.5, "Pedagogik", 60, 120, ht25)
    k2  = kurs("PED201", "Lärande och undervisning I", 7.5, "Pedagogik", 80, 140, ht25)
    k3  = kurs("PED202", "Lärande och undervisning II", 7.5, "Pedagogik", 65, 110, vt26)
    k4  = kurs("SPP101", "Introduktion till specialpedagogik", 7.5, "Specialpedagogik", 45, 90, ht25)
    k5  = kurs("SPP201", "Specialpedagogik i praktiken", 15, "Specialpedagogik", 40, 200, ht25)
    k6  = kurs("SPP301", "Inkludering och mångfald", 7.5, "Specialpedagogik", 35, 80, vt26)
    k7  = kurs("SBE101", "Språkutveckling i skolan", 7.5, "Språkpedagogik", 55, 100, ht25)
    k8  = kurs("SBE201", "Bedömning och betygsättning", 7.5, "Bedömning", 70, 130, ht25)
    k9  = kurs("SBE301", "Nationella prov och bedömning", 7.5, "Bedömning", 45, 90, vt26)
    k10 = kurs("UTB101", "Utbildningsledarskap I", 7.5, "Utbildningsledarskap", 30, 80, ht25)
    k11 = kurs("UTB201", "Skolutveckling och förändring", 7.5, "Utbildningsutveckling", 25, 70, ht25)
    k12 = kurs("UTB301", "Professionsutveckling", 15, "Utbildningsledarskap", 20, 130, vt26)
    k13 = kurs("MET101", "Vetenskaplig metod I", 7.5, "Pedagogik", 90, 150, ht25)
    k14 = kurs("MET201", "Forskningsmetodik II", 7.5, "Pedagogik", 50, 100, vt26)
    k15 = kurs("DID101", "Ämnesdidaktik", 15, "Didaktik", 40, 160, ht25)
    db.flush()

    # ── Timtyper på kurser ────────────────────────────────────────────────
    def timtyp(kurs, typ, timmar):
        db.add(KursTidfordelning(kurs=kurs, timtyp=typ, timmar=Decimal(str(timmar))))

    timtyp(k1, KurstimTyp.forelasning, 40); timtyp(k1, KurstimTyp.seminarium, 60); timtyp(k1, KurstimTyp.examination, 20)
    timtyp(k2, KurstimTyp.forelasning, 50); timtyp(k2, KurstimTyp.seminarium, 60); timtyp(k2, KurstimTyp.examination, 30)
    timtyp(k4, KurstimTyp.forelasning, 30); timtyp(k4, KurstimTyp.seminarium, 40); timtyp(k4, KurstimTyp.examination, 20)
    timtyp(k8, KurstimTyp.forelasning, 40); timtyp(k8, KurstimTyp.seminarium, 50); timtyp(k8, KurstimTyp.examination, 40)
    timtyp(k13, KurstimTyp.forelasning, 60); timtyp(k13, KurstimTyp.seminarium, 60); timtyp(k13, KurstimTyp.examination, 30)

    # ── Kursbeläggningar (mix av statusar för att visa flödet) ────────────
    def belagg(kurs, person, timmar, status, begard_av=None, granskad_av=None):
        kb = Kursbelaggning(
            kurs=kurs, person=person, timmar=Decimal(str(timmar)), status=status,
            begard_av=begard_av, granskad_av=granskad_av
        )
        db.add(kb)
        return kb

    # Godkända
    belagg(k1, p_hansson, 80, AssignmentStatus.godkand)
    belagg(k1, p_ekberg, 40, AssignmentStatus.godkand)
    belagg(k2, p_bergstrom, 60, AssignmentStatus.godkand)
    belagg(k2, p_svensson, 80, AssignmentStatus.godkand)
    belagg(k4, p_olsson, 60, AssignmentStatus.godkand)
    belagg(k4, p_johansson, 30, AssignmentStatus.godkand)
    belagg(k5, p_nilsson, 80, AssignmentStatus.godkand)
    belagg(k5, p_petersson, 80, AssignmentStatus.godkand)
    belagg(k5, p_olsson, 40, AssignmentStatus.godkand)
    belagg(k7, p_bjork, 70, AssignmentStatus.godkand)
    belagg(k7, p_hedlund, 30, AssignmentStatus.godkand)
    belagg(k8, p_wallin, 90, AssignmentStatus.godkand)
    belagg(k8, p_stromberg, 40, AssignmentStatus.godkand)
    belagg(k10, p_eliasson, 50, AssignmentStatus.godkand)
    belagg(k10, p_jonsson, 30, AssignmentStatus.godkand)
    belagg(k11, p_lindstrom, 50, AssignmentStatus.godkand)
    belagg(k11, p_axelsson, 20, AssignmentStatus.godkand)
    belagg(k13, p_hansson, 60, AssignmentStatus.godkand)
    belagg(k13, p_nyman, 60, AssignmentStatus.godkand)
    belagg(k13, p_svensson, 30, AssignmentStatus.godkand)
    belagg(k15, p_lindqvist, 100, AssignmentStatus.godkand)
    belagg(k15, p_holm, 60, AssignmentStatus.godkand)

    # Begärda (väntar på AVDC-godkännande)
    belagg(k3, p_svensson, 90, AssignmentStatus.begard)
    belagg(k3, p_nyman, 20, AssignmentStatus.begard)
    belagg(k6, p_johansson, 50, AssignmentStatus.begard)
    belagg(k9, p_wallin, 60, AssignmentStatus.begard)
    belagg(k9, p_engstrom, 30, AssignmentStatus.begard)
    belagg(k12, p_jonsson, 80, AssignmentStatus.begard)
    belagg(k14, p_lindqvist, 60, AssignmentStatus.begard)

    # Utkast (STR håller på att planera)
    belagg(k6, p_lindgren, 30, AssignmentStatus.utkast)
    belagg(k12, p_sandberg, 50, AssignmentStatus.utkast)

    db.flush()

    # ── Användare ─────────────────────────────────────────────────────────
    def anvandare(epost, namn, roller_list, person=None):
        u = Anvandare(epost=epost, namn=namn,
                      losenord_hash=_hash("demo1234"),
                      person=person)
        db.add(u)
        db.flush()
        for roll, avd in roller_list:
            db.add(AnvandarRoll(anvandare=u, roll=roll, avdelning=avd))
        return u

    u_admin  = anvandare("admin@uup.local", "Systemadministratör",
                         [(UserRoll.sysadmin, None)])
    u_pref   = anvandare("prefekt@uup.local", "Karin Nilsson (Prefekt)",
                         [(UserRoll.prefekt, None)], person=p_nilsson)
    u_avdc1  = anvandare("avdc.ped@uup.local", "Erik Bergström (AVDC Ped)",
                         [(UserRoll.avdc, avd_ped)], person=p_bergstrom)
    u_avdc2  = anvandare("avdc.spe@uup.local", "Anders Petersson (AVDC Spe)",
                         [(UserRoll.avdc, avd_spe)], person=p_petersson)
    u_avdc3  = anvandare("avdc.spr@uup.local", "Lisa Strömberg (AVDC Spr)",
                         [(UserRoll.avdc, avd_spr)], person=p_stromberg)
    u_avdc4  = anvandare("avdc.utb@uup.local", "Gunnar Eliasson (AVDC Utb)",
                         [(UserRoll.avdc, avd_utb)], person=p_eliasson)
    u_str1   = anvandare("str.ped@uup.local", "Anna Lindqvist (STR Ped)",
                         [(UserRoll.str_roll, avd_ped)], person=p_lindqvist)
    u_str2   = anvandare("str.spe@uup.local", "Helena Olsson (STR Spe)",
                         [(UserRoll.str_roll, avd_spe)], person=p_olsson)
    u_str3   = anvandare("str.spr@uup.local", "Martin Björk (STR Spr)",
                         [(UserRoll.str_roll, avd_spr)], person=p_bjork)
    u_str4   = anvandare("str.utb@uup.local", "Niklas Lindström (STR Utb)",
                         [(UserRoll.str_roll, avd_utb)], person=p_lindstrom)
    u_str5   = anvandare("str.sbe@uup.local", "Cecilia Wallin (STR Bdn)",
                         [(UserRoll.str_roll, avd_spr)], person=p_wallin)
    u_ek1    = anvandare("ekonom@uup.local", "Jonas Lindahl (Ekonom)",
                         [(UserRoll.ekonom, None)], person=p_adm2)

    db.commit()

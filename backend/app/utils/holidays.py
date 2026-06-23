"""Svenska röda dagar och semesterdagsberäkning."""
from datetime import date, timedelta


def _easter(year: int) -> date:
    """Gregoriansk påskalgoritm (Anonymous Gregorian)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def svenska_rodadagar(ar: int) -> set[date]:
    """Returnerar mängd med alla svenska röda dagar för givet år."""
    days: set[date] = {
        date(ar, 1, 1),   # Nyårsdagen
        date(ar, 1, 6),   # Trettondedag jul
        date(ar, 5, 1),   # Första maj
        date(ar, 6, 6),   # Nationaldagen
        date(ar, 12, 24), # Julafton
        date(ar, 12, 25), # Juldagen
        date(ar, 12, 26), # Annandag jul
        date(ar, 12, 31), # Nyårsafton
    }
    pask = _easter(ar)
    days.add(pask - timedelta(days=2))   # Långfredagen
    days.add(pask)                        # Påskdagen
    days.add(pask + timedelta(days=1))   # Annandag påsk
    days.add(pask + timedelta(days=39))  # Kristi himmelsfärdsdag
    days.add(pask + timedelta(days=49))  # Pingstdagen

    # Midsommarafton: fredag 19–25 juni
    d = date(ar, 6, 19)
    while d.weekday() != 4:
        d += timedelta(days=1)
    days.add(d)
    days.add(d + timedelta(days=1))  # Midsommardagen (lördag)

    # Alla helgons dag: lördag 31 okt – 6 nov
    d = date(ar, 10, 31)
    while d.weekday() != 5:
        d += timedelta(days=1)
    days.add(d)

    return days


def count_working_days(start: date, slut: date, rodadagar: set[date] | None = None) -> int:
    """Antal arbetsdagar (mån–fre exkl. röda dagar) i intervallet [start, slut]."""
    if rodadagar is None:
        # Hämta för relevanta år
        rodadagar = set()
        for ar in range(start.year, slut.year + 1):
            rodadagar |= svenska_rodadagar(ar)
    count = 0
    d = start
    while d <= slut:
        if d.weekday() < 5 and d not in rodadagar:
            count += 1
        d += timedelta(days=1)
    return count


def semesterdagar_for_alder(fodelsear: int, planeringsår: int) -> int:
    """Semesterdagar enligt Villkorsavtalet-T baserat på ålder vid planeringsårets ingång.

    < 30 år:  28 dagar
    30–39 år: 31 dagar
    ≥ 40 år:  35 dagar
    """
    alder = planeringsår - fodelsear
    if alder < 30:
        return 28
    if alder < 40:
        return 31
    return 35


def berakna_slutdatum(start: date, antal_dagar: int, rodadagar: set[date]) -> date:
    """Returnerar slutdatum så att [start, slutdatum] innehåller exakt antal_dagar arbetsdagar."""
    count = 0
    d = start
    while count < antal_dagar:
        if d.weekday() < 5 and d not in rodadagar:
            count += 1
        if count < antal_dagar:
            d += timedelta(days=1)
    return d


def fodelsear_fran_personnummer(personnummer: str | None) -> int | None:
    """Försöker parsa födelseår ur personnummer.

    Stödda format (efter borttagning av - och mellanslag):
      YYYYMMDDXXXX (12 siffror) → returnerar YYYY
      YYYYMMDDXXX  (11 siffror) → returnerar YYYY
      YYMMDDXXXX   (10 siffror) → returnerar 19YY eller 20YY
      YYMMDDXXX    (9 siffror)  → returnerar 19YY eller 20YY
    """
    if not personnummer:
        return None
    p = personnummer.replace("-", "").replace(" ", "")
    if len(p) >= 11:
        try:
            return int(p[:4])
        except ValueError:
            return None
    if len(p) >= 6:
        try:
            yy = int(p[:2])
            from datetime import datetime
            current_yy = datetime.now().year % 100
            century = 1900 if yy > current_yy else 2000
            return century + yy
        except ValueError:
            return None
    return None

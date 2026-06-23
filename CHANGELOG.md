# Changelog

## 0.7.0 — 2026-06-23

### Nytt
- Import av alla kurser, uppdrag och forskningsprojekt från verklig bemanningsmatris (260623_96EB.xls) sedan 2024-01-01
- 494 kurser importerade (VT24–HT26) med kursbeläggningar baserade på faktiska bemannade timmar
- 100 externa forskningsprojekt (bidragsforskning) importerade som uppdrag, fördelade per planeringsår
- HT 2026 period tillagd
- Alla riktiga namn anonymiserade — kurskoder bevarade

## 0.6.0 — 2026-06-22

### Nytt
- Semester som frånvarotyp (alltid 100%, beräknat på arbetsdagar)
- Frånvaro kan anges som % av heltid (servern beräknar timmar)
- Schablonsemester: rulla ut/återta per år baserat på ålder (Villkorsavtalet-T: <30=28d, 30–39=31d, ≥40=35d)
- Kursredigering inline i kursdetaljvyn med rollbaserade rättigheter (Admin/Prefekt: allt; AvdC: STR; Ekonom: HST/HPR/budget)
- Nya kursfält: HST, HPR, ansvarig ekonom
- Sorterbara kolumnrubriker i frånvarovy och projektvy
- PATCH /kurser/{id} API-endpoint
- GET /auth/users endpoint för dropdown-listor

## 0.5.0 — 2026-06-21

### Nytt
- Svenska röda dagar och semesterdagsberäkning (utils/holidays.py)
- Beräkning av slutdatum baserat på antal semesterdagar och röda dagar
- Personnummer-parsing för födelseår

## 0.4.0 — 2026-06-20

### Nytt
- Frånvarovy med filtreringschips och tabellvyn
- Projektvy med bemanningsstatus
- Redigeringsformulär för anställningsuppgifter
- Reduktionsregler för automatisk FOK/kollegial-justering

## 0.3.0

### Nytt
- Rollbaserad åtkomstkontroll (sysadmin, prefekt, avdc, str_roll, ekonom, controller, hr, lärare)
- Kursbeläggningar med godkännandeflöde (utkast → begärd → godkänd/nekad)
- Bemanningsvy per person med tidskonto
- Kapacitetsöversikt

## 0.2.0

### Nytt
- Personregister med anställningar och frånvaro
- Kursregister med planeringsperioder
- JWT-autentisering
- Grundläggande bemanningslogik

## 0.1.0

### Nytt
- Initial version — grundstruktur FastAPI + PostgreSQL + vanilla JS

# LocationFinder
LocationFinder er (enda et) forsøk på å stedfeste stedsnavn i tekster. Tekst inn, stedsnavn med koordinater ut. En tidligere versjon av LocationFinder feilet, av mange grunner. Å tolke steder fra tekst er ikke lett.

I motsetning til tidligere forsøker jeg ikke selv i identifisere stedsnavn. Det overlater jeg til [polyglot](https://github.com/aboSamoor/polyglot), og fokuserer deretter på å finne ut av hvor disse potensielle (polyglot er heller ikke perfekt) stedene befinner seg. Dette gjøres først og fremst ved å slå opp i [Sentralt stadnamnregister (SSR)](http://kartverket.no/kart/stedsnavn/sentralt-stadnamnregister-ssr/).

## Send tekst, få ut steder med koordinater
```python
from locationfinder import LocationFinder
lf = LocationFinder()

# .get_locations tar tekst inn og gir deg steder tilbake
lf.get_locations("Jeg vil helst være i Risør om sommeren.")
# sted, (lengde, bredde), kommune
[('Risør', (58.719192, 9.223242), 'Risør')]

tekst = """Jeg vil helst være i Risør om sommeren. Eller kanskje Arendal. Eller fjellene i Hemsedal. Eller en DNT-hytte i Jotunheimen. Det er digg å være i Norge om sommeren."""
lf.get_locations(tekst)
[('Arendal', (58.461214, 8.766947), 'Arendal'),
 ('Risør', (58.719192, 9.223242), 'Risør'),
 ('Jotunheimen', (61.605003, 8.477503), 'Lom'),
 ('Norge', (62.0, 10.0), 'NA'),
 ('Hemsedal', (60.8501, 8.616381), 'Hemsedal')]
```

## Disambiguering
Mange steder i Norge deler stedsnavn. Selv kommuner har samme navn! Bø i Telemark, Bø i Nordland. Os i Hordaland, Os i Hedmark. Og ikke engang begynn med hvor mange Lia, Sandvik, Grunnesund og Storemyr vi har! Uten kontekst er det umulig å vite hvor disse er. Men vi kan prioritere gjettingen, og guide prioriteringen. De er to måter dette gjøres på.
1. [Bolstads](http://www.erikbolstad.no/geo/) prioritering. Dette er den samme som yr.no bruker (i alle fall samme utgangspunkt). Oppslag gjøres i geonames og SSR, og rankes etter Bolstads tabel. Større steder prioriteres over små, kommuner over tettsteder, tettsteder over navn på fjell og vidder etc.
2. Hint. Sitter du i Bergen og snakker om Os, så snakker du mest sansynlig om Os i Hordaland og ikke om Os i Hedmark. Send med kooridinater som hint, og nærhet til hintet gis tung vekt i utvelgelsen.


```python
# .disambiguate_places tar en liste inn og returnerer en liste med beste treff i SSR
 lf.disambiguate_places(["Bergen", "Kolbotn", "Os"])
 [('Kolbotn', (59.810561, 10.803892), 'Oppegård'),
  ('Bergen', (60.398258, 5.329072), 'Bergen'),
  ('Os', (62.496489, 11.223308), 'Os')]
 # treffene i SSR rankes etter Bolstads (yr.no) prioritet

# du kan sende med et hint. Sitter vi i Bergen forventer vi Os i Hordaland, ikke Os i Hedmark
 lf.disambiguate_places(["Bergen", "Kolbotn", "Os"], hint_location=(60.391263, 5.322054))
 [('Kolbotn', (60.406044, 5.436178), 'Oppegård'),
  ('Bergen', (60.398258, 5.329072), 'Bergen'),
  ('Os', (60.188353, 5.469786), 'Os')]
# med hintet rundes avstand fra hint til treff til nærmeste 10km og deretter velges beste treff via prioritet - legge merke til at Vi nå fikk Os på 60.1, 5.4, altså på vestlandet.
```
    >>> from locationfinder import LocationFinder
    >>> lf = LocationFinder()
    >>> lf.disambiguate_places(["Risør"])
    [('Risør', (58.719192, 9.223242), 'Risør')]
    tekst = """Jeg vil helst være i Risør om sommeren. Eller kanskje Arendal. Eller fjellene i Hemsedal. Eller en DNT-hytte i Jotunheimen. Det er digg å være i Norge om sommeren."""
    >>>lf.get_locations(tekst)
[('Risør', (58.719192, 9.223242), 'Risør'), ('Arendal', (58.461214, 8.766947), 'Arendal'), ('Hemsedal', (60.8501, 8.616381), 'Hemsedal'), ('Jotunheimen', (61.605003, 8.477503), 'Lom')]


## Hints

```
echo $1 | $OBT/bin/mtag -wxml | vislcg3 --codepage-all latin1 --codepage-input \
    utf-8 --grammar $OBT/cg/bm_morf-prestat.cg --codepage-output utf-8 --no-pass-origin --show-end-tags | \
    $OBT/OBT-Stat/bin/run_obt_stat.rb | perl -ne 'print if /\S/'
```

## mysql_settings.py
Inneholder
```
    settings = {}
    settings['user'] = 'mySQL_brukernavn'
    settings['password'] = 'mySQL_passord'
```

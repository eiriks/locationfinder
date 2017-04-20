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

tekst = """Jeg vil helst være i Risør om sommeren. Eller kanskje Arendal. Eller fjellene i Hemsedal.
Eller en DNT-hytte i Jotunheimen. Det er digg å være i Norge om sommeren."""
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


## Entitetsgjennkjenning
Å plukke ut stedsnavn fra tekster er en del entitetgjenkjenning [Named-entity recognition](https://en.wikipedia.org/wiki/Named-entity_recognition), der de to typiske andre kategoriene er personer og organisasjoner. Jeg vil bare ha steder, og støtter meg her på at [polyglot](https://github.com/aboSamoor/polyglot) (som er [neurale net](http://www.cs.cmu.edu/~ytsvetko/papers/phonology-naacl16.pdf)) er bedre enn noe jeg selv koker opp.

polyglot støtter en bråte språk, hvorav norsk bare er et. Den ser ut til å fint identifisere norsk tekst som norsk, så vi trenger stort sett ikke oppgi språk, men vi kan. Jeg har pakket polyglot inn i `.from_text_to_places()` der jeg plukker ut _kun_ steder.

```python
lf.from_text_to_places(tekst, pg_help_lang='no')
['Risør', 'Arendal', 'Hemsedal', 'Jotunheimen', 'Norge']
```
Du kan sende inn hint om [andre språk](http://polyglot.readthedocs.io/en/latest/NamedEntityRecognition.html) (men forvent da ikke så mange treff i SSR?)

## get_locations = from_text_to_places + disambiguate_places
De to funksjonene i LocationFinder (hent steder med polyglot aka `.from_text_to_places()` og `disambiguate_places()`) blir til sammen `get_locations()`.

```python
lf.disambiguate_places(lf.from_text_to_places(tekst))
[('Arendal', (58.461214, 8.766947), 'Arendal'),
 ('Risør', (58.719192, 9.223242), 'Risør'),
 ('Jotunheimen', (61.605003, 8.477503), 'Lom'),
 ('Norge', (62.0, 10.0), 'NA'),
 ('Hemsedal', (60.8501, 8.616381), 'Hemsedal')]

 lf.get_locations(tekst)
 [('Arendal', (58.461214, 8.766947), 'Arendal'),
 ('Risør', (58.719192, 9.223242), 'Risør'),
 ('Jotunheimen', (61.605003, 8.477503), 'Lom'),
 ('Norge', (62.0, 10.0), 'NA'),
 ('Hemsedal', (60.8501, 8.616381), 'Hemsedal')]
```


# kommuner aka municipality=True
Default er `True`. Ved å sende med `municipality=True` får du med ut en tuple
med (kommune, kommunenr). Bruk `municipality=False` får å sleppe.

```python
rich_places = lf.disambiguate_places(lf.from_text_to_places(article.text),
                                        verbose=True, municipality=True, hint_location=(58.163832, 8.002964))
rich_places
[('Agder', (58.163832, 8.002964)),
 ('Vennesla', (58.268564, 7.973144)),
 ('Songdalen', (58.599492, 8.650208)),
 ('Grimstad', (59.214875, 11.191272)),
 ('Søgne', (58.093278, 7.782939)),
 ('Skånes', (63.769306, 11.400722)),
 ('Vestfold', (59.170786, 10.114436)),
 ('Kristiansand', (60.568156, 11.798914)),
 ('Lillesand', (59.024197, 11.034131)),
 ('Birkenes', (61.770958, 11.187083)),
 ('Norge', (62.0, 10.0))]

rich_places = lf.disambiguate_places(lf.from_text_to_places(article.text),
                                        verbose=False, municipality=True)

rich_places
[('Agder', (58.163832, 8.002964), 'NA'),
 ('Vennesla', (58.268564, 7.973144), ('Vennesla', 1014)),
 ('Songdalen', (58.195436, 7.786997), ('Songdalen', 1017)),
 ('Grimstad', (58.340464, 8.593369), ('Grimstad', 904)),
 ('Søgne', (58.093278, 7.782939), ('Søgne', 1018)),
 ('Skånes', (63.769306, 11.400722), ('Levanger', 1719)),
 ('Vestfold', (59.170786, 10.114436), 'NA'),
 ('Kristiansand', (58.14615, 7.995733), ('Kristiansand', 1001)),
 ('Lillesand', (58.249453, 8.377192), ('Lillesand', 926)),
 ('Birkenes', (62.219864, 5.938894), ('Volda', 1519)),
 ('Norge', (62.0, 10.0), 'NA')]
```                                        

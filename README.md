# LocationFinder
```python LocationFinder.py -d```
Et stygt hack for å trekke stedsnavn ut av tekster. Sånn ca. Bruker ordlister som startpunkter og aksepterer også ord som er steder (er oppførst i Sentralt Stedsnavns Register, [SSR](http://kartverket.no/Kart/Stedsnavn/)) som er innen rimelig avstand fra allerede aksepterte steder.

# Noen raske tanker om hvorfor dette er en dårlig idé
* Å bruke OBT slik gjør at scriptet blir treigt. Mye I/O
* Kandidatene fra OBT er rimelige nok, men jeg mangler en fornuftig måte å luke ut mennesker som deler navn med et sted. Folk heter ´Eide´ og ´Nygård´, ´Solberg´ og ´Hauge´ - og det gjør halve Norges veikryss og bærbusker også. Det er 1815 rader med navn ´Stormyra´ i basen. Hauge, Åsen, Storhaugen, Langmyra, Moen, Holmen, Dalen - alle har hundrevis (>600) av steder med samme navn. Og alle disse navnene er også vanlige etternavn. Det er et mareritt.
(´SELECT *, count(*) as c FROM SSR GROUP BY for_snavn order by c desc;´)
* Å bruke lister som startsted, og avstand som neste kriterium har noe for seg, men antall feil (falske positive) øver alt for rask i forhold til nye riktige steder.
* Enten er SSR for liberalt og fantasifullt, eller så har jeg misforstått hvordan det er bygget opp. Gir meg lat/lons som ser ut som de er trillet som terninger.

Jeg lurer på om det er like greit å legge denne ballen død, om ikke annet enn for en stund. Kanskje det er en bedre idé å bygge noe på [Nominatim](http://wiki.openstreetmap.org/wiki/Nominatim) i en lokal instalasjon. Jeg må kunne si ting som "finn meg en Moen på sørlandet i nærheten av Risør", og ikke bare et sted som heter Moen - de er det 747 av, og det er 20 bare i Aust-Agder ganske nært Risør. At koden også er et kaos får bare være.


## OBT
Tar det initielle settet med ord som kan være steder fra [Oslo-Bergen-Taggeren](https://github.com/noklesta/The-Oslo-Bergen-Tagger)

OBT er la jeg til min $PATH (i .bash_profile) og i folderen med OBT ligger også _tag_bm_cmd.sh_ som inneholder følgende:
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

## terskel for avstand
Ved bare å bruke lister, skårer vi ca 70%. Vi finner 70% av de stedene som omtales. Ved å øke radiusen for _rimelig avstand_ får vi med noen flere, men også mange flere feil. Radiusen er hardkodet til 15km pr nå.
![Større avstand gir flere falske positive](http://stavelin.com/uib/LocationFinder_dist_v_errors.png "Antall feil kommer raskere enn antall rette, ved å øke radiusen for hva _rimelig nært_ er")


## 100random_urls.txt
Er min "gullstandard" for å teste mot. Først og fremst lærer jeg at 1) dey ikke alltid er lett å bestemme seg for hva et sted er og 2) at det vi ser på webben i dag ikke er det samme som jeg scrapet i 2013. Precision/recall-tall kan neppe bli en perfekt måling av dette, kanskje inter-coder-reliabillity er aktuelt?

# H1 Dette er bare markdown eksempler
## H2 for min egen del
### H3
#### H4
##### H5
###### H6
Emphasis, aka italics, with *asterisks* or _underscores_.
Strong emphasis, aka bold, with **asterisks** or __underscores__.
Combined emphasis with **asterisks and _underscores_**.
Strikethrough uses two tildes. ~~Scratch this.~~
[I'm an inline-style link](https://www.google.com)
![alt text](https://github.com/adam-p/markdown-here/raw/master/src/common/images/icon48.png "Logo Title Text 1")

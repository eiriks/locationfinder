# LocationFinder
Et stygt hack for å trekke stedsnavn ut av tekster. Sånn ca. Bruker ordlister som startpunkter og aksepterer også ord som er steder (er oppførst i Sentralt Stedsnavns Register, SSR) som er innen rimelig avstand fra allerede aksepterte steder.

Tar det initielle settet med ord som kan være steder fra [Oslo-Bergen-Taggeren]https://github.com/noklesta/The-Oslo-Bergen-Tagger)

```python LocationFinder.py -d```

## mysql_settings.py
Inneholder
```
    settings = {}
    settings['user'] = 'mySQL_brukernavn'
    settings['password'] = 'mySQL_passord'
```

## terskel for avstand

![Søtrre avstand gir flere falske positive](http://stavelin.com/uib/LocationFinder_dist_v_errors.png "Antall feil kommer raskere enn antall rette, ved å øke radiusen for hva _rimelig nært_ er")



# H1
## H2
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

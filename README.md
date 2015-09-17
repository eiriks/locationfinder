# LocationFinder
Et stygt hack for å trekke stedsnavn ut av tekster. Sånn ca. Bruker ordlister som startpunkter og aksepterer også ord som er steder (er oppførst i Sentralt Stedsnavns Register, SSR) som er innen rimelig avstand fra allerede aksepterte steder.

Tar det initielle settet med ord som kan være steder fra Oslo-Bergen-Taggeren[https://github.com/noklesta/The-Oslo-Bergen-Tagger] 

```python LocationFinder.py -d```

## mysql_settings.py
Inneholder
```
    settings = {}
    settings['user'] = 'mySQL_brukernavn'
    settings['password'] = 'mySQL_passord'
```

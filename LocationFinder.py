#!/usr/bin/python3
from polyglot.text import Text
from collections import Counter
from geopy.distance import vincenty
import sqlite3 as lite

class LocationFinder(object):
    """docstring for LocationFinder."""
    def __init__(self, arg):
        super(LocationFinder, self).__init__()
        #self.arg = arg
        self.con = lite.connect('steder.db')
        self.cur = con.cursor()

    def get_locations(self, text):
        places = self.disambiguate_places(self.from_text_to_places(text))
        return places

    def from_text_to_places(self, text):
        '''Takes a text, returns a list of locations'''
        pg_text = Text(text, hint_language_code='no')
        poly_places = []
        for ent in pg_text.entities:
            if(ent.tag == 'I-LOC'):
                poly_places.append(" ".join(ent))
        return poly_places

    def disambiguate_places(self, poly_place_list, newspaper_location="unknown", verbose=False, municipality=False):
        ''' Takes a list of places (including repeaded names) ['Oslo', 'Bergen', 'Bergen', 'Risør']
        and spits out list of tuples as (Place, (lat,long))
        [('Grorud', (59.960253, 10.881408)), ...]
        if municipality = True it returns [('Grorud', (59.960253, 10.881408), 'Oslo'), ...]
        - use municipality=True to get municipality from location
        - use newspaper=(lat,long) tuple to give a hint about where a name probably belongs
        '''
        final_places = [] # populate this please

        if verbose:
            print("newspaper_location:", newspaper_location)
            print(poly_place_list)
            print()

        # make golyglot input into counter obj
        c_places = Counter(poly_place_list)
        # Lets make sure it's Titlecase (Risør, not risør) for SSR match
        for place in c_places.most_common():
            place = place[0].title()

            # Try country first - Bolstad has forreign names in Norwegian for us:
            sql_country = """SELECT Lat, Lon, * FROM bolstads_land WHERE Nynorsk = ? or Bokmål =?;"""
            self.cur.execute(sql_country, (place, place))
            hits = self.cur.fetchall()
            if len(hits) > 0:
                final_places.append((place, (hits[0][0], hits[0][1]), 'NA'))
                if verbose:
                    print("ok, **", place, "** \t utLAND, antall treff: \t", len(hits))
                continue

            # then geonames - large places abroad (this is geonames places with pop > 15k, )
            # now.. hint from input is less important, population of the place is prob a better hint
            # .. as the US tends to name their town with european names, and have larger pop.. some erros occur.
            # do not accept Norwegian places, richer data for that later.
            sql_geonames = """SELECT latitude, longitude, country, *
                FROM geoname g
                LEFT JOIN bolstads_geoname_prioritet b on g.fcode = b.Kode
                WHERE  (g.name = ? OR g.asciiname = ?)
                AND g.country !='NO'
                ORDER BY b.Prioritet, g.population DESC;"""
            self.cur.execute(sql_geonames, (place, place))
            hits = self.cur.fetchall()
            if len(hits) > 0:
                final_places.append((place, (hits[0][0], hits[0][1]), "NA"))
                if verbose:
                    print("ok, **", place, "** \t utlandet, antall treff: \t", len(hits), "valgte:", (hits[0][0], hits[0][1]))
                continue

            # And finally SSR
            sql_ssr = """SELECT s.lat, s.long, for_snavn, Namnetype, Prioritet, k.Norsk as kommune
                     FROM SSR s, bolstads_kommunesenter k, bolstads_prioritet p
                     WHERE (s.for_snavn = ? OR s.enh_snavn = ?)
                     AND s.skr_snskrstat IN ('V', 'S', 'G', 'P')
                     AND s.enh_komm = k.Kommunenummer
                     AND s.enh_navntype = p.Nr
                     ORDER BY Prioritet ASC;"""
            # fetch the SSR resutls
            self.cur.execute(sql_ssr, (place, place))
            hits = self.cur.fetchall()

            if newspaper_location == "unknown":
                # we have no way of knowing if Bø in Telemark or Bø i Nordland is more likely
                if len(hits) == 0:                 # not a place (according to SSR)
                    if verbose:
                        print("Ingen treff i SSR på", place)
                    continue                       # places like "Sør" or "Aust-" are removed this way
                else:
                    # just grab the most highest Pirority from bolstads_prioritet
                    if verbose:
                        print("ok, **", place, "** \t antall treff i SSR: \t", len(hits), "(tok den med høyest pri)")
                        if municipality:
                            print("\t-", place, "ligger i", hits[0][5], "kommune")
                    final_places.append((place, (hits[0][0], hits[0][1]), hits[0][5]))
            else:

                if len(hits) == 0:
                    if verbose:
                        print("ok, ikke et sted **", place, "** \t antall treff: \t", len(hits))
                    continue
                elif len(hits) == 1: # one match, use this, return (name, (lat,long))
                    if verbose:
                        print("ok, **", place, "** \t antall treff: \t", len(hits))
                    final_places.append((place, (hits[0][0], hits[0][1]), hits[0][5]))
                else:
                    # we have multiple local place names.
                    # Experiments show that YR ranking works well.
                    # as an alternative, use distance from hint (newspaper_location) as tie-breaker
                    if verbose:
                        print("ok **", place, "** \t antall treff: \t", len(hits), "beste treff valgt")
                    # make a list
                    alternatives = []
                    for h in hits:
                        alternatives.append(list(h)+[round(vincenty(newspaper_location, (h[0], h[1])).meters, 0)])

                    # sort by YR-priority first, dist from hint second
                    alternatives = sorted(alternatives, key=lambda x: (x[4], x[5]))
                    if verbose:
                        print()
                    # choose the top one
                    final_places.append((place, (alternatives[0][0], alternatives[0][1])))
                #print()


        return final_places

# places2map(['Risør', 'Sør', 'Høllen', 'Søgne', 'Risør', 'Holum', 'Aust', 'Søgne'], "austagderblad")
# + høyest frekvens (risør)
# - ingen treff i SSR
# - er langt fra Kjente treff
# - en langts fra Redaksjonskontor
# - er langt fra de andre Alternativene
# bruk en votering-algoritme til å velge riktig "Ås" ? (nei, alle er ikke likeverdige)

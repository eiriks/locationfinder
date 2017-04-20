#!/usr/bin/python3
from polyglot.text import Text
from collections import Counter
from geopy.distance import vincenty
import sqlite3 as lite
import os.path

package_dir = os.path.abspath(os.path.dirname(__file__))
database_path = os.path.join(package_dir, 'steder.db')

class LocationFinder(object):
    """docstring for LocationFinder."""
    def __init__(self):
        super(LocationFinder, self).__init__()
        #self.arg = arg
        self.con = lite.connect(database_path)
        self.cur = self.con.cursor()

    def get_locations(self, text):
        '''text inn, places out'''
        places = self.disambiguate_places(self.from_text_to_places(text))
        return places

    def from_text_to_places(self, text, pg_help_lang='no'):
        '''Takes a text, returns a list of locations'''
        pg_text = Text(text, hint_language_code=pg_help_lang)
        poly_places = []
        for ent in pg_text.entities:
            if(ent.tag == 'I-LOC'):
                poly_places.append(" ".join(ent))
        return poly_places

    def disambiguate_places(self, poly_place_list, hint_location="unknown", verbose=False, municipality=True):
        '''
        Takes a list of places (including repeated names) ['Oslo', 'Bergen', 'Bergen', 'Risør']
        and spits out list of tuples as (Place, (lat,long), municipality)
        [('Grorud', (59.960253, 10.881408)), ...]
        if municipality = True it returns [('Grorud', (59.960253, 10.881408), 'Oslo'), ...]
        - use municipality=True to get municipality from location
        - use newspaper=(lat,long) tuple to give a hint about where a name probably belongs
        '''
        final_places = [] # populate this please

        if verbose:
            print("hint_location:", hint_location)
            print(poly_place_list)
            print()

        # make golyglot input into counter obj
        c_places = Counter(poly_place_list)
        # Lets make sure it's Titlecase (Risør, not risør) for SSR match
        for place in c_places.most_common():

            place = place[0].title()
            if place in ["Nord", "Sør", "Øst", "Vest", "Sørlandet",
            "Østlandet", "Vestlandet"]:
                continue

            # Try country first - Bolstad has forreign names in Norwegian for us:
            # allow case insensitivity here, Usa and USA is the same.. (prob).
            sql_country = """SELECT Lat, Lon, * FROM bolstads_land
                            WHERE Nynorsk = ? or Bokmål =? COLLATE NOCASE;"""
            self.cur.execute(sql_country, (place, place))
            hits = self.cur.fetchall()
            if len(hits) > 0:
                if municipality:
                    final_places.append((place, (hits[0][0], hits[0][1]), 'NA'))
                else:
                    final_places.append((place, (hits[0][0], hits[0][1])))
                if verbose:
                    print("ok, **", place, "** utLAND, n  treff: \t", len(hits))
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
                if municipality:
                    final_places.append((place, (hits[0][0], hits[0][1]), "NA"))
                else:
                    final_places.append((place, (hits[0][0], hits[0][1])))
                if verbose:
                    print("ok, **", place, "** \t utlandet, antall treff: \t", len(hits), "valgte:", (hits[0][0], hits[0][1]))
                continue

            # Plukk ut Fylkene, de står ikke i SSR..
            fylkene = {
            "Akershus": (60.000020, 11.36903),
            "Aust-Agder": (58.667030, 8.084475),
            "Austagder": (58.667030, 8.084475),
            "Vest-Agder": (58.368605, 6.901962),
            "Vestagder": (58.368605, 6.901962),
            "Vest Agder": (58.368605, 6.901962),
            "Agder": (58.163832, 8.002964),
            "Buskerud": (60.484602, 8.698376),
            "Finnmark": (70.483039, 26.013511),
            "Hedmark": (61.396731, 11.562737),
            "Hordaland": (60.273367, 5.722019),
            "Jan Mayen": (71.031818, -8.292035),
            "Møre og Romsdal": (62.976037, 8.018272),
            "Møre": (62.976037, 8.018272),
            "Nord-Trøndelag": (64.437079, 11.746295),
            "Nord Trøndelag": (64.437079, 11.746295),
            "Nordtrøndelag": (64.437079, 11.746295),
            "Trøndelag": (63.430515, 10.395053),
            "Sør-Trøndelag": (63.013682, 10.348714),
            "Sørtrøndelag": (63.013682, 10.348714),
            "Nordland": (67.097529, 14.573629),
            "Oppland": (61.542275, 9.716631),
            "Rogaland": (59.148954, 6.014343),
            "Sogn og Fjordane": (61.553944, 6.332588),
            "Telemark": (59.391398, 8.321121),
            "Troms": (69.649205, 18.955324),
            "Vestfold": (59.170786, 10.114436),
            "Østfold": (59.255829, 11.327901)}
            if place in fylkene.keys():
                if municipality:
                    final_places.append((place, fylkene[place], "NA"))
                else:
                    final_places.append((place, fylkene[place]))
                continue
            # og USAs stater er ikke med..
            us_stater = {'Alabama': (32.361538, -86.279118),
                         'Alaska': (58.301935, -134.41974),
                         'Arizona': (33.448457, -112.073844),
                         'Arkansas': (34.736009, -92.331122),
                         'California': (38.555605, -121.468926),
                         'Colorado': (39.7391667, -104.984167),
                         'Connecticut': (41.767, -72.677),
                         'Delaware': (39.161921, -75.526755),
                         'Florida': (30.4518, -84.27277),
                         'Georgia': (33.76, -84.39),
                         'Hawaii': (21.30895, -157.826182),
                         'Idaho': (43.613739, -116.237651),
                         'Illinois': (39.78325, -89.650373),
                         'Indiana': (39.790942, -86.147685),
                         'Iowa': (41.590939, -93.620866),
                         'Kansas': (39.04, -95.69),
                         'Kentucky': (38.197274, -84.86311),
                         'Louisiana': (30.45809, -91.140229),
                         'Maine': (44.323535, -69.765261),
                         'Maryland': (38.972945, -76.501157),
                         'Massachusetts': (42.2352, -71.0275),
                         'Michigan': (42.7335, -84.5467),
                         'Minnesota': (44.95, -93.094),
                         'Mississippi': (32.32, -90.207),
                         'Missouri': (38.572954, -92.189283),
                         'Montana': (46.595805, -112.027031),
                         'Nebraska': (40.809868, -96.675345),
                         'Nevada': (39.160949, -119.753877),
                         'New Hampshire': (43.220093, -71.549127),
                         'New Jersey': (40.221741, -74.756138),
                         'New Mexico': (35.667231, -105.964575),
                         'New York': (42.659829, -73.781339),
                         'North Carolina': (35.771, -78.638),
                         'North Dakota': (48.813343, -100.779004),
                         'Ohio': (39.962245, -83.000647),
                         'Oklahoma': (35.482309, -97.534994),
                         'Oregon': (44.931109, -123.029159),
                         'Pennsylvania': (40.269789, -76.875613),
                         'Rhode Island': (41.82355, -71.422132),
                         'South Carolina': (34.0, -81.035),
                         'South Dakota': (44.367966, -100.336378),
                         'Tennessee': (36.165, -86.784),
                         'Texas': (30.266667, -97.75),
                         'Utah': (40.7547, -111.892622),
                         'Vermont': (44.26639, -72.57194),
                         'Virginia': (37.54, -77.46),
                         'Washington': (47.042418, -122.893077),
                         'West Virginia': (38.349497, -81.633294),
                         'Wisconsin': (43.074722, -89.384444),
                         'Wyoming': (41.145548, -104.802042)}
            if place in us_stater.keys():
                if municipality:
                    final_places.append((place, us_stater[place], "NA"))
                else:
                    final_places.append((place, us_stater[place]))
                continue

            # And finally SSR
            sql_ssr = """SELECT s.lat, s.long, for_snavn, Namnetype, Prioritet,
                                k.Norsk as kommune, k.Kommunenummer
                     FROM SSR s, bolstads_kommunesenter k, bolstads_prioritet p
                     WHERE (s.for_snavn = ? OR s.enh_snavn = ?)
                     AND s.skr_snskrstat IN ('V', 'S', 'G', 'P')
                     AND s.enh_komm = k.Kommunenummer
                     AND s.enh_navntype = p.Nr
                     ORDER BY Prioritet ASC;"""
            # fetch the SSR resutls
            #print(sql_ssr.replace("?", "{}").format(place, place))
            self.cur.execute(sql_ssr, (place, place))
            hits = self.cur.fetchall()

            if len(hits) == 0:                 # not a place (according to SSR)
                if verbose:
                    print("Ingen treff i SSR på", place)
                continue   # some errors like "Sør" or "Aust-" are removed this way

            if hint_location == "unknown":
                # we have no way of knowing if Bø in Telemark or Bø i Nordland is more likely
                if verbose:
                    print("ok, *", place, "* har n treff i SSR: ", len(hits), "(tok den med høyest pri)")
                    if municipality:
                        print("\t-", place, "ligger i", hits[0][5], "kommune")
                # just grab the most highest Pirority from bolstads_prioritet
                if municipality:
                    final_places.append((place, (hits[0][0], hits[0][1]), (hits[0][5],hits[0][6]))) # here add mun number
                else:
                    final_places.append((place, (hits[0][0], hits[0][1])))
            else:
                # we have a hint to guide us
                # NB: this still does not work as well as hoped. Prioritet from
                # bolstad often tips wrong latlons into the top score (eg. Birkenes in Agder)
                # always ends up in Volda because Volda-Birkenes has a better pri...

                if len(hits) == 1: # one match, use this, return (name, (lat,long))
                    if verbose:
                        print("ok, **", place, "**  Bare et treff:", len(hits))
                    if municipality:
                        final_places.append((place, (hits[0][0], hits[0][1]), (hits[0][5], hits[0][6]))) # here add mun number
                    else:
                        final_places.append((place, (hits[0][0], hits[0][1])))
                else:
                    # we have multiple local place names.
                    # Experiments show that YR ranking works well.
                    # as an alternative, use distance from hint (hint_location) as tie-breaker
                    if verbose:
                        print("ok **", place, "** \t antall treff: \t", len(hits), "beste treff valgt")
                    # make a list
                    alternatives = []
                    for h in hits:
                        #print("rundet til nærmeste 10km", round(vincenty(hint_location, (h[0], h[1])).meters, -4))
                        alternatives.append(list(h)+[round(vincenty(hint_location, (h[0], h[1])).meters, 0), round(vincenty(hint_location, (h[0], h[1])).meters, -4)])
                    # sort by YR-priority first, dist from hint second
                    alternatives = sorted(alternatives, key=lambda x: (x[6], x[4]))
                    if verbose:
                        print()
                        for a in alternatives:
                            print(a)
                    # choose the top one
                    if municipality:
                        final_places.append((place, (alternatives[0][0], alternatives[0][1]), (hits[0][5], hits[0][6]))) # here add mun number
                    else:
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


# add collate nocase to countries
# create index bolstads_land_navn_index_nn
#   on bolstads_land (Nynorsk collate nocase);
#  create index bolstads_land_navn_index_bn
#   on bolstads_land (Bokmål collate nocase);

#create index geoname_name
#   on geoname (name);
# create index geoname_asciiname
#   on geoname (asciiname);

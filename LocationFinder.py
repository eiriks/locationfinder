#!/usr/bin/env python
# encoding: utf-8
"""
Created by Eirik Stavelin on 2015

"""

import sys
import re
# import pygeoj    # https://github.com/karimbahgat/PyGeoj
import pymysql              # for fetching data from newspaper db
import requests
import sqlite3 as lite      # for ssr db
# from collections import Counter
from subprocess import Popen, PIPE
from geopy.distance import vincenty

import argparse
import logging  # DEBUG, INFO, WARNING, ERROR, CRITICAL

from mysql_settings import settings

# select nrk2013b_tbl.id, CONCAT(nrk2013b_tbl.title, " ",
# nrk2013b_tbl.full_text)
# as text from nrk2013b_tbl left outer join article_location on
# (nrk2013b_tbl.id = article_location.id)
# where article_location.id is null
# order by nrk2013b_tbl.id desc;
# SELECT for_snavn, lat, long, printf("%.2f", long) FROM SSR WHERE enh_snavn
# = 'National' AND skr_snskrstat in ('V', 'S', 'G', 'P')
# GROUP BY printf("%.2f", long);


class LocationFinder:
    '''experimantal module to extract locations from news articles
    is based on Oslo-Bergen-Taggeren,
    Lists of important places  and sentralt stedsnavn register (SSR)'''

    def __init__(self):
        self.con = lite.connect('steder.db')
        self.cur = self.con.cursor()
        # get ppnames: people and place names
        self.ppnames = self.load_person_names_that_is_also_place_names()
        self.abroad_lat_lon = self.load_abroad_lat_lon()
        self.abroad = self.load_abroad()
        self.fylker = self.load_fyler()
        self.admin_steder = self.load_admin_steder()
        self.kommuner = self.load_kommuner()        # 428 stk
        self.byer = self.load_byer()                # bystatus
        self.tettsteder = self.load_tettsteder()    # 200 innbyggere+

    def is_poststed(self, s):
        self.cur.execute(
            "SELECT * FROM POST_NR WHERE poststed='%s'" % s.upper()
            )
        return False if len(self.cur.fetchall()) == 0 else True

    def is_in_ssr(self, s):
        """ Function that to ckeck if placename is in ssr
        requiress an open con  / cur
        # http://wiki.openstreetmap.org/wiki/Import/Catalogue/Central_place_name_register_import_(Norway)#GeoJSON
        """
        # ignore = ('U', 'A', 'F', 'K', 'I', 'H')
        valid = ('V', 'S', 'G', 'P')
        self.cur.execute("SELECT * FROM SSR WHERE (for_snavn = '%s' OR enh_snavn = '%s') \
        AND skr_snskrstat IN %s;" % (s, s, valid))
        if len(self.cur.fetchall()) == 0:
            return False
        else:
            return True

    def get_nr_ssr_rows(self, placename):
        """ Her ble det noe ball pga sqlite3s måte å deale med
        str interpolation på... """
        valid = ("'V'", "'S'", "'G'", "'P'")
        sql = """SELECT COUNT(*) FROM SSR WHERE
                (for_snavn = ? OR enh_snavn = ?) AND
                skr_snskrstat IN (%s)""" % (",".join(valid))
        # print(self.check_sql_string(sql, (placename, placename)))
        self.cur.execute(sql, (placename, placename))
        return self.cur.fetchone()[0]

    def connect(self):
        try:
            # Set up a database cursor:
            # rdbms_hostname = "localhost"
            rdbms_username = settings['user']
            rdbms_password = settings['password']
            connection = pymysql.connect(
                unix_socket="/Applications/MAMP/tmp/mysql/mysql.sock",
                user=rdbms_username,
                passwd=rdbms_password,
                db="nrk", charset='utf8')
            cur = connection.cursor()
            cur.execute("USE nrk;")
            logging.debug("koblet til MySQL")
            return connection, cur
        except:
            logging.error("kunne ikke logge på databasen")

    def disconnect(self, connection):
        if connection:
            connection.close()
            logging.info("koblet av mysql")

    def load_abroad(self):
        """ loads data from public gist (eiriks)
        data is from Eirik Bolstad http://www.erikbolstad.no/geo/
        & Wikipedia
        https://no.wikipedia.org/wiki/Liste_over_hovedsteder_etter_land
        returns four (4) lists of placenames"""
        url = 'https://gist.githubusercontent.com/eiriks/0eaf384b05b2d200982b/raw/18c82bbc1ebb52bf5c0689cc85148352569671af/verdensdeler_og_regioner.json'  # noqa
        r = requests.get(url)
        data = r.json()
        # Verdensdeler
        verdensdeler = list(set(v["Verdsdel"] for v in data))
        # Ynderregioner (bokmålkolonnen)
        regioner = list(set(v[u"ureg-Bokmål"] for v in data
                            if v[u"ureg-Bokmål"] != ''))
        # Land
        land = list(set(v[u"land-Bokmål"] for v in data))
        land_nno = list(set(v[u"land-Nynorsk"] for v in data))
        land = list(set(land + land_nno))
        # Hovedsteder
        url = 'https://gist.githubusercontent.com/eiriks/0eaf384b05b2d200982b/raw/d89d977a23763aa61270d5155ffc0d2c17109ebc/hovedsteder.json'  # noqa
        r = requests.get(url)
        hovedsteder = r.json()

        ugly_hack = []  # has some spare locations..
        for p in self.abroad_lat_lon:
            ugly_hack.append(p)
        the_known_world = list(set(verdensdeler + regioner + land + hovedsteder + ugly_hack))
        return the_known_world

    def load_abroad_lat_lon(self):
        url = '''https://gist.githubusercontent.com/eiriks/feee03a5a9a04a63b4a9/raw/31e034b1dd8ab97b03fa06c86d47e6a318c090a1/the_world.json'''  # noqa
        url = '''https://gist.githubusercontent.com/eiriks/feee03a5a9a04a63b4a9/raw/b8043c2a818cccdd05e134b73a31572fe125feaf/wolrd_and_some.json'''  # noqa
        return requests.get(url).json()

    def load_person_names_that_is_also_place_names(self):
        url = 'https://gist.githubusercontent.com/eiriks/8b028e05d9b53f8de628/raw/9cb3a529361e26528e808a08a724fff2a1f39aaf/person_names_also_norwegian_place_names.json'  # noqa
        return requests.get(url).json()

    def load_fyler(self):
        url = """https://gist.githubusercontent.com/eiriks/8b028e05d9b53f8de628/raw/24d26827ab9394c4382dc1102c03516a9b2a9df4/fylker.json"""  # noqa
        return requests.get(url).json()

    def load_kommuner(self):
        url = 'https://gist.githubusercontent.com/eiriks/8b028e05d9b53f8de628/raw/24d26827ab9394c4382dc1102c03516a9b2a9df4/kommuner.json'  # noqa
        return requests.get(url).json()

    def load_admin_steder(self):
        ''' Kommuneadministrasjonssteder '''
        url = 'https://gist.githubusercontent.com/eiriks/8b028e05d9b53f8de628/raw/474e8b2e0a0a7d87bbf7e5ac65f5c801d0391aad/kommune_administrasjonssted.json'  # noqa
        return requests.get(url).json()

    def load_byer(self):
        url = 'https://gist.githubusercontent.com/eiriks/8b028e05d9b53f8de628/raw/24d26827ab9394c4382dc1102c03516a9b2a9df4/steder_med_bystatus.json'  # noqa
        return requests.get(url).json()

    def load_tettsteder(self):
        url = 'https://gist.githubusercontent.com/eiriks/8b028e05d9b53f8de628/raw/24d26827ab9394c4382dc1102c03516a9b2a9df4/norske_tettsteder_200innbyggere_pluss.json'  # noqa
        return requests.get(url).json()

    def run_obt(self, text):  # get_exitcode_stdout_stderr
        """ I think this is stil suboptimal.
        I'm not sure how shell scprips safely should be run from python.."""
        cmd = "tag-bm_cmd.sh \"%s\"" % (text)                 # make cmd
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        return p.communicate()[0].decode('utf8')         # return OBT string

    def get_base(self, obt_format_text_chunc):
        ''' løsning fra
        http://stackoverflow.com/questions/3368969/find-string-between-two-substrings
        '''
        # 3. i listen [u'', u'"<en>"', u'\t"En" subst prop <*>', u'']
        s = obt_format_text_chunc.split("\n")[2]
        start = '"'     # hent fra denne
        end = '"'       # til denne
        # slice [fra start + len av start : index for slutten ]
        return s[s.find(start)+len(start):s.rfind(end)]

    def check_sql_string(self, sql, values):
        '''http://stackoverflow.com/questions/5266430/how-to-see-the-\
        real-sql-query-in-python-cursor-execute'''
        unique = "%PARAMETER%"
        sql = sql.replace("?", unique)
        for v in values:
            sql = sql.replace(unique, repr(v), 1)
        return sql

    def get_candidates(self, text):
        candidates = []

        t = self.run_obt(text)
        # print t
        for t in re.compile("<word>.+</word>").split(t):  # and split on word
            if t:                   # some stuff is just empty.. skip that..
                if "prop" in t:     # locations get the odd "prop" attr
                    hit = self.get_base(t)
                    candidates.append(hit.rstrip('\'\"-,.:;!?'))
        return candidates

    def get_ssr_lat_lon_options(self, loc):
        'return list legal of lat/lon for loc'
        sql = """SELECT for_snavn, lat, long FROM SSR WHERE
            enh_snavn = '%s' AND skr_snskrstat in ('V', 'S', 'G', 'P')
            """ % (loc)
        sql+'GROUP BY printf("%.2f", long);'
        self.cur.execute(sql)
        rows = self.cur.fetchall()
        alt = []
        for r in rows:
            alt.append((r[1], r[2]))
        # print loc, "(",len(alt),")"
        if len(alt) == 0:
            # try worldview list.
            try:
                l = (self.abroad_lat_lon[loc][0], self.abroad_lat_lon[loc][1])
                alt.append(l)
            except:
                pass

        if loc in ["Norge", "Noreg"]:  # Exept these that create many errors
            return []
        else:
            return alt

    def f(x):
        """ at 200km away, I only award 0.1 points. """
        return (0.1**(x/200.0))

    def get_shortest_dist(self, loc1, loc2):
        closest_dist = 100000  # too far
        if (len(loc1.items()[0][1]) == 0 and loc1.items()[0][0] != 'Norge'):
            print loc1
            print loc2
        # if len(loc1.items()[0][1]) == 0:
        #     print "\t", loc1
        #     print "\t", loc2

        for pair in loc1.items()[0][1]:
            for p2 in loc2.items()[0][1]:
                if (vincenty(pair, p2).kilometers < closest_dist):
                    closest_dist = vincenty(pair, p2).kilometers
        # print "%s - %s is \t%.0f \tkm" % (
        #     loc1.items()[0][0], loc2.items()[0][0], closest_dist)
        return closest_dist

    def get_locations(self, candidates):
        accepted = []
        temp_rejected = []
        # if candidates is in
        # abroad, fylker, kommuner, admin_steder, byer
        # i want it.
        for c in candidates:
            if (c in self.abroad or
                    c in self.fylker or
                    c in self.kommuner or
                    c in self.admin_steder or
                    c in self.byer):
                # add it
                accepted.append(c)
            elif (c in self.tettsteder and c not in self.ppnames):
                # if a place, not not a common name, include it.
                accepted.append(c)
            else:
                # keep these for a little while
                temp_rejected.append(c)

        # here are my safe points:
        acc_points = {}
        for a in set(accepted):
            acc_points[a] = {a: self.get_ssr_lat_lon_options(a)}

        # check the discarded for closeness to kept locs
        if len(accepted) > 0:  # only accept more if we have safe points
            for c in set(temp_rejected):
                ssr_rows = self.get_nr_ssr_rows(c)
                if ssr_rows > 0:
                    # aksepter denne, bare hvis det finnes et sted
                    # som heter dette, som ligger i rimelig nærhet til et
                    # av de kjente aksepterte stedene.
                    # print "sjekk om dette kan reddes: ", c
                    loc2 = {c: self.get_ssr_lat_lon_options(c)}
                    closest_acc_point = {'place': None, 'dist': 100000}
                    for k in acc_points:
                        shotest_dist = self.get_shortest_dist(acc_points[k], loc2)
                        if shotest_dist < closest_acc_point['dist']:
                            closest_acc_point['dist'] = shotest_dist
                            closest_acc_point['place'] = acc_points[k].items()[0][0]
                    # print "nærmeste: ", closest_acc_point
                    # if this is closer than X
                    # append to accepted
                    if closest_acc_point['dist'] < 15:
                        # http://stavelin.com/uib/LocationFinder_dist_v_errors.png
                        # 10-20km from knows accepted locations looks fine
                        # print "add this", c
                        accepted.append(c)
        return set(accepted)

    # def get_locations_by_frequency(self, text):
    #     """ return counter object
    #     https://docs.python.org/2/library/collections.html#collections.Counter
    #     """
    #     cnt = Counter()
    #     t = self.run_obt(text)   # get obt_format_text_chuncs
    #     candidates = []
    #     ssr_hit_counter = Counter()
    #     hits_has_postcode = {}
    #     land_fylke_kommune = {}
    #
    #     for t in re.compile("<word>.+</word>").split(t):  # and split on word
    #         if t:                   # some stuff is just empty.. skip that..
    #             if "prop" in t:     # locations get the odd "prop" attr
    #                 hit = self.get_base(t)
    #                 candidates.append(hit)
    #
    #                 if hit in self.fylker or hit in self.kommuner:
    #                     cnt[hit] += 1
    #                     ssr_hit_counter[hit] = 1    # manuely assigned
    #                     hits_has_postcode[hit] = True
    #                     land_fylke_kommune[hit] = True
    #                 # Deal with places abroad?
    #                 if hit in self.abroad:
    #                     cnt[hit] += 1
    #                     ssr_hit_counter[hit] = 1  # NB! manually assigned
    #                     hits_has_postcode[hit] = True  # Also manually assigned
    #                     land_fylke_kommune[hit] = True
    #                 # remove these abiguest names that are both people & places
    #                 elif hit not in self.ppnames:
    #                     ssr_rows = self.get_nr_ssr_rows(hit)
    #                     if ssr_rows > 0:  # but is the ssr db
    #                         cnt[hit] += 1
    #                         ssr_hit_counter[hit] = ssr_rows
    #                         hits_has_postcode[hit] = self.is_poststed(hit)
    #                         land_fylke_kommune[hit] = False
    #
    #     logging.debug("candidates: %s", ", ".join(set(candidates)))
    #     # print ", ".join(candidates)
    #     return [cnt, ssr_hit_counter, hits_has_postcode]

    # def get_results_test(self, id):
    #     mysql_connection, mysql_cur = self.connect()
    #     mysql_query = '''SELECT CONCAT(title, " ", full_text) as text, url
    # FROM
    #                     nrk2013b_ism_tbl WHERE id=%s''' % (id)
    #     mysql_cur.execute(mysql_query)
    #     row = mysql_cur.fetchone()
    #     [cnt, ssr_hit_counter, hits_has_postcode] = (
    #         self.get_locations_by_frequency(row[0]))
    #     # print "Teller: \t", cnt
    #     # print "SSR hits: \t", ssr_hit_counter
    #     # print "Postkode?: \t", hits_has_postcode
    #     ranked = self.rank(cnt, ssr_hit_counter, hits_has_postcode)
    #     # print "Ranked: \t", ranked
    #     return ranked

    # def dict_mul(self, d1, d2):
    #     """http://stackoverflow.com/questions/15334783/\multiplying-values-from-\
    #     two-different-dictionaries-together-in-python/15334895#15334895 """
    #     d3 = dict()
    #     for k in d1:
    #         d3[k] = d1[k] * d2[k]
    #     return d3

    # def rank(self, cnt, ssr_hit_counter, hits_has_postcode):
    #     """expects freq counter, ssr_hit_counter, and hits_has_postcode
    #     counters and returnes a ranked weigthed counter based on
    #     the inputs.
    #     """
    #     # boost names that has postcode
    #     for hit in cnt:
    #         if hits_has_postcode[hit]:
    #             cnt[hit] = cnt[hit]*2
    #     # print "Boost post \t", cnt
    #     # normalize counter
    #     total = sum(cnt.values(), 0.0)
    #     for key in cnt:
    #         cnt[key] /= total
    #     # print "normalisert: ", cnt
    #
    #     # weigh hits i SSR
    #     try:
    #         max_hits = float(ssr_hit_counter[max(ssr_hit_counter, key=ssr_hit_counter.get)])
    #     except:
    #         max_hits = 0
    #
    #     for key in cnt:
    #         # ssr_hit_counter[key] = 1-(ssr_hit_counter[key] / total_ssr)
    #         ssr_hit_counter[key] = max_hits+1-(ssr_hit_counter[key])
    #
    #     total_ssr = sum(ssr_hit_counter.values(), 0.0)
    #     # print total_ssr, type(total_ssr)
    #     for key in cnt:
    #         ssr_hit_counter[key] = ssr_hit_counter[key]/total_ssr
    #
    #     # print "normalisert ssr: ", ssr_hit_counter
    #     # gange den ene med den andre
    #     ranked = self.dict_mul(cnt, ssr_hit_counter)
    #     # print "ranked: ", ranked
    #     d = sorted(ranked.items(), key=lambda x: x[1])
    #     return d

    def loop_text2(self):
        """ the cur object excepted is a mysqlite cur object for the
        steder.db"""
        mysql_connection, mysql_cur = self.connect()
        mysql_query = '''SELECT CONCAT(title, " ", full_text) as text, url FROM
                        nrk2013b_ism_tbl order by rand() LIMIT 5'''
        # limit 10000 OFFSET 119999
        mysql_cur.execute(mysql_query)
        mysql_rows = mysql_cur.fetchall()
        # current_row = 1
        for row in mysql_rows:
            print "\n"
            cand = self.get_candidates(row[0])
            # print "candidates: ", set(cand)
            print self.get_locations(cand)
        print "ferdig"

    def get_text_from_url(self, id):
        mysql_connection, mysql_cur = self.connect()
        mysql_query = '''SELECT CONCAT(title, " ", full_text) as text FROM
                        nrk2013b_ism_tbl WHERE id = %s''' % (id)
        mysql_cur.execute(mysql_query)
        mysql_row = mysql_cur.fetchone()
        return mysql_row[0]

    # def loop_text(self):
    #     """ the cur object excepted is a mysqlite cur object for the
    #     steder.db"""
    #     mysql_connection, mysql_cur = self.connect()
    #     mysql_query = '''SELECT CONCAT(title, " ", full_text) as text, url
    #             FROM nrk2013b_ism_tbl order by rand() LIMIT 5'''
    #     # limit 10000 OFFSET 119999
    #     mysql_cur.execute(mysql_query)
    #     mysql_rows = mysql_cur.fetchall()
    #     # current_row = 1
    #
    #     for row in mysql_rows:
    #         logging.debug("*"*20)
    #         logging.debug(row[1])    # url
    #         cnt, ssr_hit_counter, hits_has_postcode = (
    #             self.get_locations_by_frequency(row[0])
    #         )
    #         print "freq: ", cnt
    #         print "ssr hits: ", ssr_hit_counter
    #         print "has postcode: ", hits_has_postcode
    #         ranked2 = self.rank(cnt, ssr_hit_counter, hits_has_postcode)
    #         print "ranked2: ", ranked2
    #         print "_"*20
    #
    #         for hit in cnt:
    #             if hits_has_postcode[hit]:
    #                 cnt[hit] = cnt[hit]*2
    #         print "boosta postnummer", cnt
    #         # normaliser counter
    #         total = sum(cnt.values(), 0.0)
    #         for key in cnt:
    #             cnt[key] /= total
    #         print "normalisert: ", cnt
    #         # vekte for hits i SSR
    #         total_ssr = sum(ssr_hit_counter.values(), 0.0)
    #         for key in cnt:
    #             ssr_hit_counter[key] = 1-(ssr_hit_counter[key] / total_ssr)
    #         print "normalisert ssr", ssr_hit_counter
    #         # gange den ene med den andre
    #         ranked = self.dict_mul(cnt, ssr_hit_counter)
    #         print "ranked: ", ranked
    #
    #         # here I should intoduce ways to balance &
    #         # cut the cnt above some threshold
    #
    #         # low SSR               > higher score
    #         # high SSR              > lower score
    #         # hight freq in text    > ligher score
    #         # has postcode          > score above threshold     is_poststed()
    #
    #         logging.debug(row[0][:100].rstrip('\r\n')+"...")
    #
    #         # make som decitions about what to do with results,
    #         # what constitutes a "real" right place?


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d', '--debug',
        help="Print lots of debugging statements",
        action="store_const", dest="loglevel", const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        '-v', '--verbose',
        help="Be verbose",
        action="store_const", dest="loglevel", const=logging.INFO,
    )
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stderr, level=args.loglevel, format='%(asctime)s \
    L:%(lineno)d: %(message)s', datefmt='%d/%m/%y@%H:%M:%S')
    # So if --debug is set, the logging level is set to DEBUG. If --verbose,
    # logging is set to INFO. If neither, the lack of --debug sets the logging
    # level to the default of WARNING.
    # logging.basicConfig(stream=sys.stderr,level=logging.DEBUG)
    logging.info("we are running")

    a = LocationFinder()
    a.loop_text2()

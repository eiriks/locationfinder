#!/usr/bin/env python
# encoding: utf-8
"""
Created by Eirik Stavelin on 2015

"""
__version__ = '0.1'
import sys
import re
# import pygeoj    # https://github.com/karimbahgat/PyGeoj
import pymysql              # for fetching data from newspaper db
import requests
# import simplekml
import sqlite3 as lite      # for ssr db
# from collections import Counter
from subprocess import Popen, PIPE
from geopy.distance import vincenty

import argparse
import logging  # DEBUG, INFO, WARNING, ERROR, CRITICAL

from mysql_settings import settings


class LocationFinder:
    '''experimantal module to extract locations from news articles
    is based on Oslo-Bergen-Taggeren,
    Lists of important places  and sentralt stedsnavn register (SSR)'''

    def __init__(self, dist_threshold=15):
        self.dist_threshold = float(dist_threshold)
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
        # valid = ('V', 'S', 'G', 'P')
        sql = """SELECT * FROM SSR WHERE (for_snavn = ? OR enh_snavn = ?)
        AND skr_snskrstat IN ('V', 'S', 'G', 'P');"""  # % (s, s)
        # print s
        # print sql
        self.cur.execute(sql, (s, s))
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
                db="nrk", charset='utf8',
                autocommit=True)
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
        the_known_world = list(set(verdensdeler + regioner + land + hovedsteder + ugly_hack))  # noqa
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
        if len(alt) == 0:  # try worldview list.
            try:
                l = (self.abroad_lat_lon[loc][0], self.abroad_lat_lon[loc][1])
                alt.append(l)
            except:
                pass

        if loc in ["Norge", "Noreg"]:  # Exept these that create many errors
            return []
        else:
            return alt

    def get_semirandom_lat_lon(self, loc):
        'return lat/lon for loc, randomly from places named loc in ssr'
        sql = """SELECT for_snavn, lat, long FROM SSR WHERE
            enh_snavn = ? OR for_snavn = ? AND skr_snskrstat in
            ('V', 'S', 'G', 'P') ORDER BY RANDOM() LIMIT 1;
            """  # % (loc)
        self.cur.execute(sql, (loc, loc))
        rows = self.cur.fetchall()
        return rows[0]

    def f(x):
        """ at 200km away, I only award 0.1 points. """
        return (0.1**(x/200.0))

    def get_shortest_dist(self, loc1, loc2):
        closest_dist = 100000  # too far
        if (len(loc1.items()[0][1]) == 0 and loc1.items()[0][0] != 'Norge'):
            print loc1
            print loc2

        for pair in loc1.items()[0][1]:
            for p2 in loc2.items()[0][1]:
                if (vincenty(pair, p2).kilometers < closest_dist):
                    closest_dist = vincenty(pair, p2).kilometers
        # print "%s - %s is \t%.0f \tkm" % (
        #     loc1.items()[0][0], loc2.items()[0][0], closest_dist)
        return closest_dist

    def get_shortest_dist2(self, loc1, loc2):
        '''loc1 are "safe", {u'Trondheim': [(63.4305658, 10.3951929)]
        returns closest (lat,lon) for loc2
        I assumes the variety of lat/lons for loc1 to be few,
        is more than on at all'''
        closest_dist = 100000  # too far
        loc2_lat_lon = ()
        # print "loc1", loc1
        # print "loc2", loc2
        if (len(loc1.items()[0][1]) == 0 and loc1.items()[0][0] != 'Norge'):
            print loc1
            print loc2

        for pair in loc1.items()[0][1]:
            for p2 in loc2.items()[0][1]:
                if (vincenty(pair, p2).kilometers < closest_dist):
                    closest_dist = vincenty(pair, p2).kilometers
                    loc2_lat_lon = p2
        # print "%s - %s is \t%.0f \tkm" % (
        #     loc1.items()[0][0], loc2.items()[0][0], closest_dist)
        return [closest_dist, loc2_lat_lon]

    def loop_text(self):
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
                        shotest_dist = self.get_shortest_dist(acc_points[k], loc2)  # noqa
                        if shotest_dist < closest_acc_point['dist']:
                            closest_acc_point['dist'] = shotest_dist
                            closest_acc_point['place'] = acc_points[k].items()[0][0]  # noqa
                    # print "nærmeste: ", closest_acc_point
                    # if this is closer than X
                    # append to accepted
                    if closest_acc_point['dist'] < self.dist_threshold:
                        # http://stavelin.com/uib/LocationFinder_dist_v_errors.png
                        # 10-20km from knows accepted locations looks fine
                        # print "add this", c
                        accepted.append(c)
        return set(accepted)

    def get_named_locations(self, candidates):
        results = {}
        accepted = []
        temp_rejected = []
        for c in candidates:
            if c and self.is_in_ssr(c):
                if (c in self.abroad_lat_lon.keys()):
                    accepted.append(c)
                    results[c] = (float(self.abroad_lat_lon[c][0]),
                                  float(self.abroad_lat_lon[c][1]))
                elif (c in self.abroad or
                        c in self.fylker or
                        c in self.kommuner or
                        c in self.admin_steder or
                        c in self.byer):
                    accepted.append(c)
                    results[c] = (float(self.get_semirandom_lat_lon(c)[1]),
                                  float(self.get_semirandom_lat_lon(c)[2]))
                elif (c in self.tettsteder and c not in self.ppnames):
                    accepted.append(c)
                    results[c] = (float(self.get_semirandom_lat_lon(c)[1]),
                                  float(self.get_semirandom_lat_lon(c)[2]))
                else:
                    temp_rejected.append(c)
        if len(accepted) > 0:  # only accept more if we have safe points
            for c in set(temp_rejected):
                if self.get_nr_ssr_rows(c) > 0:
                    loc2 = {c: self.get_ssr_lat_lon_options(c)}
                    closest_acc_point = {'place': None, 'dist': 100000}
                    for k in results:
                        shotest_dist = self.get_shortest_dist2({k: [results[k]]}, loc2)  # noqa
                        # print shotest_dist
                        if shotest_dist[0] < closest_acc_point['dist']:
                            closest_acc_point['dist'] = shotest_dist
                            closest_acc_point['place'] = shotest_dist[1]  # noqa

                    if closest_acc_point['dist'] < self.dist_threshold:
                        # http://stavelin.com/uib/LocationFinder_dist_v_errors.png
                        # 10-20km from knows accepted locations looks fine
                        accepted.append(c)
                        results[c] = shotest_dist[1]
        # return set(accepted)
        return results

    def analyse_nrk2013(self):
        mysql_connection, mysql_cur = self.connect()
        q = """SELECT nrk2013b_tbl.id,
        CONCAT(nrk2013b_tbl.title, " ", nrk2013b_tbl.full_text)
        as text, nrk2013b_tbl.url from nrk2013b_tbl left outer join
         article_location on (nrk2013b_tbl.id = article_location.id)
        WHERE article_location.id is null
        ORDER BY RAND(); """  # nrk2013b_tbl.id desc;"""
        # q = """ SELECT nrk2013b_tbl.id,
        # CONCAT(nrk2013b_tbl.title, " ", nrk2013b_tbl.full_text)
        # as text, nrk2013b_tbl.url from nrk2013b_tbl;"""
        logging.debug("running slow query")
        mysql_cur.execute(q)
        logging.debug("affected rows = {}".format(mysql_cur.rowcount))
        rows = mysql_cur.fetchall()
        logging.debug("finnished running slow query")
        # kml = simplekml.Kml()
        cnt = 0
        for r in rows:
            cnt += 1
            if (cnt % 50) == 0:
                logging.debug(cnt)
            # print r
            cand = self.get_candidates(r[1])
            results = self.get_named_locations(cand)
            for place in results:
                # print "place", place, results[place], r[0], r[2]
                # pnt = kml.newpoint(
                #     name=place,
                #     coords=[(results[place][1], results[place][0])],
                #     description=place)
                # pnt.snippet.content = unicode(r[0])+r[2]
                # self.get_named_locations(place)
                # do some ssr magic (random?)

                sql = """ INSERT INTO article_location (id, url, location)
                VALUES (%s, %s, %s); """
                mysql_cur.execute(sql, (r[0], r[2], place))
                # print("affected rows = {}".format(mysql_cur.rowcount))
                # kml.save("steder.kml")


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
    # a.loop_text()
    a.analyse_nrk2013()

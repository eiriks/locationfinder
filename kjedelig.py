#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from locationfinder import LocationFinder
lf = LocationFinder()

import sqlite3 as lite
con = lite.connect("norges_kjedeligste.db")
cur = con.cursor()
from time import time, strftime, gmtime

from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client.hand_curated_articles
#mongo_articles = db.nrk2013_no_human_coding.find({ 'man_inspected': {"$exists": "false"} }).limit(100)
mongo_articles = db.nrk2013_no_human_coding.find({ }, no_cursor_timeout=True)#.limit(5)
tot = db.nrk2013_no_human_coding.find({}).count()

# #51992 Flatanger?
# sjekk = db.nrk2013_no_human_coding.find({"mysql_id":51992 })
# print(sjekk[0])
# rich_places = lf.disambiguate_places(lf.from_text_to_places(sjekk[0]['text']))
# print(rich_places)

def drop_table():
    #del table
    cur.execute("DROP TABLE IF EXISTS kjedelig;")
    con.commit()
    print("sletta tabell og sett inn på nytt.")

def create_table():
    sql = """CREATE TABLE `kjedelig` (
    	`id`	INTEGER,
    	`pubdate`	TEXT,
    	`url`	TEXT,
    	`sted`	TEXT,
    	`kommune`	TEXT,
    	`kommunenr`	TEXT,
    	`lat`	NUMERIC,
    	`lon`	NUMERIC
    )"""
    cur.execute(sql)
    con.commit()
    print("laget tabell")

def mongo2sqlite():
    start = time()
    ticker = 0
    counter = 0
    for art in mongo_articles:
        # if the text is in Sami, we get very odd redults..
        # skip sami...
        rich_places = lf.disambiguate_places(lf.from_text_to_places(art['text']))
        for pl in rich_places:
            # print(pl)
            # import sys
            # sys.exit(0) # ('Moss', (59.434017, 10.657697), ('Moss', 104))
            row = [art['mysql_id'], art['publication_date'].isoformat(), art['url'], pl[0], pl[2][0], pl[2][1], pl[1][0], pl[1][1]]
            cur.execute('insert into kjedelig values (?,?,?,?,?,?,?,?)', row)
        ticker+=1
        if ticker == 5000:
            counter += ticker
            ticker =0
            print("{0} av {1} ferdig, tok {2}. \t kl {3}".format(counter, tot, round(time()-start, 2), strftime("%d-%m-%Y %H:%M:%S", gmtime())))
    con.commit()
    cur.close()
    print("ferdig")
    print("antall rader:", counter)

drop_table()
create_table()
mongo2sqlite()

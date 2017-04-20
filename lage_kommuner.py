
import requests
import pandas as pd
from bs4 import BeautifulSoup
#from locationfinder import LocationFinder


from svgpathtools import svg2paths
paths, attributes = svg2paths('Norway_municipalities_2012_blank.svg')


for k in range(len(attributes)):
    print(attributes[k]['d'])
#
# print(paths)

# bilde = open('Norway_municipalities_2012_blank.svg')
#
# for line in bilde:
#     print(line)
#     print()

# #url = "http://www.erikbolstad.no/geo/noreg/kommunar/txt/"
# url = "http://www.erikbolstad.no/geo/skandinavia/norske-kommunesenter/txt/"
# r = requests.get(url)
#
# df = pd.read_html(r.text)[0]
#
# kommuner = {}
# for line in df.iterrows():
#     #print(len(line), type(line)) #print(line[1][0])
#     #print()
#     kommuner[line[1][0]] = {
#         'navn': line[1][3],
#         'geoname_id': line[1][2],
#         'Fylkenummer': line[1][4],
#         'Folketal': line[1][6],
#         'lat': line[1][12],
#         'long': line[1][13]
#     }
# # print(kommuner)
# sort_kommuner = sorted(kommuner.items(), key=lambda value: -value[1]["lat"])
# #print(sort_kommuner)
#
# for k in sort_kommuner:
#     print(k)

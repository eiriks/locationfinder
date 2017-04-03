
import requests
import pandas as pd
from bs4 import BeautifulSoup
from LocationFinder import *


url = "http://www.erikbolstad.no/geo/noreg/kommunar/txt/"
r = requests.get(url)

df = pd.read_html(r.text)[0]

kommuner = {}
for line in df.iterrows():
    #print(line, len(line), type(line))
    kommuner[line[1][0]] = {
        'navn': line[1][2],
        'geoname_id': line[1][1]
    }


print(kommuner)

import requests
import time
import json
import re
import pandas
import numpy as np
from bs4 import BeautifulSoup

class UFOData:
    
    base_page = "http://www.nuforc.org/webreports/"
    main_page = "ndxpost.html"
    index_pages = []
    data = []

    def __init__(self, datafile=None):
        if datafile is not None:
            self.load_data(datafile)

    def load_index_pages(self, datafile='index_pages.json'):
        with open(datafile, 'r') as file:
            self.index_pages = json.load(file)

    def download_index_pages(self):
        def ufopage(url):
            return url.startswith('ndxp') and url.endswith('.html')

        soup = BeautifulSoup(requests.get(self.base_page + self.main_page).text,"html.parser")
        self.index_pages = [(link.get_text(), link.attrs['href']) for link in soup.findAll('a') if ufopage(link.attrs['href'])]
        print('There are ' + str(len(self.index_pages)) + ' pages found.')

    def save_index_pages(self, datafile='index_pages.json'):
        with open(datafile, 'w') as outfile:
            json.dump(self.index_pages, outfile)

    def load_data(self, datafile='data.json'):
        with open(datafile, 'r') as file:
            self.data = json.load(file)

    def download_data(self):
        names = ["Date", "City", "State", "Shape", "Duration", "Summary", "Posted", "Description"]
        start = time.time()
        self.data = []
        for i, (date, url) in enumerate(self.index_pages):
            print('Downloading page: ' + str(i + 1) + '/' + str(len(self.index_pages)))
            soup = BeautifulSoup(requests.get(self.base_page + url).text,"html.parser")
            page_data = []
            for item in soup.find('tbody').findAll('tr'):
                row = dict(zip(names, [d.get_text() for d in item.findAll('td')]))
                row['link'] = item.find('a').attrs['href']
                page_data.append(row)
            self.data.extend(page_data)
        print('Downloading data took ' + str(time.time() - start) + 's')

    def save_data(self, filename='data.json'):
        with open(filename, 'w') as outfile:
            json.dump(self.data, outfile)
    
    def download_description_page(self, relative_link):
        soup = BeautifulSoup(requests.get(self.base_page + relative_link).text,"html.parser")
        data, decription = tuple(item.text for item in soup.find('tbody').findAll('td'))

        occurred_mark = 'Occurred'
        entered_as_mark = 'Entered as'
        reported_mark = 'Reported'
        posted_mark = 'Posted'
        location_mark = 'Location'
        shape_mark = 'Shape'
        duration_mark = 'Duration'

        return {
            'occurred': data[data.find(occurred_mark) + len(occurred_mark):data.find(entered_as_mark) - 1].lstrip(" :").rstrip(' )'),
            'entered': data[data.find(entered_as_mark) + len(entered_as_mark):data.find(reported_mark)].lstrip(" :").rstrip(' )'),
            'reported': data[data.find(reported_mark) + len(reported_mark):data.find(posted_mark)].lstrip(" :").rstrip(' )'),
            'posted': data[data.find(posted_mark) + len(posted_mark):data.find(location_mark)].lstrip(" :").rstrip(' )'),
            'location': data[data.find(location_mark) + len(location_mark):data.find(shape_mark)].lstrip(" :").rstrip(' )'),
            'shape': data[data.find(shape_mark) + len(shape_mark):data.find(duration_mark)].lstrip(" :").rstrip(' )'),
            'duration': data[data.find(duration_mark) + len(duration_mark):].lstrip(" :").rstrip(' )'),
            'description': decription
        }


class LocationFinder:
    
    states = { "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", 
       "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", 
       "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", 
       "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", 
       "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", 
       "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", 
       "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", 
       "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
       "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
       "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", 
       "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", 
       "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", 
       "Wisconsin": "WI", "Wyoming": "WY" }
    
    __lookup_cache = {}
    __offline_lookup = None

    http_sleep = 0.7
    __last_http_request = 0

    def __init__(self, cachefile=None, offlineFile=None):
        if cachefile is not None:
            with open(cachefile, 'r') as file:
                self.__lookup_cache = json.load(file)

        if offlineFile is not None:
            self.__offline_lookup = pandas.read_csv(offlineFile, sep=",", encoding="UTF8")

    def save_cache(self, filename='location_cache.json'):
        with open(filename, 'w') as outfile:
            json.dump(self.__lookup_cache, outfile)

    @property
    def missing(self):
        return {'confidence': -1}
    
    def download_geodata(self, query):
        url = 'http://nominatim.openstreetmap.org/search/'
        # let exception raised to the caller...
        response = requests.get(url + query, params={'addressdetails': 1, 'format': 'json', 'limit': 10}).json()
        return [(d['address'], d['lon'], d['lat']) for d in response if d['type'].lower() in ('city', 'administrative')]

    def get_geodata(self, city):
        if city not in self.__lookup_cache:

            now = time.time()
            if self.__last_http_request + self.http_sleep > now:  # we have to wait...
                time.sleep(self.__last_http_request + self.http_sleep - now)
            self.__last_http_request = now

            self.__lookup_cache[city] = self.download_geodata(city)
        return self.__lookup_cache[city]
    
    def __match_usa_state(self, result, state_code):
        for (address, lon, lat) in result:
            if address['country_code'].lower() == 'us':
                if address['state'] in self.states and self.states[address['state']] == state_code.upper():
                    return lon, lat
    
    def __match_country_code(self, result, state_code):
        code = state_code.lower()
        for (address, lon, lat) in result:
            if address['country_code'].lower() == code or ('state' in address and address['state'].lower() == code):
                return lon, lat
    
    def __match_usa(self, result):
        for (address, lon, lat) in result:
            if address['country_code'].lower() == 'us':
                return (lon, lat)
    
    def find(self, city, state_code):
        result = self.__offline_lookup[np.logical_and(self.__offline_lookup.city == city, self.__offline_lookup.state_id == state_code)]
        if len(result) == 1:  #it is never Null!
            return {'longitude': float(result.lng), 'latitude': float(result.lat), 'confidence': 3}

        result = self.get_geodata(city)
        # check for state in the usa
        candidate = self.__match_usa_state(result, state_code)
        if candidate is not None:
            return {'longitude': candidate[0], 'latitude': candidate[1], 'confidence': 3}
        # check against state somewhere
        candidate = self.__match_country_code(result, state_code)
        if candidate is not None:
            return {'longitude': candidate[0], 'latitude': candidate[1], 'confidence': 2}
        # check against city in usa
        candidate = self.__match_usa(result)
        if candidate is not None:
            return {'longitude': candidate[0], 'latitude': candidate[1], 'confidence': 1}
        if len(result) > 0:
            return {'longitude': result[0][1], 'latitude': result[0][2], 'confidence': 0}
        else:
            return self.missing

    def __chk_word(self, word):
        if word is None:
            return False
        return re.match("^[a-zA-Z0-9-.,' ]*$", word) is not None and len(word.rstrip()) > 1
    
    def __remove_brackets(self, word):
        bracket = word.find('(')
        if bracket != -1:
            return word[:bracket].rstrip()
    
    def __remove_div(self, word):
        bracket = word.find('/')
        if bracket != -1:
            return word[:bracket].rstrip(), word[bracket + 1:].lstrip()

    def find_ugly(self, city, state_code):
        if self.__chk_word(city):
            return city, self.find(city, state_code)
        
        city_slice = self.__remove_brackets(city)
        if self.__chk_word(city_slice):
            return city_slice, self.find(city_slice, state_code)

        if city_slice is not None:
            city_slice = self.__remove_div(city_slice)
        else:
            city_slice = self.__remove_div(city)

        if city_slice is not None:
            result_1 = None
            if self.__chk_word(city_slice[0]):
                result_1 = self.find(city_slice[0], state_code)
            if self.__chk_word(city_slice[1]):
                result_2 = self.find(city_slice[1], state_code)
                return (city_slice[0], result_1) if result_1['confidence'] > result_2['confidence'] else (city_slice[1], result_2)
            if result_1 is not None:
                return city_slice[0], result_1
        raise ValueError('Can not find city: ' + city)

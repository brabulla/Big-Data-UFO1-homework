import requests
import time
import json
import re
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

        soup = BeautifulSoup(requests.get(
            self.base_page + self.main_page).text, "html.parser")
        self.index_pages = [(link.get_text(), link.attrs['href'])
                            for link in soup.findAll('a') if ufopage(link.attrs['href'])]
        print('There are ' + str(len(self.index_pages)) + ' pages found.')

    def save_index_pages(self, datafile='index_pages.json'):
        with open(datafile, 'w') as outfile:
            json.dump(self.index_pages, outfile)

    def load_data(self, datafile='data.json'):
        with open(datafile, 'r') as file:
            self.data = json.load(file)

    def download_data(self):
        names = ["Date", "City", "State", "Shape",
                 "Duration", "Summary", "Posted", "Description"]
        start = time.time()
        self.data = []
        for i, (date, url) in enumerate(self.index_pages):
            print('Downloading page: ' + str(i + 1) +
                  '/' + str(len(self.index_pages)))
            soup = BeautifulSoup(requests.get(
                self.base_page + url).text, "html.parser")
            page_data = []
            for item in soup.find('tbody').findAll('tr'):
                row = dict(zip(names, [d.get_text()
                                       for d in item.findAll('td')]))
                row['link'] = item.find('a').attrs['href']
                page_data.append(row)
            self.data.extend(page_data)
        print('Downloading data took ' + str(time.time() - start) + 's')

    def save_data(self, filename='data.json'):
        with open(filename, 'w') as outfile:
            json.dump(self.data, outfile)

    def download_description_page(self, relative_link):
        soup = BeautifulSoup(requests.get(
            self.base_page + relative_link).text, "html.parser")
        data, decription = tuple(
            item.text for item in soup.find('tbody').findAll('td'))

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

    states = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
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
              "Wisconsin": "WI", "Wyoming": "WY"}

    __lookup_cache = {}

    def __init__(self, cachefile=None):
        if cachefile is not None:
            with open(cachefile, 'r') as file:
                self.__lookup_cache = json.load(file)

    def save_cache(self, filename='location_cache.json'):
        with open(filename, 'w') as outfile:
            json.dump(self.__lookup_cache, outfile)
        print("Location cache size:" + str(len(self.__lookup_cache)))

    @property
    def missing(self):
        return {'longitude': None, 'latitude': None, 'confidence': -1}

    def download_geodata(self, query):
        url = 'http://nominatim.openstreetmap.org/search/'
        try:
            response = requests.get(
                url + query, params={'addressdetails': 1, 'format': 'json', 'limit': 10}).json()
        except json.JSONDecodeError as e:
            print(e)
        return [(d['address'], d['lon'], d['lat']) for d in response if d['type'].lower() in ('city', 'administrative')]

    def get_geodata(self, city):
        if city not in self.__lookup_cache:
            self.__lookup_cache[city] = self.download_geodata(city)
        return self.__lookup_cache[city]

    def get_geodata_http_used(self, city):
        http_used = False
        if city not in self.__lookup_cache:
            http_used = True
            self.__lookup_cache[city] = self.download_geodata(city)
        return self.__lookup_cache[city], http_used

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

    def find(self, city, state_code, http_used=False):
        result = None
        is_http_used = False
        if http_used:
            result, is_http_used = self.get_geodata_http_used(city)
        else:
            result = self.get_geodata(city)

        # check for state in the usa
        candidate = self.__match_usa_state(result, state_code)
        if candidate is not None:
            ret = {'longitude': candidate[0],
                   'latitude': candidate[1], 'confidence': 3}
            return (ret, is_http_used)

        # check against state somewhere
        candidate = self.__match_country_code(result, state_code)
        if candidate is not None:
            ret = {'longitude': candidate[0],
                   'latitude': candidate[1], 'confidence': 2}
            return (ret, is_http_used)

        # check against city in usa
        candidate = self.__match_usa(result)
        if candidate is not None:
            ret = {'longitude': candidate[0],
                   'latitude': candidate[1], 'confidence': 1}
            return (ret, is_http_used)

        if len(result) > 0:
            ret = {'longitude': result[0][1],
                   'latitude': result[0][2], 'confidence': 0}
            return (ret, is_http_used)
        else:
            return (self.missing, is_http_used)

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

    def find_ugly(self, city, state_code, http_used=False):
        """ If called with http_used True, returns a tuple of (geodata_dict,boolean). If called with False, returns simply the geodata_dict"""
        if self.__chk_word(city):
            ret, is_http_used = self.find(city, state_code, http_used)
            return (ret, is_http_used) if http_used else ret

        city_slice = self.__remove_brackets(city)
        if self.__chk_word(city_slice):
            ret,is_http_used = self.find(city_slice, state_code, http_used)
            return (ret, is_http_used) if http_used else ret

        if city_slice is not None:
            city_slice = self.__remove_div(city_slice)
        else:
            city_slice = self.__remove_div(city)

        if city_slice is not None:
            result_1 = None
            if self.__chk_word(city_slice[0]):
                result_1, is_http_used = self.find(
                    city_slice[0], state_code, http_used)
            if self.__chk_word(city_slice[1]):
                result_2, is_http_used = self.find(
                    city_slice[1], state_code, http_used)
                if result_1 is None or result_2 is None:
                    print(city)
                ret = result_1 if result_1 is not None and result_1[
                    'confidence'] > result_2['confidence'] else result_2
                return (ret, is_http_used) if http_used else ret
            if result_1 is not None:
                return (result_1, is_http_used) if http_used else result_1
        return (self.missing, False) if http_used else self.missing

if __name__ == '__main__':
    import json
    import time
    import csv
    from collections import defaultdict
    # lf = LocationFinder("location_cache.json")
    # s = set()
    # for key,value in lf._LocationFinder__lookup_cache.items():
    #     if len(value) == 0:
    #         s.add(key)
    # for i in s:
    #     lf._LocationFinder__lookup_cache.pop(i,None)
    # all_data = []
    # print(len(lf._LocationFinder__lookup_cache))
    with open("data.json","r",encoding="utf8") as f:
        all_data = json.load(f)

    cities_by_name = defaultdict(lambda : [])
    cities_by_name_state = defaultdict()
    with open("uscitiesv1.3.csv","r",encoding="utf8") as f:
        static_data = csv.DictReader(f,delimiter=',')
        for row in static_data:
           cities_by_name[row["city"].lower()].append(row)
           cities_by_name_state[(row["city"].lower(),row["state_id"])] = row
    print(len(cities_by_name_state))
    print(len(cities_by_name))
    print(cities_by_name_state[("west salem","WI")])


    # for i,item in enumerate(all_data):
    #     try:
    #         ret,is_http_used = lf.find_ugly(item["City"],item["State"],True)
    #         if is_http_used:
    #             time.sleep(0.8)
    #         if not (i % 1000):
    #             print(i)
    #             lf.save_cache()
    #     except Exception as e:
    #         lf.save_cache()
    # lf.save_cache()
    # print(len(lf._LocationFinder__lookup_cache))
    found = 0
    approx = 0
    not_found = 0
    for i, item in enumerate(all_data):
        try:
            if cities_by_name_state[(item["City"].lower().strip(),item["State"].upper())] is not None:
                found +=1
        except KeyError as e:
            if item["City"].lower().strip() in cities_by_name:
                approx +=1
            else:
                not_found +=1
            for city in cities_by_name[item["City"].lower().strip()]:
                print(item["City"], item["State"],city["city"],city["state_id"])

    print(found,approx,not_found)
    #
    # print(lf.find_ugly("West Salem","CI"))
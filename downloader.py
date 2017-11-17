import requests
import time
import json
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

    def save_data(self, filname='data.json'):
        with open(filname, 'w') as outfile:
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

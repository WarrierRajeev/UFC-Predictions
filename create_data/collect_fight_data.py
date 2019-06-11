import requests
from bs4 import BeautifulSoup
import json
from urllib.request import urlopen

ALL_EVENTS_URL = 'http://ufcstats.com/statistics/events/completed?page=all'

def get_link_of_past_events(all_events_url=ALL_EVENTS_URL):
	links = []
	url = all_events_url
	source_code = requests.get(url, allow_redirects=False)
	plain_text = source_code.text.encode('ascii', 'replace')
	soup = BeautifulSoup(plain_text,'html.parser')
	for link in soup.findAll('td',{'class': 'b-statistics__table-col'}):
		for href in link.findAll('a'):
			foo = href.get('href')
			links.append(foo)
	return links

def get_fight_links(event_links):
	fight_links = []
	event_and_fight_links = {}
	for link in event_links:
		event_fights = []
		source_code = requests.get(link, allow_redirects=False)
		plain_text = source_code.text.encode('ascii', 'replace')
		soup = BeautifulSoup(plain_text, 'html.parser')
		for row in soup.findAll('tr', {'class': 'b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click'}):
			href = row.get('data-link')
			fight_links.append(href)
			event_fights.append(href)
		event_and_fight_links[link] = event_fights

	return fight_links, event_and_fight_links


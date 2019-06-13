import requests
from bs4 import BeautifulSoup
import json
from urllib.request import urlopen
from typing import 	List, Dict, Tuple

ALL_EVENTS_URL: str = 'http://ufcstats.com/statistics/events/completed?page=all'

def make_soup(url: str) -> BeautifulSoup:
	source_code = requests.get(url, allow_redirects=False)
	plain_text = source_code.text.encode('ascii', 'replace')
	return BeautifulSoup(plain_text,'html.parser')

def get_link_of_past_events(all_events_url: str=ALL_EVENTS_URL) -> List[str]:
	links = []
	url = all_events_url
	soup = make_soup(all_events_url)
	for link in soup.findAll('td',{'class': 'b-statistics__table-col'}):
		for href in link.findAll('a'):
			foo = href.get('href')
			links.append(foo)
	pickle_out = open("past_event_links.pickle","wb")
	pickle.dump(links, pickle_out)
	pickle_out.close()

	return links

def get_fight_links(event_links: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
	fight_links = []
	event_and_fight_links = {}
	for link in event_links:
		event_fights = []
		soup = make_soup(link)
		for row in soup.findAll('tr', {'class': 'b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click'}):
			href = row.get('data-link')
			fight_links.append(href)
			event_fights.append(href)
		event_and_fight_links[link] = event_fights

	pickle_out = open("fight_links.pickle","wb")
	pickle.dump(fight_links, pickle_out)
	pickle_out.close()
	pickle_out = open("event_and_fight_links.pickle","wb")
	pickle.dump(event_and_fight_links, pickle_out)
	pickle_out.close()

	return fight_links, event_and_fight_links
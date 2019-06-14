import requests
from bs4 import BeautifulSoup
from urllib.request import urlopen
from typing import 	List, Dict, Tuple
from pathlib import Path
import os
from create_data.print_progress import print_progress

HEADER: str = 'R_fighter;B_fighter;R_KD;B_KD;R_SIG_STR.;B_SIG_STR.\
;R_SIG_STR_pct;B_SIG_STR_pct;R_TOTAL_STR.;B_TOTAL_STR.;R_TD;B_TD;R_TD_pct\
;B_TD_pct;R_SUB_ATT;B_SUB_ATT;R_PASS;B_PASS;R_REV;B_REV;R_HEAD;B_HEAD;R_BODY\
;B_BODY;R_LEG;B_LEG;R_DISTANCE;B_DISTANCE;R_CLINCH;B_CLINCH;R_GROUND;B_GROUND\
;win_by;last_round;last_round_time;Format;Referee;date;location;Fight_type;Winner\n'
BASE_PATH = Path(os.getcwd())/'data'
CSV_PATH = BASE_PATH/'total_fight_data.csv'

def make_soup(url: str) -> BeautifulSoup:
	source_code = requests.get(url, allow_redirects=False)
	plain_text = source_code.text.encode('ascii', 'replace')
	
	return BeautifulSoup(plain_text,'html.parser')

def get_fight_stats(fight_soup: BeautifulSoup) -> str:
	tables = fight_soup.findAll('tbody')
	total_fight_data = [tables[0],tables[2]]
	fight_stats = []
	for table in total_fight_data:
	    row = table.find('tr')
	    stats = ''
	    for data in row.findAll('td'):
	        if stats == '':
	            stats = data.text
	        else:    
	            stats = stats + ',' + data.text
	    fight_stats.append(stats.replace('  ', '').replace('\n\n', '')\
	    	.replace('\n', ',').replace(', ', ',').replace(' ,',','))
	    
	fight_stats[1] = ';'.join(fight_stats[1].split(',')[6:])
	fight_stats[0] = ';'.join(fight_stats[0].split(','))
	fight_stats = ';'.join(fight_stats)
	return fight_stats

def get_fight_details(fight_soup: BeautifulSoup) -> str:
	columns = ''
	for div in fight_soup.findAll('div', {'class':'b-fight-details__content'}):
	    for col in div.findAll('p', {'class': 'b-fight-details__text'}):
	        if columns == '':
	            columns = col.text
	        else:
	            columns = columns + ',' +(col.text)

	columns = columns.replace('  ', '').replace('\n\n\n\n', ',')\
	.replace('\n', '').replace(', ', ',').replace(' ,',',')\
	.replace('Method: ', '').replace('Round:', '').replace('Time:', '')\
	.replace('Time format:', '').replace('Referee:', '')

	fight_details = ';'.join(columns.split(',')[:5])
	
	return fight_details

def get_event_info(event_soup: BeautifulSoup) -> str:
	event_info = ''
	for info in event_soup.findAll('li', {'class':'b-list__box-list-item'}):
	    if event_info == '':
	        event_info = (info.text)
	    else:
	        event_info = event_info + ';' + info.text 
	    
	event_info = ';'.join(event_info.replace('Date:','').replace('Location:','')\
		.replace('Attendance:','').replace('\n','').replace('  ', '').split(';')[:2])

	return event_info

def get_fight_result_data(fight_soup: BeautifulSoup) -> str:
	winner = ''
	for div in fight_soup.findAll('div', {'class': 'b-fight-details__person'}):
	    if div.find('i', {'class': 
	    	'b-fight-details__person-status b-fight-details__person-status_style_green'})!=None:
	        winner = div.find('h3', {'class':'b-fight-details__person-name'})\
	        .text.replace(' \n', '').replace('\n', '')
	
	fight_type = fight_soup.find("i",{"class":"b-fight-details__fight-title"})\
	.text.replace('  ', '').replace('\n', '')
	
	return fight_type + ';' + winner

def get_total_fight_stats(event_and_fight_links: Dict[str, List[str]]) -> str:
	total_stats = ''
	
	l = len(event_and_fight_links)
	print('Scraping all fight data: ')
	print_progress(0, l, prefix = 'Progress:', suffix = 'Complete')

	for index, (event,fights) in enumerate(event_and_fight_links.items()):
		event_soup = make_soup(event)
		event_info = get_event_info(event_soup)

		for fight in fights:
			try:
				fight_soup = make_soup(fight)
				fight_stats = get_fight_stats(fight_soup)
				fight_details = get_fight_details(fight_soup)
				result_data = get_fight_result_data(fight_soup)
			except Exception as e:
				continue
			
			total_fight_stats = fight_stats + ';' + fight_details + ';' + event_info + \
							';' + result_data

			if total_stats == '':
				total_stats = total_fight_stats
			else:
				total_stats = total_stats + '\n' + total_fight_stats

		print_progress(index + 1, l, prefix = 'Progress:', suffix = 'Complete')

	return total_stats

def save_data_to_csv(event_and_fight_links: Dict[str, List[str]], header: str = HEADER) -> None:
	
	total_stats = get_total_fight_stats(event_and_fight_links)
	with open(CSV_PATH.as_posix(), 'wb') as file:
		file.write(bytes(header, encoding='ascii', errors='ignore'))
		file.write(bytes(total_stats, encoding='ascii', errors='ignore'))
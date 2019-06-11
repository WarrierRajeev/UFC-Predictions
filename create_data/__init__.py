import collect_fight_data as cfd
from pathlib import Path
import pickle
import os

base_path = Path(os.getcwd())
event_and_fight_links_file = base_path/'event_and_fight_links.pickle'
fight_links_file = base_path/'fight_links.pickle'
past_event_links_file = base_path/'past_event_links.pickle'

if event_and_fight_links_file.exists()!=True:
	past_event_links = cfd.get_link_of_past_events()
	pickle_out = open("past_event_links.pickle","wb")
	pickle.dump(past_event_links, pickle_out)
	pickle_out.close()
else:
	pickle_in = open(event_and_fight_links_file.as_posix(),"rb")
	past_event_links = pickle.load(pickle_in)

if fight_links_file.exists()!=True:
	fight_links, event_and_fight_links = cfd.get_fight_links()
	pickle_out = open("fight_links.pickle","wb")
	pickle.dump(fight_links, pickle_out)
	pickle_out.close()
	pickle_out = open("event_and_fight_links.pickle","wb")
	pickle.dump(event_and_fight_links, pickle_out)
	pickle_out.close()
else:
	pickle_in = open(fight_links_file.as_posix(),"rb")
	fight_links = pickle.load(pickle_in)
	pickle_in = open(event_and_fight_links.as_posix(),"rb")
	event_and_fight_links = pickle.load(pickle_in)

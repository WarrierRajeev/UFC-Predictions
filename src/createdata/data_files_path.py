import os
from pathlib import Path

BASE_PATH = Path(os.getcwd()) / "data"
EVENT_AND_FIGHT_LINKS_PICKLE = BASE_PATH / "event_and_fight_links.pickle"
PAST_EVENT_LINKS_PICKLE = BASE_PATH / "past_event_links.pickle"
PAST_FIGHTER_LINKS_PICKLE = BASE_PATH / "past_fighter_links.pickle"
SCRAPED_FIGHTER_DATA_DICT_PICKLE = BASE_PATH / "scraped_fighter_data_dict.pickle"
NEW_EVENT_AND_FIGHTS = BASE_PATH / "new_fight_data.csv"
TOTAL_EVENT_AND_FIGHTS = BASE_PATH / "raw_total_fight_data.csv"
PREPROCESSED_DATA = BASE_PATH / "preprocessed_data.csv"
FIGHTER_DETAILS = BASE_PATH / "raw_fighter_details.csv"
UFC_DATA = BASE_PATH / "data.csv"

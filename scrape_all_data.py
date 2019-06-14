from create_data.scrape_fight_links import get_all_links
from create_data.scrape_fight_data import save_data_to_csv


event_and_fight_links = get_all_links()

save_data_to_csv(event_and_fight_links)	
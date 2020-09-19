import pandas as pd

from createdata.scrape_fight_data import create_fight_data_csv
from createdata.scrape_fight_links import UFCLinks
from createdata.scrape_fighter_details import create_fighter_data_csv

from createdata.data_files_path import (  # isort:skip
    NEW_EVENT_AND_FIGHTS,
    TOTAL_EVENT_AND_FIGHTS,
)

ufc_links = UFCLinks()
new_events_and_fight_links, all_events_and_fight_links = (
    ufc_links.get_event_and_fight_links()
)
print("Scraped and saved event and fight links!")

if not new_events_and_fight_links:
    create_fight_data_csv(all_events_and_fight_links, filename=TOTAL_EVENT_AND_FIGHTS)
else:
    create_fight_data_csv(new_events_and_fight_links, filename=NEW_EVENT_AND_FIGHTS)

    new_event_and_fights_data = pd.read_csv(NEW_EVENT_AND_FIGHTS)
    old_event_and_fights_data = pd.read_csv(TOTAL_EVENT_AND_FIGHTS)

    latest_total_fight_data = new_event_and_fights_data.append(
        old_event_and_fights_data, ignore_index=True
    )
    latest_total_fight_data.to_csv(TOTAL_EVENT_AND_FIGHTS, index=None)

create_fighter_data_csv()

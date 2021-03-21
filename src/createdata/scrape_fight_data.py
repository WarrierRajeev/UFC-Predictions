import os
import concurrent.futures
import threading
from typing import Dict, List

import pandas as pd
from bs4 import BeautifulSoup

from src.createdata.scrape_fight_links import UFCLinks
from src.createdata.utils import make_soup, print_progress

from src.createdata.data_files_path import (  # isort:skip
    NEW_EVENT_AND_FIGHTS,
    TOTAL_EVENT_AND_FIGHTS,
)

class FightDataScraper:
    def __init__(self):
        self.HEADER: str = "R_fighter;B_fighter;R_KD;B_KD;R_SIG_STR.;B_SIG_STR.\
;R_SIG_STR_pct;B_SIG_STR_pct;R_TOTAL_STR.;B_TOTAL_STR.;R_TD;B_TD;R_TD_pct\
;B_TD_pct;R_SUB_ATT;B_SUB_ATT;R_REV;B_REV;R_CTRL;B_CTRL;R_HEAD;B_HEAD;R_BODY\
;B_BODY;R_LEG;B_LEG;R_DISTANCE;B_DISTANCE;R_CLINCH;B_CLINCH;R_GROUND;B_GROUND\
;win_by;last_round;last_round_time;Format;Referee;date;location;Fight_type;Winner\n"

        self.NEW_EVENT_AND_FIGHTS_PATH = NEW_EVENT_AND_FIGHTS
        self.TOTAL_EVENT_AND_FIGHTS_PATH = TOTAL_EVENT_AND_FIGHTS

    def create_fight_data_csv(self) -> None:
        print("Scraping links!")

        ufc_links = UFCLinks()
        new_events_and_fight_links, all_events_and_fight_links = (
            ufc_links.get_event_and_fight_links()
        )
        print("Successfully scraped and saved event and fight links!\n")
        print("Now, scraping event and fight data!\n")

        if not new_events_and_fight_links:
            if self.TOTAL_EVENT_AND_FIGHTS_PATH.exists():
                print(f'No new fight data to scrape at the moment, loaded existing data from {self.TOTAL_EVENT_AND_FIGHTS_PATH}.')
                return
            else:
                self._scrape_raw_fight_data(
                    all_events_and_fight_links,
                    filepath=self.TOTAL_EVENT_AND_FIGHTS_PATH,
                )
        else:
            self._scrape_raw_fight_data(
                new_events_and_fight_links, filepath=self.NEW_EVENT_AND_FIGHTS_PATH
            )

            new_event_and_fights_data = pd.read_csv(self.NEW_EVENT_AND_FIGHTS_PATH)
            old_event_and_fights_data = pd.read_csv(self.TOTAL_EVENT_AND_FIGHTS_PATH)

            assert len(new_event_and_fights_data.columns) == len(
                old_event_and_fights_data.columns
            )

            new_event_and_fights_data = new_event_and_fights_data[
                list(old_event_and_fights_data.columns)
            ]

            latest_total_fight_data = new_event_and_fights_data.append(
                old_event_and_fights_data, ignore_index=True
            )
            latest_total_fight_data.to_csv(self.TOTAL_EVENT_AND_FIGHTS_PATH, index=None)

            os.remove(self.NEW_EVENT_AND_FIGHTS_PATH)
            print("Removed new event and fight files")

        print("Successfully scraped and saved ufc fight data!\n")

    def _scrape_raw_fight_data(
        self, event_and_fight_links: Dict[str, List[str]], filepath
    ):
        if filepath.exists():
            print(f'File {filepath} already exists, overwriting.')

        total_stats = FightDataScraper._get_total_fight_stats(event_and_fight_links)
        with open(filepath.as_posix(), "wb") as file:
            file.write(bytes(self.HEADER, encoding="ascii", errors="ignore"))
            file.write(bytes(total_stats, encoding="ascii", errors="ignore"))

    def _get_fight_stats_task(self, fight, event_info):
        #print(threading.get_native_id())
        total_fight_stats = ""
        try:
            fight_soup = make_soup(fight)
            fight_stats = FightDataScraper._get_fight_stats(fight_soup)
            fight_details = FightDataScraper._get_fight_details(fight_soup)
            result_data = FightDataScraper._get_fight_result_data(fight_soup)
            total_fight_stats = (
                    fight_stats
                    + ";"
                    + fight_details
                    + ";"
                    + event_info
                    + ";"
                    + result_data
            )
        except Exception as e:
            pass
            #print("Error getting fight stats, " + str(e))

        return total_fight_stats

    @classmethod
    def _get_total_fight_stats(cls, event_and_fight_links: Dict[str, List[str]]) -> str:
        total_stats = ""

        l = len(event_and_fight_links)
        print(f'Scraping data for {l} fights: ')
        print_progress(0, l, prefix="Progress:", suffix="Complete")

        for index, (event, fights) in enumerate(event_and_fight_links.items()):
            event_soup = make_soup(event)
            event_info = FightDataScraper._get_event_info(event_soup)

            # Get data for each fight in the event in parallel.
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                for fight in fights:
                    futures.append(executor.submit(FightDataScraper._get_fight_stats_task, self=cls, fight=fight, event_info=event_info))
                for future in concurrent.futures.as_completed(futures):
                    fighter_stats = future.result()
                    if fighter_stats != "":
                        if total_stats == "":
                            total_stats = fighter_stats
                        else:
                            total_stats = total_stats + "\n" + fighter_stats
                    print_progress(index + 1, l, prefix="Progress:", suffix="Complete")

        return total_stats

    @classmethod
    def _get_fight_stats(cls, fight_soup: BeautifulSoup) -> str:
        tables = fight_soup.findAll("tbody")
        total_fight_data = [tables[0], tables[2]]
        fight_stats = []
        for table in total_fight_data:
            row = table.find("tr")
            stats = ""
            for data in row.findAll("td"):
                if stats == "":
                    stats = data.text
                else:
                    stats = stats + "," + data.text
            fight_stats.append(
                stats.replace("  ", "")
                .replace("\n\n", "")
                .replace("\n", ",")
                .replace(", ", ",")
                .replace(" ,", ",")
            )

        fight_stats[1] = ";".join(fight_stats[1].split(",")[6:])
        fight_stats[0] = ";".join(fight_stats[0].split(","))
        fight_stats = ";".join(fight_stats)
        return fight_stats

    @classmethod
    def _get_fight_details(cls, fight_soup: BeautifulSoup) -> str:
        columns = ""
        for div in fight_soup.findAll("div", {"class": "b-fight-details__content"}):
            for col in div.findAll("p", {"class": "b-fight-details__text"}):
                if columns == "":
                    columns = col.text
                else:
                    columns = columns + "," + (col.text)

        columns = (
            columns.replace("  ", "")
            .replace("\n\n\n\n", ",")
            .replace("\n", "")
            .replace(", ", ",")
            .replace(" ,", ",")
            .replace("Method: ", "")
            .replace("Round:", "")
            .replace("Time:", "")
            .replace("Time format:", "")
            .replace("Referee:", "")
        )

        fight_details = ";".join(columns.split(",")[:5])

        return fight_details

    @classmethod
    def _get_event_info(cls, event_soup: BeautifulSoup) -> str:
        event_info = ""
        for info in event_soup.findAll("li", {"class": "b-list__box-list-item"}):
            if event_info == "":
                event_info = info.text
            else:
                event_info = event_info + ";" + info.text

        event_info = ";".join(
            event_info.replace("Date:", "")
            .replace("Location:", "")
            .replace("Attendance:", "")
            .replace("\n", "")
            .replace("  ", "")
            .split(";")[:2]
        )

        return event_info

    @classmethod
    def _get_fight_result_data(cls, fight_soup: BeautifulSoup) -> str:
        winner = ""
        for div in fight_soup.findAll("div", {"class": "b-fight-details__person"}):
            if (
                div.find(
                    "i",
                    {
                        "class": "b-fight-details__person-status b-fight-details__person-status_style_green"
                    },
                )
                is not None
            ):
                winner = (
                    div.find("h3", {"class": "b-fight-details__person-name"})
                    .text.replace(" \n", "")
                    .replace("\n", "")
                )

        fight_type = (
            fight_soup.find("i", {"class": "b-fight-details__fight-title"})
            .text.replace("  ", "")
            .replace("\n", "")
        )

        return fight_type + ";" + winner

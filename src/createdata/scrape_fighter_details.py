import pickle
import concurrent.futures
import threading
from typing import Dict, List

import numpy as np
import pandas as pd

from src.createdata.utils import make_soup, print_progress

from src.createdata.data_files_path import (  # isort:skip
    FIGHTER_DETAILS,
    PAST_FIGHTER_LINKS_PICKLE,
    SCRAPED_FIGHTER_DATA_DICT_PICKLE,
)

class FighterDetailsScraper:
    def __init__(self):
        self.HEADER = [
            "Height",
            "Weight",
            "Reach",
            "Stance",
            "DOB",
            "SLpM",
            "Str_Acc",
            "SApM",
            "Str_Def",
            "TD_Avg",
            "TD_Acc",
            "TD_Def",
            "Sub_Avg",
        ]
        self.FIGHTER_DETAILS_PATH = FIGHTER_DETAILS
        self.PAST_FIGHTER_LINKS_PICKLE_PATH = PAST_FIGHTER_LINKS_PICKLE
        self.SCRAPED_FIGHTER_DATA_DICT_PICKLE_PATH = SCRAPED_FIGHTER_DATA_DICT_PICKLE
        self.fighter_group_urls: List[str] = []
        self.new_fighters_exists = False
        self.new_fighter_links: Dict[str, List[str]] = {}
        self.all_fighter_links: Dict[str, List[str]] = {}

    def _get_fighter_group_urls(self) -> List[str]:
        alphas = [chr(i) for i in range(ord("a"), ord("a") + 26)]
        fighter_group_urls = [
            f"http://ufcstats.com/statistics/fighters?char={alpha}&page=all"
            for alpha in alphas
        ]
        return fighter_group_urls

    def _get_fighter_name_and_link(self,) -> Dict[str, List[str]]:
        fighter_name_and_link = {}
        fighter_name = ""

        l = len(self.fighter_group_urls)
        print("Scraping all fighter names and links: ")
        print_progress(0, l, prefix="Progress:", suffix="Complete")

        for index, fighter_group_url in enumerate(self.fighter_group_urls):
            soup = make_soup(fighter_group_url)
            table = soup.find("tbody")
            names = table.findAll(
                "a", {"class": "b-link b-link_style_black"}, href=True
            )
            for i, name in enumerate(names):
                if (i + 1) % 3 != 0:
                    if fighter_name == "":
                        fighter_name = name.text
                    else:
                        fighter_name = fighter_name + " " + name.text
                else:
                    fighter_name_and_link[fighter_name] = name["href"]
                    fighter_name = ""
            print_progress(index + 1, l, prefix="Progress:", suffix="Complete")

        return fighter_name_and_link

    def _get_updated_fighter_links(self):
        all_fighter_links = self._get_fighter_name_and_link()

        if not self.PAST_FIGHTER_LINKS_PICKLE_PATH.exists():
            # if no past event links are present, then there are no new event links
            new_fighter_links = {}
        else:
            # get past event links
            with open(
                self.PAST_FIGHTER_LINKS_PICKLE_PATH.as_posix(), "rb"
            ) as pickle_in:
                past_event_links = pickle.load(pickle_in)

            # Find links of the newer fighters
            new_fighters = list(
                set(all_fighter_links.keys()) - set(past_event_links.keys())
            )
            new_fighter_links = {
                name: link
                for name, link in all_fighter_links.items()
                if name in new_fighters
            }

        # dump all_event_links as PAST_EVENT_LINKS
        with open(self.PAST_FIGHTER_LINKS_PICKLE_PATH.as_posix(), "wb") as f:
            pickle.dump(all_fighter_links, f)

        return new_fighter_links, all_fighter_links

    def _get_fighter_data_task(self, fighter_name, fighter_url):
        another_soup = make_soup(fighter_url)
        divs = another_soup.findAll(
            "li",
            {"class": "b-list__box-list-item b-list__box-list-item_type_block"},
        )
        data = []
        for i, div in enumerate(divs):
            if i == 9:
                # An empty string is scraped here, let's not append that
                continue
            data.append(
                div.text.replace("  ", "")
                    .replace("\n", "")
                    .replace("Height:", "")
                    .replace("Weight:", "")
                    .replace("Reach:", "")
                    .replace("STANCE:", "")
                    .replace("DOB:", "")
                    .replace("SLpM:", "")
                    .replace("Str. Acc.:", "")
                    .replace("SApM:", "")
                    .replace("Str. Def:", "")
                    .replace("TD Avg.:", "")
                    .replace("TD Acc.:", "")
                    .replace("TD Def.:", "")
                    .replace("Sub. Avg.:", "")
            )
        return fighter_name, data

    def _get_fighter_name_and_details(
            self, fighter_name_and_link: Dict[str, List[str]]
    ) -> None:
        fighter_name_and_details = {}

        l = len(fighter_name_and_link)
        print(f'Scraping data for {l} fighters: ')

        # Get fighter data in parallel.
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for index, (fighter_name, fighter_url) in enumerate(fighter_name_and_link.items()):
                futures.append(executor.submit(FighterDetailsScraper._get_fighter_data_task, self=self,
                                               fighter_name=fighter_name, fighter_url=fighter_url))
            idx_progress = 0
            print_progress(0, l, prefix="Progress:", suffix="Complete")
            for future in concurrent.futures.as_completed(futures):
                fighter_name_and_details[future.result()[0]] = future.result()[1]
                print_progress(idx_progress + 1, l, prefix="Progress:", suffix="Complete")
                idx_progress += 1

        fighters_with_no_data = []
        for name, details in fighter_name_and_details.items():
            if len(details) != len(self.HEADER):
                fighters_with_no_data.append(name)

        [fighter_name_and_details.pop(name) for name in fighters_with_no_data]

        if not fighter_name_and_details:
            print("No new fighter data to scrape at the moment!")
            return

        self.new_fighters_exists = True

        # dump fighter_name_and_details as scraped_fighter_data_dict
        with open(self.SCRAPED_FIGHTER_DATA_DICT_PICKLE_PATH.as_posix(), "wb") as f:
            pickle.dump(fighter_name_and_details, f)

    def _fighter_details_to_df(self):

        with open(self.SCRAPED_FIGHTER_DATA_DICT_PICKLE_PATH.as_posix(), "rb") as f:
            fighter_name_and_details = pickle.load(f)

        df = (
            pd.DataFrame(fighter_name_and_details)
            .T.replace("--", value=np.NaN)
            .replace("", value=np.NaN)
        )
        df.columns = self.HEADER

        return df

    def create_fighter_data_csv(self) -> None:

        print("Getting fighter urls \n")
        self.fighter_group_urls = self._get_fighter_group_urls()
        print("Getting fighter names and details \n")
        self.new_fighter_links, self.all_fighter_links = (
            self._get_updated_fighter_links()
        )

        if not self.new_fighter_links:
            if self.FIGHTER_DETAILS_PATH.exists():
                print(f'No new fighter data to scrape at the moment, loaded existing data from {self.FIGHTER_DETAILS_PATH}.')
                return
            else:
                self._get_fighter_name_and_details(self.all_fighter_links)
                fighter_details_df = self._fighter_details_to_df()
        else:
            self._get_fighter_name_and_details(self.new_fighter_links)
            if self.new_fighters_exists:
                new_fighter_details_df = self._fighter_details_to_df()
            else:
                return

            old_fighter_details_df = pd.read_csv(
                self.FIGHTER_DETAILS_PATH, index_col="fighter_name"
            )

            fighter_details_df = new_fighter_details_df.append(
                old_fighter_details_df, ignore_index=False
            )

        fighter_details_df.to_csv(self.FIGHTER_DETAILS_PATH, index_label="fighter_name")
        print(f'Successfully scraped and saved ufc fighter data to {self.FIGHTER_DETAILS_PATH}\n')

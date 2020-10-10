import pickle
from typing import Dict, List

import numpy as np
import pandas as pd

from src.createdata.make_soup import make_soup
from src.createdata.print_progress import print_progress

from src.createdata.data_files_path import (  # isort:skip
    FIGHTER_DETAILS,
    PAST_FIGHTER_LINKS_PICKLE,
    SCRAPED_FIGHTER_DATA_DICT_PICKLE,
)


class FighterDetailsScraper:
    def __init__(self):
        self.HEADER = ["Height", "Weight", "Reach", "Stance", "DOB"]
        self.FIGHTER_DETAILS_PATH = FIGHTER_DETAILS
        self.PAST_FIGHTER_LINKS_PICKLE_PATH = PAST_FIGHTER_LINKS_PICKLE
        self.SCRAPED_FIGHTER_DATA_DICT_PICKLE_PATH = SCRAPED_FIGHTER_DATA_DICT_PICKLE
        self.fighter_group_urls: List[str] = []
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

    def _get_fighter_name_and_details(
        self, fighter_name_and_link: Dict[str, List[str]]
    ) -> None:
        fighter_name_and_details = {}

        l = len(fighter_name_and_link)
        print("Scraping all fighter data: ")
        print_progress(0, l, prefix="Progress:", suffix="Complete")

        for index, (fighter_name, fighter_url) in enumerate(
            fighter_name_and_link.items()
        ):
            another_soup = make_soup(fighter_url)
            divs = another_soup.findAll(
                "li",
                {"class": "b-list__box-list-item b-list__box-list-item_type_block"},
            )
            data = []
            for i, div in enumerate(divs):
                if i == 5:
                    break
                data.append(
                    div.text.replace("  ", "")
                    .replace("\n", "")
                    .replace("Height:", "")
                    .replace("Weight:", "")
                    .replace("Reach:", "")
                    .replace("STANCE:", "")
                    .replace("DOB:", "")
                )

            fighter_name_and_details[fighter_name] = data
            print_progress(index + 1, l, prefix="Progress:", suffix="Complete")

        fighters_with_no_data = []
        for name, details in fighter_name_and_details.items():
            if len(details) != len(self.HEADER):
                fighters_with_no_data.append(name)

        [fighter_name_and_details.pop(name) for name in fighters_with_no_data]

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
                print("No new fighter data to scrape at the moment!")
                return
            else:
                self._get_fighter_name_and_details(self.all_fighter_links)
                fighter_details_df = self._fighter_details_to_df()
        else:
            self._get_fighter_name_and_details(self.new_fighter_links)
            new_fighter_details_df = self._fighter_details_to_df()

            old_fighter_details_df = pd.read_csv(self.FIGHTER_DETAILS_PATH)

            fighter_details_df = new_fighter_details_df.append(
                old_fighter_details_df, ignore_index=True
            )

        fighter_details_df.to_csv(self.FIGHTER_DETAILS_PATH, index_label="fighter_name")
        print("Successfully scraped and saved ufc fighter data!\n")

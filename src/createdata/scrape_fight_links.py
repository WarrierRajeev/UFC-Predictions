import pickle
from typing import Dict, List, Tuple

from src.createdata.utils import make_soup, print_progress

from src.createdata.data_files_path import (  # isort:skip
    EVENT_AND_FIGHT_LINKS_PICKLE,
    PAST_EVENT_LINKS_PICKLE,
)


class UFCLinks:
    def __init__(
        self, all_events_url="http://ufcstats.com/statistics/events/completed?page=all"
    ):
        self.all_events_url = all_events_url
        self.PAST_EVENT_LINKS_PICKLE_PATH = PAST_EVENT_LINKS_PICKLE
        self.EVENT_AND_FIGHT_LINKS_PICKLE_PATH = EVENT_AND_FIGHT_LINKS_PICKLE
        self.new_event_links, self.all_event_links = self._get_updated_event_links()

    def _get_updated_event_links(self) -> Tuple[List[str], List[str]]:
        all_event_links = []
        soup = make_soup(self.all_events_url)

        for link in soup.findAll("td", {"class": "b-statistics__table-col"}):
            for href in link.findAll("a"):
                foo = href.get("href")
                all_event_links.append(foo)

        if not self.PAST_EVENT_LINKS_PICKLE_PATH.exists():
            # if no past event links are present, then there are no new event links
            new_event_links = []
        else:
            # get past event links
            with open(self.PAST_EVENT_LINKS_PICKLE_PATH.as_posix(), "rb") as pickle_in:
                past_event_links = pickle.load(pickle_in)

            # Find links of the newer events
            new_event_links = list(set(all_event_links) - set(past_event_links))

        # dump all_event_links as PAST_EVENT_LINKS
        with open(self.PAST_EVENT_LINKS_PICKLE_PATH.as_posix(), "wb") as f:
            pickle.dump(all_event_links, f)

        return new_event_links, all_event_links

    def get_event_and_fight_links(self) -> (Dict, Dict):
        def get_fight_links(event_links: List[str]) -> Dict[str, List[str]]:
            event_and_fight_links = {}

            l = len(event_links)
            print("Scraping event and fight links: ")
            print_progress(0, l, prefix="Progress:", suffix="Complete")

            for index, link in enumerate(event_links):
                event_fights = []
                soup = make_soup(link)
                for row in soup.findAll(
                    "tr",
                    {
                        "class": "b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click"
                    },
                ):
                    href = row.get("data-link")
                    event_fights.append(href)
                event_and_fight_links[link] = event_fights

                print_progress(index + 1, l, prefix="Progress:", suffix="Complete")

            return event_and_fight_links

        new_events_and_fight_links = {}
        if self.EVENT_AND_FIGHT_LINKS_PICKLE_PATH.exists():
            if not self.new_event_links:
                with open(
                    self.EVENT_AND_FIGHT_LINKS_PICKLE_PATH.as_posix(), "rb"
                ) as pickle_in:
                    all_events_and_fight_links = pickle.load(pickle_in)

                return new_events_and_fight_links, all_events_and_fight_links
            else:
                new_events_and_fight_links = get_fight_links(self.new_event_links)

        all_events_and_fight_links = get_fight_links(self.all_event_links)
        with open(self.EVENT_AND_FIGHT_LINKS_PICKLE_PATH.as_posix(), "wb") as f:
            pickle.dump(all_events_and_fight_links, f)

        return new_events_and_fight_links, all_events_and_fight_links

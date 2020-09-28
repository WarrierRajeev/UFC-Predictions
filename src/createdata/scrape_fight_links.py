import pickle
from typing import Dict, List, Tuple

from src.createdata.make_soup import make_soup

from src.createdata.data_files_path import (  # isort:skip
    EVENT_AND_FIGHT_LINKS_PICKLE_PATH,
    PAST_EVENT_LINKS_PICKLE_PATH,
)


class UFCLinks:
    def __init__(
        self, all_events_url="http://ufcstats.com/statistics/events/completed?page=all"
    ):
        self.all_events_url = all_events_url
        self.new_event_links, self.all_event_links = self._get_updated_event_links()

    def _get_updated_event_links(self) -> Tuple[List[str], List[str]]:
        all_event_links = []
        soup = make_soup(self.all_events_url)

        for link in soup.findAll("td", {"class": "b-statistics__table-col"}):
            for href in link.findAll("a"):
                foo = href.get("href")
                all_event_links.append(foo)

        if not PAST_EVENT_LINKS_PICKLE_PATH.exists():
            # if no past event links are present, then there are no new event links
            new_event_links = []
        else:
            # get past event links
            pickle_in = open(PAST_EVENT_LINKS_PICKLE_PATH.as_posix(), "rb")
            past_event_links = pickle.load(pickle_in)
            pickle_in.close()

            # Find links of the newer events
            new_event_links = list(set(all_event_links) - set(past_event_links))

        # dump all_event_links as PAST_EVENT_LINKS
        pickle_out1 = open(PAST_EVENT_LINKS_PICKLE_PATH.as_posix(), "wb")
        pickle.dump(all_event_links, pickle_out1)
        pickle_out1.close()

        return new_event_links, all_event_links

    def get_event_and_fight_links(self) -> (Dict, Dict):
        def get_fight_links(event_links: List[str]) -> Dict[str, List[str]]:
            event_and_fight_links = {}
            for link in event_links:
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

            return event_and_fight_links

        new_events_and_fight_links = {}
        if EVENT_AND_FIGHT_LINKS_PICKLE_PATH.exists():
            if not self.new_event_links:
                pickle_in = open(EVENT_AND_FIGHT_LINKS_PICKLE_PATH.as_posix(), "rb")
                all_events_and_fight_links = pickle.load(pickle_in)
                pickle_in.close()
                return new_events_and_fight_links, all_events_and_fight_links
            else:
                new_events_and_fight_links = get_fight_links(self.new_event_links)

        all_events_and_fight_links = get_fight_links(self.all_event_links)
        pickle_out = open(EVENT_AND_FIGHT_LINKS_PICKLE_PATH.as_posix(), "wb")
        pickle.dump(all_events_and_fight_links, pickle_out)
        pickle_out.close()

        return new_events_and_fight_links, all_events_and_fight_links

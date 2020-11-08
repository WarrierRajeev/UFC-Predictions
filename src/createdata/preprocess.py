import math

import numpy as np
import pandas as pd

from src.createdata.preprocess_fighter_data import FighterDetailProcessor

from src.createdata.data_files_path import (  # isort:skip
    FIGHTER_DETAILS,
    PREPROCESSED_DATA,
    TOTAL_EVENT_AND_FIGHTS,
    UFC_DATA,
)


class Preprocessor:
    def __init__(self):
        self.FIGHTER_DETAILS_PATH = FIGHTER_DETAILS
        self.TOTAL_EVENT_AND_FIGHTS_PATH = TOTAL_EVENT_AND_FIGHTS
        self.PREPROCESSED_DATA_PATH = PREPROCESSED_DATA
        self.UFC_DATA_PATH = UFC_DATA
        self.fights = None
        self.fighter_details = None
        self.store = None

    def process_raw_data(self):
        print("Reading Files")
        self.fights, self.fighter_details = self._read_files()

        print("Drop columns that contain information not yet occurred")
        self._drop_future_fighter_details_columns()

        print("Renaming Columns")
        self._rename_columns()
        self._replacing_winner_nans_draw()

        print("Converting Percentages to Fractions")
        self._convert_percentages_to_fractions()
        self._create_title_bout_feature()
        self._create_weight_classes()
        self._convert_last_round_to_seconds()
        self._convert_CTRL_to_seconds()
        self._get_total_time_fought()
        self.store = self._store_compiled_fighter_data_in_another_DF()
        self._create_winner_feature()
        self._create_fighter_attributes()
        self._create_fighter_age()
        self._save(filepath=self.UFC_DATA_PATH)

        print("Fill NaNs")
        self._fill_nas()
        print("Dropping Non Essential Columns")
        self._drop_non_essential_cols()
        self._save(filepath=self.PREPROCESSED_DATA_PATH)
        print("Successfully preprocessed and saved ufc data!\n")

    def _read_files(self):
        try:
            fights_df = pd.read_csv(self.TOTAL_EVENT_AND_FIGHTS_PATH, sep=";")

        except Exception as e:
            raise FileNotFoundError("Cannot find the data/total_fight_data.csv")

        try:
            fighter_details_df = pd.read_csv(
                self.FIGHTER_DETAILS_PATH, index_col="fighter_name"
            )

        except Exception as e:
            raise FileNotFoundError("Cannot find the data/fighter_details.csv")

        return fights_df, fighter_details_df

    def _drop_future_fighter_details_columns(self):
        self.fighter_details.drop(
            columns=[
                "SLpM",
                "Str_Acc",
                "SApM",
                "Str_Def",
                "TD_Avg",
                "TD_Acc",
                "TD_Def",
                "Sub_Avg",
            ],
            inplace=True,
        )

    def _rename_columns(self):
        columns = [
            "R_SIG_STR.",
            "B_SIG_STR.",
            "R_TOTAL_STR.",
            "B_TOTAL_STR.",
            "R_TD",
            "B_TD",
            "R_HEAD",
            "B_HEAD",
            "R_BODY",
            "B_BODY",
            "R_LEG",
            "B_LEG",
            "R_DISTANCE",
            "B_DISTANCE",
            "R_CLINCH",
            "B_CLINCH",
            "R_GROUND",
            "B_GROUND",
        ]

        attempt_suffix = "_att"
        landed_suffix = "_landed"

        for column in columns:
            self.fights[column + attempt_suffix] = self.fights[column].apply(
                lambda X: int(X.split("of")[1])
            )
            self.fights[column + landed_suffix] = self.fights[column].apply(
                lambda X: int(X.split("of")[0])
            )

        self.fights.drop(columns, axis=1, inplace=True)

    def _replacing_winner_nans_draw(self):
        self.fights["Winner"].fillna("Draw", inplace=True)

    def _convert_percentages_to_fractions(self):
        pct_columns = ["R_SIG_STR_pct", "B_SIG_STR_pct", "R_TD_pct", "B_TD_pct"]

        def pct_to_frac(X):
            if X != "---":
                return float(X.replace("%", "")) / 100
            else:
                # if '---' means it's taking pct of `0 of 0`.
                # Taking a call here to consider 0 landed of 0 attempted as 0 percentage
                return 0

        for column in pct_columns:
            self.fights[column] = self.fights[column].apply(pct_to_frac)

    def _create_title_bout_feature(self):
        self.fights["title_bout"] = self.fights["Fight_type"].apply(
            lambda X: True if "Title Bout" in X else False
        )

    def _create_weight_classes(self):
        def make_weight_class(X):
            weight_classes = [
                "Women's Strawweight",
                "Women's Bantamweight",
                "Women's Featherweight",
                "Women's Flyweight",
                "Lightweight",
                "Welterweight",
                "Middleweight",
                "Light Heavyweight",
                "Heavyweight",
                "Featherweight",
                "Bantamweight",
                "Flyweight",
                "Open Weight",
            ]

            for weight_class in weight_classes:
                if weight_class in X:
                    return weight_class

            if X == "Catch Weight Bout" or "Catchweight Bout":
                return "Catch Weight"
            else:
                return "Open Weight"

        self.fights["weight_class"] = self.fights["Fight_type"].apply(make_weight_class)

        renamed_weight_classes = {
            "Flyweight": "Flyweight",
            "Bantamweight": "Bantamweight",
            "Featherweight": "Featherweight",
            "Lightweight": "Lightweight",
            "Welterweight": "Welterweight",
            "Middleweight": "Middleweight",
            "Light Heavyweight": "LightHeavyweight",
            "Heavyweight": "Heavyweight",
            "Women's Strawweight": "WomenStrawweight",
            "Women's Flyweight": "WomenFlyweight",
            "Women's Bantamweight": "WomenBantamweight",
            "Women's Featherweight": "WomenFeatherweight",
            "Catch Weight": "CatchWeight",
            "Open Weight": "OpenWeight",
        }

        self.fights["weight_class"] = self.fights["weight_class"].apply(
            lambda weight: renamed_weight_classes[weight]
        )

    def _convert_last_round_to_seconds(self):
        # Converting to seconds
        self.fights["last_round_time"] = self.fights["last_round_time"].apply(
            lambda X: int(X.split(":")[0]) * 60 + int(X.split(":")[1])
        )

    def _convert_CTRL_to_seconds(self):
        # Converting to seconds
        CTRL_columns = ["R_CTRL", "B_CTRL"]

        def conv_to_sec(X):
            if X != "--":
                return int(X.split(":")[0]) * 60 + int(X.split(":")[1])
            else:
                # if '--' means there was no time spent on the ground.
                # Taking a call here to consider this as 0 seconds
                return 0

        for column in CTRL_columns:
            self.fights[column + "_time(seconds)"] = self.fights[column].apply(
                conv_to_sec
            )

        # drop original columns
        self.fights.drop(["R_CTRL", "B_CTRL"], axis=1, inplace=True)

    def _get_total_time_fought(self):
        # '1 Rnd + 2OT (15-3-3)' and '1 Rnd + 2OT (24-3-3)' is not included because it has 3 uneven timed rounds.
        # We'll have to deal with it separately
        time_in_first_round = {
            "3 Rnd (5-5-5)": 5 * 60,
            "5 Rnd (5-5-5-5-5)": 5 * 60,
            "1 Rnd + OT (12-3)": 12 * 60,
            "No Time Limit": 1,
            "3 Rnd + OT (5-5-5-5)": 5 * 60,
            "1 Rnd (20)": 1 * 20,
            "2 Rnd (5-5)": 5 * 60,
            "1 Rnd (15)": 15 * 60,
            "1 Rnd (10)": 10 * 60,
            "1 Rnd (12)": 12 * 60,
            "1 Rnd + OT (30-5)": 30 * 60,
            "1 Rnd (18)": 18 * 60,
            "1 Rnd + OT (15-3)": 15 * 60,
            "1 Rnd (30)": 30 * 60,
            "1 Rnd + OT (31-5)": 31 * 5,
            "1 Rnd + OT (27-3)": 27 * 60,
            "1 Rnd + OT (30-3)": 30 * 60,
        }

        exception_format_time = {
            "1 Rnd + 2OT (15-3-3)": [15 * 60, 3 * 60],
            "1 Rnd + 2OT (24-3-3)": [24 * 60, 3 * 60],
        }

        def get_total_time(row):
            if row["Format"] in time_in_first_round.keys():
                return (row["last_round"] - 1) * time_in_first_round[
                    row["Format"]
                ] + row["last_round_time"]

            elif row["Format"] in exception_format_time.keys():

                if (row["last_round"] - 1) >= 2:
                    return (
                        exception_format_time[row["Format"]][0]
                        + (row["last_round"] - 2)
                        * exception_format_time[row["Format"]][1]
                        + row["last_round_time"]
                    )
                else:
                    return (row["last_round"] - 1) * exception_format_time[
                        row["Format"]
                    ][0] + row["last_round_time"]

        self.fights["total_time_fought(seconds)"] = self.fights.apply(
            get_total_time, axis=1
        )
        self.fights.drop(
            ["Format", "Fight_type", "last_round_time"], axis=1, inplace=True
        )

    def _store_compiled_fighter_data_in_another_DF(self):
        store = self.fights.copy()
        store.drop(
            [
                "R_KD",
                "B_KD",
                "R_SIG_STR_pct",
                "B_SIG_STR_pct",
                "R_TD_pct",
                "B_TD_pct",
                "R_SUB_ATT",
                "B_SUB_ATT",
                "R_REV",
                "B_REV",
                "R_CTRL_time(seconds)",
                "B_CTRL_time(seconds)",
                "win_by",
                "last_round",
                "R_SIG_STR._att",
                "R_SIG_STR._landed",
                "B_SIG_STR._att",
                "B_SIG_STR._landed",
                "R_TOTAL_STR._att",
                "R_TOTAL_STR._landed",
                "B_TOTAL_STR._att",
                "B_TOTAL_STR._landed",
                "R_TD_att",
                "R_TD_landed",
                "B_TD_att",
                "B_TD_landed",
                "R_HEAD_att",
                "R_HEAD_landed",
                "B_HEAD_att",
                "B_HEAD_landed",
                "R_BODY_att",
                "R_BODY_landed",
                "B_BODY_att",
                "B_BODY_landed",
                "R_LEG_att",
                "R_LEG_landed",
                "B_LEG_att",
                "B_LEG_landed",
                "R_DISTANCE_att",
                "R_DISTANCE_landed",
                "B_DISTANCE_att",
                "B_DISTANCE_landed",
                "R_CLINCH_att",
                "R_CLINCH_landed",
                "B_CLINCH_att",
                "B_CLINCH_landed",
                "R_GROUND_att",
                "R_GROUND_landed",
                "B_GROUND_att",
                "B_GROUND_landed",
                "total_time_fought(seconds)",
            ],
            axis=1,
            inplace=True,
        )
        return store

    def _create_winner_feature(self):
        def get_renamed_winner(row):
            if row["R_fighter"] == row["Winner"]:
                return "Red"

            elif row["B_fighter"] == row["Winner"]:
                return "Blue"

            elif row["Winner"] == "Draw":
                return "Draw"

        self.store["Winner"] = self.store[["R_fighter", "B_fighter", "Winner"]].apply(
            get_renamed_winner, axis=1
        )

    def _create_fighter_attributes(self):
        frame = FighterDetailProcessor(self.fights, self.fighter_details).frame
        self.store = self.store.join(frame, how="outer")

    def _create_fighter_age(self):
        self.store["R_DOB"] = pd.to_datetime(self.store["R_DOB"])
        self.store["B_DOB"] = pd.to_datetime(self.store["B_DOB"])
        self.store["date"] = pd.to_datetime(self.store["date"])

        def get_age(row):
            B_age = (row["date"] - row["B_DOB"]).days
            R_age = (row["date"] - row["R_DOB"]).days

            if np.isnan(B_age) != True:
                B_age = math.floor(B_age / 365.25)

            if np.isnan(R_age) != True:
                R_age = math.floor(R_age / 365.25)

            return pd.Series([B_age, R_age], index=["B_age", "R_age"])

        self.store[["B_age", "R_age"]] = self.store[["date", "R_DOB", "B_DOB"]].apply(
            get_age, axis=1
        )
        self.store.drop(["R_DOB", "B_DOB"], axis=1, inplace=True)

    def _save(self, filepath):
        self.store.to_csv(filepath, index=False)

    def _fill_nas(self):
        self.store["R_Reach_cms"].fillna(self.store["R_Height_cms"], inplace=True)
        self.store["B_Reach_cms"].fillna(self.store["B_Height_cms"], inplace=True)
        self.store.fillna(self.store.median(), inplace=True)

        self.store["R_Stance"].fillna("Orthodox", inplace=True)
        self.store["B_Stance"].fillna("Orthodox", inplace=True)

    def _drop_non_essential_cols(self):
        self.store.drop(self.store.index[self.store["Winner"] == "Draw"], inplace=True)
        self.store = pd.concat(
            [
                self.store,
                pd.get_dummies(self.store[["weight_class", "B_Stance", "R_Stance"]]),
            ],
            axis=1,
        )
        self.store.drop(
            columns=[
                "weight_class",
                "B_Stance",
                "R_Stance",
                "Referee",
                "location",
                "date",
                "R_fighter",
                "B_fighter",
            ],
            inplace=True,
        )

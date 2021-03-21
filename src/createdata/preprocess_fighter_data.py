import re

import numpy as np
import pandas as pd
from tqdm import tqdm


class FighterDetailProcessor:
    def __init__(self, fights, fighter_details):
        self.fights = fights
        self.fighter_details = fighter_details
        self._one_hot_encode_win()
        self.temp_red_frame, self.temp_blue_frame = self._calculate_fighter_data()
        self._convert_height_reach_to_cms()
        self._convert_weight_to_pounds()
        self.frame = self._merge_frames()
        self._rename_columns()

    def _one_hot_encode_win(self):

        self.fights = pd.concat(
            [self.fights, pd.get_dummies(self.fights["win_by"], prefix="win_by")],
            axis=1,
        )
        self.fights.drop(["win_by"], axis=1, inplace=True)

    def _get_fighters(self):

        red_fighters = self.fights["R_fighter"].value_counts().index
        blue_fighters = self.fights["B_fighter"].value_counts().index

        return list(set(red_fighters) | set(blue_fighters))

    def _calculate_fighter_data(self):

        temp_blue_frame = pd.DataFrame()
        temp_red_frame = pd.DataFrame()

        fighters = self._get_fighters()
        self.red = self.fights.groupby("R_fighter")
        self.blue = self.fights.groupby("B_fighter")

        result_stats = [
            "current_win_streak",
            "current_lose_streak",
            "longest_win_streak",
            "wins",
            "losses",
            "draw",
        ]

        win_by_columns = [
            "win_by_Decision - Majority",
            "win_by_Decision - Split",
            "win_by_Decision - Unanimous",
            "win_by_KO/TKO",
            "win_by_Submission",
            "win_by_TKO - Doctor's Stoppage",
        ]

        Numerical_columns = [
            "hero_KD",
            "opp_KD",
            "hero_SIG_STR_pct",
            "opp_SIG_STR_pct",
            "hero_TD_pct",
            "opp_TD_pct",
            "hero_SUB_ATT",
            "opp_SUB_ATT",
            "hero_REV",
            "opp_REV",
            "hero_SIG_STR._att",
            "hero_SIG_STR._landed",
            "opp_SIG_STR._att",
            "opp_SIG_STR._landed",
            "hero_TOTAL_STR._att",
            "hero_TOTAL_STR._landed",
            "opp_TOTAL_STR._att",
            "opp_TOTAL_STR._landed",
            "hero_TD_att",
            "hero_TD_landed",
            "opp_TD_att",
            "opp_TD_landed",
            "hero_HEAD_att",
            "hero_HEAD_landed",
            "opp_HEAD_att",
            "opp_HEAD_landed",
            "hero_BODY_att",
            "hero_BODY_landed",
            "opp_BODY_att",
            "opp_BODY_landed",
            "hero_LEG_att",
            "hero_LEG_landed",
            "opp_LEG_att",
            "opp_LEG_landed",
            "hero_DISTANCE_att",
            "hero_DISTANCE_landed",
            "opp_DISTANCE_att",
            "opp_DISTANCE_landed",
            "hero_CLINCH_att",
            "hero_CLINCH_landed",
            "opp_CLINCH_att",
            "opp_CLINCH_landed",
            "hero_GROUND_att",
            "hero_GROUND_landed",
            "opp_GROUND_att",
            "opp_GROUND_landed",
            "hero_CTRL_time(seconds)",
            "opp_CTRL_time(seconds)",
            "total_time_fought(seconds)",
        ]

        print("Creating Fighter Level Features")
        for fighter_name in tqdm(fighters):
            fighter_red = self._get_fighter_red(fighter_name)
            fighter_blue = self._get_fighter_blue(fighter_name)
            fighter_index = None

            if fighter_red is None:
                fighter = fighter_blue
                fighter_index = "blue"
            elif fighter_blue is None:
                fighter = fighter_red
                fighter_index = "red"
            else:
                fighter = pd.concat([fighter_red, fighter_blue]).sort_index()

            fighter["Winner"] = fighter["Winner"].apply(
                lambda X: "hero" if X == fighter_name else "opp"
            )

            for i, index in enumerate(fighter.index):

                fighter_slice = fighter[(i + 1) :].sort_index(ascending=False)
                s = (
                    fighter_slice[Numerical_columns]
                    .ewm(span=3, adjust=False)
                    .mean()
                    .tail(1)
                )
                if len(s) != 0:
                    pass
                else:
                    s.loc[len(s)] = [np.NaN for _ in s.columns]
                s["total_rounds_fought"] = fighter_slice["last_round"].sum()
                s["total_title_bouts"] = fighter_slice[
                    fighter_slice["title_bout"] == True
                ]["title_bout"].count()
                s["hero_fighter"] = fighter_name
                results = self._get_result_stats(list(fighter_slice["Winner"]))
                for result_stat, result in zip(result_stats, results):
                    s[result_stat] = result
                win_by_results = fighter_slice[fighter_slice["Winner"] == "hero"][
                    win_by_columns
                ].sum()
                for win_by_column, win_by_result in zip(win_by_columns, win_by_results):
                    s[win_by_column] = win_by_result

                s.index = [index]

                if fighter_index is None:
                    if index in fighter_blue.index:
                        temp_blue_frame = temp_blue_frame.append(s)
                    elif index in fighter_red.index:
                        temp_red_frame = temp_red_frame.append(s)
                elif fighter_index == "blue":
                    temp_blue_frame = temp_blue_frame.append(s)
                elif fighter_index == "red":
                    temp_red_frame = temp_red_frame.append(s)

        return temp_red_frame, temp_blue_frame

    @staticmethod
    def lreplace(pattern, sub, string):
        """
        Replaces 'pattern' in 'string' with 'sub' if 'pattern' starts 'string'.
        """
        return re.sub("^%s" % pattern, sub, string)

    def _get_fighter_red(self, fighter_name):

        try:
            fighter_red = self.red.get_group(fighter_name)
        except:
            return None

        rename_columns = {}
        for column in fighter_red.columns:

            if re.search("^R_", column) is not None:
                rename_columns[column] = self.lreplace("R_", "hero_", column)

            elif re.search("^B_", column) is not None:
                rename_columns[column] = self.lreplace("B_", "opp_", column)

        fighter_red = fighter_red.rename(rename_columns, axis="columns")
        return fighter_red

    def _get_fighter_blue(self, fighter_name):

        try:
            fighter_blue = self.blue.get_group(fighter_name)
        except:
            return None

        rename_columns = {}
        for column in fighter_blue.columns:

            if re.search("^B_", column) is not None:
                rename_columns[column] = self.lreplace("B_", "hero_", column)

            elif re.search("^R_", column) is not None:
                rename_columns[column] = self.lreplace("R_", "opp_", column)

        fighter_blue = fighter_blue.rename(rename_columns, axis="columns")
        return fighter_blue

    @staticmethod
    def _get_result_stats(result_list):
        result_list.reverse()  # To get it in ascending order
        current_win_streak = 0
        current_lose_streak = 0
        longest_win_streak = 0
        wins = 0
        losses = 0
        draw = 0
        for result in result_list:

            if result == "hero":
                wins += 1
                current_win_streak += 1
                current_lose_streak = 0
                if longest_win_streak < current_win_streak:
                    longest_win_streak += 1

            elif result == "opp":
                losses += 1
                current_win_streak = 0
                current_lose_streak += 1

            elif result == "draw":
                draw += 1
                current_lose_streak = 0
                current_win_streak = 0

        return (
            current_win_streak,
            current_lose_streak,
            longest_win_streak,
            wins,
            losses,
            draw,
        )

    def _convert_height_reach_to_cms(self):
        def convert_to_cms(X):

            if X is np.NaN:
                return X

            elif len(X.split("'")) == 2:
                feet = float(X.split("'")[0])
                inches = int(X.split("'")[1].replace(" ", "").replace('"', ""))
                return (feet * 30.48) + (inches * 2.54)

            else:
                return float(X.replace('"', "")) * 2.54

        self.fighter_details["Height_cms"] = self.fighter_details["Height"].apply(
            convert_to_cms
        )
        self.fighter_details["Reach_cms"] = self.fighter_details["Reach"].apply(
            convert_to_cms
        )

    def _convert_weight_to_pounds(self):
        self.fighter_details["Weight_lbs"] = self.fighter_details["Weight"].apply(
            lambda X: float(X.replace(" lbs.", "")) if X is not np.NaN else X
        )
        self.fighter_details.drop(["Height", "Weight", "Reach"], axis=1, inplace=True)

    def _merge_frames(self):

        self.fighter_details.reset_index(inplace=True)
        self.temp_red_frame.reset_index(inplace=True)
        self.temp_blue_frame.reset_index(inplace=True)

        self.temp_blue_frame = self.temp_blue_frame.merge(
            self.fighter_details,
            left_on="hero_fighter",
            right_on="fighter_name",
            how="left",
        )
        self.temp_blue_frame.set_index("index", inplace=True)

        self.temp_red_frame = self.temp_red_frame.merge(
            self.fighter_details,
            left_on="hero_fighter",
            right_on="fighter_name",
            how="left",
        )
        self.temp_red_frame.set_index("index", inplace=True)

        self.temp_blue_frame.drop("fighter_name", axis=1, inplace=True)
        self.temp_red_frame.drop("fighter_name", axis=1, inplace=True)

        blue_frame = self.temp_blue_frame.add_prefix("B_")
        red_frame = self.temp_red_frame.add_prefix("R_")

        return blue_frame.join(red_frame, how="outer")

    def _rename_columns(self):

        rename_cols = {}

        for col in self.frame.columns:
            if "hero" in col:
                rename_cols[col] = col.replace("_hero_", "_avg_").replace(".", "")
            if "opp" in col:
                rename_cols[col] = col.replace("_opp_", "_avg_opp_").replace(".", "")
            if "win_by" in col:
                rename_cols[col] = (
                    col.replace(" ", "").replace("-", "_").replace("'s", "_")
                )

        self.frame.rename(rename_cols, axis="columns", inplace=True)
        self.frame.drop(["R_avg_fighter", "B_avg_fighter"], axis=1, inplace=True)

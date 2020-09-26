import math
import re

import numpy as np
import pandas as pd

from createdata.data_files_path import (  # isort:skip
    FIGHTER_DETAILS,
    PREPROCESSED_DATA,
    TOTAL_EVENT_AND_FIGHTS,
)


def format_data():
    """
    Preprocesses raw data, creates and saves usable data for ML model consumption
    :return: None
    """

    df = pd.read_csv(TOTAL_EVENT_AND_FIGHTS, sep=";")

    # Splitting landed of attempted to different columns
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
        df[column + attempt_suffix] = df[column].apply(lambda X: int(X.split("of")[1]))
        df[column + landed_suffix] = df[column].apply(lambda X: int(X.split("of")[0]))

    df.drop(columns, axis=1, inplace=True)

    # Replacing Winner NaNs as Draw
    for column in df.columns:
        if df[column].isnull().sum() != 0:
            print(f"NaN values in {column} = {df[column].isnull().sum()}")

    df["Winner"].fillna("Draw", inplace=True)

    pct_columns = ["R_SIG_STR_pct", "B_SIG_STR_pct", "R_TD_pct", "B_TD_pct"]

    # Converting percentages to fractions
    for column in pct_columns:
        df[column] = df[column].apply(lambda X: float(X.replace("%", "")) / 100)

    # Creating a title_bout feature and weight_class
    df["title_bout"] = df["Fight_type"].apply(
        lambda X: True if "Title Bout" in X else False
    )

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

    def make_weight_class(X):
        for weight_class in weight_classes:
            if weight_class in X:
                return weight_class
        if X == "Catch Weight Bout" or "Catchweight Bout":
            return "Catch Weight"
        else:
            return "Open Weight"

    df["weight_class"] = df["Fight_type"].apply(make_weight_class)

    assert list(df[df["weight_class"].isnull()]["Fight_type"].value_counts()) is None

    renamed_weight_classes = {
        "Flyweight": "flyweight",
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

    df["weight_class"] = df["weight_class"].apply(lambda X: renamed_weight_classes[X])

    # Creating total_time_fought
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

    df["last_round_time"] = df["last_round_time"].apply(
        lambda X: int(X.split(":")[0]) * 60 + int(X.split(":")[1])
    )  # Converting to seconds

    def get_total_time(row):
        if row["Format"] in time_in_first_round.keys():
            return (row["last_round"] - 1) * time_in_first_round[row["Format"]] + row[
                "last_round_time"
            ]
        elif row["Format"] in exception_format_time.keys():
            if (row["last_round"] - 1) >= 2:
                return (
                    exception_format_time[row["Format"]][0]
                    + (row["last_round"] - 2) * exception_format_time[row["Format"]][1]
                    + row["last_round_time"]
                )
            else:
                return (row["last_round"] - 1) * exception_format_time[row["Format"]][
                    0
                ] + row["last_round_time"]

    # So if the fight ended in round 1, we only need last_round_time.
    # If it ended in round 2, we need the full time of round 1 and the last_round_time
    # This works for fights with same time in each round and fights with only two rounds.

    df["total_time_fought(seconds)"] = df.apply(get_total_time, axis=1)

    def get_no_of_rounds(X):
        if X == "No Time Limit":
            return 1
        else:
            return len(X.split("(")[1].replace(")", "").split("-"))

    df["no_of_rounds"] = df["Format"].apply(get_no_of_rounds)

    df.drop(["Format", "Fight_type", "last_round_time"], axis=1, inplace=True)

    # Create another DataFrame to save the compiled data per fighter (Our Prediction DataFrame)

    df2 = df.copy()

    df2.drop(
        [
            "R_KD",
            "B_KD",
            "R_SIG_STR_pct",
            "B_SIG_STR_pct",
            "R_TD_pct",
            "B_TD_pct",
            "R_SUB_ATT",
            "B_SUB_ATT",
            "R_PASS",
            "B_PASS",
            "R_REV",
            "B_REV",
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

    # Compiling Data per fighter
    red_fighters = df["R_fighter"].value_counts().index
    blue_fighters = df["B_fighter"].value_counts().index

    fighters = list(set(red_fighters) | set(blue_fighters))

    def get_renamed_winner(row):
        if row["R_fighter"] == row["Winner"]:
            return "Red"
        elif row["B_fighter"] == row["Winner"]:
            return "Blue"
        elif row["Winner"] == "Draw":
            return "Draw"

    df2["Winner"] = df2[["R_fighter", "B_fighter", "Winner"]].apply(
        get_renamed_winner, axis=1
    )

    df = pd.concat([df, pd.get_dummies(df["win_by"], prefix="win_by")], axis=1)
    df.drop(["win_by"], axis=1, inplace=True)

    Numerical_columns = [
        "hero_KD",
        "opp_KD",
        "hero_SIG_STR_pct",
        "opp_SIG_STR_pct",
        "hero_TD_pct",
        "opp_TD_pct",
        "hero_SUB_ATT",
        "opp_SUB_ATT",
        "hero_PASS",
        "opp_PASS",
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
        "total_time_fought(seconds)",
    ]

    Categorical_columns = ["win_by", "last_round", "Winner", "title_bout"]

    def lreplace(pattern, sub, string):
        """
        Replaces 'pattern' in 'string' with 'sub' if 'pattern' starts 'string'.
        """
        return re.sub("^%s" % pattern, sub, string)

    red = df.groupby("R_fighter")
    blue = df.groupby("B_fighter")

    def get_fighter_red(fighter_name):
        try:
            fighter_red = red.get_group(fighter_name)
        except:
            return None
        rename_columns = {}
        for column in fighter_red.columns:
            if re.search("^R_", column) is not None:
                rename_columns[column] = lreplace("R_", "hero_", column)
            elif re.search("^B_", column) is not None:
                rename_columns[column] = lreplace("B_", "opp_", column)
        fighter_red = fighter_red.rename(rename_columns, axis="columns")
        return fighter_red

    def get_fighter_blue(fighter_name):
        try:
            fighter_blue = blue.get_group(fighter_name)
        except:
            return None
        rename_columns = {}
        for column in fighter_blue.columns:
            if re.search("^B_", column) is not None:
                rename_columns[column] = lreplace("B_", "hero_", column)
            elif re.search("^R_", column) is not None:
                rename_columns[column] = lreplace("R_", "opp_", column)
        fighter_blue = fighter_blue.rename(rename_columns, axis="columns")
        return fighter_blue

    def get_result_stats(result_list):
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

    win_by_columns = [
        "win_by_Decision - Majority",
        "win_by_Decision - Split",
        "win_by_Decision - Unanimous",
        "win_by_KO/TKO",
        "win_by_Submission",
        "win_by_TKO - Doctor's Stoppage",
    ]

    temp_blue_frame = pd.DataFrame()
    temp_red_frame = pd.DataFrame()
    result_stats = [
        "current_win_streak",
        "current_lose_streak",
        "longest_win_streak",
        "wins",
        "losses",
        "draw",
    ]

    for fighter_name in fighters:
        fighter_red = get_fighter_red(fighter_name)
        fighter_blue = get_fighter_blue(fighter_name)
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
            fighter_slice = fighter[(i + 1) :]
            s = fighter_slice[Numerical_columns].mean()
            s["total_rounds_fought"] = fighter_slice["last_round"].sum()
            s["total_title_bouts"] = fighter_slice[fighter_slice["title_bout"] == True][
                "title_bout"
            ].count()
            s["hero_fighter"] = fighter_name
            results = get_result_stats(list(fighter_slice["Winner"]))
            for result_stat, result in zip(result_stats, results):
                s[result_stat] = result
            win_by_results = fighter_slice[fighter_slice["Winner"] == "hero"][
                win_by_columns
            ].sum()
            for win_by_column, win_by_result in zip(win_by_columns, win_by_results):
                s[win_by_column] = win_by_result
            s.name = index

            if fighter_index is None:
                if index in fighter_blue.index:
                    temp_blue_frame = temp_blue_frame.append(s)
                elif index in fighter_red.index:
                    temp_red_frame = temp_red_frame.append(s)
            elif fighter_index == "blue":
                temp_blue_frame = temp_blue_frame.append(s)
            elif fighter_index == "red":
                temp_red_frame = temp_red_frame.append(s)

    # Adding fighter details like height, weight, reach, stance and dob
    fighter_details = pd.read_csv(FIGHTER_DETAILS, index_col="fighter_name")
    fighter_details = fighter_details[fighter_details.index.isin(fighters)]

    def convert_to_cms(X):
        if X is np.NaN:
            return X
        elif len(X.split("'")) == 2:
            feet = float(X.split("'")[0])
            inches = int(X.split("'")[1].replace(" ", "").replace('"', ""))
            return (feet * 30.48) + (inches * 2.54)
        else:
            return float(X.replace('"', "")) * 2.54

    fighter_details["Height_cms"] = fighter_details["Height"].apply(convert_to_cms)
    fighter_details["Reach_cms"] = fighter_details["Reach"].apply(convert_to_cms)

    fighter_details["Weight_lbs"] = fighter_details["Weight"].apply(
        lambda X: float(X.replace(" lbs.", "")) if X is not np.NaN else X
    )

    fighter_details.drop(["Height", "Weight", "Reach"], axis=1, inplace=True)

    fighter_details.reset_index(inplace=True)
    temp_red_frame.reset_index(inplace=True)
    temp_blue_frame.reset_index(inplace=True)

    temp_blue_frame = temp_blue_frame.merge(
        fighter_details, left_on="hero_fighter", right_on="fighter_name", how="left"
    )
    temp_blue_frame.set_index("index", inplace=True)

    temp_red_frame = temp_red_frame.merge(
        fighter_details, left_on="hero_fighter", right_on="fighter_name", how="left"
    )
    temp_red_frame.set_index("index", inplace=True)

    temp_blue_frame.drop("fighter_name", axis=1, inplace=True)
    temp_red_frame.drop("fighter_name", axis=1, inplace=True)

    blue_frame = temp_blue_frame.add_prefix("B_")
    red_frame = temp_red_frame.add_prefix("R_")

    frame = blue_frame.join(red_frame, how="outer")

    rename_cols = {}
    for col in frame.columns:
        if "hero" in col:
            rename_cols[col] = col.replace("_hero_", "_avg_").replace(".", "")
        if "opp" in col:
            rename_cols[col] = col.replace("_opp_", "_avg_opp_").replace(".", "")
        if "win_by" in col:
            rename_cols[col] = col.replace(" ", "").replace("-", "_").replace("'s", "_")

    frame.rename(rename_cols, axis="columns", inplace=True)
    frame.drop(["R_avg_fighter", "B_avg_fighter"], axis=1, inplace=True)
    df2 = df2.join(frame, how="outer")

    # Create Age
    df2["R_DOB"] = pd.to_datetime(df2["R_DOB"])
    df2["B_DOB"] = pd.to_datetime(df2["B_DOB"])
    df2["date"] = pd.to_datetime(df2["date"])

    def get_age(row):
        B_age = (row["date"] - row["B_DOB"]).days
        R_age = (row["date"] - row["R_DOB"]).days
        if np.isnan(B_age) != True:
            B_age = math.floor(B_age / 365.25)
        if np.isnan(R_age) != True:
            R_age = math.floor(R_age / 365.25)
        return pd.Series([B_age, R_age], index=["B_age", "R_age"])

    df2[["B_age", "R_age"]] = df2[["date", "R_DOB", "B_DOB"]].apply(get_age, axis=1)

    df2.drop(["R_DOB", "B_DOB"], axis=1, inplace=True)

    # Dealing with NaNs

    df2["R_Reach_cms"].fillna(df2["R_Height_cms"], inplace=True)
    df2["B_Reach_cms"].fillna(df2["B_Height_cms"], inplace=True)
    df2.fillna(df2.median(), inplace=True)

    df2["R_Stance"].fillna("Orthodox", inplace=True)
    df2["B_Stance"].fillna("Orthodox", inplace=True)

    # One hot encoding important columns
    df2 = pd.concat(
        [df2, pd.get_dummies(df2[["weight_class", "B_Stance", "R_Stance"]])], axis=1
    )

    # Removing non essential columns
    df2.drop(df2.index[df2["Winner"] == "Draw"], inplace=True)
    df2.drop(
        columns=[
            "location",
            "date",
            "R_fighter",
            "B_fighter",
            "Referee",
            "weight_class",
            "B_Stance",
            "R_Stance",
        ],
        inplace=True,
    )

    df2.to_csv(PREPROCESSED_DATA, index=False)

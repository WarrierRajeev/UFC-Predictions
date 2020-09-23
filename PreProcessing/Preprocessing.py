from PreProcessing.PreProcessFighterData import ProcessFighterDetail
from pathlib import Path
import pandas as pd
import numpy as np
import math
import os


class Preprocessing:


    def __init__(self):

        self.BASE_PATH  = Path(os.getcwd())

        print('Reading Files')
        self.Read_files()

        print('Renaming Columns')
        self.Rename_Columns()
        self.ReplacingWinnerNansDraw()

        print('Converting Percentages to Fractions')
        self.ConvertPercentagesToFractions()
        self.CreateTitleBoutFeature()
        self.CreateWeightClasses()
        self.ConvertToSeconds()
        self.GetTotalTimeFought()
        self.StoreCompiledFighterDataInAnotherDF()
        self.CreateWinnerFeature()
        self.CreateFighterAttributes()
        self.CreateFighterAge()
        self.save(filename='data/data.csv')

        print('Fill NaNs')
        self.FillNas()
        print('Dropping Non Essential Columns')
        self.DropNonEssentialCols()
        self.save(filename='data/preprocessed_data.csv')
        print('Saved File')

        
    def Read_files(self):

        try:
            self.fights = pd.read_csv(self.BASE_PATH/'data/total_fight_data.csv', sep=';')
        
        except:
            raise FileNotFoundError('Cannot find the data/total_fight_data.csv')

        try:
            self.fighter_details = pd.read_csv(self.BASE_PATH/'data/fighter_details.csv', index_col='fighter_name')
        
        except:
            raise FileNotFoundError('Cannot find the data/fighter_details.csv')



    def Rename_Columns(self):

        columns = ['R_SIG_STR.', 'B_SIG_STR.', 'R_TOTAL_STR.', 'B_TOTAL_STR.', 'R_TD', 'B_TD',
        'R_HEAD', 'B_HEAD', 'R_BODY','B_BODY', 'R_LEG', 'B_LEG', 'R_DISTANCE', 'B_DISTANCE',
        'R_CLINCH','B_CLINCH', 'R_GROUND', 'B_GROUND']

        attempt_suffix = '_att'
        landed_suffix = '_landed'

        for column in columns:
            self.fights[column+attempt_suffix] = self.fights[column].apply(lambda X: int(X.split('of')[1]))
            self.fights[column+landed_suffix]  = self.fights[column].apply(lambda X: int(X.split('of')[0]))
    
        self.fights.drop(columns, axis=1, inplace=True)


    def ReplacingWinnerNansDraw(self):
        self.fights['Winner'].fillna('Draw', inplace=True)


    def ConvertPercentagesToFractions(self):
        pct_columns = ['R_SIG_STR_pct','B_SIG_STR_pct', 'R_TD_pct', 'B_TD_pct']

        for column in pct_columns: 
            self.fights[column] = self.fights[column].apply(lambda X: float(X.replace('%', ''))/100)


    def CreateTitleBoutFeature(self):
        self.fights['title_bout'] = self.fights['Fight_type'].apply(lambda X: True if 'Title Bout' in X else False)


    @staticmethod
    def make_weight_class(X):

        weight_classes = ['Women\'s Strawweight', 'Women\'s Bantamweight', 
                  'Women\'s Featherweight', 'Women\'s Flyweight', 'Lightweight', 
                  'Welterweight', 'Middleweight','Light Heavyweight', 
                  'Heavyweight', 'Featherweight','Bantamweight', 'Flyweight', 'Open Weight']

        for weight_class in weight_classes:

            if weight_class in X:
                return weight_class

        if X == 'Catch Weight Bout' or 'Catchweight Bout':
            
            return 'Catch Weight'
        else:
            return 'Open Weight'

    
    def CreateWeightClasses(self):
        self.fights['weight_class'] = self.fights['Fight_type'].apply(self.make_weight_class)



    def ConvertToSeconds(self):
        # Converting to seconds
        self.fights['last_round_time'] = self.fights['last_round_time'].apply(lambda X: int(X.split(':')[0])*60 + int(X.split(':')[1]))



    def get_total_time(self, row):

        if row['Format'] in self.time_in_first_round.keys():
            return (row['last_round'] - 1) * self.time_in_first_round[row['Format']] + row['last_round_time']

        elif row['Format'] in self.exception_format_time.keys():

            if (row['last_round'] - 1) >= 2:
                return self.exception_format_time[row['Format']][0] + (row['last_round'] - 2) * \
                        self.exception_format_time[row['Format']][1] + row['last_round_time']
            else:
                return (row['last_round'] - 1) * self.exception_format_time[row['Format']][0] + row['last_round_time']

       
    
    def GetTotalTimeFought(self):

        # '1 Rnd + 2OT (15-3-3)' and '1 Rnd + 2OT (24-3-3)' is not included because it has 3 uneven timed rounds. 
        # We'll have to deal with it separately

        self.time_in_first_round = {'3 Rnd (5-5-5)': 5*60, '5 Rnd (5-5-5-5-5)': 5*60, '1 Rnd + OT (12-3)': 12*60,
       'No Time Limit': 1, '3 Rnd + OT (5-5-5-5)': 5*60, '1 Rnd (20)': 1*20,
       '2 Rnd (5-5)': 5*60, '1 Rnd (15)': 15*60, '1 Rnd (10)': 10*60,
       '1 Rnd (12)':12*60, '1 Rnd + OT (30-5)': 30*60, '1 Rnd (18)': 18*60, '1 Rnd + OT (15-3)': 15*60,
       '1 Rnd (30)': 30*60, '1 Rnd + OT (31-5)': 31*5,
       '1 Rnd + OT (27-3)': 27*60, '1 Rnd + OT (30-3)': 30*60}

        self.exception_format_time = {'1 Rnd + 2OT (15-3-3)': [15*60, 3*60], '1 Rnd + 2OT (24-3-3)': [24*60, 3*60]}

        self.fights['total_time_fought(seconds)'] = self.fights.apply(self.get_total_time, axis=1)
        self.fights.drop(['Format', 'Fight_type', 'last_round_time'], axis = 1, inplace=True)


    def StoreCompiledFighterDataInAnotherDF(self):

        self.store = self.fights.copy()
        self.store.drop(['R_KD', 'B_KD', 'R_SIG_STR_pct', 'B_SIG_STR_pct', 'R_TD_pct', 'B_TD_pct', 
        'R_SUB_ATT', 'B_SUB_ATT', 'R_PASS', 'B_PASS', 'R_REV', 'B_REV', 'win_by', 'last_round', 
        'R_SIG_STR._att', 'R_SIG_STR._landed','B_SIG_STR._att', 'B_SIG_STR._landed', 'R_TOTAL_STR._att',
        'R_TOTAL_STR._landed', 'B_TOTAL_STR._att', 'B_TOTAL_STR._landed','R_TD_att', 'R_TD_landed',
        'B_TD_att', 'B_TD_landed', 'R_HEAD_att', 'R_HEAD_landed', 'B_HEAD_att', 'B_HEAD_landed', 'R_BODY_att',
        'R_BODY_landed', 'B_BODY_att', 'B_BODY_landed', 'R_LEG_att','R_LEG_landed', 'B_LEG_att', 'B_LEG_landed',
        'R_DISTANCE_att','R_DISTANCE_landed', 'B_DISTANCE_att', 'B_DISTANCE_landed','R_CLINCH_att', 'R_CLINCH_landed',
        'B_CLINCH_att', 'B_CLINCH_landed','R_GROUND_att', 'R_GROUND_landed', 'B_GROUND_att', 'B_GROUND_landed',
        'total_time_fought(seconds)'], axis = 1, inplace=True)

    
    @staticmethod
    def get_renamed_winner(row):

        if row['R_fighter'] == row['Winner']:return 'Red'

        elif row['B_fighter'] == row['Winner']:return 'Blue'

        elif row['Winner'] == 'Draw':return 'Draw'


    def CreateWinnerFeature(self):
        self.store['Winner'] = self.store[['R_fighter', 'B_fighter', 'Winner']].apply(self.get_renamed_winner, axis=1)


    def CreateFighterAttributes(self):
        frame = ProcessFighterDetail(self.fights, self.fighter_details).frame
        self.store = self.store.join(frame, how='outer')

    
    @staticmethod
    def get_age(row):

        B_age = (row['date'] - row['B_DOB']).days
        R_age = (row['date'] - row['R_DOB']).days

        if np.isnan(B_age)!=True:
            B_age = math.floor(B_age/365.25)

        if np.isnan(R_age)!=True:
            R_age = math.floor(R_age/365.25)

        return pd.Series([B_age, R_age], index=['B_age', 'R_age'])


    def CreateFighterAge(self):

        self.store['R_DOB'] = pd.to_datetime(self.store['R_DOB'])
        self.store['B_DOB'] = pd.to_datetime(self.store['B_DOB'])
        self.store['date'] = pd.to_datetime(self.store['date'])

        self.store[['B_age', 'R_age']]= self.store[['date', 'R_DOB', 'B_DOB']].apply(self.get_age, axis=1)
        self.store.drop(['R_DOB', 'B_DOB'], axis=1, inplace=True)


    def save(self, filename):
        self.store.to_csv(self.BASE_PATH/filename, index=False)


    def FillNas(self):

        self.store['R_Reach_cms'].fillna(self.store['R_Height_cms'], inplace=True)
        self.store['B_Reach_cms'].fillna(self.store['B_Height_cms'], inplace=True)
        self.store.fillna(self.store.median(), inplace=True)

        self.store['R_Stance'].fillna('Orthodox', inplace=True)
        self.store['B_Stance'].fillna('Orthodox', inplace=True)


    def DropNonEssentialCols(self):

        self.store.drop(self.store.index[self.store['Winner'] == 'Draw'], inplace = True)
        self.store = pd.concat([self.store, pd.get_dummies(self.store[['weight_class', 'B_Stance', 'R_Stance']])], axis=1)
        self.store.drop(columns=['weight_class', 'B_Stance', 'R_Stance', 'Referee',
                                'location', 'date', 'R_fighter', 'B_fighter'], inplace=True)

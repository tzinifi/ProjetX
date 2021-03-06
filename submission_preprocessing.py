import pandas as pd
from configuration import CONFIG
import numpy as np
import datetime as dt
import logging
logging.basicConfig(filename='log_27112016_2.txt', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def find_day(day):             #Transforme les jours de la semaine en int compris entre 0 et 1
    if (day == "Dimanche"):
        return 0
    if (day == "Lundi"):
        return 1
    if (day == "Mardi"):
        return 2
    if (day == "Mercredi"):
        return 3
    if (day == "Jeudi"):
        return 4
    if (day == "Vendredi"):
        return 5
    if (day == "Samedi"):
        return 6

def hourlymean_past(date, y):
    
    nday_before = 7
    ysel = y.loc[(y.index > date - dt.timedelta(nday_before))]
    ysel = ysel.loc[(ysel.index < date)]
    logging.debug(date,ysel['TIME','CSPL_RECEIVED_CALLS'].head(n=5))
    h = extract_hour(date)
    if (len(ysel.loc[ysel.loc[:,'TIME'] == h]) < 0):
        return(0)
    else:
        return(ysel.loc[ysel.loc[:,'TIME'] == h].loc[:,"CSPL_RECEIVED_CALLS"].mean())

def extract_date(string):
    d = dt.datetime.strptime(string, "%Y-%m-%d %H:%M:%S.000")
    return(d)

def extract_weekday(date):
    return(date.weekday())

def extract_hour(date):
    return(date.hour)

def extract_month(date):
    return(date.month)

def extract_year(date):
    return(date.year)

def extract_min(date):
    return(date.hour*60+date.minute)
    
class submission_preprocessing():
    
    def __init__(self, filename = None, sepa = None):
        if filename == None and sepa == None:
            self.data = pd.DataFrame()
        else:
            self.data = pd.read_csv(filename, sep=sepa)

    def ass_id_creation(self): # Create ASS_ID (int between 0 and 28) from ASS_ASSIGNMENT as defined in configuration.py
        self.data['ASS_ID'] = self.data['ASS_ASSIGNMENT'].apply(lambda x: int(CONFIG.ass_assign[x]))
    
    def select_assid(self, assid):
        self.data=self.data.loc[self.data['ASS_ID'] == assid]
        self.data.drop('ASS_ID',axis = 1, inplace = True)
        self.data=self.data.groupby(['DATE']).sum()
        self.data.reset_index(inplace = True)
    
    def preprocess_date(self):
        self.data['DATE'] = self.data["DATE"].apply(extract_date)
    
    def date_vector(self):
        self.data['YEAR'] = self.data['DATE'].apply(extract_year)
        for year in ['2011','2012','2013']:
            self.data[year] = self.data['YEAR'].apply(lambda x: (int(year) == x)*1)
        
        self.data['MONTH'] = self.data['DATE'].apply(extract_month)
        for key, month in CONFIG.months.items():
            self.data[month] = self.data['MONTH'].apply(lambda x: int(x == key))
        
        self.data['TIME']= self.data['DATE'].apply(extract_min)
        self.data['SLOT'] = self.data['TIME'].apply(lambda x: (x in range(450,1411))*(x-450)/30 + (x in range(0,451))*(x/30+1) + (x in range(1411,1441))*0)
#        self.data['YEAR_DAY']= self.data['DATE'].apply(extract_weekday)
        self.data['WEEK_DAY'] = self.data['DATE'].apply(extract_weekday)
    
    
    def lastvalue(self,date):
        temp = self.data[self.data.loc[[date-dt.timedelta(days=ndays) for ndays in [7,14,21,28]]]].as_matrix()
        for key in [7,14,21,28]:
            self.data[date, 'before'+str(key)] = temp
    
    
    
    def hourlymean_past(self, weeks):
        
        self.data['MEAN'+str(weeks)]=[0]*self.data.shape[0]
        
        for k in range(1,weeks+1):
            self.lastvalue(k*7)
            self.data['MEAN'+str(weeks)]=self.data['MEAN'+str(weeks)]+ self.data['before' + str(k*7)]
        
        
        self.data['MEAN'+str(weeks)] = self.data['MEAN'+str(weeks)]/weeks

    def valeur_max(self):
        self.data['MAX'] = np.maximum.reduce([self.data['before7'], self.data['before14'], self.data['before21'], self.data['before28'], self.data['before35']])
    
    
    
    def jour_nuit_creation(self):  #Création de la feature jour nuit
        
        jour = []
        nuit = []
        nrows = self.data.shape[0]
#        print(self.data['TIME'])
        for i in range(nrows) :
            if(self.data.ix[i,'TIME'] in range(450,1410,30)):
                jour.append(1)
                nuit.append(0)
            else:
                nuit.append(1)
                jour.append(0)
    
        self.data['JOUR'] = jour
        self.data['NUIT'] = nuit

    def week_day_to_vector(self):  #Création des Features SUNDAY, MONDAY, TUESDAY, etc qui prennent les valeurs 0 ou 1

        for key,day in CONFIG.days.items():
            self.data[day] = self.data['WEEK_DAY'].apply(lambda x: int(x == key))
        self.data.drop('WEEK_DAY', axis = 1, inplace = True)
                
                
    def full_preprocess(self, assid, keep_all_ass_id = False, used_columns=CONFIG.sub_columns, keep_all = False, remove_columns = []):
        self.ass_id_creation()
        if keep_all_ass_id!=True:
            self.select_assid(assid)
        self.preprocess_date()
        self.date_vector()
        self.data.set_index('DATE',inplace = True,verify_integrity = True)
        #        print("Past mean processing...")
        #        self.data['MEAN_PAST'] = self.data.index.map(lambda x : hourlymean_past(x,self.data))
        self.jour_nuit_creation()
        self.week_day_to_vector()
        for date in [dt.datetime(2012,4,1),dt.datetime(2012,4,2)]:
            self.lastvalue(date)
            return (self.data[date])
        self.valeur_max()

        
        if not keep_all:
            print(used_columns)
            self.data = self.data[used_columns]
        else:
            self.data = self.data.drop(remove_columns, axis=1)


if __name__ == "__main__": #execute the code only if the file is executed directly and not imported
    pp = submission_preprocessing('submission.txt','\t')
    pp.full_preprocess(6, keep_all = False)
    print(pp.data.head(n=10))
#    pp.data.to_csv('../data_test1.csv', sep=";")





#print(pp.data.sort_values(by=['CSPL_CALLS'], ascending=[0]))



"""
%(name)s: %(white)s%(asctime)s%(reset)s
^ use to add timestamp to logger
"""
import datetime
import logging
import os
import pickle
import statistics
import timeit
import pandas as pd
import warnings
#import sys
#import colorlog
from functions import newScraper as Sc

warnings.filterwarnings("ignore", category=UserWarning)
# This will ignore all UserWarning warnings in your code.

log = logging.getLogger()
"""stdout = colorlog.StreamHandler(stream=sys.stdout)
fmt = colorlog.ColoredFormatter(
    "%(name)s | %(log_color)s%(levelname)s%(reset)s | %(blue)s%(filename)s:%(lineno)s%"
    "(reset)s | %(process)d >>> %(log_color)s%(message)s%(reset)s"
)

stdout.setFormatter(fmt)
log.addHandler(stdout)"""
log.setLevel(logging.DEBUG)

sheet_data = pd.DataFrame

site = "https://progress.getcircuit.com/?user=ZdPO85SjmDRniyPjtVk4K3er44m2&route=B443C144-CDB2-468B-A1F0-046D1B18580E&displayName=Max+Julian"


class Sheet:
    pass
    """BEGIN STATIC METHODS"""

    # default values are for testing within class
    @staticmethod
    def __import_master_sheet(loc: str = '../src/delivery.xlsx') -> 'pd.DataFrame()':
        """
        Imports main reporting sheet from Excel file

        :param loc: String value of path provided by file dialog
        :return: pandas.DataFrame() object with only necessary columns for reporting
        """
        log.info("Beginning Master Sheet Import")

        def check_headers(headers: list) -> bool:
            expected_headers = ['MAP', 'NUM', 'STREET', 'FULL ADDRESS', 'CITY', 'STATE', 'CBSA', 'ZIP', 'Visited',
                                'Date', 'Notes']
            for c, i in enumerate(headers):
                if i != expected_headers[c]:
                    log.error(f"Expected header: {expected_headers[c]}, got {i}")
                    return False
            return True

        def reformat_dates(d):
            if d != "" and type(d) == str:
                dt = datetime.datetime
                up = dt.strptime(d, "%Y-%m-%d %H:%M:%S")
                return up.strftime('%m/%d/%Y')

        try:
            global sheet_data
            sheet = pd.read_excel(loc, sheet_name='REFERRAL LIST', index_col=False,
                                  converters={'NUM': int, 'Date': str})
        except:
            log.error("Master Sheet Empty")
            log.exception("Location: sheet_manager.import_master_sheet")
            return pd.DataFrame()
        else:
            clms = sheet.columns
            sheet['Date'] = sheet['Date'].apply(reformat_dates)
            sheet.fillna("", inplace=True)
            if sheet.columns[5] != 'FULL ADDRESS':
                sheet.rename(columns={sheet.columns[5]: 'FULL ADDRESS'}, inplace=True)
            sheet.drop(columns=[clms[0], clms[4], clms[10], clms[11], clms[12], clms[13],
                                clms[14], clms[18], clms[19]], inplace=True)
            sheet = sheet.iloc[:, :11]
            log.debug(f'Master Sheet Length: {len(sheet)}')
            if check_headers(sheet.columns.to_list()):
                # Structure = Maps[0], House#[1], Street[2], FullAddr[3], City[4], State[5], CBSA[6], ZIP[7],
                #             Visited[8], Date[9], Notes[10]
                return sheet
            else:
                raise ValueError("Bad headers @ sheet_manager.__import_master_list")

    # default values are for testing within class
    def __import_report_sheet(self, loc: str = 'src/report.csv', mode: int = 0) -> 'tuple':
        """
        Imports Delivery report from Circuit link as a tuple containing the name of the route
        and a pd.Dataframe representing the results of the route

        :param loc: Link to website as String
        :param mode: 0 (default) = for testing, 1 = normal operation
        :return: tuple with len(2)
        """
        expected_headers = ['MAP', 'NUM', 'STREET', 'FULL ADDRESS', 'CITY', 'STATE', 'CBSA', 'ZIP', 'Visited',
                            'Date', 'Notes']

        if mode == 0:  # used for testing, will pull default data
            sheet_report = pd.read_csv(loc)
            mer = pd.merge(self.master, sheet_report, how='inner', on=['NUM', 'STREET', 'FULL ADDRESS'],
                           suffixes=('_Master', None))
            if len(mer) != 0:
                log.info(mer.columns.to_list())
                mer.drop(columns=['Visited_Master', 'Date_Master', 'Notes_Master', 'MAP', 'CITY', 'STATE', 'CBSA',
                                  'ZIP'], inplace=True)
                mer.rename(columns={'MAP_Master': 'MAP', 'CITY_Master': 'CITY', 'STATE_Master': 'STATE',
                                    'CBSA_Master': 'CBSA', 'ZIP_Master': 'ZIP'}, inplace=True)
                mer.sort_values(by=['Date', 'MAP', 'STREET', 'NUM'], axis=0, ascending=[False, True, True, True],
                                ignore_index=True, kind='quicksort', na_position='first', key=None, inplace=True)
                sheet_report = mer.fillna("")
                if mer.columns.to_list() != expected_headers:
                    raise ValueError("Bad Report Headers @ sheet_manager.Sheet.__import_report_sheet ")
            else:
                raise ValueError("Length of Merged List Cannot Be 0 \n Probably"
                                 "caused by mismatched reports \n @ sheet_manager.Sheet.__import_report_sheet")

            return "Test Report", sheet_report

        elif mode == 1:
            sc = Sc.Scraper(loc)
            sheet_report = sc.requestDataframe()
            mer = pd.merge(self.master, sheet_report[1], how='inner', on=['NUM', 'STREET', 'FULL ADDRESS'],
                           suffixes=('_Master', None))
            if len(mer) != 0:
                mer.drop(columns=['Visited_Master', 'Date_Master', 'Notes_Master', 'CITY'], inplace=True)
                mer.rename(columns={'CITY_Master': 'CITY'}, inplace=True)
                mer.sort_values(by=['Date', 'MAP', 'STREET', 'NUM'], axis=0, ascending=[False, True, True, True],
                                ignore_index=True, kind='quicksort', na_position='first', key=None, inplace=True)
                sheet_report = (sheet_report[0], mer.fillna(""))

                if mer.columns.to_list() != expected_headers:
                    raise ValueError("Bad Report Headers @ sheet_manager.Sheet.__import_report_sheet ")
                for i in self.reports:
                    if mer.equals(i[1]):
                        raise ValueError("Duplicate Sheet")
            else:
                raise ValueError("Length of Merged List Cannot Be 0 \n Probably"
                                 "caused by mismatched reports \n @ sheet_manager.Sheet.__import_report_sheet")

            return sheet_report


    """END STATIC METHODS"""

    """BEGIN MASTER SHEET METHODS"""

    def __get_total_delivered(self):
        cols = self.master.columns
        del_count = 0
        for index, value in pd.DataFrame(self.master).iterrows():
            if self.master.iloc[index][8] != "":
                if self.master.iloc[index][9] != "":
                    del_count += 1
                else:
                    log.debug(f'Row {index} has Visited tag: {self.master.iloc[index][8]} but no Date')
        self.delivered = del_count

    def __get_maps(self, col):
        self.maps = self.master.iloc[:, 0].unique()

    def __get_used_maps(self, col=None):
        if col is None:
            col = list()
        adjacent_rows = []
        df = self.master
        for value in self.maps:
            adjacent_rows.extend(df[(df.iloc[:, 0] == value) | (df.iloc[:, 0].shift(-1) == value)].index)

        if df.iloc[adjacent_rows, 7:9].any().any():
            # log.info("Adjacent rows with value in the 8th or 9th column exist.")
            r: pd.Series = df.iloc[adjacent_rows, 0]
            self.usedMaps = r.unique()
        else:
            log.error("No adjacent rows with value in the 8th or 9th column. loc: sm.Sheet.__get_used_maps()")
            self.usedMaps = list()

    def get_remaining(self):
        """convenience method, does math for me"""
        return len(self.master) - self.delivered

    def del_today(self):
        """convenience method for today's date, needs to run in multiprocess thread"""
        col = self.master.columns
        dt = datetime.date.today()
        txt = dt.strftime('%m/%d/%Y')
        return self.get_del_by_day(txt)

    def get_del_by_day(self, date):
        """ Possibly needs to run in multiprocess thread

        :param date: requested date as string
        :return: int value containing amount delivered on given date
        """
        count = 0
        cols = self.master.columns
        for i in self.master[cols[9]]:
            if i == date:
                count += 1
        return count

    def del_avg(self, days, date):
        dt = datetime.datetime.strptime(date, "%m/%d/%Y")
        countByDay = list()
        for day in range(days):
            d = dt - datetime.timedelta(days=day)
            txt = d.strftime('%m/%d/%Y')
            count = self.get_del_by_day(txt)
            countByDay.append(count)
        return round(statistics.mean(countByDay), 2)

    def __main_stats(self):
        """loads relevant stats to sheet"""
        col = self.master.columns
        self.__get_total_delivered()
        self.__get_maps(col)
        self.__get_used_maps(col)
        self._7day = self.del_avg(7, self.get_last_delivered_date())
        self.length = len(self.master)

    def update_master(self, index: int, overwrite: bool = False, test: bool = False):
        m: pd.DataFrame = self.master
        r = self.reports[index][1]
        columns_to_update = ['Visited', 'Date', 'Notes']

        # Merge the master table with the report table based on the 'FULL ADDRESS' column
        mer = m.merge(r, on='FULL ADDRESS', how='left', suffixes=('', '_update'))

        log.info(mer.columns.to_list())

        if not mer.equals(m):
            for column in columns_to_update:
                mer[column] = mer[column + '_update'].fillna(mer[column])

            master_columns = m.columns.to_list()
            master_columns.pop(3)
            # Drop the columns from the merge operation that are not needed in the master table
            mer.drop(columns=[column + '_update' for column in master_columns], inplace=True)

            log.info(mer.columns.to_list())

            if overwrite:
                self.master = mer

            start_address = r.iloc[0, 3]
            end_address = r.iloc[-1, 3]
            log.info(f'\nStarting Address {start_address}\nEnding Address: {end_address}')

            # Find the index of the first and last address in the main DataFrame
            first_index = m[m.iloc[:, 3] == start_address].index[0]
            last_index = m[m.iloc[:, 3] == end_address].index[-1]
            log.info(f'\nStarting Address index: {first_index}\n Ending Index: {last_index}')

            # Create a new DataFrame from the range of indices
            updateRpt: pd.DataFrame = self.master.iloc[first_index:last_index].copy()
            if self.updateReport is None:
                self.updateReport = updateRpt
            else:
                self.updateReport = pd.concat([self.updateReport, updateRpt]).drop_duplicates(subset=['FULL ADDRESS',
                                                                                              'CITY'])
                self.updateReport.sort_values(by=['MAP', 'STREET', 'NUM'], axis=0, ascending=[True, True, True],
                                              ignore_index=True, kind='quicksort', na_position='first', key=None,
                                              inplace=True)
            if not test:
                self.__main_stats()

        else:
            log.warning("No new info detected in this report")
        # Update the specified columns in the master table with the values from the report table

    def get_last_delivered_date(self):
        #log.info(self.master['Date'].info())
        frame = pd.DataFrame(self.master).sort_values(by=['Date'], axis=0, ascending=[False],
                                                        kind='quicksort', na_position='first', ignore_index=True, key=None)
        return frame['Date'][0]

    """END MASTER SHEET METHODS"""

    """BEGIN REPORT METHODS"""

    def import_report(self, link="", test: bool = False):
        """
        Returns a tuple containing the name of the route and a dataframe containing the results
        of the route
        :param link: the circuit link (https://progress.getcircuit.com/...
        :param test: used for testing
        :return: tuple with len(2)
        """

        log.info("Starting Report Import")
        if test:
            route = self.__import_report_sheet(mode=0)
        else:
            route = self.__import_report_sheet(link, 1)

        report = route[1]

        if len(self.reports) < 10:
            self.reports.append((route[0], report))
        else:
            log.warning("For memory/display purposes, len(routes) !> 10, removing first index")
            self.reports.pop(-1)
            self.reports.append((route[0], report))

        log.info("Import Complete")


    def export_report_csv(self, index, path):
        self.reports[index][1].to_csv(f'{path}/{self.reports[index][0]}.csv', index=False)
        log.info("Exported Report")

    def merge_loaded_reports(self):
        names = []
        reports = []
        unusual_entries = []  # List to store unusual entries
        for i in self.reports:
            names.append(i[0])
            reports.append(i[1])
        fullFrame = pd.concat(reports, axis=0)
        fullFrame.drop_duplicates(subset='FULL ADDRESS', inplace=True)
        fullFrame.sort_values(by=['Date', 'MAP', 'STREET', 'NUM'], axis=0, ascending=[False, True, True, True],
                              ignore_index=True, kind='quicksort', na_position='first', key=None, inplace=True)

        unique_numbers = set()
        parts = ""
        prefix = "CA Map"  # Default prefix
        unusual = False
        if len(names) > 0:
            first_name_parts = names[0].split(" ")[:2]
            prefix = " ".join(first_name_parts)

        for name in names:
            parts = name.split(" ")
            if len(parts) >= 2 and ('-' in name or '_' in name):
                if '-' in name:
                    numbers = name.split(" ")[-1].split("-")
                else:  # '_' separator
                    numbers = name.split(" ")[-1].split("_")
                unique_numbers.update(numbers)
            else:
                log.warning("Unusual Name Found")
                unusual_entries.append(f"{parts[2]}")  # Store the third part of the unusual entry

        if len(parts) >= 3:
            concat_nums = "-".join(sorted(unique_numbers))
            unusual_parts = "-".join(unusual_entries)  # Join the unusual entries using '_'
            if unusual_parts == '':
                newName = f'{prefix} {concat_nums}'
            else:
                newName = f"{prefix} {concat_nums}_{unusual_parts}"
        else:
            newName = f"{prefix} {parts[2]}"
        self.reports.clear()
        self.reports.append((newName, fullFrame))

    """END REPORT METHODS"""

    def __init__(self, path=""):
        self.updateReport = None
        if path !="":
            self.master = self.__import_master_sheet(path)
        else:
            self.master = self.__import_master_sheet(loc='src/delivery.xlsx')
        log.info("Sheet Initialized")
        start = timeit.default_timer()
        self.reports = list()
        self.maps = None
        self.usedMaps = None
        self.delivered = 0
        self._7day = 0
        self.__main_stats()
        end = timeit.default_timer()
        log.info(f"Stats Gathered, loading took {end-start} seconds")


def save_object(obj):
    try:
        os.mkdir('data')
    except FileExistsError:
        log.info("Directory Exists, not needed")

    try:
        with open("data/data.pickle", "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    except FileNotFoundError:
        log.exception("Error during pickling object (Possibly unsupported):")


def load_object(filename):
    try:
        with open('data/data.pickle', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        raise FileNotFoundError


def main():
    pass


if __name__ == "__main__":
    # do stuff
    main()

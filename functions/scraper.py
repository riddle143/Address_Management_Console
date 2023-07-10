import logging
import traceback

import pandas as pd
from bs4 import BeautifulSoup

site = "https://progress.getcircuit.com/?user=PE0JWyzicagNpLj93iZ67RBbHod2&route=90A391DE-DAF5-40DD-B7FA-A2C76955B8D6" \
       "&displayName=Zandavious+Whatley"
e = "downshift-0-menu"

logging.basicConfig(level=logging.INFO)


class Scraper:
    @staticmethod
    def __get_data_from_request(link) -> 'bytes':
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(link, timeout=120000)
                page.wait_for_selector(
                    '.CellAtoms__CellWrapper-sc-1u0wwp-0.StopCell___StyledCellWrapper-sc-13i9aak-0.bASAPq.heHSon.group',
                    timeout=120000)
                html = page.content().encode('utf-8')
                page.context.close()
                browser.close()
        except TimeoutError:
            traceback.print_exc()
            raise TimeoutError("Page Timed Out.")
        else:
            return html
        pass

    @staticmethod
    def __build_data_arrays(data, completed) -> 'list, None':
        classes = {
            'Button': ".CellAtoms__CellWrapper-sc-1u0wwp-0.StopCell___StyledCellWrapper-sc-13i9aak-0.kHgkIm.heHSon.group",
            'Address': '.CellAtoms__BasicCellTitle-sc-1u0wwp-5.jXCpQU.StopCell___StyledCellTitle-sc-13i9aak-3.grdeWf',
            'City': '.CellAtoms__BasicCellDescription-sc-1u0wwp-10.eeWZbP.StopCell___StyledCellDescription-sc-13i9aak-4.jHJJmX',
            'Note': '.CellAtoms___StyledSpan-sc-1u0wwp-13.jGWHBN',
            'Confirmed': "M9.00003 16.17L4.83003 12L3.41003 13.41L9.00003 19L21 7L19.59 5.59L9.00003 16.17Z",
            'No Delivery': "M19 6.41L17.59 5L12 10.59L6.41 5L5 6.41L10.59 12L5 17.59L6.41 19L12 13.41L17.59 19L19 17.59L13.41 12L19 6.41Z",
            'Pending': "M6.99423 1.22217C3.8049 1.22217 1.22223 3.81061 1.22223 6.99995C1.22223 10.1893 3.8049 12.7777 6.99423 "
                       "12.7777C10.1893 12.7777 12.7778 10.1893 12.7778 6.99995C12.7778 3.81061 10.1893 1.22217 6.99423 "
                       "1.22217ZM7.00001 11.6222C4.44623 11.6222 2.37778 9.55373 2.37778 6.99996C2.37778 4.44618 4.44623 2.37773 "
                       "7.00001 2.37773C9.55378 2.37773 11.6222 4.44618 11.6222 6.99996C11.6222 9.55373 9.55378 11.6222 7.00001 "
                       "11.6222ZM6.42223 4.11107H7.2889V7.1444L9.8889 8.68707L9.45556 9.39773L6.42223 7.57773V4.11107Z"
        }
        buttonClass = classes['Button']
        addrClass = classes['Address']
        cityClass = classes['City']
        noteClass = classes['Note']
        conf = classes['Confirmed']
        noDel = classes['No Delivery']
        pend = classes['Pending']

        def convert_data():
            logging.info("Beginning Build...")
            # initial loop, populates lists with strings from specified elements
            nonlocal addrs, cities, times, dates, notes, delco
            for s in stops:
                if s.select_one(classes['Address']).text is not None:
                    addrs.append(s.select_one(classes['Address']).text)
                else:
                    addrs.append("Missing")
                if s.select_one(classes['City']).text is not None:
                    cities.append(s.select_one(classes['City']).text)
                else:
                    cities.append("Missing")
                times.append(s.find('time').text)
                dates.append("")
                # checks for missing notes

                if s.select_one(classes['Note']) is not None:
                    notes.append(s.select_one(classes['Note']).text)
                    sym = s.find('path')
                    status = sym.find_next('path')['d']
                else:
                    logging.info("Note is missing")
                    notes.append("Missing")
                    status = s.find('path')['d']

                # assigns status (Delivered?) based on codes as defined
                if status != "":
                    if status == conf:
                        delco.append("Confirmed")
                    elif status == pend:
                        delco.append("Pending")
                    elif status == noDel:
                        delco.append("Undelivered")
                    else:
                        delco.append("Not Started")
                else:
                    delco.append("No Data")

        def addFinal():
            final_button = ".CellAtoms__CellWrapper-sc-1u0wwp-0.StopCell___StyledCellWrapper-sc-13i9aak-0.bASAPq.heHSon.group"
            final_stop = data.select_one(final_button)
            nonlocal addrs, cities, times, dates, delco
            try:
                addrs.append(final_stop.select_one(addrClass).text)
                cities.append(final_stop.select_one(cityClass).text)
                times.append(final_stop.find('time').text)
                dates.append("")
            except AttributeError:
                return logging.exception("Func: __build_data_arrays.addFinal()")

            if final_stop.select_one(noteClass) is not None:
                notes.append(final_stop.select_one(noteClass).text)
                sym = final_stop.find('path')
                status = sym.find_next('path')['d']
            else:
                logging.info("Note is missing")
                notes.append("Missing")
                status = final_stop.find('path')['d']

            if status != "":
                if status == conf:
                    delco.append("Confirmed")
                elif status == pend:
                    delco.append("Pending")
                elif status == noDel:
                    delco.append("Undelivered")
                else:
                    delco.append("Not Started")
            else:
                delco.append("No Data")

        stops = data.css.select(buttonClass)

        addrs = list()
        cities = list()
        times = list()
        dates = list()
        notes = list()
        delco = list()

        if len(stops > 0):
            convert_data()
        else:
            logging.error("Error, 0 Stops Found")
            return None

        # special case conditional due to different class name for final cell, adds final address
        if completed:
            addFinal()

        master = list()  # parent list

        logging.info("Assembling Master List...")

        # packs data neatly into a parent list, and passes data along
        for i in range(len(dates)):
            newStop = (addrs[i], cities[i], times[i], dates[i], notes[i], delco[i])
            # log.info(f"Found new stop @ index {i}: {newStop}")
            if newStop[5] == "Confirmed" or newStop[5] == "Undelivered":
                master.append(newStop)

        logging.info(f"Master List Assembled, length:{len(master)}")

        return master

    @staticmethod
    def __convert_arrays_to_DataFrame(data) -> 'pd.DataFrame':
        if data is not None:
            houseNum = list()
            adr = list()
            city = list()
            time = list()
            date = list()
            notes = list()
            status = list()

            # newData=addDates(data)

            logging.info("Received Data. Converting...")

            for i in data:
                try:
                    parts = i[0].split()
                    if str(parts[0]).isnumeric():
                        no = int(parts[0])
                        parts.pop(0)

                    cityName = ""
                    # if the len of the str at the last index of parts is greater than 5
                    if len(parts[-1]) > 5 and len(parts) > 2:
                        cityName = parts[len(parts) - 1]
                        parts.pop(len(parts) - 1)
                    houseNum.append(no)
                    adr.append(" ".join(parts))
                    if cityName != "":
                        newName = (cityName, i[1])
                        city.append(",".join(newName))
                    else:
                        city.append(i[1])
                    time.append(i[2])
                    date.append(i[3])
                    notes.append(i[4])
                    status.append(i[5])
                except IndexError:
                    logging.warning("Dummy Entry Used")
                    houseNum.append("1234")
                    adr.append("Home Rd")
                    city.append("Liberty City")
                    time.append("00:00 AM")
                    date.append("00/00/00")
                    notes.append("Dummy Entry")
                    status.append("Error")
                    traceback.print_exc()

            dataWithHead = {'House #': houseNum, 'Address': adr, 'City': city, 'Time': time, 'Date': date,
                            'Notes': notes, 'Status': status}

            df = pd.DataFrame(dataWithHead)

            logging.info("DataFrame Assembled")
            return df

        else:
            logging.error("Data is Null, Cancel CSV")

    def __check_if_loaded_info(self) -> 'None':
        try:  # try to find driver's name
            self.route = self.soup.select_one(".PlanTitle___StyledH-sc-1j4cj25-0.gmUykI").text
            try:
                self.driverName = self.soup.select_one(
                    ".CellAtoms__BasicCellTitle-sc-1u0wwp-5.jXCpQU.FocusedDriver___StyledCellTitle-sc"
                    "-v6hs6q-4.hkgkOW"
                ).text
            except:
                logging.info("Driver Name not Found")
                traceback.print_exc()
        except:
            traceback.print_exc()
            self.loaded = False
        else:
            self.info = (self.driverName, self.route)
            self.loaded = True

    def __check_if_list_completed(self) -> 'bool':
        statusElement = self.soup.select_one(".CellAtoms__BasicCellDescription-sc-1u0wwp-10.eeWZbP")
        statusText = statusElement.find('span').contents
        if statusText[0] == "Finished ":
            listCompleted = True
        else:
            listCompleted = False

        return listCompleted


    def test(self):
        pass
    def getDataFrame(self) -> 'pd.DataFrame':
        if self.loaded:
            self.dataFrame = self.__convert_arrays_to_DataFrame(self.__build_data_arrays(self.soup.find(id=e), self.completed))
            return self.dataFrame
        else:
            raise InterruptedError("Scraper.loaded = False")
            # handle place

    def exportCSV(self):
        # export_CSV(self.dataFrame)
        pass

    def getRouteInfo(self) -> 'str':
        if self.loaded:
            return self.route
        else:
            return "No Route"

    def __init__(self, link=site):
        self.dataFrame = None
        self.driverName = ""
        self.route = ""
        self.info = list()
        self.loaded = ""

        try:
            html = self.__get_data_from_request(link)
        except TimeoutError:
            logging.exception("HTML has no Value due to Timeout")
            self.loaded = False
        else:
            self.soup = BeautifulSoup(html, 'html.parser')
            self.__check_if_loaded_info()
            self.completed = self.__check_if_list_completed()


def main():
    a = Scraper()
    print(a.getDataFrame())


if __name__ == '__main__':
    main()

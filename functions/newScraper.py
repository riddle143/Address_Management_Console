import json
import logging
import os
import re
import time
from datetime import date, datetime
import pandas as pd
import playwright
from haralyzer import HarParser
from playwright.sync_api import sync_playwright

# @@@!!!enable these imports for class testing!!!@@@
# import sys
# import colorlog
# import traceback


site = "https://progress.getcircuit.com/?user=PE0JWyzicagNpLj93iZ67RBbHod2&route=90A391DE-DAF5-40DD-B7FA-A2C76955B8D6" \
       "&displayName=Zandavious+Whatley"

log = logging.getLogger()
"""stdout = colorlog.StreamHandler(stream=sys.stdout)
fmt = colorlog.ColoredFormatter(
    "%(name)s | %(log_color)s%(levelname)s%(reset)s | %(blue)s%(filename)s:%(lineno)s%"
    "(reset)s | %(process)d >>> %(log_color)s%(message)s%(reset)s"
)

stdout.setFormatter(fmt)
log.addHandler(stdout)"""
log.setLevel(logging.INFO)


class Scraper(object):

    @staticmethod
    def __request_data(link: str):
        # set_debug(True)

        uri = "https://firestore.googleapis.com/google.firestore.v1.Firestore/Listen/channel?database=projects" \
              "%2Fcircuit-test-project%2Fdatabases%2F(default)&g"

        rightResponse = playwright.sync_api.Response
        counter = 0

        def handleResponse(u: playwright.sync_api.Response):
            nonlocal rightResponse, counter
            counter += 1
            if u.url.startswith(uri):
                log.info(f"Response Ping: {counter}")
                rightResponse = u

        log.debug("handleResponse Defined")

        try:
            log.debug("Trying sync_playwright")
            with sync_playwright() as p:
                log.debug("Launching Browser")
                browser = p.chromium.launch(headless=True)
                log.debug("Browser Launched")
                page = browser.new_page(record_har_path="tmp/site.har")
                log.debug("New Page Set")
                page.set_default_timeout(90000)
                page.on('response', handleResponse)
                log.debug("Time out 1 set")
                page.goto(link)
                log.info(f"Page at {link} opened, recording traffic")
                page.wait_for_selector(
                    '.CellAtoms__CellWrapper-sc-1u0wwp-0.StopCell___StyledCellWrapper-sc-13i9aak-0.bASAPq.heHSon.group',
                    timeout=120000)

                for i in range(90):
                    time.sleep(1)
                    log.debug(f'Waiting... {i - 90} seconds remaining')

                # noinspection PyArgumentList
                rightResponse.finished()
                page.wait_for_timeout(10000)
                log.info(".har file generated")

                page.context.close()
                browser.close()
        except TimeoutError:
            raise TimeoutError("Page Timed Out.")
        except playwright.sync_api.Error:
            log.exception("Issue with playwright, investigate further in newScraper.Scraper.__request_data()")
            raise InterruptedError("Playwright Error, are you connected to the internet?")


    @staticmethod
    def __analyze_har():
        log.info("Beginning Parse")
        file_path = "tmp/site.har"
        with open(file_path, 'r', encoding='utf8') as f:
            har_parser = HarParser(json.loads(f.read()))
            har_page = har_parser.pages[0]
            entries = har_page.entries
        index = 0
        for i, r in enumerate(entries):
            if r.url.startswith("https://firestore.googleapis.com"):
                try:
                    if len(str(r.response.text)) > 100000:
                        index = i
                except KeyError:
                    log.warning("Key Error @ newScraper.Scraper.__analyze_har()")
        entry = entries[index].response

        starter = entry.text[7:]
        pattern = r"]\d{2,6}\s+\["
        newText = re.sub(pattern, ", \n", starter)

        try:
            os.remove(file_path)
            log.info(f"File '{file_path}' deleted successfully.")
        except FileNotFoundError:
            log.exception(f"File '{file_path}' not found.")
        except PermissionError:
            log.exception(f"Permission denied: unable to delete file '{file_path}'.")

        data = json.loads(newText)  # Load JSON data once

        if isinstance(data, list):
            log.info("JSON Valid - Generating Lists")
            with open(f'tmp/{datetime.now().strftime("%m-%d-%y_%H-%M-%S")}.json', 'w') as f:
                json.dump(data, f, indent=4)
            return data
        else:
            return None

    def __get_route_from_json(self):
        data = self.__analyze_har()

        if data is not None:
            count = 0
            inds = list()

            for i in range(len(data)):
                if type(data[i][1][0]) == dict:
                    if 'documentChange' in data[i][1][0].keys():
                        inds.append(count)
                count += 1

            rt = None
            if len(inds) != 0:
                for doc in inds:
                    dc = data[doc][1][0]['documentChange']['document']['fields']
                    if 'title' in dc.keys():
                        rt = dc['title']['stringValue']
                        inds.remove(doc)
                        break

                if rt is not None:
                    log.info(f'Route Title: {rt}')
                else:
                    log.warning("Route Title not found, using default")
                    rt = "Unknown"

                stops = list()

                for i in inds:
                    ent = data[i][1][0]['documentChange']['document']

                    street = ent['fields']['addressLineOne']['stringValue']
                    city = ent['fields']['addressLineTwo']['stringValue']
                    done = ent['fields']['done']['booleanValue']
                    success = ent['fields']['deliveryInfo']['mapValue']['fields']['succeeded']['booleanValue']

                    jsonDate = ent['updateTime']
                    u2 = re.sub('T', ' ', jsonDate)
                    u3 = re.sub('Z', '', u2)
                    jsonTime = datetime.strptime(u3, "%Y-%m-%d %H:%M:%S.%f")
                    updated = date.strftime(jsonTime, "%m/%d/%Y")

                    if 'notes' in ent['fields'].keys():
                        notes = ent['fields']['notes']['stringValue']
                    else:
                        notes = ""

                    if done and success:
                        stop = (street, city, "Yes", updated, re.sub(r'^\d*;', "", str(notes)))
                        stops.append(stop)
                    elif done and not success:
                        stop = (street, city, "No", updated, re.sub(r'^\d*;', "", str(notes)))
                        stops.append(stop)
                    else:
                        log.debug(f'Skipped adding stop at {street}, Done: {done}')

                return rt, stops

        else:
            raise TypeError("JSON cannot be None @ newScraper.Scraper.getRouteFromJson()")

    @staticmethod
    def __set_to_dataFrame(data: tuple) -> tuple:
        """ Private method, returns a tuple containing the name of the route and
            a dataFrame representing the route results

        :param data: tuple from __get_route_from_json
        :return: tuple containing name at first index and dataFrame at second
        """
        if len(data) == 2:
            houseNums: list[int] = list()
            addrs = list()
            faddrs = list()
            cities = list()
            confs = list()
            dates: list[str] = list()
            notes = list()

            for i in data[1]:
                div = str(i[0]).find(" ")
                num = str(i[0])[:div]
                if num.isnumeric():
                    houseNums.append(int(num))
                else:
                    houseNums.append(99999)
                addrs.append(str(i[0])[div + 1:])
                faddrs.append(i[0])
                cities.append(i[1])
                confs.append(i[2])
                dates.append(i[3])
                notes.append(i[4])

            dataWithHeads = {'NUM': houseNums, 'STREET': addrs, 'FULL ADDRESS': faddrs, 'CITY': cities,
                             'Visited': confs, 'Date': dates, 'Notes': notes}
            df = pd.DataFrame(dataWithHeads)

            return data[0], df
        else:
            raise AttributeError("Data Param is not a tuple with len 2 @ newScraper.Scraper.__set_to_Dataframe")

    def requestDataframe(self) -> tuple:
        """ Returns a tuple containing the name of the route and a dataframe representing
            the results of the route

        :return: tuple with len(2)
        """
        return self.__set_to_dataFrame(self.__get_route_from_json())

    def __init__(self, link: str = ""):
        if link.startswith("https://progress.getcircuit.com"):
            log.info("Generating .har file")
            self.__request_data(link)
        elif link == 'test' or '':
            log.warning("Link does not start with URL. Will use default Resources")


def main():
    s = Scraper()
    t = s.requestDataframe()
    log.info(f"{t[0]}\n{t[1]}")
    pass


if __name__ == "__main__":
    main()

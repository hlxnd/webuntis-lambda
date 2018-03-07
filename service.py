from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import sys
import math

################################################################
class Hours:
    def __init__(self,driver):
        css_hours = driver.find_elements_by_css_selector('.timetableRowHeader .timetableGridRow')
        self.hours = []

        for item in css_hours:
            hour=(item.text,item.location['y'],item.location['y']+item.size['height'])
            self.hours.append(hour)
            #print hour

    def getHourForCell(self,cell):
        pos=cell.location['y'] + cell.size['height']/2

        for item in self.hours:
            #print pos,item[1],item[0]
            if pos>item[1] and pos<item[2]:
                return item[0]
        return "?"

################################################################
class Days:
    def __init__(self,driver):
        css_days = driver.find_elements_by_css_selector('.timetableGridColumn.timetableColumnHeader')
        self.days=[]
        
        for item in css_days:
            day=(item.text,item.location['x'],item.location['x']+item.size['width'])
            self.days.append(day)
            #print day

    def getDayForCell(self,cell):
        pos=cell.location['x'] + cell.size['width']/2

        for item in self.days:
            #print pos,item[1],item[0]
            if pos>item[1] and pos<item[2]:
                return item[0]
        return "?"

################################################################
# Constants
################################################################
TIMEOUT = 5

################################################################
def loadUrlAndWait(driver):
    url = "https://asopo.webuntis.com/WebUntis/?school=Einstein-Gym-Kehl#/basic/timetable"
    driver.get(url) #navigate to the page
    # wait till element loaded
    element_present = EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='5d']"))
    WebDriverWait(driver, TIMEOUT).until(element_present)
    driver.set_window_size(1024,768)
    #driver.save_screenshot('screen.png')

################################################################
def clickOnClassAndWait(driver):
    button5d = driver.find_element_by_css_selector("a[title='5d']")
    button5d.click()
    element_present = EC.presence_of_element_located((By.CSS_SELECTOR, '.entryContent .def span'))
    WebDriverWait(driver, TIMEOUT).until(element_present)
    #driver.save_screenshot('screen2.png')

################################################################
def main(*args):
    
    #browser = webdriver.Firefox() #replace with .Firefox(), or with the browser of your choice
    browser = webdriver.PhantomJS() 
  
    try:
        # load url
        loadUrlAndWait(browser)

        # click element
        clickOnClassAndWait(browser) 

        # get hours postion as element order is sometimes wrong
        hours = Hours(browser)
        days = Days(browser)

        # get cells with lessons
        zellen = browser.find_elements_by_css_selector(".renderedEntry")

        stundenplan = []
        for zelle in zellen:

            stunde = hours.getHourForCell(zelle)
            tag = days.getDayForCell(zelle)

            details = zelle.find_elements_by_css_selector(".entryContent .def span")


            kurs = ""
            deleted = False
            for item in details:
                kurs = kurs + item.text + " "
                #print item.text + "/" + str(zelle.location['x']) + ',' + str(zelle.location['y'])
                if item.find_element_by_xpath('..').get_attribute('style').find('line-through')>-1:
                    deleted = True

            stunde=(kurs,tag,stunde,deleted)
            stundenplan.append(stunde)
            #print stunde


        print "-------------------"
        for item in stundenplan:
            if item[3]:
                print item[1] + ": Stunde " + item[2] + ":" + item[0] + " entfaellt"
            else:
                print item[1] + ": Stunde " + item[2] + ":" + item[0] + " entfaellt nicht"
        print "-------------------"


    except TimeoutException:
        print "Timed out waiting for page to load"

    browser.close()

# main
if __name__ == '__main__': 
    main(*sys.argv[1:])
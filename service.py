#!/usr/bin/env python
import httplib2
#import datetime
import time
import os
import selenium 
import json
import boto3
import requests
from dateutil.parser import parse
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from apiclient.discovery import build
from oauth2client.client import GoogleCredentials
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import sys
import math
import yaml
from datetime import datetime, timedelta, date
import dynamoDB

global config

# Entry point in AWS lambda
def handler(event, context):
    # set user agent
    main()

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
    url = config["source"]["url"]

    if ("parameters" in config["source"]):
        if len(config["source"]["parameters"])>0:
            url+="?"
            for paramName in config["source"]["parameters"]:
                url+=paramName+"="+config["source"]["parameters"][paramName]
    
    if ((config["source"]["fragment"]).strip()!=""):
        url+="#"+(config["source"]["fragment"]).strip()

    driver.get(url) #navigate to the page
    # wait till element loaded
    element_present = EC.presence_of_element_located((By.CSS_SELECTOR,
                                                      "a[title='" + config["class_link_title"] + "']"))
    WebDriverWait(driver, TIMEOUT).until(element_present)
    driver.set_window_size(1024,768)
    #driver.save_screenshot('screen.png')

################################################################
def clickOnClassAndWait(driver):
    button_class = driver.find_element_by_css_selector("a[title='"+config["class_link_title"]+"']")
    button_class.click()
    element_present = EC.presence_of_element_located((  By.CSS_SELECTOR, 
                                                        '.renderedEntry .entryContent .def span'))
    try:
        WebDriverWait(driver, TIMEOUT).until(element_present)
    except TimeoutException:
        if datetime.today().weekday()>=5:
            button_next_week = driver.find_element_by_css_selector(".un-week-picker__btn .fa-arrow-right")
            button_next_week.click()
            driver.save_screenshot('screen3.png')
            element_present = EC.presence_of_element_located((By.CSS_SELECTOR, '.renderedEntry .entryContent .def span'))
            WebDriverWait(driver, TIMEOUT).until(element_present)
        else:
            raise

def sort_function(c):
    return c['datetime'] + c['hour']

def loadLastStundeplan():
    db=dynamoDB.XDB()
    my_dict={}
    data=db.get_data()
    try:
        my_dict = json.loads(data)
    except:
        pass
    print data
    return my_dict

def writeData(stdata):
    db=dynamoDB.XDB()
    data = json.dumps(stdata)
    db.write_data(data)

def makeMsg(stundenplan):
    msg=""
    last_day=""

    # Map DELETED
    undel=dict()
    for lesson in stundenplan:
        if lesson['deleted']==False:
            undel[lesson['day']+"_"+str(lesson['hour'])]=lesson

    for lesson in stundenplan:
        if lesson['deleted']:
            if last_day==lesson['day']:
                out_datum="," + str(lesson['hour'])+"."
            else:
                out_datum = lesson['day'] + str(lesson['hour'])+"."
            out_deleted = lesson['subject'] + "/" + lesson['teacher']
            if lesson['day']+"_"+str(lesson['hour']) in undel:
                newLesson=undel[lesson['day']+"_"+str(lesson['hour'])]
                out_new = newLesson['subject'] + "/" + newLesson['teacher']
                out = out_datum+out_new+" ("+out_deleted+")"
            else:
                out = out_datum+"FREI("+out_deleted+")"
            if msg!='' and last_day != lesson['day']:
                msg+=" / "
            msg+=out
            last_day = lesson['day']
    return msg

def sendSMS(msg):
    print msg

    
################################################################
def main(*args):
    
    global config
    config = yaml.safe_load(open("config.yml"))

    #browser = webdriver.Firefox() #replace with .Firefox(), or with the browser of your choice
    #browser = webdriver.PhantomJS()

    user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36")
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = user_agent
    dcap["phantomjs.page.settings.javascriptEnabled"] = True
    browser = webdriver.PhantomJS(service_log_path=os.path.devnull, 
                                  executable_path="/var/task/phantomjs", 
                                  service_args=['--ignore-ssl-errors=true'], 
                                  desired_capabilities=dcap) 
  
    try:
        # load url
        loadUrlAndWait(browser)

        # click element
        clickOnClassAndWait(browser) 

        # get hours position as element order is sometimes wrong
        hours = Hours(browser)
        days = Days(browser)

        # get cells with lessons
        zellen = browser.find_elements_by_css_selector(".renderedEntry")

        stundenplan = []

        for zelle in zellen:

            stunde = hours.getHourForCell(zelle)
            tag = days.getDayForCell(zelle)

            details = zelle.find_elements_by_css_selector(".entryContent .def span")

            kurs = {}
            deleted = False
            course = []
            for node in details:
                course.append(node.text)
                #print item.text + "/" + str(zelle.location['x']) + ',' + str(zelle.location['y'])
                if node.find_element_by_xpath('..').get_attribute('style').find('line-through')>-1:
                    deleted = True

            if course[0]==config["class_name"]:

                # determine year
                year=datetime.now().year
                if datetime.now().month==12 and tag[6:8]==1:
                    year+=1
                elif datetime.now().month==1 and tag[6:8]==12:
                    year-=1

                kurs['datetime']=datetime.strptime(tag[3:9]+str(year),"%d.%m.%Y").strftime("%Y%m%d")
                kurs['day']=tag
                kurs['hour']=stunde
                kurs['class']=course[0]
                kurs['teacher']=course[1]
                kurs['subject']=course[2]
                kurs['room']=course[3]
                kurs['deleted']=deleted
                kurs['id']=kurs['class']+"_"+kurs['day']+"_"+kurs['hour']

                stundenplan.append(kurs)

        stundenplan=sorted(stundenplan,key=sort_function)

        # Compare to last message
        old_tt=loadLastStundeplan()
        # remove old days
        old_tt= [x for x in old_tt if x['datetime'] >= datetime.now().strftime("%Y%m%d")]
        msg_old=makeMsg(old_tt)

        msg=makeMsg(stundenplan)

        print msg

        if msg!=msg_old:
            writeData(stundenplan)
            sendSMS(msg)

    except TimeoutException:
        print "Timed out waiting for page to load"
        #browser.save_screenshot('timeout_screen.png')

    browser.close()

# main
if __name__ == '__main__': 
    main(*sys.argv[1:])
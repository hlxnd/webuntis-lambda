#!/usr/bin/env python
import httplib2
import datetime
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

        # get hours postion as element order is sometimes wrong
        hours = Hours(browser)
        days = Days(browser)

        # get cells with lessons
        zellen = browser.find_elements_by_css_selector(".renderedEntry")

        stundenplan = []
        undel=dict()

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

            stunde_=(kurs,tag,stunde,deleted)
            stundenplan.append(stunde_)
            if (deleted == False):
                #item[1]+"_"+str(item[2])
                undel[tag+"_"+str(stunde)]=stunde_

            #print stunde


        print "-------------------"
        for item in stundenplan:
            if item[3]:
                out = item[1] + ", "+item[2]+". Stunde (" + item[0] +") "
                #print item[1]+"_"+str(item[2])
                if item[1]+"_"+str(item[2]) in undel:
                    print out + " ersetzt durch "+undel[item[1]+"_"+str(item[2])][0]
                else:
                    print out+" FREI!"
            #else:
                #print item[1] + ": Stunde " + item[2] + ":" + item[0] + " entfaellt nicht"
        print "-------------------"


    except TimeoutException:
        print "Timed out waiting for page to load"

    browser.close()

# main
if __name__ == '__main__': 
    main(*sys.argv[1:])
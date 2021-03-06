#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: get the most recent donor json files
version: 0.0.2
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires environmental variables: import environmentalVariables.py
    * list of donors generated by get-donor-list.py
license: BSD-2-Clause
TODO:
* [] save files in the cloud
"""

# %% load in required libraries
import environmentalVariables
import pandas as pd
import datetime as dt
import os
import sys
import argparse
import requests
import json


# %% define functions
def get_user_data(email, password, userid, outputFilePathName):

    url1 = "https://api.tidepool.org/auth/login"
    myResponse = requests.post(url1, auth=(email, password))

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]
        url2 = "https://api.tidepool.org/data/" + userid
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
            }

        myResponse2 = requests.get(url2, headers=headers)
        if(myResponse2.ok):

            usersData = json.loads(myResponse2.content.decode())
            with open(outputFilePathName, 'w') as outfile:
                json.dump(usersData, outfile)

        else:
            print(donorGroup, "ERROR", myResponse2.status_code)
    else:
        print(donorGroup, "ERROR", myResponse.status_code)

    return


# %% user inputs (choices to be made in order to run the code)
codeDescription = "Download donor's json files"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--date-stamp",
                    dest="dateStamp",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="date in '%Y-%m-%d' format of unique donor list" +
                    "(e.g., PHI-2018-03-02-uniqueDonorList)")

args = parser.parse_args()

# create a datestamp of when the data is pulled, and add PHI bc data has PHI
phiDateStamp = "PHI-" + args.dateStamp

parser.add_argument("-i",
                    "--input-data-path",
                    dest="donorListPath",
                    default=os.path.join("..",
                                         "data",
                                         phiDateStamp + "-donor-data",
                                         phiDateStamp + "-uniqueDonorList.csv"),
                    help="csv file that contains the a list of donors")

parser.add_argument("-o",
                    "--output-data-path",
                    dest="donorJsonDataFolder",
                    default=os.path.join("..",
                                         "data",
                                         phiDateStamp + "-donor-data",
                                         phiDateStamp + "-donorJsonData"),
                    help="the output path where the data is stored")

args = parser.parse_args()


# %% check inputs and load donor list
if not os.path.exists(args.donorListPath):
    sys.exit("{0} does not exist in the given path".format(args.donorListPath))

if not os.path.isdir(args.donorJsonDataFolder):
    os.makedirs(args.donorJsonDataFolder)

# load in list of unique donors
uniqueDonors = pd.read_csv(args.donorListPath,
                           index_col="dIndex",
                           low_memory=False)


# %% pull the json files for all of the unique donors
for userID, donorGroup in zip(uniqueDonors.userID, uniqueDonors.donorGroup):
    outputFilePathName = os.path.join(args.donorJsonDataFolder,
                                      "PHI-" + userID + ".json")

    # if the json file already exists, do NOT pull it again
    if not os.path.exists(outputFilePathName):

        # case where donorGroup is bigdata, but should be ""
        if donorGroup == "bigdata":
            donorGroup = ""

        # get environmental variables
        email, password = \
            environmentalVariables.get_environmental_variables(donorGroup)

        # get json data
        get_user_data(email, password, userID, outputFilePathName)

        print(userID, "complete")

    else:
        print(userID, "data already downloaded")

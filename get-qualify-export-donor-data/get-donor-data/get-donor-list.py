#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: download donors for each of the Tidepool donor groups
version: 0.0.2
created: 2018-02-21
author: Ed Nykaza
dependencies:
    * requires that donors are accepted (currently a manual process)
    * requires a list of qa accounts on production to be ignored
    * requires environmental variables: import environmentalVariables.py
    * requires https://github.com/tidepool-org/command-line-data-tools
license: BSD-2-Clause
TODO:
* [] once the process of accepting new donors is automated, the use of the
dateStamp will make more sense. As it is being used now, it is possible that
the dateStamp does NOT reflect all of the recent donors.
* [] refactor script to get rid of commandline tools
"""


# %% load in required libraries

import pandas as pd
import datetime as dt
import numpy as np
import hashlib
import os
import sys
import subprocess as sub
import requests
import json
import argparse
sys.path.insert(0, "../")
import environmentalVariables


# %% user inputs (choices to be made in order to run the code)
codeDescription = "Download a list of donors for each of the Tidepool" + \
                  "accounts defined in .env"

parser = argparse.ArgumentParser(description=codeDescription)

parser.add_argument("-d",
                    "--date-stamp",
                    dest="dateStamp",
                    default=dt.datetime.now().strftime("%Y-%m-%d"),
                    help="date, in '%Y-%m-%d' format, of the date when " +
                    "donors were accepted")

parser.add_argument("-i",
                    "--input-donor-groups",
                    dest="donorGroupsCsvFile",
                    default="2018-02-28-donor-groups.csv",
                    help="a .csv file that contains a column heading " +
                    "'donorGroups' and a list of donor groups")

parser.add_argument("-o",
                    "--output-data-path",
                    dest="dataPath",
                    default="../data",
                    help="the output path where the data is stored")

parser.add_argument("--ignore-accounts",
                    dest="ignoreAccountsCsvFile",
                    default="PHI-2018-02-28-prod-accounts-to-be-ignored.csv",
                    help="a .csv file that contains a column heading " +
                    "'userID' and a list of userIDs to ignore")

args = parser.parse_args()


# %% Make sure the data directory exists
if not os.path.isdir(args.dataPath):
    sys.exit("{0} is not a directory".format(args.dataPath))


# %% define global variables
ignoreAccountsPath = os.path.join(args.dataPath, args.ignoreAccountsCsvFile)
donorGroupPath = os.path.join(args.dataPath, args.donorGroupsCsvFile)

donorGroups = pd.read_csv(donorGroupPath,
                          header=0,
                          names=["donorGroups"],
                          low_memory=False)

donorGroups = donorGroups.donorGroups

try:
    salt = os.environ["BIGDATA_SALT"]
except KeyError:
    sys.exit("Environment variable BIGDATA_SALT not found in .env file")

phiDateStamp = "PHI-" + args.dateStamp

donorMetadataColumns = ["userID", "bDay", "dDay",
                            "diagnosisType",
                            "targetDevices",
                            "targetTimezone",
                            "termsAccepted",
                            "hashID"]

alldonorMetadataList = pd.DataFrame(columns=donorMetadataColumns)

# create output folders
donorFolder = os.path.join(args.dataPath, phiDateStamp + "-donor-data")
if not os.path.exists(donorFolder):
    os.makedirs(donorFolder)

donorListFolder = os.path.join(donorFolder, phiDateStamp + "-donorLists")
if not os.path.exists(donorListFolder):
    os.makedirs(donorListFolder)

uniqueDonorPath = os.path.join(donorFolder,
                               phiDateStamp + "-uniqueDonorList.csv")


# %% define functions
def get_donor_lists(email, password, outputDonorList):
    p = sub.Popen(["getusers", email,
                   "-p", password, "-o",
                   outputDonorList, "-v"], stdout=sub.PIPE, stderr=sub.PIPE)

    output, errors = p.communicate()
    output = output.decode("utf-8")
    errors = errors.decode("utf-8")

    if output.startswith("Successful login.\nSuccessful") is False:
        sys.exit("ERROR with" + email +
                 " ouput: " + output +
                 " errorMessage: " + errors)

    return


def load_donors(outputDonorList, donorGroup):
    donorList = []
    if os.stat(outputDonorList).st_size > 0:
        donorList = pd.read_csv(outputDonorList,
                                header=None,
                                usecols=[0, 1],
                                names=["userID", "name"],
                                low_memory=False)
        if donorGroup == "":
            donorGroup = "bigdata"
        donorList[donorGroup] = True
        donorList["donorGroup"] = donorGroup

    return donorList


def get_metadata(email, password, donorMetadataColumns):

    tempBandDdayList = pd.DataFrame(columns=donorMetadataColumns)
    url1 = "https://api.tidepool.org/auth/login"
    myResponse = requests.post(url1, auth=(email, password))

    if(myResponse.ok):
        xtoken = myResponse.headers["x-tidepool-session-token"]
        userid = json.loads(myResponse.content.decode())["userid"]
        url2 = "https://api.tidepool.org/metadata/users/" + userid + "/users"
        headers = {
            "x-tidepool-session-token": xtoken,
            "Content-Type": "application/json"
        }

        myResponse2 = requests.get(url2, headers=headers)
        if(myResponse2.ok):

            usersData = json.loads(myResponse2.content.decode())

            for i in range(0, len(usersData)):
                try:
                    bDay = usersData[i]["profile"]["patient"]["birthday"]
                except Exception:
                    bDay = np.nan
                try:
                    dDay = usersData[i]["profile"]["patient"]["diagnosisDate"]
                except Exception:
                    dDay = np.nan
                try:
                    diagnosisType = usersData[i]["profile"]["patient"]["diagnosisType"]
                except Exception:
                    diagnosisType = np.nan
                try:
                    targetDevices = usersData[i]["profile"]["patient"]["targetDevices"]
                except Exception:
                    targetDevices = np.nan
                try:
                    targetTimezone = usersData[i]["profile"]["patient"]["targetTimezone"]
                except Exception:
                    targetTimezone = np.nan
                try:
                    termsAccepted = usersData[i]["termsAccepted"]
                except Exception:
                    termsAccepted = np.nan

                userID = usersData[i]["userid"]
                usr_string = userID + salt
                hash_user = hashlib.sha256(usr_string.encode())
                hashID = hash_user.hexdigest()
                tempBandDdayList = tempBandDdayList.append(
                        pd.DataFrame([[userID,
                                       bDay,
                                       dDay,
                                       diagnosisType,
                                       targetDevices,
                                       targetTimezone,
                                       termsAccepted,
                                       hashID]],
                                     columns=donorMetadataColumns),
                        ignore_index=True)
        else:
            print(donorGroup, "ERROR", myResponse2.status_code)
    else:
        print(donorGroup, "ERROR", myResponse.status_code)

    return tempBandDdayList


# %% loop through each donor group to get a list of donors, bdays, and ddays
for donorGroup in donorGroups:
    outputDonorList = os.path.join(donorListFolder, donorGroup + "-donors.csv")

    if donorGroup == "bigdata":
        donorGroup = ""

    # get environmental variables
    email, password = \
        environmentalVariables.get_environmental_variables(donorGroup)

    # get the list of donors
    get_donor_lists(email, password, outputDonorList)

    # load in the donor list
    donorList = load_donors(outputDonorList, donorGroup)

    # load in bdays and ddays and append to all donor list
    donorMetadataList = get_metadata(email, password, donorMetadataColumns)

    donorMetadataList = pd.merge(donorMetadataList,
                                 donorList,
                                 how="left",
                                 on="userID")

    alldonorMetadataList = alldonorMetadataList.append(donorMetadataList,
                                                       ignore_index=True,
                                                       sort=False)

    print("BIGDATA_" + donorGroup, "complete")


# %% save output

uniqueDonors = alldonorMetadataList.loc[
        ~alldonorMetadataList["userID"].duplicated(),
        donorMetadataColumns + ["name", "donorGroup"]]

# add donor groups to unique donors
donorCounts = alldonorMetadataList.groupby("userID").count()
donorCounts = donorCounts[donorGroups]
donorCounts["userID"] = donorCounts.index

uniqueDonors = pd.merge(uniqueDonors,
                        donorCounts,
                        how="left",
                        on="userID")

# cross reference the QA users here and DROP them
ignoreAccounts = pd.read_csv(ignoreAccountsPath, low_memory=False)
uniqueIgnoreAccounts = \
    ignoreAccounts[ignoreAccounts.Userid.notnull()].Userid.unique()

for ignoreAccount in uniqueIgnoreAccounts:
    uniqueDonors = uniqueDonors[uniqueDonors.userID != ignoreAccount]

uniqueDonors = uniqueDonors.reset_index(drop=True)
uniqueDonors.index.name = "dIndex"

print("There are",
      len(uniqueDonors),
      "unique donors, of the",
      len(alldonorMetadataList),
      "records")

print("The total number of missing datapoints:",
      "\n",
      uniqueDonors[["bDay", "dDay"]].isnull().sum())

uniqueDonors.to_csv(uniqueDonorPath)

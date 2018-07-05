'''
Created on Jul 4, 2018

TODO: Add parallelism
TODO: Write back to spreadsheet
TODO: Make filename start with file id so pack updates can be automated
TODO: Move more variables to the external variable json

@author: Alex
'''

# Plenty of imports
import json
import sys
import urllib.request
from lxml import html
import os.path
import requests
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# Fire up some variables
FILES_TO_DOWNLOAD = {}
MODS_NEEDING_UPDATES = []
VARIABLE_FILE = 'vars.json'

# Try to open variable file to fire up some more variables
try:
    with open(VARIABLE_FILE) as FILE:
        VARS_FROM_FILE = json.load(FILE)
        SPREADSHEET_ID = VARS_FROM_FILE.get('spreadsheetId')
        RANGE_1 = VARS_FROM_FILE.get('range1')
        RANGE_2_PRE = VARS_FROM_FILE.get('range2pre')
        MOD_URL_PRE = VARS_FROM_FILE.get('modURLpre')
        MOD_URL_POST = VARS_FROM_FILE.get('modURLpost')
        LOCAL_PATH = VARS_FROM_FILE.get('localPath')
except FileNotFoundError: 
    print('Variable file not found: ', VARIABLE_FILE)
    sys.exit()


# Setup the Sheets API
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
STORE = file.Storage('credentials.json')
CREDS = STORE.get()
if not CREDS or CREDS.invalid:
    FLOW = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    CREDS = tools.run_flow(FLOW, STORE)
SERVICE = build('sheets', 'v4', http=CREDS.authorize(Http()))

# Look for existing data and get it if it doesn't exist
# RESULT_1 is a range of values that will contain how many mods are in the list and when this program was last run 
try:
    with open('data_1.json') as FILE:
        RESULT_1 = json.load(FILE)
except FileNotFoundError:
    # Call the Sheets API
    RESULT_1 = SERVICE.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_1).execute()                                  
    with open('data_1.json', 'w') as OUTFILE:  
        json.dump(RESULT_1, OUTFILE)

# Use RESULT_1 to determine how many cells to request for RESULT_2
NUM_MODS = RESULT_1.get('values')[0][1]
RANGE_2_BEGIN = RANGE_2_PRE[-1:]
RANGE_2_END = int(NUM_MODS) + int(RANGE_2_BEGIN) - 1
RANGE_2 = RANGE_2_PRE[:-1] + str(RANGE_2_END)

# Look for existing data and get it if it doesn't exist
# RESULT_2 contains: mod names, link, old file id, and a download link
try:
    with open('data_2.json') as FILE:
        RESULT_2 = json.load(FILE)
except FileNotFoundError:
    RESULT_2 = SERVICE.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_2).execute()               
    with open('data_2.json', 'w') as OUTFILE:  
        json.dump(RESULT_2, OUTFILE)

# Use the project id from RESULTS_2 to build the Curse URL and get the files page
# then find the latest jar and add it to a list to download
MODS_ONLY = RESULT_2.get('values')
for line in MODS_ONLY:
    PROJECT_ID = line[2]
    OLD_FILE_ID = line[3]
    MOD_NAME = line[0]
    MOD_URL = MOD_URL_PRE + PROJECT_ID + MOD_URL_POST
    PAGE = requests.get(MOD_URL)
    PAGE_DATA = html.fromstring(PAGE.content)
    for TABLE in PAGE_DATA.xpath('//table[@class="listing listing-project-file project-file-listing b-table b-table-a"]'):
        DOWNLOAD_PATH = TABLE.xpath('//a[@class="button tip fa-icon-download icon-only"]/@href')[0]
        DOWNLOAD_URL = 'https://minecraft.curseforge.com' + DOWNLOAD_PATH
        NEW_FILE_ID = DOWNLOAD_PATH.split('/')[4]
        FILENAME = TABLE.xpath('//div[@class="project-file-name-container"]/a/@data-name')[0].replace(' ', '')
        if FILENAME[-4:] != '.jar':
            FILENAME += '.jar'
    if NEW_FILE_ID > OLD_FILE_ID:
        MODS_NEEDING_UPDATES.append(MOD_NAME)
        FILES_TO_DOWNLOAD[FILENAME] = DOWNLOAD_URL
        line[3] = NEW_FILE_ID
    line[4] = DOWNLOAD_URL

# List mods we need to update
print('Update required for the following ', len(MODS_NEEDING_UPDATES), ' mods:')
for MOD in MODS_NEEDING_UPDATES:
    print(MOD)
print()

# Write the updated info back to the sheet
BODY = {'values': MODS_ONLY}
RESULT_3 = SERVICE.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=RANGE_2, valueInputOption='USER_ENTERED', body=BODY).execute()

# Download the updated mods
for ENTRY in FILES_TO_DOWNLOAD:
    FILE_PATH = LOCAL_PATH + ENTRY
    if os.path.isfile(FILE_PATH):
        print('Already exists: ', ENTRY)
    else:
            urllib.request.urlretrieve(FILES_TO_DOWNLOAD[ENTRY], FILE_PATH)

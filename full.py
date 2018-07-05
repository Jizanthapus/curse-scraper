'''
Created on Jul 4, 2018

TODO: Add parallelism
TODO: Write back to spreadsheet
TODO: Make filename start with file id so pack updates can be automated
TODO: Move more variables to the external variable json

@author: Alex
'''
import json
import sys
import urllib.request
from lxml import html
import os.path
import requests
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

MOD_URL_PRE = 'https://minecraft.curseforge.com/projects/'
MOD_URL_POST = '/files?filter-game-version=2020709689%3A6756'
FILES_TO_DOWNLOAD = {}
MODS_NEEDING_UPDATES = []

try:
    with open('vars.json') as FILE:
        VARS_FROM_FILE = json.load(FILE)
except FileNotFoundError: 
    print('Variable file not found')
    sys.exit()

try:
    with open('data.json') as FILE:
        RESULT = json.load(FILE)
except FileNotFoundError: 
    # Setup the Sheets API
    SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
    STORE = file.Storage('credentials.json')
    CREDS = STORE.get()
    if not CREDS or CREDS.invalid:
        FLOW = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        CREDS = tools.run_flow(FLOW, STORE)
    SERVICE = build('sheets', 'v4', http=CREDS.authorize(Http()))
    
    # Call the Sheets API
    SPREADSHEET_ID = VARS_FROM_FILE.get('spreadsheetId')
    RANGE_NAME = ['Curse Mods!A1:B1', 'Curse Mods!A5:E8']
    RESULT = SERVICE.spreadsheets().values().batchGet(spreadsheetId=SPREADSHEET_ID,
                                                 ranges=RANGE_NAME).execute()
                                                 
    with open('data.json', 'w') as OUTFILE:  
        json.dump(RESULT, OUTFILE)

RANGES = RESULT.get('valueRanges')
for RANGE in RANGES:
    if RANGE.get('range') == "'Curse Mods'!A1:B1":
        NUM_MODS = RANGE.get('values')[0][1]
        #print('Number of Mods: ',NUM_MODS, '\n')
    if RANGE.get('range') == "'Curse Mods'!A5:E8":
        MOD_INFO = RANGE.get('values')
        MODS_ONLY = MOD_INFO[1:]
        for line in MODS_ONLY:
            #print('Line: ', line)
            PROJECT_ID = line[2]
            OLD_FILE_ID = line[3]
            MOD_NAME = line[0]
            #print('Project ID: ', PROJECT_ID)
            MOD_URL = MOD_URL_PRE + PROJECT_ID + MOD_URL_POST
            #print('Mod URL:', MOD_URL)
            PAGE = requests.get(MOD_URL)
            PAGE_DATA = html.fromstring(PAGE.content)
            for TABLE in PAGE_DATA.xpath('//table[@class="listing listing-project-file project-file-listing b-table b-table-a"]'):
                DOWNLOAD_PATH = TABLE.xpath('//a[@class="button tip fa-icon-download icon-only"]/@href')[0]
                DOWNLOAD_URL = 'https://minecraft.curseforge.com' + DOWNLOAD_PATH
                NEW_FILE_ID = DOWNLOAD_PATH.split('/')[4]
                FILENAME = TABLE.xpath('//div[@class="project-file-name-container"]/a/@data-name')[0].replace(' ', '')
                if FILENAME[-4:] != '.jar':
                    FILENAME += '.jar'
                #print(FILENAME)
                #print('File ID: ', NEW_FILE_ID)
                #print('Download URL: ', DOWNLOAD_URL)
            if NEW_FILE_ID > OLD_FILE_ID:
                MODS_NEEDING_UPDATES.append(MOD_NAME)
                FILES_TO_DOWNLOAD[FILENAME] = DOWNLOAD_URL
                line[3] = NEW_FILE_ID
            line[4] = DOWNLOAD_URL
            #print('Line: ', line)

print('Update required for:')
for MOD in MODS_NEEDING_UPDATES:
    print(MOD)
print()

for ENTRY in FILES_TO_DOWNLOAD:
    #print('File: ', ENTRY, '\t', 'URL: ', FILES_TO_DOWNLOAD[ENTRY])
    LOCAL_PATH = VARS_FROM_FILE.get('localPath') + ENTRY
    if os.path.isfile(LOCAL_PATH):
        print('Already exists: ', ENTRY)
    else:
            urllib.request.urlretrieve(FILES_TO_DOWNLOAD[ENTRY], LOCAL_PATH)

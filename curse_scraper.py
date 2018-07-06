'''
Created on Jul 4, 2018
v1.0
This program obtains a list of mods from a Google Sheet and checks it against info from Curse. When an update is found, it's downloaded. 

TODO: Print time since last run
TODO: Collect upload time from Curse to calculate and display how recently the update is
TODO: (Maybe) Move to beautifulsoup for HTML parsing
'''

# Plenty of imports
import json
import sys
import urllib.request
from lxml import html
import os.path
from multiprocessing.dummy  import Pool
import requests
import datetime
# Imports for Sheets API
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# Try to open variable file to fire up some variables
try:
    VARIABLE_FILE = 'vars.json'
    print('Loading variable file:', VARIABLE_FILE, '\n')
    with open(VARIABLE_FILE) as FILE:
        VARS_FROM_FILE = json.load(FILE)
        SPREADSHEET_ID = VARS_FROM_FILE.get('spreadsheetId')
        RANGE_1 = VARS_FROM_FILE.get('range1')
        RANGE_2_PRE = VARS_FROM_FILE.get('range2pre')
        RANGE_3_PRE = VARS_FROM_FILE.get('range3pre')
        RANGE_4 = VARS_FROM_FILE.get('range4')
        MOD_URL_PRE = VARS_FROM_FILE.get('modURLpre')
        MOD_URL_POST = VARS_FROM_FILE.get('modURLpost')
        LOCAL_PATH = VARS_FROM_FILE.get('localPath')
        NUM_OF_PROCESSES = int(VARS_FROM_FILE.get('processes'))
except FileNotFoundError: 
    print('Variable file not found: ', VARIABLE_FILE)
    sys.exit()

print('*** Running with the following settings ***')
print('Number of processes for downloads and HTTP requests:', NUM_OF_PROCESSES)
print('Files will be downloaded to:', LOCAL_PATH, '\n')

# Fire up some more variables
FILES_TO_DOWNLOAD = {}
MODS_NEEDING_UPDATES = []
INFO_TO_WRITE = []
POOL = Pool(NUM_OF_PROCESSES)

def download_entry(ENTRY):
    '''
    Function for downloading files
    '''
    FILE_PATH = LOCAL_PATH + ENTRY
    if os.path.isfile(FILE_PATH):
        print('Already exists: ', ENTRY)
    else:
            urllib.request.urlretrieve(FILES_TO_DOWNLOAD[ENTRY], FILE_PATH)
            print('Downloaded:', ENTRY)

def get_info_from_curse(line):
    '''
    Retrieve the mod info from curse
    '''
    PROJECT_ID = line[1].split('/')[4]
    if len(line) == 4:
        OLD_FILE_ID = int(line[2])
    else:
        line.append(0)
        OLD_FILE_ID = int(line[2])
        line.append('Error')
    MOD_NAME = line[0]
    MOD_URL = MOD_URL_PRE + PROJECT_ID + MOD_URL_POST
    PAGE = requests.get(MOD_URL)
    PAGE_DATA = html.fromstring(PAGE.content)
    for TABLE in PAGE_DATA.xpath('//table[@class="listing listing-project-file project-file-listing b-table b-table-a"]'):
        DOWNLOAD_PATH = TABLE.xpath('//a[@class="button tip fa-icon-download icon-only"]/@href')[0]
        DOWNLOAD_URL = 'https://minecraft.curseforge.com' + DOWNLOAD_PATH
        NEW_FILE_ID = int(DOWNLOAD_PATH.split('/')[4])
        FILENAME = TABLE.xpath('//div[@class="project-file-name-container"]/a/@data-name')[0].replace(' ', '') + '-' + str(NEW_FILE_ID) 
        if FILENAME[-4:] != '.jar':
            FILENAME += '.jar'
    if NEW_FILE_ID > OLD_FILE_ID:
        MODS_NEEDING_UPDATES.append(MOD_NAME)
        FILES_TO_DOWNLOAD[FILENAME] = DOWNLOAD_URL
        line[2] = NEW_FILE_ID
    line[3] = DOWNLOAD_URL
    
# Setup the Sheets API
print('Attempting to contact Sheets\n')
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
STORE = file.Storage('credentials.json')
CREDS = STORE.get()
if not CREDS or CREDS.invalid:
    FLOW = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    CREDS = tools.run_flow(FLOW, STORE)
SERVICE = build('sheets', 'v4', http=CREDS.authorize(Http()))

# Call the Sheets API
# RESULT_1 is a range of values that will contain how many mods are in the list and when this program was last run 
RESULT_1 = SERVICE.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, majorDimension='COLUMNS', range=RANGE_1).execute()                                  

# Use RESULT_1 to determine how many cells to request for RESULT_2 and RESULT_3
NUM_MODS = RESULT_1.get('values')[0][0]
print('Sheet indicates there are', NUM_MODS, 'mods to check\n')
RANGE_2_BEGIN = RANGE_2_PRE[-1:]
RANGE_2_END = int(NUM_MODS) + int(RANGE_2_BEGIN) - 1
RANGE_2 = RANGE_2_PRE[:-1] + str(RANGE_2_END)
RANGE_3_BEGIN = RANGE_3_PRE[-1:]
RANGE_3_END = int(NUM_MODS) + int(RANGE_3_BEGIN) - 1
RANGE_3 = RANGE_3_PRE[:-1] + str(RANGE_3_END)

# RESULT_2 contains: mod names, link, old file id, and a download link
RESULT_2 = SERVICE.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_2).execute()               

# Use the project id from RESULTS_2 to build the Curse URL and get the files page
# then find the latest jar and add it to a list to download
print('Attempting to contact Curse for mod info\n')
MODS_ONLY = RESULT_2.get('values')
POOL.map(get_info_from_curse, MODS_ONLY)

# See if any mods need updating
if len(MODS_NEEDING_UPDATES) > 0:
    # List mods we need to update
    print('Update required for the following', len(MODS_NEEDING_UPDATES), 'mods:')
    for MOD in MODS_NEEDING_UPDATES:
        print(MOD)
    print()
    
    # Write the updated info back to the sheet
    for line in MODS_ONLY:
        INFO_TO_WRITE.append(line[2:4])
    MOD_DATA_FOR_SHEET = {'values': INFO_TO_WRITE}
    print('Writing updated mod info back to Sheets\n')
    RESULT_3 = SERVICE.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=RANGE_3, valueInputOption='USER_ENTERED', body=MOD_DATA_FOR_SHEET).execute()
        
    # Download the updated mods
    print('Starting downloads')
    POOL.map(download_entry, FILES_TO_DOWNLOAD)
    print()
else:
    print('Looks like all the mods are currently up to date\n')
    
# Update the sheet to show this run
TIME = datetime.datetime.now()
TIME_STRING = [[TIME.strftime("%Y-%m-%d %H:%M")]]
print('Writing the current time back to Sheets\n')
TIME_TO_WRITE = {'values': TIME_STRING}
RESULT_4 = SERVICE.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=RANGE_4, valueInputOption='USER_ENTERED', body=TIME_TO_WRITE).execute()

print('Program complete\n')


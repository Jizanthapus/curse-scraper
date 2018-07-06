'''
Created on Jul 4, 2018
v1.0
This program obtains a list of mods from a Google Sheet and checks it against info from Curse. When an update is found, it's downloaded. 

TODO: Add OLD_FILE_ID to the filename so it can be used to identify files in the instance for automated updating
        or output a json file with the mod name, file ID, and jar name
TODO: Print time since last run
TODO: Collect upload time from Curse to calculate and display how recently the update is
TODO: (Maybe) Move to beautifulsoup for HTML parsing
TODO: Split vars file into programVars and userVars for simplicity
TODO: Add compatibility with other versions of MC
'''

# Plenty of imports
import json
import sys
import urllib.request
import urllib.parse
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
    UPDATE_LIST_NAME = VARS_FROM_FILE.get('updateListName') # Not used yet
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
UPDATE_LIST = []
POOL = Pool(NUM_OF_PROCESSES)

def download_entry(ENTRY):
    '''
    Function for downloading files
    '''
    ENTRY_JAR = FILES_TO_DOWNLOAD[ENTRY].get('jar')
    ENTRY_PATH = LOCAL_PATH + ENTRY_JAR
    ENTRY_URL = FILES_TO_DOWNLOAD[ENTRY].get('downloadURL')
    if os.path.isfile(ENTRY_PATH):
        print('Already exists:', ENTRY_JAR)
    else:
            urllib.request.urlretrieve(ENTRY_URL, ENTRY_PATH)
            print('Downloaded:', ENTRY, '->', ENTRY_JAR)

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
    print('Checking on', MOD_NAME)
    PAGE = requests.get(MOD_URL)
    PAGE_DATA = html.fromstring(PAGE.content)
    for TABLE in PAGE_DATA.xpath('//table[@class="listing listing-project-file project-file-listing b-table b-table-a"]'):
        DOWNLOAD_PATH = TABLE.xpath('//a[@class="button tip fa-icon-download icon-only"]/@href')[0]
        if not DOWNLOAD_PATH:
            print('Something went wrong retrieving the download path')
            sys.exit()
        DOWNLOAD_URL = 'https://minecraft.curseforge.com' + DOWNLOAD_PATH
        NEW_FILE_ID = int(DOWNLOAD_PATH.split('/')[4])
    if NEW_FILE_ID > OLD_FILE_ID:
        REAL_URL = urllib.request.urlopen(DOWNLOAD_URL).geturl()
        FILENAME = REAL_URL.split('/')[-1]
        FINAL_FILENAME = urllib.parse.unquote(FILENAME)
        if FINAL_FILENAME[-4:] != '.jar':
            print('Error: Something changed with the download URL. Report this.')
            sys.exit()
        MODS_NEEDING_UPDATES.append(MOD_NAME)
        FILES_TO_DOWNLOAD[MOD_NAME] = {'currentFileID':NEW_FILE_ID, 'jar':FINAL_FILENAME, 'downloadURL':DOWNLOAD_URL}
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
print(MODS_ONLY)
POOL.map(get_info_from_curse, MODS_ONLY)

# Setup time for reasons
TIME = datetime.datetime.now()
TIME_STRING = [[TIME.strftime("%Y-%m-%d %H:%M")]]
TIME_STRING_2 = TIME.strftime("%y-%m-%d_%H-%M-")
TIME_STRING_3 = TIME.strftime("%Y-%m-%d %H:%M")


# See if any mods need updating
if len(MODS_NEEDING_UPDATES) > 0:
    # List mods we need to update
    print('Update required for the following', len(MODS_NEEDING_UPDATES), 'mods:')
    for MOD in MODS_NEEDING_UPDATES:
        print(MOD)
    print()
    
    # Write out a list of the updated mods
    UPDATE_LIST_NAME_TIME = str(TIME_STRING_2) + str(UPDATE_LIST_NAME)
    UPDATE_LIST_DATA = {'meta': {
                                    'time':TIME_STRING_3,
                                    'numModsUpdated': len(MODS_NEEDING_UPDATES)},
                        'mods':FILES_TO_DOWNLOAD}
    with open(UPDATE_LIST_NAME_TIME, 'w') as FILE:
        json.dump(UPDATE_LIST_DATA, FILE)
    
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
print('Writing the current time back to Sheets\n')
TIME_TO_WRITE = {'values': TIME_STRING}
RESULT_4 = SERVICE.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=RANGE_4, valueInputOption='USER_ENTERED', body=TIME_TO_WRITE).execute()

print('Program complete\n')


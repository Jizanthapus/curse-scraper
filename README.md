# curse-scraper
This program obtains a list of Minecraft mods from a Google Sheet and checks it against info from Curse. When an update is found, it's downloaded.

## Use
1. Clone this repo
1. You need to have Python installed (tested with 3.6.6)
1. Make your own copy of [this demo sheet](https://docs.google.com/spreadsheets/d/1x4Gq7Uvn_huaaXHmJXdFpE1fbVlheOipG3AfwmuQ1tI/edit?usp=sharing)
	1. You only have fill in columns A, B, and C
		1. Column A is the name that will be used in the program - this doesn't affect filenames
		1. Column B is the version of Minecraft you wish to search for
		1. Column C should contain the link to the project on Curse Forge - see demo sheet for example
	1. Fill in the number of mods you put in the list to cell `B1` if it doesn't update automatically
1. Check to make sure you have the required python imports installed
	1. `pip install --upgrade [package]`
		1. `requests`
		1. `lxml`
		1. `google-api-python-client`
1. Give yourself [API access to Google Sheets](https://developers.google.com/sheets/api/quickstart/python)
	1. Make sure you request read and write access using `https://www.googleapis.com/auth/spreadsheets` for `SCOPE`
	1. Add the 2 files this process generates to the directory where you cloned this repo
1. Prepare your `userVars.json`.
	1. Rename `sample_userVars.json` to `userVars.json`
	1. Fill in your values for:
		* `spreadsheetId` Big random string in the URL of your sheet. The demo sheet ID is provided by default.
		* `processes` The number of processes that the program will launch when making HTTP requests and downloads from Curse.
		* `localPath` Directory where the program will attempt to place downloaded mod jars.

### Variables in `programVars.json`
**If you are using a copy of the demo sheet there is no need to change these.**
* `userVarsName` Name of the file that contains values a normal user might need to change
* `range1` Cell location for the number of mods in your list. 
* `range4` Cell location for the last run date. 
* `range2pre` Where the program looks for all the mods you want checked.
* `range3pre` A subset of range2pre that contains cells that will be written to by the program.
* `modURLpre` First part of the Curseforge URL (before the project ID)
* `modURLpost` Second part of the Curseforge URL (after the project ID)
* `filters` Entries for the MC versions that are appended to modURLpost to search for mods
* `updateListName` File where info on the mods updated will be saved

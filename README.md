# curse-scraper
This program obtains a list of Minecraft mods from a Google Sheet and checks it against info from Curse. When an update is found, it's downloaded.

## Use
1. Clone this repo
1. Make your own copy of [this Demo sheet](https://docs.google.com/spreadsheets/d/1x4Gq7Uvn_huaaXHmJXdFpE1fbVlheOipG3AfwmuQ1tI/edit?usp=sharing)
	1. Fill in the number of mods you put in the list to cell `B1`
	1. You only have to add data to columns A and B
		1. Column A is the name that will be used in the program - this doesn't affect filenames
		1. Column B should contain the link to the project on Curse Forge - see template for example
1. Check to make sure you have the required imports
1. Give yourself [API access to Google Sheets](https://developers.google.com/sheets/api/quickstart/python)
	1. Make sure you request read and write access using `https://www.googleapis.com/auth/spreadsheets` for `SCOPE`
	1. Add the 2 files this process generates to the directory where you cloned this repo
1. Prepare your `vars.json`. If you are using an unaltered copy of the Demo sheet, then you only have to change the `spreadsheetId` and `localPath`.
	1. Rename `sample_vars.json` to `vars.json`
	1. Fill in your values for:
		1. `spreadsheetId` This is your the big random string in the URL of your sheet.
		1. `range1` This is where the program looks for the number of mods in your list and the last run date. **If you are using the provided template there is no need to change this.**
		1. `range2pre` This is where the program looks for all the mods you want checked. **If you are using the provided template there is no need to change this.**
		1. `range3pre` This is a subset of range2pre that contains cells that will be written to by the program. **If you are using the provided template there is no need to change this.**
		1. `processes` This is the number of processes that the program will launch when making HTTP requests and downloads from Curse.
		1. `localPath` This is where the program will attempt to place files.

from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import argparse
import sys
import fileinput

parser = argparse.ArgumentParser(description='Update object definitions from spreadsheets.')
parser.add_argument('path', metavar='path', nargs='?',
                    help='Path to Crimson Chronicles project root')
args = parser.parse_args()
if args.path == None:
    args.path = "."

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'
SPREADSHEETID = '1hxyrJsx0BcTtOFSlwuqyY3wYNqj_nxH3vDOUAoRUma4'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_service():
    # Get credentials and build service to access sheets API.
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)
    return service

def main():
    try:
        with open(args.path+'/.git/config') as f:
            config_file = f.read()
            if not "crimson-chronicles" in config_file:
                print("This is not a Crimson Chronicles project folder. Check your path argument.")
                return
    except EnvironmentError:
        print("This is not a Crimson Chronicles project folder. Check your path argument.")
        return

    service = get_service()
    # Get all sheets in spreadsheet.
    result = service.spreadsheets().get(spreadsheetId=SPREADSHEETID).execute()
    sheets = result.get('sheets', [])
    sheetNames = [sheet["properties"]["title"] for sheet in sheets]

    # Update our local files.
    for sheet in sheetNames:
        print('[.] Updating sheet: %s' % (sheet))
        if sheet.startswith('Mob'):
            pass
            # update_zone_mobs(service, sheet)
        else:
            update_team(service, sheet)

def get_towers(service, sheet):
    rangeName = '%s!C27:D' % (sheet)
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEETID, range=rangeName).execute()
    values = result.get('values', [])

    towers = {}
    if not values:
        return towers, True
    else:
        for row in values:
            # print(row)
            wurst = row[0]
            if len(row) == 1:
                print("\t[!] Missing filename")
                continue
            filename = row[1]
            towers[filename] = wurst
    return towers, False

def update_team(service, sheet):
    towers, err = get_towers(service, sheet)
    if err:
        print('\t[!] No data found.')
        return

    # Ugly: len(towers) number of file tree traversals.
    # Ugly: Can't verify that all towers has been found.
    for root, subdirs, files in os.walk(args.path):
        for f in files:
            if not f in towers:
                continue
            path = root+"/"+f
            print("\t[.] Found path for %s: %s" % (f, path))
            if not update_tower(path, towers[f]):
                print("\t[!] Couldn't update: %s" % (f))
            del towers[f]

def update_tower(path, tower):
    lines = [line.split("=") for line in tower.split('\n')]
    values = {}
    for i, vs in enumerate(lines):
        vals = [v.strip() for v in vs]
        if vals[1] == '':
            print("\t\t[!] Broken fields: %s" % (path))
            return False
        values[vals[0] + " = "] = vals[1]
    
    # Ugly: writes the whole file again.
    for i, line in enumerate(fileinput.input(path, inplace=1)):
        found = False
        for vs in values:
            if line.startswith(vs):
                sys.stdout.write(vs + values[vs] + '\n')
                del values[vs]
                found = True
                break
        if not found:
            sys.stdout.write(line)

    return True

if __name__ == '__main__':
    main()


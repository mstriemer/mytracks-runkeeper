#!/usr/bin/python

import httplib2
import urllib2
import pprint
import os
import json
from itertools import izip
from datetime import datetime

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import OAuth2WebServerFlow, OAuth2Credentials

from pykml import parser

# Copy your credentials from the APIs Console
CLIENT_ID = os.environ['GOOGLE_API_CLIENT_ID']
CLIENT_SECRET = os.environ['GOOGLE_API_CLIENT_SECRET']

# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

# Redirect URI for installed apps
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

def load_credentials():
    try:
        with open('credentials.json', 'r') as f:
            return OAuth2Credentials.new_from_json(f.read())
    except IOError, e:
        return None

def save_credentials(credentials):
    with open('credentials.json', 'w') as f:
        f.wite(credentials.to_json())

def authorize(client_id, client_secret, oauth_scope, redirect_uri):
    # Run through the OAuth flow and retrieve credentials
    flow = OAuth2WebServerFlow(client_id, client_secret, oauth_scope, redirect_uri)
    authorize_url = flow.step1_get_authorize_url()
    print 'Go to the following link in your browser: ' + authorize_url
    code = raw_input('Enter verification code: ').strip()
    credentials = flow.step2_exchange(code)
    return credentials

with open('runkeeper_credentials.json') as f:
    data = json.loads(f.read())
    rkaccess_token = data['access_token']

credentials = load_credentials()
if credentials is None:
    credentials = authorize(CLIENT_ID, CLIENT_SECRET, OAUTH_SCOPE, REDIRECT_URI)
    save_credentials(credentials)

# Create an httplib2.Http object and authorize it with our credentials
http = httplib2.Http()
http = credentials.authorize(http)

drive_service = build('drive', 'v2', http=http)

FOLDER_MIMETYPE = 'application/vnd.google-apps.folder'
files = drive_service.files().list().execute()

folders = [f for f in files['items'] if f['mimeType'] == FOLDER_MIMETYPE]

print("Please select a folder to sync tracks from:")
for i, folder in enumerate(folders):
    print "{}: {}".format(i, folder['title'])
index = raw_input("Folder number: ")

folder = folders[int(index)]
print("You chose the folder: {}".format(folder['title']))

tracks = [f for f in files['items'] if folder['id'] in [p['id'] for p in f['parents']]]
for i, track in enumerate(tracks):
    print('{}: {}'.format(i, track['title']))
index = raw_input("Track number: ")

track = tracks[int(i)]
resp, content = http.request(track['downloadUrl'], 'GET')
root = parser.fromstring(content)
ns = '{http://www.opengis.net/kml/2.2}'
placemark_tag = ns + 'Placemark'
tour = None
for child in root.Document.iterchildren():
    if child.tag == placemark_tag:
        if child.get('id') == 'tour':
            tour = child

assert tour is not None

path = []
start_time = None

ns = '{http://www.google.com/kml/ext/2.2}'
multi_track_tag = ns + 'MultiTrack'
track_tag = ns + 'Track'
for child in tour.iterchildren():
    if child.tag == multi_track_tag:
        multi_track = child
        for child in multi_track.iterchildren():
            if child.tag == track_tag:
                track = child
                children = track.iterchildren()
                for ts, geo in izip(children, children):
                    time = datetime.strptime(ts.text, '%Y-%m-%dT%H:%M:%S.000Z')
                    if start_time is None:
                        start_time = time
                    time_delta = time - start_time
                    longitude, latitude, altitude = geo.text.split(' ')
                    path.append({
                        'timestamp': time_delta.total_seconds(),
                        'altitude': altitude,
                        'longitude': longitude,
                        'latitude': latitude,
                        'type': 'gps',
                    })

path[0]['type'] = 'start'
path[-1]['type'] = 'end'

activity = {
    'type': 'Cycling',
    'equipment': 'None',
    'start_time': start_time.strftime("%A, %d %b %Y %H:%M:%S"),
    'notes': 'Auto submitted',
    'path': path,
    'post_to_facebook': False,
    'post_to_twitter': False,
}

activity_json = json.dumps(activity)

rk_http = httplib2.Http()
resp, content = rk_http.request('https://api.runkeeper.com/fitnessActivities',
        method='POST',
        headers={
            'Content-Type': 'application/vnd.com.runkeeper.NewFitnessActivity+json',
            'Authorization': "Bearer {}".format(rkaccess_token),
        },
        body=activity_json,
        )

pprint.pprint(resp)
pprint.pprint(content)

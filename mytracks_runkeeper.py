#!/usr/bin/python

import os

from runkeeper import upload_to_runkeeper
from drive import Drive
from models import DriveActivity

drive_service = Drive(
    os.environ['GOOGLE_API_CLIENT_ID'],
    os.environ['GOOGLE_API_CLIENT_SECRET'],
)

folders = drive_service.folders()
print("Please select a folder to sync tracks from:")
for i, folder in enumerate(folders):
    print "{}: {}".format(i, folder['title'])
index = raw_input("Folder number: ")

folder = folders[int(index)]
print("You chose the folder: {}".format(folder['title']))

tracks = drive_service.files(folder)
for i, track in enumerate(tracks):
    print('{}: {}'.format(i, track['title']))
index = raw_input("Track number: ")
track = tracks[int(index)]

q = DriveActivity.all()
q.filter('pk =', track['id'])
drive_activity = q[0]

content = drive_service.download(track)
activity = upload_to_runkeeper(content)

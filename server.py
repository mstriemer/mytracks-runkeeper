import os
import json
from datetime import datetime

import webapp2
from webapp2 import redirect
from webapp2_extras import jinja2
from google.appengine.api import urlfetch

from models import DriveActivity
from drive import Drive
from runkeeper import upload_to_runkeeper

urlfetch.set_default_fetch_deadline(45)
credentials_path = os.path.join(
    os.path.dirname(__file__),
    'google_api_credentials.json')
with open(credentials_path) as f:
    credentials = json.loads(f.read())

def DriveService():
  return Drive(credentials['client_id'], credentials['client_secret'])


class BaseHandler(webapp2.RequestHandler):

    @webapp2.cached_property
    def jinja2(self):
        # Returns a Jinja2 renderer cached in the app registry.
        return jinja2.get_jinja2(app=self.app)

    def render_response(self, _template, **context):
        # Renders a template and writes the result to the response.
        rv = self.jinja2.render_template(_template, **context)
        self.response.write(rv)


def find_drive_folder(drive_service, folder_name):
    drive_folders = drive_service.folders()
    drive_folder = next(
        f for f in drive_folders if f['title'] == 'My Tracks')
    return drive_folder


class DriveActivityList(BaseHandler):

    def get(self):
        q = DriveActivity.all()
        q.order('-uploaded_version_date')
        drive_service = DriveService()
        uploaded_drive_ids = [da.pk for da in q]
        drive_folder = find_drive_folder(drive_service, 'My Tracks')
        drive_files = drive_service.files(drive_folder)
        drive_files = [f for f in drive_files
                       if f['id'] not in uploaded_drive_ids]
        self.render_response(
            'drive_activity_list.html',
            drive_activities=q,
            drive_files=drive_files,
        )


class UploadDriveActivity(BaseHandler):

    def post(self, file_id):
        drive_service = DriveService()
        drive_file = drive_service.file(file_id)
        content = drive_service.download(drive_file)
        activity = upload_to_runkeeper(content)
        modified_date = datetime.strptime(
            drive_file['modifiedDate'],
            "%Y-%m-%dT%H:%M:%S.%fZ")
        drive_activity = DriveActivity(
            pk=file_id,
            name=drive_file['title'],
            uploaded_version_date=modified_date,
            runkeeper_activity_id=activity['id'],
        )
        drive_activity.put()
        return redirect('/')


application = webapp2.WSGIApplication([
    ('/', DriveActivityList),
    ('/upload/(.*)/', UploadDriveActivity),
], debug=True)

from google.appengine.ext import db


class DriveActivity(db.Model):
    pk = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    uploaded_version_date = db.DateTimeProperty(required=True)
    runkeeper_activity_id = db.IntegerProperty(required=True)

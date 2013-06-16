import httplib2

from apiclient.discovery import build
from oauth2client.client import OAuth2Credentials, OAuth2WebServerFlow

# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

# Redirect URI for installed apps
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
FOLDER_MIMETYPE = 'application/vnd.google-apps.folder'


class Drive(object):
    def __init__(self, client_id, client_secret):
        credentials = self.credentials(client_id, client_secret)

        # Create an httplib2.Http object and authorize it with our credentials
        http = httplib2.Http()
        self.http = credentials.authorize(http)

        self.service = build('drive', 'v2', http=http)
        self._files = None

    def files(self, parent=None):
        if self._files is None:
            self._files = self.service.files().list().execute()['items']
        if parent is None:
            return self._files
        else:
            return [f for f in self._files
                    if parent['id'] in [p['id'] for p in f['parents']]]

    def file(self, file_id):
        return self.service.files().get(fileId=file_id).execute()

    def load_credentials(self):
        try:
            with open('credentials.json', 'r') as f:
                return OAuth2Credentials.new_from_json(f.read())
        except IOError:
            return None

    def save_credentials(self, credentials):
        with open('credentials.json', 'w') as f:
            f.write(credentials.to_json())

    def authorize(self, client_id, client_secret):
        # Run through the OAuth flow and retrieve credentials
        flow = OAuth2WebServerFlow(
            client_id,
            client_secret,
            OAUTH_SCOPE,
            REDIRECT_URI,
        )
        authorize_url = flow.step1_get_authorize_url()
        print 'Go to the following link in your browser: ' + authorize_url
        code = raw_input('Enter verification code: ').strip()
        credentials = flow.step2_exchange(code)
        return credentials

    def credentials(self, client_id, client_secret):
        credentials = self.load_credentials()
        if credentials is None:
            credentials = self.authorize(client_id, client_secret)
            self.save_credentials(credentials)
        return credentials

    def folders(self):
        return [f for f in self.files() if f['mimeType'] == FOLDER_MIMETYPE]

    def download(self, drive_file):
        resp, content = self.service._http.request(drive_file['downloadUrl'])
        if resp.status == 200:
            return content
        else:
            raise IOError('server returned status {}'.format(resp.status))

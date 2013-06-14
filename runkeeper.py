import pprint
import httplib2
from itertools import izip
from datetime import datetime, timedelta
import time
import json

from pykml import parser


def upload_to_runkeeper(content):
    root = parser.fromstring(content)
    ns = '{http://www.opengis.net/kml/2.2}'
    tour = root.find('.//{ns}{tag}[@id="tour"]'.format(ns=ns, tag='Placemark'))

    assert tour is not None

    path = []
    start_time = None
    tz_offset = current_timezone_offset()

    ns = '{http://www.google.com/kml/ext/2.2}'
    track = root.find('.//{ns}{tag}'.format(ns=ns, tag='Track'))
    children = track.iterchildren()
    for ts, geo in izip(children, children):
        point_time = datetime.strptime(
            ts.text,
            '%Y-%m-%dT%H:%M:%S.000Z')
        point_time += tz_offset
        if start_time is None:
            start_time = point_time
        time_delta = point_time - start_time
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
    content_type = 'application/vnd.com.runkeeper.NewFitnessActivity+json'

    with open('runkeeper_credentials.json') as f:
        data = json.loads(f.read())
        rkaccess_token = data['access_token']

    with open('activity-{}.json'.format(start_time), 'w') as f:
        f.write(activity_json)

    rk_http = httplib2.Http()
    resp, content = rk_http.request(
        'https://api.runkeeper.com/fitnessActivities',
        method='POST',
        headers={
            'Content-Type': content_type,
            'Authorization': "Bearer {}".format(rkaccess_token),
        },
        body=activity_json,
    )

    pprint.pprint(resp)
    pprint.pprint(content)


def current_timezone_offset():
    tz_offset_seconds = time.altzone if time.daylight else time.timezone
    tz_offset = timedelta(seconds=tz_offset_seconds)
    if time.gmtime() > time.localtime():
        tz_offset = -tz_offset
    return tz_offset
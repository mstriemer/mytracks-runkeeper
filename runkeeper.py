import httplib2
from itertools import izip, tee
from datetime import datetime, timedelta
import time
import json
import xml.etree.ElementTree as parser
import logging


def upload_to_runkeeper(content):
    start_time, path = parse_track(content)

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

    logger = logging.getLogger('runkeeper_api')
    logger.info("Request: %s", activity_json)

    rk_http = httplib2.Http(timeout=45)
    resp, content = rk_http.request(
        'https://api.runkeeper.com/fitnessActivities',
        method='POST',
        headers={
            'Content-Type': content_type,
            'Authorization': "Bearer {}".format(rkaccess_token),
        },
        body=activity_json,
    )

    logger.info("Response: %s", resp)
    activity = {
        'id': int(resp['location'].split('/')[-1]),
        'location': resp['location'],
    }

    return activity


def current_timezone_offset():
    tz_offset_seconds = time.altzone if time.daylight else time.timezone
    tz_offset = timedelta(seconds=tz_offset_seconds)
    if time.gmtime() > time.localtime():
        tz_offset = -tz_offset
    return tz_offset

def parse_track(content):
    root = parser.fromstring(content)
    ns = '{http://www.opengis.net/kml/2.2}'
    tour = root.find('.//{ns}{tag}[@id="tour"]'.format(ns=ns, tag='Placemark'))

    assert tour is not None

    path = []
    start_time = None
    tz_offset = current_timezone_offset()

    ns = '{http://www.google.com/kml/ext/2.2}'
    track = root.find('.//{ns}{tag}'.format(ns=ns, tag='Track'))
    children, alt_finder = tee(track, 2)
    altitude = None
    for ts, geo in izip(alt_finder, alt_finder):
        geo_parts = geo.text.split(' ')
        if len(geo_parts) == 3:
            _, _, altitude = geo_parts
            break
    for ts, geo in izip(children, children):
        point_time = datetime.strptime(
            ts.text,
            '%Y-%m-%dT%H:%M:%S.%fZ')
        point_time += tz_offset
        if start_time is None:
            start_time = point_time
        time_delta = point_time - start_time
        geo_parts = geo.text.split(' ')
        if len(geo_parts) == 3:
            longitude, latitude, altitude = geo_parts
        elif len(geo_parts) == 2:
            longitude, latitude = geo_parts
        else:
            raise ValueError("need at least a lat and lon...")
        path.append({
            'timestamp': time_delta.total_seconds(),
            'altitude': altitude,
            'longitude': longitude,
            'latitude': latitude,
            'type': 'gps',
        })

    path[0]['type'] = 'start'
    path[-1]['type'] = 'end'

    return start_time, path

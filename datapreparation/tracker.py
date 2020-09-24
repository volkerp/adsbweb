import argparse
from datetime import datetime
import sys
from math import radians, cos, sin, asin, sqrt
from dataclasses import dataclass, field, asdict
import subprocess as sp
import json


import asterixfile


EDTF = 48.02220, 7.83292


args = None
msgs = []


def haversine(lat1, lon1, lat2, lon2):
    R =  6372.8 # Earth radius

    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
    c = 2*asin(sqrt(a))

    return R * c


def record_filter(rec, max_height_ft, max_range_km):
    """
    Return True if record is accepted
    """
    if 'target_adr' not in rec or 'pos_wgs84' not in rec:
        return False

    if rec['target_adr'] == 'baaeb0':
        return False  # reference transmitter

    if 'geom_height' in rec and rec['geom_height'] > max_height_ft:
        return False

    if 'flight_lvl' in rec and rec['flight_lvl'] * 100 > max_height_ft:
        return False

    if haversine(*EDTF, rec['pos_wgs84']['lat'], rec['pos_wgs84']['lon']) > max_range_km:
        return False

    return True


@dataclass
class Track:
    adr: str  # icao 24bit adr
    first_report: float
    last_report: float  # timestamp of last report
    reports: list
    target_ids: set = field(default_factory=set)
    mode3as: set = field(default_factory=set)
    emittercat: int = None

    def __str__(track):
        return "{}\t{}\t\t{}\t{}–{}\t{}".format(track.adr, track.target_ids, track.mode3as,
        datetime.utcfromtimestamp(track.first_report), datetime.utcfromtimestamp(track.last_report), len(track.reports))


tracks = {}
last_stamp = 0

def tracker(filename, max_height, max_range):
    global last_stamp
    for rec in asterixfile.process_file(filename):
        stamp = rec['block_stamp']

        if record_filter(rec, max_height, max_range):

            if rec['target_adr'] not in tracks:
                tracks[rec['target_adr']] = Track(rec['target_adr'], stamp, None, [])

            track = tracks[rec['target_adr']]

            track.reports.append(rec)
            if 'target_id' in rec:
                track.target_ids.add(rec['target_id'])
            if 'mode3a_code' in rec:
                track.mode3as.add(rec['mode3a_code'])
            if 'emitter_cat' in rec:
                track.emittercat = rec['emitter_cat']
            track.last_report = stamp

        if int(last_stamp/10.0) != int(stamp/10.0):  # every 10 seconds
            update_state()

        last_stamp = stamp


def update_state():
    for track_adr in list(tracks):
        track = tracks[track_adr]
        if track.last_report < last_stamp - args.track_timeout:
            if len(track.reports) < args.track_min:
                msgs.append("Dropping: " + str(track))
            else:
                save_track(track)
                msgs.append("Saving: " + str(track))
            del tracks[track_adr]

    print_stats()


def save_track(track):
    filename = datetime.utcfromtimestamp(track.first_report).strftime('%Y-%m-%d_%H:%M:%S') + '_' + str(track.adr) + '.json'

    # consolidate reports
    # skip reports which are too close to another to save space
    position_reports = []
    last_time_trans = track.reports[0]['time_trans']
    position_reports.append(track.reports[0]['pos_wgs84'])  # add the first
    for i in range(1, len(track.reports) - 2):
        report = track.reports[i]
        if report['time_trans'] > last_time_trans + 1.0:
            entry = {}
            entry.update(report['pos_wgs84'])
            entry['time_trans'] = report['time_trans']
            if 'geom_height' in report:
                entry['geom_height'] = report['geom_height']
            if 'flight_lvl' in report:
                entry['flight_lvl'] = report['flight_lvl']
            position_reports.append(entry)
            last_time_trans = report['time_trans']
        else:
            continue  # skip this report

    position_reports.append(track.reports[-1]['pos_wgs84'])  # add the last

    target_id = next(iter(track.target_ids)) if len(track.target_ids) > 0 else None
    mode3a = next(iter(track.mode3as)) if len(track.mode3as) > 0 else None

    with open(args.outdir + '/' + filename, 'w') as file:
        json.dump({'start': track.first_report, 'end': track.last_report, 'report': track.reports[0],
        'target_id': target_id, 'mode3a': mode3a, 'emittercat': track.emittercat, 'positions': position_reports}, file)


def print_stats():
    global msgs
    _ = sp.call('clear', shell=True)  # clear the terminal
    print(datetime.utcfromtimestamp(last_stamp), end='\n')
    for track in tracks.values():
        print(track)

    if len(msgs) > 30:
        msgs = msgs[-30:]

    for msg in msgs[::-1]:
        print(msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate tracks from Cat21.')
    parser.add_argument('filenames', help='filename(s)', nargs='+')
    parser.add_argument('--height', dest='max_height', type=float, help='Max height (ft)', default=5000.0)
    parser.add_argument('--range', dest='max_range', type=float, help='Max dist from EDTF (km)', default=30.0)
    parser.add_argument('--timeout', dest='track_timeout', type=float, help='Track timeout (s)', default=60.0)
    parser.add_argument('--reports', dest='track_min', type=float, help='Min reports for track', default=5)
    parser.add_argument('--outdir', dest='outdir', help='Output directory', default='./')

    args = parser.parse_args()

    for filename in args.filenames:
        tracker(filename, args.max_height, args.max_range)

import argparse
from datetime import datetime
import os
import sys
import json
from collections import OrderedDict
import subprocess as sp

args = None
daystats = OrderedDict()
iacoadrs = {}

def _datetime_isoformat(dt: datetime):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def process_track(filename):
    with open(filename, 'r') as file:
        track = json.load(file)

        start = datetime.utcfromtimestamp(track['start'])
        end = datetime.utcfromtimestamp(track['end'])

        start_date = start.strftime('%Y-%m-%d')
        start_yday = start.timetuple().tm_yday
        end_date = end.strftime('%Y-%m-%d')

        if start_date not in daystats:
            daystats[start_date] = []

        daystats[start_date].append({'start': _datetime_isoformat(start), 'end': _datetime_isoformat(end), 'target_adr': track['report']['target_adr'],
        'target_id': track['target_id'], 'filename': os.path.basename(filename)})

        iacoadrs[track['report']['target_adr']] = True


def print_stats():
    _ = sp.call('clear', shell=True)  # clear the terminal
    for date, entries in daystats.items():
        print(date, len(entries), entries)


def save_stats():
    with open(args.outdir + 'mainindex.json', 'w') as file:
        json.dump(daystats, file, indent=1)

    with open(args.outdir + 'ac_stats.txt', 'w') as file:
        for line in iacoadrs.keys():
            file.write(line + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate day based statistics')
    parser.add_argument('filenames', help='filename(s)', nargs='+')

    parser.add_argument('--height', dest='max_height', type=float, help='Max height (ft)', default=6000.0)
    parser.add_argument('--range', dest='max_range', type=float, help='Max dist from EDTF (km)', default=30.0)
    parser.add_argument('--timeout', dest='track_timeout', type=float, help='Track timeout (s)', default=60.0)
    parser.add_argument('--reports', dest='track_min', type=float, help='Min reports for track', default=3)
    parser.add_argument('--outdir', dest='outdir', help='Output directory', default='./')

    args = parser.parse_args()

    for filename in args.filenames:
        process_track(filename)
        #print_stats()

    save_stats()

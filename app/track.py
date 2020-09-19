from dataclasses import dataclass
from datetime import datetime
import json
import os
import sys

MAININDEX = 'mainindex.json'
TRACKSDIR = os.environ.get('TRACKSDIR') + '/'
main_index = None

EMITTERCAT = {
    0: 'no info',
    1: 'light ac < 7t',
    2: 'small ac < 34t',
    3: 'medium ac < 136t',
    4: 'High Vortex Large',
    5: 'heavy ac',
    6: 'highly manoeuvrable',
    10: 'rotocraft',
    11: 'glider/sailplane',
    12: 'lighter-than-air',
    13: 'UAV',
    14: 'space vehicle',
    15: 'ultralight',
    16: 'skydiver',
    20: 'emergency vehicle',
    21: 'service vehicle',
    22: 'fixed ground',
    23: 'cluster obstacle',
    24: 'line obstacle'
}


def _datetime_fromisoformat(s: str):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')


def _seconds_since_midnight(d: datetime):
    return (d - d.replace(hour = 0, minute = 0, second = 0)).seconds


@dataclass
class Track:
    start: datetime
    end: datetime
    adr: str
    id: str
    filename: str
    start_s: int = -1   # seconds since midnight
    len_s: int = -1  # length in secs
    overlap_level: int = -1  # time overlap level with other tracks
    mode3a: str = None
    reports = None
    emittercat = None

    def __post_init__(self):
        self.start_s = _seconds_since_midnight(self.start)
        self.len_s = (self.end - self.start).seconds


def resolve_overlap(tracks):
    """
    Check for overlapping track intervals.
    Assign each track an level value according to other flights in same interval
    """
    TIME, TYPE, TRCK = 0, 1, 2
    times = []

    for track in tracks.values():
        times.append((track.start_s, 's', track))
        times.append((track.start_s + track.len_s, 'e', track))

    times = sorted(times, key=lambda entry: entry[TIME])

    def find_level(lvls):
        # find lowest possible level
        for i in range(len(lvls)):
            if i not in lvls:
                return i

        return len(lvls)

    levels = []
    for e in times:
        if e[TYPE] == 's':
            lvl = find_level(levels)
            e[TRCK].overlap_level = lvl
            levels.append(lvl)    # place track at level
        else:
            levels.remove(e[TRCK].overlap_level)   # remove track at level

    return tracks


def read_main_index():
    """
    Read main index.
    Ordered list of days.
    """
    with open(TRACKSDIR + MAININDEX, 'r') as file:
        data = json.load(file)

    return data


def read_track(filename: str) -> dict:
    """
    Read single track and return dict
    """
    filename = os.path.basename(filename)
    if not filename.endswith('.json'):    
        return dict()

    with open(TRACKSDIR + filename, 'r') as file:
        data = json.load(file)

    return data


def read_day(date):
    """
    Read all track files of a given date
    """
    tracks = {}
    if date.strftime('%Y-%m-%d') in main_index:
        for entry in main_index[date.strftime('%Y-%m-%d')]:
            track = Track(_datetime_fromisoformat(entry['start']), _datetime_fromisoformat(entry['end']), entry['target_adr'], entry['target_id'], entry['filename'])
            track_dict = read_track(track.filename)
            track.reports = json.dumps(track_dict)
            track.mode3a = oct(track_dict['mode3a'])[2:].rjust(4, '0') if track_dict['mode3a'] else ''
            track.emittercat = EMITTERCAT.get(track_dict.get('emittercat'))
            tracks[track.filename] = track

    return resolve_overlap(tracks)


# read main index
main_index = read_main_index()

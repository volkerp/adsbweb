from app import app
from datetime import datetime
from calendar import monthrange
from collections import OrderedDict
from flask import render_template, abort
import json
from .track import main_index, read_day, read_track


def calendar_data(year : int):
    months = []
    names = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']

    for m in range(1, 13):
        month = { 'num': m, 'name': names[m-1] }
        month['day_ofs'], month['day_num'] = monthrange(year, m)

        for day in range(1, month['day_num'] + 1):
            yday = datetime(year, m, day).timetuple().tm_yday
            if yday in main_index:
                pass

        months.append(month)

    return months


def render_flight_profile_svg(track):
    scale = 1.0
    height = 100
    svg = '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{}" height="{}">\n'.format(int((track['end'] - track['start']) / scale), height)
    for x, posreport in enumerate(track['positions']):
        geom_height = posreport.get('geom_height', 0.0)
        svg += '<line style="stroke:#888; stroke-width:1;" x1="{}" y1="{}" x2="{}" y2="{}" shape-rendering="crispEdges" />\n'.format(x, height, x, height-geom_height / 100.0)

    svg += '</svg>'
    return svg


@app.route('/test')
def test():
    return 'Test ok'


@app.route('/favicon.ico')
def favicon():
    abort(404)


@app.route('/', defaults={'datestr': '2020-01-02', 'adr': None})
@app.route('/<string:datestr>', defaults={'adr': None})
@app.route('/<string:datestr>/<string:adr>')
def index(datestr, adr):
    date = datetime.strptime(datestr, '%Y-%m-%d')

    selected_track = None
    selected_filename = None
    svg = None
    # read all tracks of day
    day_tracks = read_day(date)

    if adr is not None:
        selected_track = read_track(adr)
        selected_filename = adr
        svg = render_flight_profile_svg(selected_track)

    data = {'months': calendar_data(2020),
        'main_index': main_index,
        'date': datestr,
        'day_tracks': day_tracks,
        'selected_track': selected_track,
        'selected_filename': selected_filename,
        'svg': svg }

    return render_template('index.html', data=data)




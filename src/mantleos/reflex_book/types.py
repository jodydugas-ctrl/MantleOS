"""Offline Bool3 and bounded synthetic observation semantics."""
from datetime import datetime, timezone
import re
from .errors import refuse

TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
TRUE, FALSE, UNKNOWN = 'TRUE', 'FALSE', 'UNKNOWN'


def and3(values):
    values = list(values)
    return FALSE if FALSE in values else UNKNOWN if UNKNOWN in values else TRUE


def or3(values):
    values = list(values)
    return TRUE if TRUE in values else UNKNOWN if UNKNOWN in values else FALSE


def not3(value):
    return UNKNOWN if value == UNKNOWN else FALSE if value == TRUE else TRUE


def timestamp(value):
    if type(value) is not str or not TIMESTAMP.fullmatch(value):
        refuse('E_TIMESTAMP', 'timestamp must use YYYY-MM-DDTHH:MM:SSZ')
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        refuse('E_TIMESTAMP', 'invalid UTC timestamp')


def _shape(value, fields, what):
    if type(value) is not dict or set(value) != set(fields):
        refuse('E_SHAPE', f'{what} must contain exactly {sorted(fields)}')


def _i(value, low, high, field):
    if type(value) is not int or not low <= value <= high:
        refuse('E_RANGE', f'{field} must be an integer in [{low},{high}]')


def validate_value(type_name, value):
    if type_name == 'Int':
        _i(value, -(2**31), 2**31-1, 'Int')
    elif type_name == 'GeoFix':
        fields = ['type','lat_e6','lon_e6','accuracy_m','observed_at','source']
        _shape(value, fields, 'GeoFix')
        if value['type'] != 'GeoFix':
            refuse('E_TYPE', 'GeoFix type tag mismatch')
        _i(value['lat_e6'], -90000000, 90000000, 'lat_e6')
        _i(value['lon_e6'], -180000000, 180000000, 'lon_e6')
        _i(value['accuracy_m'], 0, 100000, 'accuracy_m')
        timestamp(value['observed_at'])
        if type(value['source']) is not str or not value['source'].startswith('synthetic:') or len(value['source']) > 80:
            refuse('E_SOURCE', 'prototype requires synthetic: provenance marker')
    elif type_name == 'Region':
        fields = ['type','crs','lat_min_e6','lat_max_e6','lon_min_e6','lon_max_e6']
        _shape(value, fields, 'Region')
        if value['type'] != 'Region' or value['crs'] != 'WGS84-E6-RECT/0.1':
            refuse('E_TYPE', 'unsupported Region tag/CRS')
        for coord in ('lat_min_e6','lat_max_e6'):
            _i(value[coord], -55000000, 55000000, coord)
        for coord in ('lon_min_e6','lon_max_e6'):
            _i(value[coord], -180000000, 180000000, coord)
        if value['lat_min_e6'] >= value['lat_max_e6'] or value['lon_min_e6'] >= value['lon_max_e6']:
            refuse('E_RANGE', 'Region rectangle must be nonempty and not cross antimeridian')
    else:
        refuse('E_TYPE', f'unsupported type: {type_name}')
    return value


def geo_outside(position, region):
    """Conservative deterministic demo rectangle, NOT a true geodesic geofence.

    Latitudes outside +/-55 degrees are UNKNOWN. Fixed lower-bound scale
    factors deliberately understate metres-per-degree. Boundary uncertainty
    returns UNKNOWN rather than an unsafe categorical claim.
    """
    if abs(position['lat_e6']) > 55000000:
        return UNKNOWN
    acc = position['accuracy_m']
    # Differences in integer microdegrees, compared as integer metre-microdegrees.
    lat, lon = position['lat_e6'], position['lon_e6']
    amin, amax = region['lat_min_e6'], region['lat_max_e6']
    omin, omax = region['lon_min_e6'], region['lon_max_e6']
    lat_out = max(amin - lat, lat - amax, 0)
    lon_out = max(omin - lon, lon - omax, 0)
    # Conservative scale factors valid for demonstration in +/-55 latitude band.
    if lat_out * 110000 > acc * 1000000 or lon_out * 50000 > acc * 1000000:
        return TRUE
    if amin <= lat <= amax and omin <= lon <= omax:
        lat_margin = min(lat - amin, amax - lat)
        lon_margin = min(lon - omin, omax - lon)
        if lat_margin * 110000 > acc * 1000000 and lon_margin * 50000 > acc * 1000000:
            return FALSE
    return UNKNOWN

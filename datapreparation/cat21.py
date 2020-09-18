from bitstring import Bits
from functools import partial

'''
Asterix Cat21 decoder
(c) Volker Poplawski 2019
'''

def mask(n):
    return (1 << n) - 1


def bitextrct(v: bytes, s: int, e: int, signed = False):
    """ extract bits starting a s up to e (excluded)
    """
    left_byte_ix = s // 8
    right_byte_ix = (e-1) // 8
    v = bytes([v[left_byte_ix] & mask(8 - (s % 8))]) + v[left_byte_ix + 1:right_byte_ix + 1]
    i = int.from_bytes(v, 'big', signed=signed)
    i = i >> ((8 - ((e-1) % 8)) - 1)
    return i


def decodeIcaoStr(data):
    """decode icao 8 character string encoded in 6 bytes"""
    chrs = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ                     0123456789      '
    #b = Bits(bytes=data, length=6 * 8)
    return ''.join([chrs[ bitextrct(data, i*6, i*6+6) ] for i in range(8)])


def count_extends(data):
    """Count number of extended bytes"""
    return next((i + 1 for i, b in enumerate(data) if (b & 0x1) == 0), 0)


def decode_fspec(data):
    """Returns FRN from Fspec section as list()"""
    numExtends = count_extends(data)
    iterbits = lambda n: (7 - i for i in range(7, 0, -1) if n & (1 << i))  # iterate over non-zero bit indexes
    return [j + i*7 + 1 for i in range(numExtends) for j in iterbits(data[i])], numExtends


def iterate_fields(uap, data, out):
    frns, size = decode_fspec(data)
    data = data[size:]           # skip fspec section
    for frn in frns:
        name, len_type, *cb = uap[frn]
        if len(cb) > 0:                     # callback function for this frn?
            out[name] = cb[0](data)
        length = len_type(data, out)
        size += length
        data = data[length:]           # advance to next field
    return size


def fixed(size):
    return lambda *args: size


def variable():
    return lambda data, *args: count_extends(data)


def repetive(size):
    return lambda data, *args: data[0] * size + 1


def explicit():
    return lambda data, *args: data[0]


def compound(uap):
    return partial(iterate_fields, uap)    # bind 'uap' to first parameter


def extrct(data, ofs, len, signed=True):
    return int.from_bytes(data[ofs:ofs+len], byteorder='big', signed=True)


def target_report(data):
    b = Bits(bytes=data, length=8)
    d = {'ATP': b[0:3].uint, 'ARC': b[3:5].uint, 'RC': b[5:6].uint, 'RAB': b[6:7].uint}
    if b[7]:
        b = Bits(bytes=data[1:], length=8)
        d.update({'DCR': b[0:1].uint, 'GBS': b[1:2].uint, 'SIM': b[2:3].uint, 'TST': b[3:4].uint, 'SAA': b[4:5].uint, 'CL': b[5:7].uint})
    return d


def ac_op_state(data):
    b = Bits(bytes=data, length=8)
    return {'RA': b[0:1].uint, 'TC': b[1:3].uint, 'TS': b[3:4].uint, 'ARV': b[4:5].uint,
        'CDTI': b[5:6].uint, 'TCAS': b[6:7].uint, 'SA': b[7:8].uint
    }


def time_recp_pos_hp(data):
    return {'FSI': Bits(bytes=data, length=8)[0:2].uint, 'time': Bits(bytes=data, length=4*8)[2:].uint / 2**30}


def time_recp_velo_hp(data):
    return {'FSI': Bits(bytes=data, length=8)[0:2].uint, 'time': Bits(bytes=data, length=4*8)[2:].uint / 2**30}


def ground_vector(data):
    b = Bits(bytes=data, length=4*8)
    return {'RE': b[0:1].uint, 'speed': round(b[1:16].uint / 2**14, 3), 'angle': round(b[16:32].uint * (306.0/2**16), 3)}


def baro_vert_rate(data):
    b = Bits(bytes=data, length=8)
    return {'RE': b[0:1].uint, 'rate': b[1:16].int / 6.25}


def geom_vert_rate(data):
    b = Bits(bytes=data, length=8)
    return {'RE': b[0:1].uint, 'rate': b[1:16].int / 6.25}


def quality_ind(data):
    b = Bits(bytes=data, length=8)
    d = {'NUCr': b[0:4].uint, 'NUCp': b[4:7].uint}
    if b[7]:
        b = Bits(bytes=data[1:], length=8)
        d.update({'NICBARO': b[0:1].uint, 'SIL': b[1:3].uint, 'NACp': b[3:7].uint})
    if b[7]:
        b = Bits(bytes=data[2:], length=8)
        d.update({'SILs': b[2:3].uint, 'SDA': b[3:5].uint, 'GVA': b[5:7].uint})
    if b[7]:
        b = Bits(bytes=data[3:], length=8)
        d.update({'PIC': b[0:4].uint})
    return d


def selected_alt(data):
    b = Bits(bytes=data, length=2*8)
    return {'SAS': b[0:1].uint, 'src': b[1:3].uint, 'alt': b[3:16].int * 25}


def target_state(data):
    b = Bits(bytes=data, length=8)
    return {'ICF': b[0:1].uint, 'LNAV': b[1:2].uint, 'ME': b[2:3].uint, 'PS': b[3:6].uint, 'SS': b[6:8].uint}


def mops_ver(data):
    b = Bits(bytes=data, length=8)
    return {'VNS': b[1:2].uint, 'VN': b[2:5].uint, 'LTT': b[5:8].uint}


uap = {
    36: ('ac_op_state', fixed(1)), # ac_op_state),
    1: ('data_src', fixed(2), lambda data: {'SAC': data[0], 'SIC': data[1]}),
    4: ('service_id', fixed(1), lambda data: data[0]),
    35: ('service_mng', fixed(1)),
    30: ('emitter_cat', fixed(1), lambda data: data[0]),
    2: ('target_report', variable(), target_report),
    19: ('mode3a_code', fixed(2), lambda data: int.from_bytes(data[:2], byteorder='big', signed=False) & 0xfff),
    5: ('time_apl_pos', fixed(3), lambda data: extrct(data, 0, 3, signed=False) / 128.0),
    8: ('time_appl_velo', fixed(3), lambda data: extrct(data, 0, 3, signed=False) / 128.0),
    12: ('time_recp_pos', fixed(3), lambda data: extrct(data, 0, 3, signed=False) / 128.0),
    13: ('time_recp_pos_hp', fixed(4)), # time_recp_pos_hp),
    14: ('time_recp_velo', fixed(3), lambda data: extrct(data, 0, 3, signed=False) / 128.0),
    15: ('time_recp_velo_hp', fixed(4)), # time_recp_pos_hp),
    28: ('time_trans', fixed(3), lambda data: extrct(data, 0, 3, signed=False) / 128.0),
    11: ('target_adr', fixed(3), lambda data: data[:3].hex()),
    17: ('quality_ind', variable()), # quality_ind),
    34: ('traj_intent', compound({
        1: ('COM', fixed(1)),
        2: ('traj_data', repetive(15))
    })),
    6: ('pos_wgs84', fixed(6), lambda data: {'lat': round(extrct(data, 0, 3) * (180.0/2**23), 5), 'lon': round(extrct(data, 3, 3) * (180.0/2**23), 5)}),
    7: ('pos_wgs84', fixed(8), lambda data: {'lat': round(extrct(data, 0, 4) * (180.0/2**30), 5), 'lon': round(extrct(data, 4, 4) * (180.0/2**30), 5)}),
    38: ('msg_ampl', fixed(1), lambda data: extrct(data, 0, 1)),
    16: ('geom_height', fixed(2), lambda data: extrct(data, 0, 2, signed=True) * 6.25),
    21: ('flight_lvl', fixed(2), lambda data: extrct(data, 0, 2, signed=False) / 4.0),
    32: ('sel_alt', fixed(2)), # selected_alt),
    33: ('final_sel_alt', fixed(2)),
    9: ('airspeed', fixed(2)),
    10: ('true_airspeed', fixed(2)),
    22: ('mag_heading', fixed(2)),
    24: ('Baro Vert Rate', fixed(2)), #, baro_vert_rate),
    25: ('geom_vert_rate', fixed(2)), #, geom_vert_rate),
    26: ('ground_vector', fixed(4), ground_vector),
    3: ('track_num', fixed(2)),
    27: ('angle_rate', fixed(2)),
    29: ('target_id', fixed(6), lambda data: decodeIcaoStr(data[:6])),
    23: ('target_state', fixed(1)), #, target_state),
    18: ('mops_ver', fixed(1)), #, mops_ver),
    31: ('met_info', compound({
        1: ('Wind Speed', fixed(2)),
        2: ('Wind Direction', fixed(2)),
        3: ('Temperature', fixed(2)),
        4: ('Turbulance', fixed(1))
    })),
    20: ('rollangle', fixed(2)),
    39: ('mode_s_data', repetive(8)),
    40: ('ACAS Report', fixed(7)),
    37: ('Surface Cap', variable()),
    42: ('Data Ages', compound({
        1: ('AC Op Status Age', fixed(1)),
        2: ('Target Report Age', fixed(1)),
        3: ('Mode3A Age', fixed(1)),
        4: ('Quality Age', fixed(1)),
        5: ('Traj Itent Age', fixed(1)),
        6: ('Msg Amplitude Age', fixed(1)),
        7: ('Geom Height Age', fixed(1)),
        8: ('Flight Lvl Age', fixed(1)),
        9: ('Selected Alt Age', fixed(1)),
        10: ('Final Selected Alt Age', fixed(1)),
        11: ('Airspeed Age', fixed(1)),
        12: ('True Airspeed Age', fixed(1)),
        13: ('Mag Heading Age', fixed(1)),
        14: ('Baro Vert Age', fixed(1)),
        15: ('Geom Vert Age', fixed(1)),
        16: ('Ground Vector Age', fixed(1)),
        17: ('Angle Rate Age', fixed(1)),
        18: ('Target Id Age', fixed(1)),
        19: ('Target State Age', fixed(1)),
        20: ('Met Info Age', fixed(1)),
        21: ('Roll Angle Age', fixed(1)),
        22: ('ACAS Report Age', fixed(1)),
        23: ('Surface Cap Age', fixed(1))
    })),
    41: ('Receiver Id', fixed(1)),
    48: ('Rsrvf Exp', explicit()),
    49: ('SP', explicit())
}


def decode_records(data):
    ret = []
    while len(data) > 1:
        s = {}
        rec_size = iterate_fields(uap, data, s)
        ret.append(s)
        data = data[rec_size:]
    return ret


if __name__ == '__main__':
    TESTBLOCK = bytes.fromhex("150048dd1ff34bc1222f28010804439eca23c4ad058b9e4ba74b439eca25\
    1378c3439d6f3787d81b18240f5101b00205f0000785cfb3439ed1407535\
    54d82000ad0381501c001cff")

    TESTBLOCK = bytes.fromhex("15005ddd1ffb6bd1a3042f280004439eca22c6980629e24cab9b439eca253c1a8d\
    439ebb1d5f8a8917b02ff113a012024a05c8400000082e8017439ed14994\
    b8d9256003c5c81bb6f3c358030c100302010c0202201007c40858050700")

    s = decode_records(TESTBLOCK[3:])
    print(s)

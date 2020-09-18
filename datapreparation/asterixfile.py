import sys
import cat21
import lzma
import argparse
import json


def records_from_blocks(data):
    """
    yields list of records of block(s)
    """

    while True:
        if len(data) < 3:
            break
        cat = int.from_bytes(data[0:1], byteorder='big', signed=False)
        blocksize = int.from_bytes(data[1:3], byteorder='big', signed=False)
        if len(data) < blocksize:
            break
        if cat == 21:
            try:
                yield cat21.decode_records(data[3:blocksize])
            except KeyError:
                break

        data = data[blocksize:]


def blocks_from_recording(file):
    """Return blocks from asterixRecorder as iterable"""
    while True:
        header = file.read(13)
        if len(header) < 13:
            break
        stamp = int.from_bytes(header[5:13], byteorder='big', signed=False)
        data = file.read(int.from_bytes(header[1:5], byteorder='big', signed=False) - 13)
        yield stamp/1000.0, data


def iterate_records(filelike):
    """
    Iterate of records of a asterix file
    Return dict
    """
    for stamp, blockdata in blocks_from_recording(filelike):
        for rec_list in records_from_blocks(blockdata):
            for rec in rec_list:
                rec['block_stamp'] = stamp  # add block time stamp to every record in block
                yield rec


def process_file(filename):
    """
    Process asterix file (optional .xz compressed)
    """
    if filename[-3:] == '.xz':
        fopen = lzma.open
    else:
        fopen = open

    with fopen(filename, 'rb') as file:
        for rec in iterate_records(file):
            yield rec


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dump cat21 asterix recording.')
    parser.add_argument('filename', help='filename', nargs='+')
    parser.add_argument('--outfile', dest='outfile', type=argparse.FileType('wb'), help='Output file')

    args = parser.parse_args()

    for rec in process_file(sys.argv[len(sys.argv) - 1]):
        print(rec)

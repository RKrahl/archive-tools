#! /usr/bin/python3
"""Convert a tar file to POSIX.1-2001 (pax) format.
"""

import argparse
from pathlib import Path
import tarfile


compression_map = {
    '.tar': '',
    '.tar.gz': 'gz',
    '.tar.bz2': 'bz2',
    '.tar.xz': 'xz',
}
"""Map path suffix to compression mode."""


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('input', type=Path,
                           help=("input tar file"))
    argparser.add_argument('output', type=Path,
                           help=("output tar file"))
    args = argparser.parse_args()

    try:
        compression = compression_map["".join(args.output.suffixes)]
    except KeyError:
        # Last ressort default
        compression = 'gz'
    mode = 'x:' + compression
    pax = tarfile.PAX_FORMAT
    with tarfile.open(args.input, mode='r') as inp:
        with tarfile.open(args.output, mode=mode, format=pax) as outp:
            for ti in inp:
                if ti.isfile():
                    outp.addfile(ti, fileobj=inp.extractfile(ti))
                else:
                    outp.addfile(ti)


if __name__ == "__main__":
    main()

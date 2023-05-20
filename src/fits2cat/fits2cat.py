#!/usr/bin/python
"""
FITS2CAT.

Combine multiple FITS images into an RGB FITS image.

Copyright (C) 2023  Maurizio D'Addona <mauritiusdadd@gmail.com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import sys
import os
import io
import argparse
from astropy.table import Table
from astropy.time import Time


def __argshandler(options=None):
    """
    Handle input arguments.

    Parameters
    ----------
    options : TYPE, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    args : TYPE
        DESCRIPTION.

    """
    parser = argparse.ArgumentParser(
        description="Converts a simple fits catalog into a plain text ascii."
    )

    parser.add_argument(
        "catfile", metavar='CAT_FITS_FILE', type=str, help="input catalogs"
    )

    parser.add_argument(
        "--header", type=str, metavar='HDR_FILE', default=None, required=False,
        help='Read the header of the catalog from the file %(metavar)s'
    )

    parser.add_argument(
        "--version", type=str, metavar='VERSION', default="1.0.0",
        required=False, help='Set the file version to %(metavar)s'
    )

    parser.add_argument(
        "--text-columns", type=str, metavar='TEXT_COLUMNS', default=None,
        help='Columns to be safely converted to text.'
    )

    parser.add_argument(
        "--exclude-columns", type=str, metavar='EXCLUDE_COLUMNS', default=None,
        help='Columns to be excluded.'
    )

    parser.add_argument(
        "--mask-values", type=str, metavar='VALS', default="99,-99",
        required=False,
        help='Mask the values %(metavar)s with a -99. Default values are'
        '%(default)s'
    )

    args = None
    if options is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(options)

    return args


def main(args=None):
    """
    Run the main function of this module.

    Returns
    -------
    None.

    """
    args = __argshandler(args)
    basename = os.path.splitext(os.path.basename(args.catfile))[0]

    header = ""
    if args.header is not None:
        try:
            with open(args.header, 'r') as f:
                header = ''.join([f'# {x}' for x in f.readlines()])
                if header[-2:] != '#\n':
                    header = header + '#\n'
                header = header.replace('{file_name}', basename)
                header = header.replace('{version}', args.version)
                header = header.replace('{build_time}', Time.now().isot)
        except (OSError, IOError) as exc:
            print(
                f"Warning, cannot read header from file {args.header}: {exc}",
                file=sys.stderr
            )

    my_cat = Table.read(args.catfile)

    for mask_val in args.mask_values.split(','):
        mask_val = float(mask_val)
        for col in my_cat.colnames:
            try:
                my_cat[col].mask = my_cat[col].mask | (my_cat[col] == mask_val)
            except Exception:
                continue

    if args.text_columns:
        for col in args.text_columns.split(','):
            for j, v in enumerate(my_cat[col]):
                my_cat[col][j] = f'"{my_cat[col][j]}"'

    my_cat = my_cat.filled(-99)

    if args.exclude_columns:
        for col in args.exclude_columns.split(','):
            my_cat.remove_column(col)

    fh = io.StringIO()
    my_cat.write(
        fh,
        format='ascii.fixed_width',
        delimiter=None,
        bookend=False
    )

    header += '#' + fh.getvalue().splitlines()[0][1:] + '\n'
    table_string = '\n'.join(fh.getvalue().splitlines()[1:])

    with open(f'{basename}.cat', 'w') as f:
        f.write(header + table_string)


if __name__ == '__main__':
    main()

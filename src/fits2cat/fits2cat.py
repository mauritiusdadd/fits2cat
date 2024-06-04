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
import re
import argparse

import numpy as np
import pandas as pd

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

    my_cat = Table.read(args.catfile)
    my_df = my_cat.to_pandas()

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

    # Evaluate expressions
    res_map = {}
    for m in re.finditer('{.*}', header):
        expr = header[m.start()+1: m.end()-1]
        if expr[-1] != ')':
            print(f"WARNING: missing ) in expression: {expr}")
            continue
        func_name, args_str = expr[:-1].split('(')

        func = None
        if func_name == 'len':
            func = len
        if func_name == 'sum':
            func = sum
        elif func_name == 'sum':
            func = np.sum
        elif func_name == 'max':
            func = np.max
        elif func_name == 'min':
            func = np.min
        elif func_name == 'mean':
            func = np.mean
        elif func_name == 'std':
            func = np.std
        else:
            print(
                f"WARNING: Unknown function {func_name} in expression: {expr}"
            )
            continue

        replaced_arg_str = args_str
        for x in re.finditer(r'\$[^+*-/^=]+', args_str):
            sub_str = args_str[x.start():x.end()]
            replaced_arg_str = replaced_arg_str.replace(
                sub_str, f"my_df.{sub_str[1:]}"
            )

        func_res = func(pd.eval(replaced_arg_str, target=my_df))
        res_map[expr] = func_res

    for expr, res in res_map.items():
        header = header.replace(f'{{{expr}}}', f'{res}')

    for mask_val in args.mask_values.split(','):
        mask_val = float(mask_val)
        for col in my_cat.colnames:
            try:
                my_cat[col].mask = my_cat[col].mask | (my_cat[col] == mask_val)
            except Exception:
                continue

    for col in my_cat.colnames:
        if (
            isinstance(my_df[col].dtype, pd.StringDtype) or
            my_df[col].dtype == 'object'
        ):
            try:
                my_cat[col] = my_df[col].str.replace(' ','_')
            except TypeError:
                new_col = (
                    (
                        my_df[col]
                        .str
                        .decode("utf-8")
                    ).str.strip()
                ).str.replace(' ', '_')

                my_cat[col] = new_col


    my_cat = my_cat.filled(-99)

    if args.exclude_columns:
        for col in args.exclude_columns.split(','):
            my_cat.remove_column(col)

    fh = io.StringIO()
    my_cat.write(
        fh,
        format='ascii.fixed_width',
        delimiter=None,
        bookend=False,
    )

    header += '#' + fh.getvalue().splitlines()[0][1:] + '\n'
    table_string = '\n'.join(fh.getvalue().splitlines()[1:])

    with open(f'{basename}.cat', 'w') as f:
        f.write(header + table_string)


if __name__ == '__main__':
    main()

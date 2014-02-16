# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
``fitshead`` is a command line script based on astropy.io.fits for printing
the header(s) of a FITS file to the standard output.

Example uses of fitshead:

1. Print the header of all the HDUs of a single .fits file:

    $ fitshead filename.fits

2. Print the header of the third HDU extension:

    $ fitshead --ext 3 filename.fits

3. Print the header of the extension with EXTNAME='SCI' and EXTVER='2':

    $ fitshead --ext "SCI,2" filename.fits

4. Print the headers of a file in JSON format:

    $ fitshead --json filename.fits

5. Print the headers of all fits files in a directory:

    $ fitshead *.fits
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os

from ... import fits
from .... import log


class FormattingException(Exception):
    pass


class HeaderFormatter(object):
    """
    Base class to format the header(s) of a FITS file into a readable format.

    Parameters
    ----------
    filename : str
        Path to the FITS file.
    """
    def __init__(self, filename):
        try:
            self.hdulist = fits.open(filename)
        except IOError as e:
            raise FormattingException(e.message)

    def parse(self, extension=None):
        """Returns the FITS file header(s) in a readable format.

        Parameters
        ----------
        extension : int or str, optional
            Format only a specific HDU, identified by its number or its name.
            The name is the "EXTNAME" or "EXTNAME,EXTVER" string.

        Returns
        -------
        formatted_header : str
            Nicely formatted header information.
        """
        # `hdukeys` will hold the keys of the HDUList items to display
        if extension is None:
            hdukeys = range(len(self.hdulist))  # Display all by default
        else:
            try:
                hdukeys = [int(extension)]  # HDU may be specified by number
            except ValueError:
                # The user can specify "EXTNAME" or "EXTNAME,EXTVER" as well
                parts = extension.split(',')
                if len(parts) > 1:
                    extname = str(','.join(parts[0:-1]))
                    extver = int(parts[-1])
                    hdukeys = [(extname, extver)]
                else:
                    hdukeys = [extension]

        # Having established which HDUs are wanted, we can now format these
        return self._format_hdulist(hdukeys)

    def _get_header(self, hdukey):
        """Returns the `astropy.io.fits.header.Header` object for the HDU."""
        try:
            return self.hdulist[hdukey].header
        except IndexError:
            raise FormattingException('{0}: Extension #{1} not found.'.
                                      format(self.hdulist.filename(), hdukey))
        except KeyError as e:
            raise FormattingException('{0}: {1}'.format(
                                      self.hdulist.filename(), e.message))

    def _format_hdulist(self, hdukeys):
        """Returns the formatted version of the header; the important bit."""
        text = ''
        for i, key in enumerate(hdukeys):
            if i > 0:
                prefix = os.linesep + os.linesep  # Separate HDUs
            else:
                prefix = ''
            text += '{prefix}# HDU {key} in {filename}:{cr}{header}'.format(
                    prefix=prefix,
                    key=key,
                    filename=self.hdulist.filename(),
                    cr=os.linesep,
                    header=self._get_header(key).tostring(sep=os.linesep,
                                                          padding=False))
        return text


class JSONHeaderFormatter(HeaderFormatter):
    """
    Overrides HeaderFormatter to return the headers in JSON format.
    """

    def _format_hdulist(self, hdukeys):
        import json

        try:
            from collections import OrderedDict
            mydict = OrderedDict
        except ImportError:  # OrderedDict was new in Python 2.7
            mydict = dict

        js = mydict()
        js['filename'] = self.hdulist.filename()
        js['hdulist'] = []

        for i, key in enumerate(hdukeys):
            hdudict = mydict()
            hdudict['hdu'] = key
            hdr = self._get_header(key)
            hdudict['cards'] = mydict(zip(hdr.keys(), hdr.values()))
            js['hdulist'].append(hdudict)

        return json.dumps(js, indent=2)


def main(args=None):
    from astropy.utils.compat import argparse

    parser = argparse.ArgumentParser(
        description=("Print the header(s) of a FITS file. "
                     "By default, all HDU extensions are shown."))
    parser.add_argument('-e', '--ext', metavar='hdu',
                        help='specify the HDU extension number or name')
    parser.add_argument('-j', '--json', action='store_true',
                        help='display the output in JSON format')
    parser.add_argument('filename', nargs='+',
                        help='path to one or more FITS files to display')
    args = parser.parse_args(args)

    try:
        for filename in args.filename:
            if args.json:
                print(JSONHeaderFormatter(filename).parse(args.ext))
            else:
                print(HeaderFormatter(filename).parse(args.ext))
    except FormattingException as e:
        log.error(e)
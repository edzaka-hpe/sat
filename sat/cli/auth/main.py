"""
Entry point for the auth subcommand.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import getpass
import logging

from sat.config import get_config_value
from sat.session import SATSession

LOGGER = logging.getLogger(__name__)


def do_auth(args):
    """Prompts user for a password, fetches a token, and saves it to disk.

    The prompt indicates the username to be used in combination with the
    password. The command-line argument "--username" is checked first, then
    the "username" option in the configuration file, and if nothing is found,
    getpass.getuser() is called to get the system username of the user invoking sat.

    The token is saved to $HOME/.config/sat/tokens/hostname.username.json,
    unless overriden by --token-file on the command line.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """

    session = SATSession(no_unauth_warn=True)
    password = getpass.getpass('Password for {}: '.format(session.username))

    session.fetch_token(password)
    if session.token:
        print('Succeeded!')
        session.save()
    else:
        print('Authenication failed!')
        LOGGER.error('Authentication Failed.')
        raise SystemExit(1)

"""
The parser for the bootsys subcommand.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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

from sat.cli.bootsys.main import DEFAULT_PODSTATE
import sat.parsergroups


def add_bootsys_subparser(subparsers):
    """Add the bootsys subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    redfish_opts = sat.parsergroups.create_redfish_options()

    bootsys_parser = subparsers.add_parser(
        'bootsys', help='Boot or shut down the system.',
        description='Boot or shut down the entire system, including the '
                    'compute nodes, user access nodes, and non-compute '
                    'nodes running the management software.',
        parents=[redfish_opts]
    )

    bootsys_parser.add_argument(
        'action', help='Specify whether to boot or shut down.',
        choices=['boot', 'shutdown']
    )

    bootsys_parser.add_argument(
        '--dry-run', action='store_true',
        help='Do not run any commands, only print what would run.'
    )

    bootsys_parser.add_argument(
        '-i', '--ignore-failures', action='store_true',
        help='Proceed with the shutdown regardless of failed steps.'
    )

    bootsys_parser.add_argument(
        '--ignore-service-failures', action='store_true',
        help='If specified, do not fail to shutdown if querying services '
             'for active sessions fails.',
    )

    bootsys_parser.add_argument(
        '--ignore-pod-failures', action='store_true',
        help='Disregard any failures associated with storing pod state '
             'while shutting down.',
    )

    bootsys_parser.add_argument(
        '--pod-state-file', default=DEFAULT_PODSTATE,
        help='Custom location to dump pod state data.',
    )
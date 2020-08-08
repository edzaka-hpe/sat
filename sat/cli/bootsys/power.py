"""
IPMI power support.

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

import logging
import shlex
import subprocess

from sat.cli.bootsys.waiting import GroupWaiter

LOGGER = logging.getLogger(__name__)


class IPMIPowerStateWaiter(GroupWaiter):
    """Implementation of a waiter for IPMI power states.

    Waits for all members to reach the given IPMI power state."""

    def __init__(self, members, power_state, timeout, username, password,
                 send_command=False, poll_interval=1):
        """Constructor for an IPMIPowerStateWaiter object.

        Args:
            power_state (str): either 'on' or 'off', corresponds the desired
                IPMI power state.
            send_command (bool): if True, send a 'power on' or 'power off' command
                to each node before waiting.
            username (str): the username to use when running ipmitool commands
            password (str): the password to use when running ipmitool commands
        """
        self.power_state = power_state
        self.username = username
        self.password = password
        self.send_command = send_command

        super().__init__(members, timeout, poll_interval=poll_interval)

    def condition_name(self):
        return 'IPMI power ' + self.power_state

    def get_ipmi_command(self, member, command):
        """Get the full command-line for an ipmitool command.

        Args:
            member (str): the host to query
            command (str): the ipmitool command to run, e.g. `chassis power status`

        Returns:
            The command to run, split into a list of args by shlex.split.
        """
        return shlex.split(
            'ipmitool -I lanplus -U {} -P {} -H {}-mgmt {}'.format(
                self.username, self.password, member, command
            )
        )

    def member_has_completed(self, member):
        """Check if a host is in the desired state.

        Return:
            If the powerstate of the host matches that which was given
            in the constructor, return True. Otherwise, return False.
        """
        ipmi_command = self.get_ipmi_command(member, 'chassis power status')
        try:
            proc = subprocess.run(ipmi_command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, encoding='utf-8')
        except OSError as err:
            # TODO (SAT-552): Improve handling of ipmitool errors
            LOGGER.error('Unable to find ipmitool: %s', err)
            return False

        if proc.returncode:
            # TODO (SAT-552): Improve handling of ipmitool errors
            LOGGER.error('ipmitool command failed with code %s: stderr: %s',
                         proc.returncode, proc.stderr)
            return False

        return self.power_state in proc.stdout

    def pre_wait_action(self):
        """Send IPMI power commands to given hosts.

        This will issue IPMI power commands to put the given hosts in the power
        state given by `self.power_state`.

        Returns:
            None
        """
        LOGGER.debug("Entered pre_wait_action with self.send_command: %s.", self.send_command)
        if self.send_command:
            for member in self.members:
                LOGGER.info('Sending IPMI power %s command to host %s', self.power_state, member)
                ipmi_command = self.get_ipmi_command(member,
                                                     'chassis power {}'.format(self.power_state))
                try:
                    proc = subprocess.run(ipmi_command, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, encoding='utf-8')
                except OSError as err:
                    # TODO (SAT-552): Improve handling of ipmitool errors
                    LOGGER.error('Unable to find ipmitool: %s', err)
                    return

                if proc.returncode:
                    # TODO (SAT-552): Improve handling of ipmitool errors
                    LOGGER.error('ipmitool command failed with code %s: stderr: %s',
                                 proc.returncode, proc.stderr)
                    return
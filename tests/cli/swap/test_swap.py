"""
Unit tests for sat.cli.swap.swap

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

import unittest
from unittest import mock

from sat.cli.swap.swap import SwitchSwapper, CableSwapper, output_json
from sat.cli.swap import swap


class TestCableSwapper(unittest.TestCase):

    def setUp(self):
        """Mock functions called."""
        self.mock_port_manager = mock.patch('sat.cli.swap.swap.PortManager', autospec=True).start().return_value
        self.mock_port_manager.get_jack_ports.return_value = ['x1000c6r7j101p0', 'x1000c6r7j2p0']
        self.mock_port_manager.get_port_set_config.return_value = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'}
            ]
        }

        self.mock_pester = mock.patch('sat.cli.swap.swap.pester', autospec=True).start()
        self.mock_pester.return_value = True
        self.mock_print = mock.patch('builtins.print', autospec=True).start()
        self.mock_output_json = mock.patch('sat.cli.swap.swap.output_json', autospec=True).start()

        self.swap_args = {
            'action': None,
            'component_id': ['x1000c6r7j101'],
            'disruptive': True,
            'dry_run': True,
            'force': False,
            'overwrite': False,
            'save_port_set': False
        }

    def tearDown(self):
        mock.patch.stopall()

    def run_swap_component(self):
        """Run swap_component()"""
        CableSwapper().swap_component(**self.swap_args)

    def test_basic(self):
        """Test basic swap cable"""
        self.run_swap_component()
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_swap_force(self):
        """Test swap cable with force"""
        self.swap_args['force'] = True
        self.run_swap_component()
        self.mock_port_manager.get_jack_ports.assert_called_once_with(self.swap_args['component_id'], force=True)
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_save_port_set_file(self):
        """Test swap_component saves a port set file"""
        self.swap_args['save_port_set'] = True
        self.run_swap_component()
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_called_once()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_enable(self):
        """Test swap_component enables components"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        self.run_swap_component()
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_disable(self):
        """Test swap_component disables components"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.run_swap_component()
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_not_disruptive_not_dry(self):
        """Test swap_component not disruptive and not dry run"""
        self.swap_args['disruptive'] = False
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        self.run_swap_component()
        self.mock_pester.assert_called_once()
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_not_dry_without_action(self):
        """Test swap_component not dry run without action"""
        self.swap_args['disruptive'] = False
        self.swap_args['dry_run'] = False
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_INVALID_OPTIONS)
        self.mock_pester.assert_not_called()
        self.mock_port_manager.get_jack_ports.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_not_called()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_dry_run_and_action(self):
        """Test action and dry run is invalid"""
        self.swap_args['action'] = 'enable'
        self.swap_args['dry_run'] = True
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_INVALID_OPTIONS)
        self.mock_pester.assert_not_called()
        self.mock_port_manager.get_jack_ports.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_not_called()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_get_ports_error(self):
        """Test swap_component error getting ports"""
        self.mock_port_manager.get_jack_ports.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_GET_PORTS_FAIL)
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_not_called()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_update_port_set_error(self):
        """Test swap_component with an error updating port set configuration"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.update_port_set.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_TOGGLE_FAIL)
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called()
        self.mock_port_manager.update_port_set.assert_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_not_called()

    def test_no_jack_ports(self):
        """Test swap_component when no jack ports are returned"""
        self.mock_port_manager.get_jack_ports.return_value = []
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_NO_PORTS_FOUND)
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_not_called()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_set_cable_exists(self):
        """Test swap_component when a port set for the cable already exists"""
        self.mock_port_manager.get_port_sets.return_value = {'names': ['SAT-x1000c6r7j101']}
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_EXISTS)
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_set_port_exists(self):
        """Test swap_component when portset for a port already exists"""
        self.mock_port_manager.get_port_sets.return_value = {'names': ['SAT-x1000c6r7j101p0']}
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_EXISTS)
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_config_missing(self):
        """Test swap_component when there is no configuration for the port"""
        self.mock_port_manager.get_port_set_config.return_value = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'}
            ]
        }
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_GET_CONFIG)
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_not_called()

    def test_port_config_missing_with_xname(self):
        """Test swap_component when there is no configuration for the port, but its xname appears"""
        self.mock_port_manager.get_port_set_config.return_value = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'},
                {'xname': 'x1000c6r7j2p0'}
            ]
        }
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_GET_CONFIG)
        self.mock_port_manager.get_jack_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_not_called()

    def test_swap_cable_get_port_set_fail(self):
        """Test swapping a cable when get_port_sets returns None"""
        self.mock_port_manager.get_port_sets.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_GET_PORTS_FAIL)


class TestSwitchSwapper(unittest.TestCase):

    def setUp(self):
        """Mock functions called."""
        self.mock_port_manager = mock.patch('sat.cli.swap.swap.PortManager', autospec=True).start().return_value
        self.mock_port_manager.get_switch_ports.return_value = ['x1000c6r7j101p0', 'x1000c6r7j101p1',
                                                                'x1000c6r7j2p0', 'x1000c6r7j2p1']
        self.mock_port_manager.get_port_set_config.return_value = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'}
            ]
        }

        self.mock_pester = mock.patch('sat.cli.swap.swap.pester', autospec=True).start()
        self.mock_pester.return_value = True
        self.mock_print = mock.patch('builtins.print', autospec=True).start()
        self.mock_output_json = mock.patch('sat.cli.swap.swap.output_json', autospec=True).start()

        self.swap_args = {
            'action': None,
            'component_id': 'x1000c6r7',
            'disruptive': True,
            'dry_run': True,
            'force': False,
            'overwrite': False,
            'save_port_set': False
        }

    def tearDown(self):
        mock.patch.stopall()

    def run_swap_component(self):
        """Run swap_component()"""
        SwitchSwapper().swap_component(**self.swap_args)

    def test_basic(self):
        """Test basic swap switch"""
        self.run_swap_component()
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_save_port_set_file(self):
        """Test swap_component saves a port set file"""
        self.swap_args['save_port_set'] = True
        self.run_swap_component()
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_called_once()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_enable(self):
        """Test swap_component enables components"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        self.run_swap_component()
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_disable(self):
        """Test swap_component disables components"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.run_swap_component()
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_not_disruptive_not_dry(self):
        """Test swap_component not disruptive and not dry run"""
        self.swap_args['disruptive'] = False
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        self.run_swap_component()
        self.mock_pester.assert_called_once()
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called_once()
        self.mock_port_manager.update_port_set.assert_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_called_once()

    def test_not_dry_without_action(self):
        """Test swap_component not dry run without action"""
        self.swap_args['disruptive'] = False
        self.swap_args['dry_run'] = False
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_INVALID_OPTIONS)
        self.mock_pester.assert_not_called()
        self.mock_port_manager.get_switch_ports.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_not_called()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_dry_run_and_action(self):
        """Test action and dry run is invalid"""
        self.swap_args['action'] = 'enable'
        self.swap_args['dry_run'] = True
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_INVALID_OPTIONS)
        self.mock_pester.assert_not_called()
        self.mock_port_manager.get_jack_ports.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_not_called()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_get_ports_error(self):
        """Test swap_component error getting ports"""
        self.mock_port_manager.get_switch_ports.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_GET_PORTS_FAIL)
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_not_called()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_update_port_set_error(self):
        """Test swap_component with an error updating port set configuration"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.update_port_set.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_TOGGLE_FAIL)
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called()
        self.mock_port_manager.update_port_set.assert_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_not_called()

    def test_no_switch_ports(self):
        """Test swap_component when no switch ports are returned"""
        self.mock_port_manager.get_switch_ports.return_value = []
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_NO_PORTS_FOUND)
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_not_called()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_set_switch_exists(self):
        """Test swap_component when a port set for the switch already exists"""
        self.mock_port_manager.get_port_sets.return_value = {'names': ['SAT-x1000c6r7']}
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_EXISTS)
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_set_port_exists(self):
        """Test swap_component when portset for a port already exists"""
        self.mock_port_manager.get_port_sets.return_value = {'names': ['SAT-x1000c6r7j101p0']}
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_EXISTS)
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_not_called()
        self.mock_port_manager.get_port_set_config.assert_not_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_config_missing(self):
        """Test swap_component when there is no configuration for the port"""
        self.mock_port_manager.get_port_set_config.return_value = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'}
            ]
        }
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_GET_CONFIG)
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_not_called()

    def test_port_config_missing_with_xname(self):
        """Test swap_component when there is no configuration for the port, but its xname appears"""
        self.mock_port_manager.get_port_set_config.return_value = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'},
                {'xname': 'x1000c6r7j2p0'}
            ]
        }
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORTSET_GET_CONFIG)
        self.mock_port_manager.get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.get_port_sets.assert_called_once()
        self.mock_port_manager.create_port_set.assert_called()
        self.mock_port_manager.get_port_set_config.assert_called()
        self.mock_port_manager.update_port_set.assert_not_called()
        self.mock_port_manager.delete_port_set_list.assert_called()
        self.mock_print.assert_not_called()

    def test_swap_switch_get_port_set_fail(self):
        """Test swapping a switch when get_port_sets returns None"""
        self.mock_port_manager.get_port_sets.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_GET_PORTS_FAIL)


class TestOutputJson(unittest.TestCase):
    """Unit test for swap output_json()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_json_dump = mock.patch('json.dump', autospec=True).start()
        self.mock_open = mock.patch('builtins.open', autospec=True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test output_json basic"""
        output_json({}, 'filepath')
        self.mock_open.assert_called_once()
        self.mock_json_dump.assert_called_once()

    def test_api_error(self):
        """Test output_json OSError"""
        self.mock_open.side_effect = OSError
        with self.assertLogs(level='ERROR'):
            output_json({}, 'filepath')
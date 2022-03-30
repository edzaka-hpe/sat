"""
Tests for the sat.cli.swap.blade module.

(C) Copyright 2022 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
:s/out/in
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

from argparse import Namespace
import io
import json
import unittest
from unittest.mock import MagicMock, patch

from kubernetes.client.exceptions import ApiException

from sat.apiclient.capmc import CAPMCClient
from sat.apiclient.gateway import APIError
from sat.apiclient.hsm import HSMClient
from sat.cli.swap.blade import (
    blade_swap_stage,
    BladeSwapError,
    BladeSwapProcedure,
    RedfishEndpointDiscoveryWaiter,
    SwapOutProcedure,
    SwapInProcedure,
    swap_blade,
)
from sat.hms_discovery import HMSDiscoveryError


class TestBladeSwapStage(unittest.TestCase):
    """Tests for the blade_swap_stage decorator"""

    def test_logging_message(self):
        """Test that logging messages are printed for blade swap stages"""
        @blade_swap_stage('Perform a test')
        def stage_for_testing():
            pass
        with self.assertLogs(level='INFO') as cm:
            stage_for_testing()

        self.assertIn('Performing a test', cm.output[0])

    def test_exceptions_flattened(self):
        """Test that unhandled non-BladeSwapError exceptions are passed through"""
        @blade_swap_stage('Do something wrong')
        def do_bad_thing():
            return {'foo': 'bar'}['baz']
        with self.assertRaises(KeyError):
            do_bad_thing()

    def test_bladeswaperrors_passed_through(self):
        """Test that BladeSwapErrors are passed through blade swap stages"""
        @blade_swap_stage('Do something wrong differently')
        def do_error():
            raise BladeSwapError('something bad happened')

        with self.assertRaises(BladeSwapError):
            do_error()

    def test_apierrors_flattened(self):
        """Test that APIErrors are flattened into BladeSwapErrors"""
        @blade_swap_stage('Do something with the API, but badly')
        def do_api_error():
            raise APIError('API is broken')
        with self.assertRaisesRegex(BladeSwapError, 'Error accessing API'):
            do_api_error()


class BaseBladeSwapProcedureTest(unittest.TestCase):
    def setUp(self):
        self.mock_hsm_client = MagicMock(autospec=HSMClient)
        patch('sat.cli.swap.blade.HSMClient', return_value=self.mock_hsm_client).start()

        self.mock_capmc_client = MagicMock(autospec=CAPMCClient)
        patch('sat.cli.swap.blade.CAPMCClient', return_value=self.mock_capmc_client).start()

        self.mock_sat_session = patch('sat.cli.swap.blade.SATSession').start()

        self.blade_xname = 'x1000c0s1'
        self.args = Namespace(
            xname=self.blade_xname,
            src_mapping='src_mapping.json',
            dst_mapping='dst_mapping.json',
        )
        self.swap_in = SwapInProcedure(self.args)
        self.swap_out = SwapOutProcedure(self.args)

        self.node_bmcs = [
            {
                'ID': f'{self.blade_xname}b{b}',
                'Type': 'NodeBMC',
                'State': 'Off',
                'Flag': 'OK',
                'Enabled': True,
                'NetType': 'Sling',
                'Arch': 'X86',
                'Class': 'Mountain'
            }
            for b in range(2)
        ]

        self.nodes = [
            {
                'ID': f'{self.blade_xname}b{b}n{n}',
                'Type': 'Node',
                'State': 'Ready',
                'Flag': 'OK',
                'Enabled': True,
                'SoftwareStatus': 'DvsAvailable',
                'Role': 'Compute',
                'NID': 2,
                'NetType': 'Sling',
                'Arch': 'X86',
                'Class': 'Mountain'
            }
            for b in range(2)
            for n in range(2)
        ]

    def tearDown(self):
        patch.stopall()


class TestBladeSwapProcedure(BaseBladeSwapProcedureTest):
    """Tests for the base BladeSwapProcedure class"""

    def test_bladeswaperror_logging(self):
        """Test that BladeSwapErrors are logged in a BladeSwapProcedure"""

        msg = 'procedure failed'

        class FailingBladeSwapProcedure(BladeSwapProcedure):
            def procedure(self):
                raise BladeSwapError(msg)

        with self.assertLogs(level='ERROR') as cm, self.assertRaises(SystemExit):
            FailingBladeSwapProcedure(self.args).run()
        self.assertIn(msg, cm.output[0])


class TestPreSwapChecks(BaseBladeSwapProcedureTest):
    """Tests for the swap out (blade removal) procedure"""

    def test_pre_swap_checks_xname_is_slot(self):
        """Test that non-blade components are not swapped"""
        for non_blade in ['x1000', 'x1000c0', 'x1000c0s0b1n0']:
            with self.subTest(xname=non_blade), self.assertRaises(BladeSwapError):
                self.args.xname = non_blade
                SwapOutProcedure(self.args).pre_swap_checks()

    def test_pre_swap_checks_test_xnames_are_off(self):
        """Test that only blades with powered-off nodes are swapped"""
        self.mock_hsm_client.get_node_components.return_value = self.nodes

        with self.assertRaises(BladeSwapError):
            self.swap_out.pre_swap_checks()

    def test_pre_swap_checks_succeed(self):
        """Test the successful case of pre-swap checks"""
        for node in self.nodes:
            node['State'] = 'Off'

        self.mock_hsm_client.get_node_components.return_value = self.nodes
        try:
            self.swap_out.pre_swap_checks()
        except BladeSwapError as err:
            self.fail(f'BladeSwapError in pre_swap_checks: {err}')


class TestDisablingRedfishEndpoints(BaseBladeSwapProcedureTest):
    def test_node_bmcs_disabled(self):
        """Test that NodeBMCs Redfish endpoints are disabled properly"""
        self.mock_hsm_client.query_components.return_value = self.node_bmcs
        self.swap_out.disable_redfish_endpoint()
        for node_bmc in self.node_bmcs:
            self.mock_hsm_client.set_redfish_endpoint_enabled.assert_any_call(
                node_bmc['ID'], enabled=False
            )


class TestDisablingSlot(BaseBladeSwapProcedureTest):
    def test_slots_disabled(self):
        """Test that slots are disabled in HSM properly"""
        self.swap_out.disable_slot()
        self.mock_hsm_client.set_component_enabled.assert_called_once_with(
            self.blade_xname, enabled=False
        )


class TestSuspendHMSDiscoveryCronJob(BaseBladeSwapProcedureTest):
    """Tests for suspending the hms-discovery cron job"""

    def setUp(self):
        super().setUp()
        self.mock_cron = patch('sat.cli.swap.blade.HMSDiscoveryCronJob').start()

    def test_suspend_stage(self):
        """Test suspending the hms-discovery cron job"""
        self.swap_out.suspend_hms_discovery_cron_job()
        self.mock_cron.return_value.set_suspend_status.assert_called_once_with(True)

    def test_suspend_stage_error_reraised(self):
        """Test HMSDiscoveryErrors re-raised as BladeSwapErrors"""
        self.mock_cron.return_value.set_suspend_status.side_effect = HMSDiscoveryError
        with self.assertRaises(BladeSwapError):
            self.swap_out.suspend_hms_discovery_cron_job()
        self.mock_cron.return_value.set_suspend_status.assert_called_once_with(True)


class TestPromptUserClearBMC(BaseBladeSwapProcedureTest):
    """Tests for prompting the user to clear BMC settings before swapping"""
    # CRAYSAT-1373: These changes will become obsolete once SCSD automates
    # performing StatefulResets on BMCs.

    def setUp(self):
        super().setUp()
        self.mock_pester_choices = patch('sat.util.pester_choices', return_value='yes').start()
        self.mock_print = patch('builtins.print').start()

        self.bmc_entries = [
            {
                'ID': f'{self.blade_xname}b{n}',
                'Type': 'NodeBMC',
                'State': 'Off',
                'Flag': 'OK',
                'Enabled': True,
                'NetType': 'Sling',
                'Arch': 'X86',
                'Class': 'Mountain'
            }
            for n in range(4)
        ]
        self.mock_hsm_client.query_components.return_value = self.bmc_entries

    def test_user_prompted_to_continue(self):
        """Test that the user the swap procedure continues if the user selects yes"""
        self.swap_out.prompt_clear_node_controller_settings()

    def test_user_prompted_with_bmcs(self):
        """Test that the user is prompted to reset all given BMCs"""
        self.swap_out.prompt_clear_node_controller_settings()
        self.mock_print.assert_called()
        for bmc in self.bmc_entries:
            self.assertIn(bmc['ID'], self.mock_print.mock_calls[0].args[0])

    def test_user_bails(self):
        """Test that the blade swap procedure never proceeds if the user bails"""
        self.mock_pester_choices.return_value = 'no'
        with self.assertRaises(SystemExit):
            self.swap_out.prompt_clear_node_controller_settings()


class TestDeletingEthernetInterfaces(BaseBladeSwapProcedureTest):
    """Test for deleting ethernet interfaces from HSM"""

    def setUp(self):
        super().setUp()
        self.ethernet_interfaces = [
            {
                'ComponentID': f'{node["ID"]}',
                'Description': 'Ethernet Interface Lan1',
                'ID': f'b42e99be24e{chr(suffix)}',
                'IPAddresses': [{'IPAddress': '10.0.0.1'}],
                'LastUpdate': '2021-09-03T15:36:00.545019Z',
                'MACAddress': 'ab:cd:ef:01:23:45',
                'Type': 'Node'
            }
            for node, suffix in zip(self.nodes, range(ord('a'), ord('e')))
        ]
        self.mock_hsm_client.get_node_components.return_value = self.nodes
        self.mock_hsm_client.get_ethernet_interfaces.return_value = self.ethernet_interfaces

    def test_deleting_ethernet_interfaces(self):
        """Test that ethernet interfaces are deleted"""
        self.swap_out.delete_ethernet_interfaces()
        for eth_id in self.ethernet_interfaces:
            self.mock_hsm_client.delete_ethernet_interface.assert_any_call(eth_id['ID'])


class TestDeletingRedfishEndpoints(BaseBladeSwapProcedureTest):
    """Tests for deleting BMC Redfish endpoints"""

    def test_deleting_redfish_endpoints(self):
        """Test that Redfish endpoints are deleted"""
        self.mock_hsm_client.query_components.return_value = self.node_bmcs
        self.swap_out.delete_redfish_endpoints()
        for endpoint in self.node_bmcs:
            self.mock_hsm_client.delete_redfish_endpoint.assert_any_call(endpoint['ID'])


class TestPowerOffSlot(BaseBladeSwapProcedureTest):
    """Tests for the powering off slot stage"""

    def test_slot_power_off_command_sent(self):
        """Test that the slot power off command is sent"""
        self.swap_out.power_off_slot()
        self.mock_capmc_client.set_xnames_power_state.assert_called_once_with(
            [self.blade_xname],
            'off',
            recursive=True,
        )


class TestStoreEthernetInterfaceMapping(BaseBladeSwapProcedureTest):
    """Tests for storing the MAC/IP address mapping"""

    def setUp(self):
        super().setUp()
        self.mock_file = io.StringIO()
        patch.object(self.mock_file, 'close').start()
        self.mock_open = patch('builtins.open', return_value=self.mock_file).start()

        self.mock_hsm_client.get_ethernet_interfaces.return_value = [
            {
                "ID": "a31e83fd84eb",
                "Description": "Node Management Network",
                "MACAddress": "e1:3f:83:ca:31:db",
                "LastUpdate": "2021-09-03T15:36:00.545019Z",
                "ComponentID": "x1000c0s1b0n1",
                "Type": "Node",
                "IPAddresses": [
                    {
                        "IPAddress": "10.1.0.1"
                    }
                ]
            },
        ]

    def test_store_ethernet_interfaces(self):
        """Test storing ethernet interface MAC/IP address mapping"""
        self.swap_out.store_ip_mac_address_mapping()
        self.mock_hsm_client.get_ethernet_interfaces.assert_called_once_with(self.blade_xname)
        self.mock_file.seek(0)
        self.assertEqual(
            json.load(self.mock_file),
            [
                {
                    "Description": "Node Management Network",
                    "ComponentID": "x1000c0s1b0n1",
                    "MACAddress": "e1:3f:83:ca:31:db",
                    "IPAddress": "10.1.0.1"
                }
            ]
        )

    def test_store_ethernet_interfaces_with_no_nmn_ethernet_ifaces(self):
        """Test that no mapping is written if no interfaces located"""
        self.mock_hsm_client.get_ethernet_interfaces.return_value = []
        with self.assertLogs(level='WARNING'):
            self.swap_out.store_ip_mac_address_mapping()
        self.mock_open.assert_not_called()

    def test_bladeswaperror_on_write_failure(self):
        """Test that a BladeSwapError is thrown on write error"""
        self.mock_open.side_effect = OSError
        with self.assertRaises(BladeSwapError):
            self.swap_out.store_ip_mac_address_mapping()

    def test_bladeswaperror_on_malformed_api_response(self):
        """Test that a BladeSwapError is thrown on bad API response for ethernet address querying"""
        self.mock_hsm_client.get_ethernet_interfaces.return_value.append(
            {
                'Description': 'Node Management Network',
                'ComponentID': 'x1000c0s1b1n0'
            }
        )
        with self.assertRaises(BladeSwapError):
            self.swap_out.store_ip_mac_address_mapping()


class TestWaitingForChassisBMCEndpoints(BaseBladeSwapProcedureTest):
    """Tests for waiting for the ChassisBMC endpoints"""

    def setUp(self):
        super().setUp()
        self.mock_endpoint_waiter = MagicMock(autospec=RedfishEndpointDiscoveryWaiter)
        self.mock_endpoint_waiter_constructor = patch(
            'sat.cli.swap.blade.RedfishEndpointDiscoveryWaiter',
            return_value=self.mock_endpoint_waiter
        ).start()

        self.chassis_bmcs = [
            {
                'ID': f'x1000c{n}',
                'Type': 'ChassisBMC',
                'State': 'Off',
                'Flag': 'OK',
                'Enabled': True,
                'NetType': 'Sling',
                'Arch': 'X86',
                'Class': 'Mountain'
            }
            for n in range(2)
        ]
        self.mock_hsm_client.query_components.return_value = self.chassis_bmcs

    def test_waiting_for_chassis_bmc_endpoints(self):
        """Test that ChassisBMC endpoints are waited for"""
        self.mock_endpoint_waiter.failed = False
        self.swap_in.wait_for_chassisbmc_endpoints()
        self.mock_endpoint_waiter_constructor.assert_called_once_with(
            [cbmc['ID'] for cbmc in self.chassis_bmcs],
            self.mock_hsm_client,
            timeout=300
        )
        self.mock_endpoint_waiter.wait_for_completion.assert_called_once_with()

    def test_bladeswaperror_raised_on_wait_failure(self):
        """Test that a BladeSwapError is raised if any ChassisBMCs can't be waited for"""
        self.mock_endpoint_waiter.failed = ['x1000c0b0']
        with self.assertRaises(BladeSwapError):
            self.swap_in.wait_for_chassisbmc_endpoints()


class TestWaitingForNodeBMCEndpoints(BaseBladeSwapProcedureTest):
    def setUp(self):
        super().setUp()
        self.mock_endpoint_waiter = MagicMock(autospec=RedfishEndpointDiscoveryWaiter)
        self.mock_endpoint_waiter_constructor = patch(
            'sat.cli.swap.blade.RedfishEndpointDiscoveryWaiter',
            return_value=self.mock_endpoint_waiter
        ).start()
        self.mock_hsm_client.query_components.return_value = self.node_bmcs

    def test_waiting_for_node_bmc_endpoints(self):
        """Test that NodeBMC Redfish endpoints are waited for"""
        self.mock_endpoint_waiter.failed = False
        self.swap_in.wait_for_nodebmc_endpoints()
        self.mock_endpoint_waiter_constructor.assert_called_once_with(
            [nbmc['ID'] for nbmc in self.node_bmcs],
            self.mock_hsm_client,
            timeout=300
        )
        self.mock_endpoint_waiter.wait_for_completion.assert_called_once_with()


class TestEnablingSlots(BaseBladeSwapProcedureTest):
    """Tests for enabling slots"""

    def test_enabling_slot(self):
        """Test enabling the blade's slot"""
        self.swap_in.enable_slot()
        self.mock_hsm_client.set_component_enabled.assert_called_once_with(
            self.blade_xname, enabled=True
        )


class TestPoweringOnSlot(BaseBladeSwapProcedureTest):
    """Tests for powering on the slot"""

    def test_power_on_slot(self):
        """Test powering on the slot"""
        self.swap_in.power_on_slot()
        self.mock_capmc_client.set_xnames_power_state.assert_called_once_with(
            [self.blade_xname],
            'on',
            recursive=True
        )


class TestEnablingNodes(BaseBladeSwapProcedureTest):
    """Tests for enabling nodes"""

    def test_enabling_nodes(self):
        """Test enabling the nodes on the blade"""
        self.mock_hsm_client.get_node_components.return_value = self.nodes
        self.swap_in.enable_nodes()
        self.mock_hsm_client.bulk_enable_components.assert_called_once_with(
            [node['ID'] for node in self.nodes]
        )


class TestBeginningSlotDiscovery(BaseBladeSwapProcedureTest):
    """Test beginning the slot discovery"""

    def test_begin_slot_discovery(self):
        """Test that slot discovery is begun"""
        self.swap_in.begin_slot_discovery()
        self.mock_hsm_client.begin_discovery.assert_called_once_with(self.blade_xname)


class TestResumeHMSDiscoveryCronJob(BaseBladeSwapProcedureTest):
    """Tests for resuming the hms-discovery cron job"""

    def setUp(self):
        super().setUp()
        self.mock_cron = patch('sat.cli.swap.blade.HMSDiscoveryCronJob').start()
        self.mock_hms_waiter = MagicMock()
        patch('sat.cli.swap.blade.HMSDiscoveryScheduledWaiter', return_value=self.mock_hms_waiter).start()

    def test_resume_stage(self):
        """Test suspending the hms-discovery cron job"""
        self.swap_in.resume_hms_discovery_cron_job()
        self.mock_cron.return_value.set_suspend_status.assert_called_once_with(False)
        self.mock_hms_waiter.wait_for_completion.assert_called_once_with()

    def test_resume_stage_error_reraised(self):
        """Test HMSDiscoveryErrors re-raised as BladeSwapErrors"""
        self.mock_cron.return_value.set_suspend_status.side_effect = HMSDiscoveryError
        with self.assertRaises(BladeSwapError):
            self.swap_in.resume_hms_discovery_cron_job()
        self.mock_cron.return_value.set_suspend_status.assert_called_once_with(False)
        self.mock_hms_waiter.wait_for_completion.assert_not_called()


class TestMappingIpMacAddresses(BaseBladeSwapProcedureTest):
    """Tests for the IP/MAC address mapping stage"""

    def setUp(self):
        super().setUp()
        self.mock_k8s_api = patch('sat.cli.swap.blade.CoreV1Api').start()
        patch('sat.cli.swap.blade.load_kube_config').start()

        self.pod_name = 'cray-dhcp-kea-123456789-cafe'
        self.mock_pod = MagicMock()
        self.mock_pod.metadata.name = self.pod_name

        self.mock_k8s_api.return_value.list_namespaced_pod.return_value = [self.mock_pod]

        self.ethernet_interfaces = [
            {
                'ComponentID': f'{node["ID"]}',
                'Description': 'Node Management Network',
                'ID': f'b42e99be24e{chr(suffix)}',
                'IPAddresses': [{'IPAddress': '10.0.0.1'}],
                'LastUpdate': '2021-09-03T15:36:00.545019Z',
                'MACAddress': 'ab:cd:ef:01:23:45',
                'Type': 'Node'
            }
            for node, suffix in zip(self.nodes, range(ord('a'), ord('a') + len(self.nodes)))
        ]

        self.mock_hsm_client.get_ethernet_interfaces.return_value = self.ethernet_interfaces

        self.mock_src_mapping = [
            {
                'ComponentID': 'x1000c0s0b0n0',
                'IPAddress': '10.0.1.1',
                'MACAddress': 'ab:cd:ef:01:23:45'
            }
        ]
        self.mock_dst_mapping = [
            {
                'ComponentID': 'x3000c1s0b0n0',
                'IPAddress': '10.0.1.10',
                'MACAddress': '01:23:ab:cd:ef:45'
            }
        ]

        def mock_open_fn(path):
            if 'src' in path:
                output = self.mock_src_mapping
            elif 'dst' in path:
                output = self.mock_dst_mapping
            else:
                raise FileNotFoundError(path)

            return io.StringIO(json.dumps(output))

        self.mock_open = patch(
            'builtins.open',
            mock_open_fn
        ).start()

    def test_retrieving_kea_pod_name(self):
        """Test retrieving the cray-kea-dhcp pod name"""
        self.assertEqual(self.swap_in.kea_pod_name, self.pod_name)

    def test_nmn_ethernet_ifaces_deleted(self):
        """Test that ethernet interfaces on the NMN are deleted"""
        self.swap_in.map_ip_mac_addresses()
        for eth_iface in self.ethernet_interfaces:
            self.mock_hsm_client.delete_ethernet_interface.assert_any_call(
                eth_iface['ID']
            )

    def test_non_nmn_ethernet_ifaces_not_deleted(self):
        """Test that ethernet interfaces not on the NMN are left alone"""
        for eth_iface in self.ethernet_interfaces:
            eth_iface['Description'] = 'not NMN'
        self.swap_in.map_ip_mac_addresses()
        self.mock_hsm_client.delete_ethernet_interface.assert_not_called()

    def test_non_node_ethernet_interfaces_not_mapped(self):
        """Test mapping IP and MAC addresses"""
        self.ethernet_interfaces = [
            {
                'ComponentID': f'x1000c0s0b{n}',
                'Description': 'Node Management Network'
            }
            for n in range(4)
        ]
        self.mock_hsm_client.get_ethernet_interfaces.return_value = self.ethernet_interfaces
        self.swap_in.map_ip_mac_addresses()
        self.mock_hsm_client.delete_ethernet_interface.assert_not_called()

    def test_bladeswaperror_on_k8s_apiexception(self):
        """Test that k8s ApiExceptions are re-raised as BladeSwapErrors"""
        self.mock_k8s_api.return_value.list_namespaced_pod.side_effect = ApiException
        with self.assertRaises(BladeSwapError):
            self.swap_in.map_ip_mac_addresses()


class TestMergeInterfaceMappings(BaseBladeSwapProcedureTest):
    """Tests for merging interface mappings"""

    def setUp(self):
        super().setUp()

        self.src_mapping = [
            {
                "ComponentID": "x1000c0s0b0n0",
                "IPAddress": "10.0.0.11",
                "MACAddress": "ab:cd:ef:01:23:45",
            },
            {
                "ComponentID": "x1000c0s0b1n0",
                "IPAddress": "10.0.0.12",
                "MACAddress": "cd:ef:01:23:45:ab",
            },
            {
                "ComponentID": "x1000c0s0b1n1",
                "IPAddress": "10.0.0.13",
                "MACAddress": "ef:01:23:45:ab:cd",
            },
        ]

        self.dst_mapping = [
            {
                "ComponentID": "x3000c0s0b0n0",
                "IPAddress": "10.0.1.11",
                "MACAddress": "23:45:ab:cd:ef:01",
            },
            {
                "ComponentID": "x3000c0s0b1n0",
                "IPAddress": "10.0.1.12",
                "MACAddress": "cd:ef:23:45:ab:01",
            },
            {
                "ComponentID": "x3000c0s0b1n1",
                "IPAddress": "10.0.1.13",
                "MACAddress": "23:45:ab:ef:01:cd",
            },
        ]

    def test_merging_interface_mappings(self):
        """Test that interface mappings are merged properly"""
        merged_mapping = SwapInProcedure.merge_mappings(self.src_mapping, self.dst_mapping)
        for elem in merged_mapping:
            self.assertIn(elem, [
                {
                    "ComponentID": "x3000c0s0b0n0",
                    "IPAddress": "10.0.1.11",
                    "MACAddress": "ab:cd:ef:01:23:45",
                },
                {
                    "ComponentID": "x3000c0s0b1n0",
                    "IPAddress": "10.0.1.12",
                    "MACAddress": "cd:ef:01:23:45:ab",
                },
                {
                    "ComponentID": "x3000c0s0b1n1",
                    "IPAddress": "10.0.1.13",
                    "MACAddress": "ef:01:23:45:ab:cd",
                },
            ])

    def test_merging_mappings_of_different_lengths(self):
        """Test merging mappings of different lengths"""
        self.dst_mapping.append({
            "ComponentID": "x3000c0s0b2n0",
            "IPAddress": "10.0.1.17",
            "MACAddress": "ef:01:65:45:ef:cd",
        })
        with self.assertRaises(BladeSwapError):
            SwapInProcedure.merge_mappings(self.src_mapping, self.dst_mapping)

    def test_merging_mappings_no_matching_destination(self):
        """Test that merging mappings without matching destination blade fails"""
        self.dst_mapping[0]['ComponentID'] = "x3000c0s0b0n9"
        with self.assertRaises(BladeSwapError):
            SwapInProcedure.merge_mappings(self.src_mapping, self.dst_mapping)


class TestSwapBladeEntrypoint(unittest.TestCase):
    """Test that the `sat swap blade` entrypoint behaves properly"""

    def setUp(self):
        self.mock_swap_in_procedure = patch('sat.cli.swap.blade.SwapInProcedure').start()
        self.mock_swap_out_procedure = patch('sat.cli.swap.blade.SwapOutProcedure').start()

    def test_enable_blade(self):
        """Test that the correct procedure is used for swapping in a blade"""
        args = Namespace(action='enable')
        swap_blade(args)
        self.mock_swap_in_procedure.assert_called_once_with(args)
        self.mock_swap_in_procedure.return_value.run.assert_called_once()
        self.mock_swap_out_procedure.assert_not_called()

    def test_disable_blade(self):
        """Test that the correct procedure is used for swapping out a blade"""
        args = Namespace(action='disable')
        swap_blade(args)
        self.mock_swap_out_procedure.assert_called_once_with(args)
        self.mock_swap_out_procedure.return_value.run.assert_called_once()
        self.mock_swap_in_procedure.assert_not_called()

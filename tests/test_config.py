"""
Unit tests for sat.config

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import os
import unittest
from unittest import mock

import sat
from sat.config import ConfigValidationError, DEFAULT_CONFIG_PATH, get_config_value, load_config,\
    SATConfig, SAT_CONFIG_SPEC, validate_log_level

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), 'resources/configs')


class TestValidateLogLevel(unittest.TestCase):
    """Tests for validate_log_level validation function"""

    def test_validate_log_level_valid(self):
        """Test validate_log_level with valid levels"""
        validate_log_level('debug')
        validate_log_level('info')
        validate_log_level('warning')
        validate_log_level('error')
        validate_log_level('critical')

        # Verify that case doesn't matter
        validate_log_level('dEbUg')

    def test_validate_log_level_invalid(self):
        """Test validate_log_level with invalid level"""
        invalid_level = 'foo'
        expected_msg = "Level '{}' is not one of the valid log levels".format(invalid_level)
        with self.assertRaisesRegex(ConfigValidationError, expected_msg):
            validate_log_level(invalid_level)


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config function"""

    def setUp(self):
        """Sets up for test methods.

        Patches SATConfig constructor.
        """
        # Ensure that CONFIG is None to start with a clean slate
        sat.config.CONFIG = None
        self.mock_sat_config_obj = mock.Mock()
        self.patcher = mock.patch('sat.config.SATConfig',
                                  return_value=self.mock_sat_config_obj)
        self.mock_sat_config_cls = self.patcher.start()

    def tearDown(self):
        """Cleans up after test methods.

        Stops patcher for the SATConfig constructor.
        """
        self.patcher.stop()

    def test_load_config(self):
        """Test load_config with default config path."""
        load_config()
        self.mock_sat_config_cls.assert_called_once_with(DEFAULT_CONFIG_PATH)
        self.assertEqual(self.mock_sat_config_obj, sat.config.CONFIG)

    def test_load_config_env_var(self):
        """Test load_config with the config file path set in an env var."""
        config_file_path = '/my/custom/config.ini'
        with mock.patch('os.getenv', return_value=config_file_path):
            load_config()
        self.mock_sat_config_cls.assert_called_once_with(config_file_path)
        self.assertEqual(self.mock_sat_config_obj, sat.config.CONFIG)

    @mock.patch('sat.config.CONFIG')
    def test_load_config_already_loaded(self, mock_config):
        """Test load_config with CONFIG already loaded."""
        load_config()
        self.mock_sat_config_cls.assert_not_called()
        self.assertEqual(sat.config.CONFIG, mock_config)


class TestGetConfigValue(unittest.TestCase):
    """Tests for the get_config function."""

    @mock.patch('sat.config.CONFIG')
    @mock.patch('sat.config.load_config')
    def test_get_config_value(self, mock_load_config, mock_config):
        option_name = 'option'
        expected_value = 'expected'
        mock_config.get.return_value = expected_value
        option_value = get_config_value(option_name)
        mock_load_config.assert_called_once_with()
        mock_config.get.assert_called_once_with('default', option_name)
        self.assertEqual(expected_value, option_value)


class TestSATConfig(unittest.TestCase):
    """Tests for the SATConfig class"""

    def assert_in_element(self, element, container):
        """Assert the given element is in one of the elements in container.

        Returns:
            None.

        Raises:
            AssertionError: if the assertion fails.
        """
        for item in container:
            if element in item:
                return
        self.fail("Element '{}' is not in any of the elements in "
                  "the given container.".format(element))

    def assert_defaults_set(self, config):
        """Assert that all options in config are set to defaults.

        Returns:
            None.

        Raises:
            AssertionError: if any assertions fail.
        """
        for section in SAT_CONFIG_SPEC:
            for option_name, option_spec in SAT_CONFIG_SPEC[section].items():
                self.assertEqual(config.get(section, option_name),
                                 option_spec.default)

    def test_valid_config(self):
        """Test creating a SATConfig from a valid config file."""
        config = SATConfig(os.path.join(CONFIGS_DIR, 'valid.ini'))
        self.assertEqual(config.get('default', 'log_file_name'),
                         '/var/log/sat.log')
        self.assertEqual(config.get('default', 'log_file_level'),
                         'DEBUG')
        self.assertEqual(config.get('default', 'log_stderr_level'),
                         'ERROR')

    def test_invalid_log_levels(self):
        """Test creating a SATConfig from a config file w/ invalid option vals

        Currently, this is just invalid log levels.
        """
        with self.assertLogs(level='ERROR') as cm:
            config = SATConfig(os.path.join(CONFIGS_DIR, 'invalid_levels.ini'))

        msg_template = "Invalid value '{}' given for option '{}' in section 'default'"
        file_err_msg = msg_template.format('BLAH', 'log_file_level')
        stderr_err_msg = msg_template.format('WHATEVA', 'log_stderr_level')

        self.assert_in_element(file_err_msg, cm.output)
        self.assert_in_element(stderr_err_msg, cm.output)

        self.assert_defaults_set(config)

    def test_unknown_sections(self):
        """Test creating a SATConfig from a config file w/ unknown sections."""
        with self.assertLogs(level='WARNING') as cm:
            config = SATConfig(os.path.join(CONFIGS_DIR, 'unknown_sections.ini'))

        unknown_section_template = "Ignoring unknown section '{}' in config file."

        self.assertEqual(len(cm.output), 2)
        for section in ['unknown', 'another_unknown']:
            self.assert_in_element(unknown_section_template.format(section), cm.output)

        self.assert_defaults_set(config)

    def test_unknown_options(self):
        """Test creating a SATConfig from a config file w/ unknown options."""
        with self.assertLogs(level='WARNING') as cm:
            config = SATConfig(os.path.join(CONFIGS_DIR, 'unknown_options.ini'))

        unknown_option_template = ("Ignoring unknown option '{}' in section 'default' "
                                   "of config file.")

        self.assertEqual(len(cm.output), 2)
        for option in ['unknown', 'another_unknown']:
            self.assert_in_element(unknown_option_template.format(option), cm.output)

        self.assert_defaults_set(config)

    def test_empty_file(self):
        """Test creating a SATConfig from an empty config file."""
        config = SATConfig(os.path.join(CONFIGS_DIR, 'empty.ini'))
        self.assert_defaults_set(config)

    def test_nonexistent_file(self):
        """Test creating a SATConfig from a non-existent file."""
        file_name = 'does_not_exist.ini'
        with self.assertLogs(level='ERROR') as cm:
            config = SATConfig(file_name)

        expected_err_msg = ("Unable to read config file at '{}'. "
                            "Using default configuration values.").format(file_name)
        self.assert_in_element(expected_err_msg, cm.output)

        self.assert_defaults_set(config)


if __name__ == '__main__':
    unittest.main()
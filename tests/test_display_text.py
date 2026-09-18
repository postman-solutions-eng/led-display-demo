import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch

_lednamebadge_backup = sys.modules.get('lednamebadge')
_mock_creator = MagicMock()
_mock_lednamebadge = MagicMock()
_mock_lednamebadge.SimpleTextAndIcons.return_value = _mock_creator
sys.modules['lednamebadge'] = _mock_lednamebadge

from api import (  # noqa: E402
    LED_HARDWARE_DETAILS,
    LED_HARDWARE_ERROR,
    LED_PERMISSION_DETAILS,
    LED_PERMISSION_ERROR,
    _hardware_write_error_response,
    _is_led_permission_error,
    app,
)


class TestLedPermissionHelpers(TestCase):
    @classmethod
    def tearDownClass(cls):
        if _lednamebadge_backup is not None:
            sys.modules['lednamebadge'] = _lednamebadge_backup
        else:
            sys.modules.pop('lednamebadge', None)

    def test_detects_permission_error(self):
        self.assertTrue(_is_led_permission_error(PermissionError('denied')))

    def test_detects_os_error_access_denied(self):
        import errno

        self.assertTrue(_is_led_permission_error(OSError(errno.EACCES, 'Permission denied')))

    def test_detects_message_markers(self):
        self.assertTrue(_is_led_permission_error(Exception('Access denied (insufficient permissions)')))

    def test_non_permission_errors_return_500(self):
        body, status = _hardware_write_error_response(Exception('device busy'))
        self.assertEqual(status, 500)
        self.assertEqual(body['error'], LED_HARDWARE_ERROR)
        self.assertEqual(body['details'], LED_HARDWARE_DETAILS)

    def test_permission_errors_return_403(self):
        body, status = _hardware_write_error_response(PermissionError('denied'))
        self.assertEqual(status, 403)
        self.assertEqual(body['error'], LED_PERMISSION_ERROR)
        self.assertEqual(body['details'], LED_PERMISSION_DETAILS)


class TestDisplayText(TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_display_text_returns_500_when_hardware_write_fails(self):
        with patch('api._process_and_write', return_value=(
            {'error': LED_HARDWARE_ERROR, 'details': LED_HARDWARE_DETAILS},
            500,
        )):
            response = self.client.post(
                '/display-text',
                json={'text': 'Hello World!'},
            )

        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body['error'], LED_HARDWARE_ERROR)
        self.assertEqual(body['details'], LED_HARDWARE_DETAILS)

    def test_display_text_returns_403_when_hardware_write_is_denied(self):
        with patch('api._process_and_write', return_value=(
            {'error': LED_PERMISSION_ERROR, 'details': LED_PERMISSION_DETAILS},
            403,
        )):
            response = self.client.post(
                '/display-text',
                json={'text': 'Hello World!'},
            )

        self.assertEqual(response.status_code, 403)
        body = response.get_json()
        self.assertEqual(body['error'], LED_PERMISSION_ERROR)
        self.assertEqual(body['details'], LED_PERMISSION_DETAILS)

    def test_display_text_propagates_hardware_permission_error(self):
        with patch('api._process_and_write', return_value=(
            {'error': LED_PERMISSION_ERROR, 'details': LED_PERMISSION_DETAILS},
            403,
        )):
            response = self.client.post(
                '/display-text',
                json={'text': 'Hello World!'},
            )

        self.assertEqual(response.status_code, 403)
        body = response.get_json()
        self.assertEqual(body['error'], LED_PERMISSION_ERROR)

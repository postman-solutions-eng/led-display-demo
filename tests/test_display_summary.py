import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch

_lednamebadge_backup = sys.modules.get('lednamebadge')
_mock_creator = MagicMock()
_mock_lednamebadge = MagicMock()
_mock_lednamebadge.SimpleTextAndIcons.return_value = _mock_creator
sys.modules['lednamebadge'] = _mock_lednamebadge

from api import DEFAULT_SUMMARY, app  # noqa: E402


class TestDisplaySummary(TestCase):
    @classmethod
    def tearDownClass(cls):
        if _lednamebadge_backup is not None:
            sys.modules['lednamebadge'] = _lednamebadge_backup
        else:
            sys.modules.pop('lednamebadge', None)

    def setUp(self):
        self.client = app.test_client()

    def test_display_summary_without_postman_key_uses_default(self):
        with patch('api._process_and_write', return_value=None) as write_mock:
            response = self.client.post(
                '/display-summary',
                json={'type': 'welcome'},
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body, {'status': 'Summary displayed on LED'})
        write_mock.assert_called_once()
        self.assertEqual(write_mock.call_args.args[0], DEFAULT_SUMMARY)

    def test_display_summary_with_empty_api_key_uses_default(self):
        with patch('api._process_and_write', return_value=None) as write_mock, patch(
            'api.fetch_catalog_summary',
        ) as fetch_mock:
            response = self.client.post(
                '/display-summary',
                headers={'X-API-Key': '   '},
                json={'apiKey': ''},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'Summary displayed on LED'})
        fetch_mock.assert_not_called()
        write_mock.assert_called_once()
        self.assertEqual(write_mock.call_args.args[0], DEFAULT_SUMMARY)

    def test_display_summary_with_api_key_uses_catalog(self):
        catalog_summary = {
            'text': 'Production - 2 svcs (2 ok) :star:',
            'systemEnvironment': {'id': 'env-1', 'name': 'Production'},
            'serviceCount': 2,
            'services': [
                {'id': 'svc-1', 'name': 'payments', 'status': 'healthy'},
                {'id': 'svc-2', 'name': 'billing', 'status': 'healthy'},
            ],
            'hasMore': False,
        }
        with patch('api.fetch_catalog_summary', return_value=catalog_summary) as fetch_mock, patch(
            'api._process_and_write',
            return_value=None,
        ) as write_mock:
            response = self.client.post(
                '/display-summary',
                headers={'X-API-Key': 'PMAK-test'},
                json={'systemEnvironmentId': 'env-1'},
            )

        self.assertEqual(response.status_code, 200)
        fetch_mock.assert_called_once_with('PMAK-test', 'env-1')
        body = response.get_json()
        self.assertEqual(body['source'], 'postman-api-catalog')
        self.assertEqual(body['serviceCount'], 2)
        self.assertEqual(body['text'], catalog_summary['text'])
        write_mock.assert_called_once_with(catalog_summary['text'], command_queue=None, write_hardware=True)

    def test_display_summary_propagates_catalog_errors(self):
        from postman_catalog import PostmanCatalogError

        with patch(
            'api.fetch_catalog_summary',
            side_effect=PostmanCatalogError('Unauthorized', status_code=401),
        ):
            response = self.client.post(
                '/display-summary',
                headers={'X-API-Key': 'bad-key'},
                json={},
            )

        self.assertEqual(response.status_code, 401)
        body = response.get_json()
        self.assertEqual(body['error'], 'Failed to fetch API catalog')

    def test_display_summary_returns_500_when_hardware_write_fails(self):
        from api import LED_HARDWARE_DETAILS, LED_HARDWARE_ERROR

        with patch('api._process_and_write', return_value=(
            {'error': LED_HARDWARE_ERROR, 'details': LED_HARDWARE_DETAILS},
            500,
        )):
            response = self.client.post(
                '/display-summary',
                json={'type': 'welcome'},
            )

        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body['error'], LED_HARDWARE_ERROR)

    def test_display_summary_returns_403_when_hardware_write_is_denied(self):
        from api import LED_PERMISSION_DETAILS, LED_PERMISSION_ERROR

        with patch('api._process_and_write', return_value=(
            {'error': LED_PERMISSION_ERROR, 'details': LED_PERMISSION_DETAILS},
            403,
        )):
            response = self.client.post(
                '/display-summary',
                json={'type': 'welcome'},
            )

        self.assertEqual(response.status_code, 403)
        body = response.get_json()
        self.assertEqual(body['error'], LED_PERMISSION_ERROR)

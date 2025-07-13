import unittest
import os
import json
from unittest.mock import patch, mock_open
from crd.web.app import app

class TestWebApp(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page_no_data_directories(self):
        with patch('os.path.exists', return_value=False):
            with patch('os.listdir', side_effect=FileNotFoundError):
                response = self.app.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'No content available', response.data)

    def test_home_page_with_data(self):
        mock_json_data = {
            "AI & Tech": [
                {
                    "url": "http://example.com/ai-article",
                    "original_title": "AI is taking over",
                    "chinese_title": "人工智能正在接管",
                    "chinese_summary": "中文摘要",
                    "english_summary": "English Summary",
                    "source": "example.com"
                }
            ]
        }
        mock_json_str = json.dumps(mock_json_data)
        
        with patch('os.listdir', return_value=['2023-01-01']):
            with patch('os.path.isdir', return_value=True):
                with patch('os.path.exists', return_value=True):
                    with patch('builtins.open', mock_open(read_data=mock_json_str)):
                        response = self.app.get('/')
                        self.assertEqual(response.status_code, 200)
                        self.assertIn(b'AI & Tech', response.data)
                        self.assertIn(b'AI is taking over', response.data)
                        self.assertIn(b'English Summary', response.data)
                        self.assertIn(b'2023-01-01', response.data) # Check date tab

    def test_home_page_with_malformed_json(self):
        malformed_json_str = '{"AI & Tech": [}' # Incomplete JSON
        with patch('os.listdir', return_value=['2023-01-01']):
            with patch('os.path.isdir', return_value=True):
                with patch('os.path.exists', return_value=True):
                    with patch('builtins.open', mock_open(read_data=malformed_json_str)):
                        with patch('crd.web.app.app.logger.error') as mock_logger_error:
                            response = self.app.get('/')
                            self.assertEqual(response.status_code, 200)
                            self.assertIn(b'No content available', response.data)
                            mock_logger_error.assert_called_once()

    def test_home_page_date_selection(self):
        dates = ['2023-01-03', '2023-01-02', '2023-01-01']
        with patch('os.listdir', return_value=dates):
            with patch('os.path.isdir', return_value=True):
                # Mock open to return empty json for any path
                with patch('os.path.exists', return_value=True):
                    with patch('builtins.open', mock_open(read_data='{}')):
                        # Request a specific date
                        response = self.app.get('/?date=2023-01-02')
                        self.assertEqual(response.status_code, 200)
                        # Check that the selected tab is active
                        self.assertIn(b'href="/?date=2023-01-02" class="date-tab active"', response.data)
                        self.assertIn(b'No content available for 2023-01-02', response.data)
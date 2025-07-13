import unittest
from unittest.mock import patch, MagicMock
import os
from datetime import datetime, date, timedelta
import tempfile
import sys

# Add project root to path to allow importing crd
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crd.cli import main as crd_main

class TestCli(unittest.TestCase):

    def _setup_common_mocks(self, mock_config):
        """Helper to set up common mock configurations."""
        mock_config_instance = mock_config.return_value
        mock_config_instance.api_url = "test_url"
        mock_config_instance.api_key = "test_key"
        mock_config_instance.date_range_days = 7
        mock_config_instance.threads = 1
        mock_config_instance.keywords = []
        mock_config_instance.top_articles = 5
        mock_config_instance.rating_model = "gpt-3.5-turbo"
        mock_config_instance.summary_model = "gpt-4o"
        mock_config_instance.newsletter_title = "Test Newsletter"
        mock_config_instance.newsletter_font = "Arial"
        mock_config_instance.width = 800

    @patch('crd.cli.setup_logger')
    @patch('crd.cli.Config')
    @patch('crd.cli.APIClient')
    @patch('crd.cli.ArticleFetcher')
    @patch('crd.cli.ArticleAnalyzer')
    @patch('crd.cli.ArticleSummarizer')
    @patch('crd.cli.NewsletterRenderer')
    @patch('crd.cli.os.makedirs')
    @patch('crd.cli.write_json')
    @patch('crd.cli.os.path.exists', return_value=False) # Assume no data exists
    @patch('sys.argv', ['crd', '--output-dir', 'test_output'])
    def test_main_pipeline_runs_summarizer_correctly(
        self, mock_exists, mock_write_json, mock_makedirs, mock_renderer, mock_summarizer,
        mock_analyzer, mock_fetcher, mock_api_client, 
        mock_config, mock_setup_logger
    ):
        self._setup_common_mocks(mock_config)
        mock_config.return_value.feeds_config = {
            "Test Category": {
                "rating_criteria": "test criteria",
                "feeds": ["http://test.com/rss"]
            }
        }

        # Mock return values of process methods
        mock_fetcher.return_value.fetch_all_articles.return_value = [{'title': 't', 'link': 'l', 'date': 'd'}]
        mock_analyzer.return_value.process.return_value = [{"filename": "top_article.txt", "score": 9.0, "title": "Top Article", "url": "http://top.com"}]
        mock_summarizer.return_value.process.return_value = {"summary1": {"url": "http://example.com", "original_title": "ot", "chinese_title": "ct", "chinese_summary": "cs", "english_summary": "es", "source": "example.com"}}

        # Run the main function
        result = crd_main()

        # Assertions
        self.assertEqual(result, 0)
        # Should be called 3 times for the last 3 days
        self.assertEqual(mock_fetcher.call_count, 3)
        self.assertEqual(mock_analyzer.call_count, 3)
        self.assertEqual(mock_summarizer.call_count, 3)
        
        # Check that the renderer's thumbnail download and processing methods are called
        self.assertEqual(mock_renderer.return_value.download_thumbnails.call_count, 3)
        self.assertEqual(mock_renderer.return_value.process.call_count, 3)

        # Check that JSON files are written for each of the 3 days
        self.assertEqual(mock_write_json.call_count, 6) # 2 files per day

    @patch('crd.cli.setup_logger')
    @patch('crd.cli.Config')
    @patch('crd.cli.APIClient')
    @patch('crd.cli.ArticleFetcher')
    @patch('crd.cli.ArticleAnalyzer')
    @patch('crd.cli.ArticleSummarizer')
    @patch('crd.cli.NewsletterRenderer')
    @patch('crd.cli.os.makedirs')
    @patch('crd.cli.write_json')
    @patch('crd.cli.os.path.exists', return_value=False)
    @patch('sys.argv', ['crd', '--output-dir', 'test_output'])
    def test_main_pipeline_no_articles_found(
        self, mock_exists, mock_write_json, mock_makedirs, mock_renderer, mock_summarizer,
        mock_analyzer, mock_fetcher, mock_api_client, 
        mock_config, mock_setup_logger
    ):
        self._setup_common_mocks(mock_config)
        mock_config.return_value.feeds_config = {
            "Test Category": {
                "rating_criteria": "test criteria",
                "feeds": ["http://test.com/rss"]
            }
        }

        # Mock fetcher to return no articles
        mock_fetcher.return_value.fetch_all_articles.return_value = []
        # When no articles are fetched, analyzer finds no top articles
        mock_analyzer.return_value.process.return_value = []

        # Run the main function
        result = crd_main()

        # Assertions
        self.assertEqual(result, 0)
        self.assertEqual(mock_fetcher.return_value.fetch_all_articles.call_count, 3)
        self.assertEqual(mock_analyzer.return_value.process.call_count, 3)
        mock_summarizer.assert_not_called()

        # Renderer methods should not be called if there are no summaries
        mock_renderer.return_value.download_thumbnails.assert_not_called()
        mock_renderer.return_value.process.assert_not_called()

    @patch('crd.cli.setup_logger')
    @patch('crd.cli.Config')
    @patch('crd.cli.APIClient')
    @patch('crd.cli.ArticleFetcher')
    @patch('crd.cli.ArticleAnalyzer')
    @patch('crd.cli.ArticleSummarizer')
    @patch('crd.cli.NewsletterRenderer')
    @patch('crd.cli.os.makedirs')
    @patch('crd.cli.write_json')
    @patch('crd.cli.os.path.exists', return_value=False)
    @patch('sys.argv', ['crd', '--output-dir', 'test_output'])
    def test_main_pipeline_no_high_rated_articles(
        self, mock_exists, mock_write_json, mock_makedirs, mock_renderer, mock_summarizer,
        mock_analyzer, mock_fetcher, mock_api_client, 
        mock_config, mock_setup_logger
    ):
        self._setup_common_mocks(mock_config)
        mock_config.return_value.feeds_config = {
            "Test Category": {
                "rating_criteria": "test criteria",
                "feeds": ["http://test.com/rss"]
            }
        }

        # Mock return values
        mock_fetcher.return_value.fetch_all_articles.return_value = [{'title': 't', 'link': 'l', 'date': 'd'}]
        # Mock analyzer to return no top articles
        mock_analyzer.return_value.process.return_value = []

        # Run the main function
        result = crd_main()

        # Assertions
        self.assertEqual(result, 0)
        self.assertEqual(mock_analyzer.return_value.process.call_count, 3)
        mock_summarizer.assert_not_called()
        
        # Renderer methods should not be called if there are no summaries
        mock_renderer.return_value.download_thumbnails.assert_not_called()
        mock_renderer.return_value.process.assert_not_called()

    @patch('crd.cli.setup_logger')
    @patch('crd.cli.Config')
    @patch('crd.cli.APIClient')
    @patch('crd.cli.ArticleFetcher')
    @patch('crd.cli.ArticleAnalyzer')
    @patch('crd.cli.ArticleSummarizer')
    @patch('crd.cli.NewsletterRenderer')
    @patch('crd.cli.os.makedirs')
    @patch('crd.cli.write_json')
    @patch('crd.cli.os.path.exists', return_value=False)
    @patch('sys.argv', ['crd', '--output-dir', 'test_output'])
    def test_main_pipeline_one_category_fails(
        self, mock_exists, mock_write_json, mock_makedirs, mock_renderer, mock_summarizer,
        mock_analyzer, mock_fetcher, mock_api_client, 
        mock_config, mock_setup_logger
    ):
        self._setup_common_mocks(mock_config)
        mock_config.return_value.feeds_config = {
            "Failing Category": {
                "rating_criteria": "fail criteria",
                "feeds": ["http://fail.com/rss"]
            },
            "Successful Category": {
                "rating_criteria": "success criteria",
                "feeds": ["http://success.com/rss"]
            }
        }
        mock_logger = mock_setup_logger.return_value

        # Mock fetcher to fail for the first category and succeed for the second
        mock_fetcher.return_value.fetch_all_articles.side_effect = [
            Exception("Fetch failed"),
            [{'title': 's_title', 'link': 's_link', 'date': 's_date'}]
        ]
        
        # Mock analyzer and summarizer for the successful call
        mock_analyzer.return_value.process.return_value = [{"filename": "s_article.txt", "score": 8.0, "title": "Success", "url": "http://success.com/s"}]
        mock_summarizer.return_value.process.return_value = {"s_summary": {"url": "http://success.com/s", "original_title": "ot", "chinese_title": "ct", "chinese_summary": "cs", "english_summary": "es", "source": "success.com"}}

        result = crd_main()

        self.assertEqual(result, 0)
        # Check that the error for the failing category was logged 3 times (once per day)
        self.assertEqual(mock_logger.error.call_count, 3)
        
        # Check that fetcher was called 6 times (2 categories * 3 days)
        self.assertEqual(mock_fetcher.return_value.fetch_all_articles.call_count, 6)
        
        # Check that analyzer and summarizer were called 3 times for the successful category
        self.assertEqual(mock_analyzer.return_value.process.call_count, 3)
        self.assertEqual(mock_summarizer.return_value.process.call_count, 3)

        # Check that final JSONs were written for the successful runs
        self.assertEqual(mock_write_json.call_count, 6) # 2 files * 3 days

    @patch('crd.cli.setup_logger')
    @patch('crd.cli.Config')
    @patch('crd.cli.APIClient')
    @patch('crd.cli.ArticleFetcher')
    @patch('crd.cli.ArticleAnalyzer')
    @patch('crd.cli.ArticleSummarizer')
    @patch('crd.cli.NewsletterRenderer')
    @patch('crd.cli.os.makedirs')
    @patch('crd.cli.write_json')
    @patch('crd.cli.os.path.exists', return_value=True) # Assume data EXISTS
    @patch('sys.argv', ['crd', '--output-dir', 'test_output']) # NO --force
    def test_main_pipeline_skips_when_data_exists_and_no_force(
        self, mock_exists, mock_write_json, mock_makedirs, mock_renderer, mock_summarizer,
        mock_analyzer, mock_fetcher, mock_api_client, 
        mock_config, mock_setup_logger
    ):
        self._setup_common_mocks(mock_config)
        mock_config.return_value.feeds_config = {
            "Test Category": {
                "rating_criteria": "test criteria",
                "feeds": ["http://test.com/rss"]
            }
        }

        # Run the main function
        result = crd_main()

        # Assertions
        self.assertEqual(result, 0)
        # The pipeline should be skipped for all 3 days
        mock_fetcher.assert_not_called()
        mock_analyzer.assert_not_called()
        mock_summarizer.assert_not_called()
        # Check that the renderer's methods are not called
        mock_renderer.return_value.download_thumbnails.assert_not_called()
        mock_renderer.return_value.process.assert_not_called()

    @patch('crd.cli.setup_logger')
    @patch('crd.cli.Config')
    @patch('crd.cli.APIClient')
    @patch('crd.cli.ArticleFetcher')
    @patch('crd.cli.ArticleAnalyzer')
    @patch('crd.cli.ArticleSummarizer')
    @patch('crd.cli.NewsletterRenderer')
    @patch('crd.cli.os.makedirs')
    @patch('crd.cli.write_json')
    @patch('crd.cli.os.path.exists', return_value=True) # Assume data EXISTS
    @patch('sys.argv', ['crd', '--output-dir', 'test_output', '--force']) # Run with --force
    def test_main_pipeline_runs_with_force_flag_when_data_exists(
        self, mock_exists, mock_write_json, mock_makedirs, mock_renderer, mock_summarizer,
        mock_analyzer, mock_fetcher, mock_api_client, 
        mock_config, mock_setup_logger
    ):
        self._setup_common_mocks(mock_config)
        mock_config.return_value.feeds_config = {
            "Test Category": {
                "rating_criteria": "test criteria",
                "feeds": ["http://test.com/rss"]
            }
        }

        # Mock return values
        mock_fetcher.return_value.fetch_all_articles.return_value = [{'title': 't', 'link': 'l', 'date': 'd'}]
        mock_analyzer.return_value.process.return_value = [{"filename": "top_article.txt", "score": 9.0, "title": "Top Article", "url": "http://top.com"}]
        mock_summarizer.return_value.process.return_value = {"summary1": {"url": "http://example.com", "original_title": "ot", "chinese_title": "ct", "chinese_summary": "cs", "english_summary": "es", "source": "example.com"}}

        # Run the main function
        result = crd_main()

        # Assertions
        self.assertEqual(result, 0)
        # Even though os.path.exists is True, the pipeline should run due to --force
        self.assertEqual(mock_fetcher.call_count, 3)
        self.assertEqual(mock_analyzer.call_count, 3)
        self.assertEqual(mock_summarizer.call_count, 3)

if __name__ == '__main__':
    unittest.main()
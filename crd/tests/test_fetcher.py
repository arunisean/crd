import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from datetime import datetime, date

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crd.fetcher import ArticleFetcher

class TestArticleFetcher(unittest.TestCase):

    def test_fetch_articles_from_rss_filters_by_date(self):
        # Mock feedparser and requests
        mock_http_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b''
        mock_http_client.get.return_value = mock_response

        # Create a mock feed with entries on different dates
        mock_feed = {
            'entries': [
                {'title': 'Article 1', 'link': 'http://a1.com', 'published_parsed': datetime(2023, 1, 1, 12, 0, 0).timetuple()},
                {'title': 'Article 2', 'link': 'http://a2.com', 'published_parsed': datetime(2023, 1, 2, 12, 0, 0).timetuple()},
                {'title': 'Article 3', 'link': 'http://a3.com', 'published_parsed': datetime(2023, 1, 2, 18, 0, 0).timetuple()}
            ]
        }

        target_date = date(2023, 1, 2)
        fetcher = ArticleFetcher(http_client=mock_http_client, target_date=target_date)

        with patch('feedparser.parse', return_value=mock_feed):
            articles = fetcher.fetch_articles_from_rss('http://dummy.url/rss')

            self.assertEqual(len(articles), 2)
            self.assertEqual(articles[0]['title'], 'Article 2')
            self.assertEqual(articles[1]['title'], 'Article 3')

    def test_fetch_articles_from_atom_feed_with_updated_date(self):
        # Mock feedparser and requests
        mock_http_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b''
        mock_http_client.get.return_value = mock_response

        # Mock feed with 'updated_parsed' for Atom feeds (like arXiv)
        mock_feed = {
            'entries': [
                {'title': 'Article 1', 'link': 'http://a1.com', 'updated_parsed': datetime(2023, 1, 1, 12, 0, 0).timetuple()},
                {'title': 'Article 2', 'link': 'http://a2.com', 'updated_parsed': datetime(2023, 1, 2, 12, 0, 0).timetuple()}
            ]
        }

        target_date = date(2023, 1, 2)
        fetcher = ArticleFetcher(http_client=mock_http_client, target_date=target_date)

        with patch('feedparser.parse', return_value=mock_feed):
            articles = fetcher.fetch_articles_from_rss('http://dummy.url/atom')

            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0]['title'], 'Article 2')

    def test_fetch_articles_skips_entries_without_date(self):
        mock_http_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b''
        mock_http_client.get.return_value = mock_response

        mock_feed = {
            'entries': [
                {'title': 'Article 1', 'link': 'http://a1.com'},  # No date
                {'title': 'Article 2', 'link': 'http://a2.com', 'published_parsed': datetime(2023, 1, 2, 12, 0, 0).timetuple()}
            ]
        }

        target_date = date(2023, 1, 2)
        fetcher = ArticleFetcher(http_client=mock_http_client, target_date=target_date)

        with patch('feedparser.parse', return_value=mock_feed):
            articles = fetcher.fetch_articles_from_rss('http://dummy.url/rss')

            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0]['title'], 'Article 2')

if __name__ == '__main__':
    unittest.main()
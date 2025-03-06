import unittest
from unittest.mock import patch, MagicMock
from crd.fetcher import ArticleFetcher

class TestArticleFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = ArticleFetcher()
    
    @patch('crd.fetcher.requests.get')
    def test_fetch_articles_from_rss(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = b'<?xml version="1.0"?><rss><channel><item><title>Test Article</title><link>http://example.com/article</link><pubDate>Mon, 01 Jan 2023 12:00:00 GMT</pubDate></item></channel></rss>'
        mock_get.return_value = mock_response
        
        # Call the method
        articles = self.fetcher.fetch_articles_from_rss('http://example.com/rss')
        
        # Assert results
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]['title'], 'Test Article')
        self.assertEqual(articles[0]['link'], 'http://example.com/article')
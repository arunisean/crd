import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
import sys

# Add project root to path to allow importing crd
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crd.renderer import NewsletterRenderer

class TestNewsletterRenderer(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_renderer_temp"
        os.makedirs(self.test_dir, exist_ok=True)
        self.renderer = NewsletterRenderer(width=800)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('crd.renderer.NewsletterRenderer._render_html_to_png')
    def test_process_creates_image_with_data(self, mock_render_png):
        summaries_data = {
            "Test Category": [{
                "url": "http://example.com", "chinese_title": "测试标题",
                "chinese_summary": "测试摘要", "source": "example.com"
            }]
        }
        thumbnails_dir = os.path.join(self.test_dir, 'thumbnails')

        result = self.renderer.process(summaries_data, thumbnails_dir)

        self.assertTrue(result)
        self.assertTrue(os.path.isdir(thumbnails_dir))
        mock_render_png.assert_called_once()

    @patch('crd.renderer.NewsletterRenderer.get_thumbnail', return_value="http://example.com/thumb.jpg")
    @patch('crd.renderer.NewsletterRenderer.download_thumbnail', return_value=True)
    def test_download_thumbnails(self, mock_download, mock_get_thumbnail):
        summaries_data = {
            "Test Category": [{
                "url": "http://example.com/article",
                "original_title": "Test Title"
            }]
        }
        thumbnails_dir = os.path.join(self.test_dir, 'thumbnails')

        modified_data = self.renderer.download_thumbnails(summaries_data, thumbnails_dir)

        mock_get_thumbnail.assert_called_with("http://example.com/article")
        mock_download.assert_called_once()
        
        article = modified_data["Test Category"][0]
        self.assertIn('thumbnail', article)
        self.assertIsNotNone(article['thumbnail'])
        self.assertTrue(article['thumbnail'].startswith('thumbnails'))

    @patch('crd.renderer.NewsletterRenderer._render_html_to_png')
    def test_process_does_nothing_without_data(self, mock_render_png):
        summaries_data = {}
        thumbnails_dir = os.path.join(self.test_dir, 'thumbnails')

        result = self.renderer.process(summaries_data, thumbnails_dir)

        self.assertFalse(result)
        self.assertFalse(os.path.isdir(thumbnails_dir))
        mock_render_png.assert_not_called()

if __name__ == '__main__':
    unittest.main()
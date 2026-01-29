import sys
import unittest
import inspect
from datetime import datetime
from main import FetchRequest, _fetch_gmail, _fetch_ft, _fetch_dsa, _fetch_rss, _fetch_google

class TestMonthlyFetch(unittest.TestCase):
    def test_fetch_request_model(self):
        """Test that FetchRequest accepts date_start and date_end."""
        # Provide valid datetime objects
        req = FetchRequest(
            date_start=datetime.now(), 
            date_end=datetime.now(),
            sources=[]
        )
        self.assertTrue(hasattr(req, 'date_start'))
        self.assertTrue(hasattr(req, 'date_end'))
        self.assertFalse(hasattr(req, 'date_from'))

    def test_scraper_signatures(self):
        """Test that scraper helper functions accept start/end dates."""
        
        # Helper to check signature
        def check_sig(func):
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            self.assertIn('date_start', params, f"{func.__name__} missing date_start")
            self.assertIn('date_end', params, f"{func.__name__} missing date_end")

        check_sig(_fetch_gmail)
        check_sig(_fetch_ft)
        check_sig(_fetch_dsa)
        check_sig(_fetch_rss)
        check_sig(_fetch_google)

if __name__ == '__main__':
    unittest.main()

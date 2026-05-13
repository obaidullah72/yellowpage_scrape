from bs4 import BeautifulSoup
from django.test import SimpleTestCase

from core.scraper import (
    _decode_cloudflare_email_protection_hex,
    extract_yellowpages_detail_email,
)


class CloudflareEmailDecodeTests(SimpleTestCase):
    def test_decode_sample_hash(self):
        hex_payload = "5f3d003b3a383a313430333d1f263e373030713c3032"
        self.assertEqual(_decode_cloudflare_email_protection_hex(hex_payload), "b_degenkolb@yahoo.com")

    def test_extract_from_cloudflare_href_anchor(self):
        html = (
            '<a class="email-business" href="/cdn-cgi/l/email-protection#5f3d003b3a383a313430333d1f263e373030713c3032">'
            "Email</a>"
        )
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            extract_yellowpages_detail_email(soup.select_one("a.email-business")),
            "b_degenkolb@yahoo.com",
        )

    def test_extract_mailto(self):
        html = '<a class="email-business" href="mailto:hello@example.com">Email</a>'
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            extract_yellowpages_detail_email(soup.select_one("a.email-business")),
            "hello@example.com",
        )

    def test_extract_data_cfemail_on_child(self):
        hex_payload = "5f3d003b3a383a313430333d1f263e373030713c3032"
        html = (
            f'<a class="email-business" href="#">'
            f'<span data-cfemail="{hex_payload}">[email\xa0protected]</span></a>'
        )
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            extract_yellowpages_detail_email(soup.select_one("a.email-business")),
            "b_degenkolb@yahoo.com",
        )

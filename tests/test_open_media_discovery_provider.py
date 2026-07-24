"""Focused offline contract tests for open-media discovery."""

import json
import unittest
from urllib.parse import parse_qs, urlparse

from modules.source_intake.open_media_discovery_provider import (
    OpenMediaDiscoveryProvider,
)

REQUEST = {
    "candidate_id": "A-1",
    "title": "폭염 경보 확산",
    "category": "사회",
}


class RoutingTransport:
    def __init__(self, google_body="{}", commons_body="{}"):
        self.google_body = google_body
        self.commons_body = commons_body
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        if "googleapis.com/customsearch" in url:
            return self.google_body
        if "commons.wikimedia.org" in url:
            return self.commons_body
        raise AssertionError(f"unexpected endpoint: {url}")


def provider_with(transport, google=True):
    return OpenMediaDiscoveryProvider(
        transport=transport,
        google_api_key="google-key" if google else "",
        google_cse_id="google-cse-id" if google else "",
    )


class OpenMediaDiscoveryProviderTest(unittest.TestCase):
    def test_missing_google_credentials_fail_without_network(self):
        transport = RoutingTransport()
        result = provider_with(transport, google=False).discover(
            "A",
            "search_open_images",
            REQUEST,
        )
        self.assertEqual(result["status"], "empty")
        self.assertEqual(
            result["diagnostics"]["google"],
            "google_credentials_missing",
        )
        self.assertTrue(result["network_used"])
        self.assertEqual(result["assets"], [])
        self.assertEqual(len(transport.calls), 1)

    def test_google_image_search_sends_rights_filter(self):
        transport = RoutingTransport(
            google_body=json.dumps(
                {
                    "items": [
                        {
                            "title": "폭염 현장 사진",
                            "link": "https://images.example.com/heat.jpg",
                            "displayLink": "images.example.com",
                            "image": {
                                "contextLink": "https://news.example.com/heat",
                            },
                        }
                    ]
                }
            )
        )
        result = provider_with(transport).discover(
            "A",
            "search_open_images",
            {**REQUEST, "open_media_source": "google_cse"},
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["network_used"])
        self.assertEqual(len(transport.calls), 1)
        query = parse_qs(urlparse(transport.calls[0]["url"]).query)
        self.assertEqual(query["searchType"], ["image"])
        self.assertIn("rights", query)
        self.assertTrue(query["rights"][0])

    def test_google_images_are_rights_filtered_production_candidates(self):
        transport = RoutingTransport(
            google_body=json.dumps(
                {
                    "items": [
                        {
                            "title": "폭염 현장 사진",
                            "link": "https://images.example.com/heat.jpg",
                            "displayLink": "images.example.com",
                            "image": {
                                "contextLink": "https://news.example.com/heat",
                            },
                        }
                    ]
                }
            )
        )
        result = provider_with(transport).discover(
            "A",
            "search_open_images",
            {**REQUEST, "open_media_source": "google_cse"},
        )
        asset = result["assets"][0]
        self.assertEqual(asset["url"], "https://images.example.com/heat.jpg")
        self.assertEqual(
            asset["source_url"],
            "https://news.example.com/heat",
        )
        self.assertEqual(asset["source_api"], "google_custom_search")
        self.assertFalse(asset["metadata_only"])
        self.assertFalse(asset["reference_only"])
        self.assertTrue(asset["usable_in_production"])
        self.assertTrue(asset["manual_visual_review_required"])
        self.assertFalse(asset["publish_authorized"])
        self.assertFalse(asset["downloaded"])

    def test_wikimedia_commons_preserves_license_attribution_and_source(self):
        transport = RoutingTransport(
            commons_body=json.dumps(
                {
                    "query": {
                        "pages": {
                            "10": {
                                "title": "File:Heat wave.jpg",
                                "imageinfo": [
                                    {
                                        "url": "https://upload.wikimedia.org/heat.jpg",
                                        "thumburl": "https://upload.wikimedia.org/heat-1600.jpg",
                                        "descriptionurl": (
                                            "https://commons.wikimedia.org/wiki/"
                                            "File:Heat_wave.jpg"
                                        ),
                                        "mime": "image/jpeg",
                                        "mediatype": "BITMAP",
                                        "width": 4096,
                                        "height": 2731,
                                        "extmetadata": {
                                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                            "Artist": {"value": "Example Photographer"},
                                            "Credit": {"value": "Wikimedia Commons"},
                                        },
                                    }
                                ],
                            }
                        }
                    }
                }
            )
        )
        result = provider_with(transport).discover(
            "A",
            "search_open_images",
            {**REQUEST, "open_media_source": "wikimedia_commons"},
        )
        self.assertEqual(result["status"], "ok")
        asset = result["assets"][0]
        self.assertEqual(
            asset["url"],
            "https://upload.wikimedia.org/heat-1600.jpg",
        )
        self.assertEqual(asset["original_url"], "https://upload.wikimedia.org/heat.jpg")
        self.assertEqual(asset["license"], "CC BY-SA 4.0")
        self.assertEqual(asset["attribution"], "Example Photographer")
        self.assertEqual(asset["mime_type"], "image/jpeg")
        self.assertEqual(asset["media_type"], "BITMAP")
        self.assertEqual(asset["width"], 4096)
        self.assertEqual(asset["height"], 2731)
        self.assertEqual(asset["pixel_area"], 11186176)
        self.assertEqual(
            asset["source_url"],
            "https://commons.wikimedia.org/wiki/File:Heat_wave.jpg",
        )
        self.assertEqual(asset["source_api"], "wikimedia_commons")
        self.assertFalse(asset["reference_only"])
        self.assertTrue(asset["usable_in_production"])
        self.assertFalse(asset["downloaded"])

    def test_commons_excludes_document_media_and_prioritizes_raster_photos(self):
        transport = RoutingTransport(
            commons_body=json.dumps(
                {
                    "query": {
                        "pages": [
                            {
                                "title": "File:Heat report.pdf",
                                "imageinfo": [
                                    {
                                        "url": "https://upload.wikimedia.org/report.pdf",
                                        "descriptionurl": "https://commons.wikimedia.org/wiki/report",
                                        "mime": "application/pdf",
                                        "mediatype": "OFFICE",
                                        "width": 1200,
                                        "height": 1600,
                                        "extmetadata": {
                                            "LicenseShortName": {"value": "CC BY 4.0"}
                                        },
                                    }
                                ],
                            },
                            {
                                "title": "File:Heat icon.svg",
                                "imageinfo": [
                                    {
                                        "url": "https://upload.wikimedia.org/icon.svg",
                                        "descriptionurl": "https://commons.wikimedia.org/wiki/icon",
                                        "mime": "image/svg+xml",
                                        "mediatype": "DRAWING",
                                        "width": 800,
                                        "height": 800,
                                        "extmetadata": {
                                            "LicenseShortName": {"value": "CC0"}
                                        },
                                    }
                                ],
                            },
                            {
                                "title": "File:Heat chart.png",
                                "imageinfo": [
                                    {
                                        "url": "https://upload.wikimedia.org/chart.png",
                                        "descriptionurl": "https://commons.wikimedia.org/wiki/chart",
                                        "mime": "image/png",
                                        "mediatype": "BITMAP",
                                        "width": 2000,
                                        "height": 1200,
                                        "extmetadata": {
                                            "LicenseShortName": {"value": "CC BY 4.0"}
                                        },
                                    }
                                ],
                            },
                            {
                                "title": "File:Heat street.jpg",
                                "imageinfo": [
                                    {
                                        "url": "https://upload.wikimedia.org/street.jpg",
                                        "descriptionurl": "https://commons.wikimedia.org/wiki/street",
                                        "mime": "image/jpeg",
                                        "mediatype": "BITMAP",
                                        "width": 1800,
                                        "height": 1200,
                                        "extmetadata": {
                                            "LicenseShortName": {"value": "CC BY-SA 4.0"}
                                        },
                                    }
                                ],
                            },
                        ]
                    }
                }
            )
        )
        result = provider_with(transport).discover(
            "A",
            "search_open_images",
            {
                **REQUEST,
                "open_media_source": "wikimedia_commons",
                "category": "",
            },
        )
        self.assertEqual(
            [asset["title"] for asset in result["assets"]],
            ["File:Heat street.jpg", "File:Heat chart.png"],
        )

    def test_commons_prioritizes_title_then_explicit_terms_with_a_hard_limit(self):
        transport = RoutingTransport(commons_body=json.dumps({"query": {"pages": []}}))
        result = provider_with(transport).discover(
            "A",
            "search_open_images",
            {
                **REQUEST,
                "open_media_source": "wikimedia_commons",
                "search_terms": ["서울 폭염 현장", "온열질환", "서울 폭염 현장", "기상청"],
            },
        )
        self.assertEqual(
            result["queries"],
            ["폭염 경보 확산", "서울 폭염 현장", "온열질환"],
        )
        self.assertEqual(len(transport.calls), 3)
        searches = [
            parse_qs(urlparse(call["url"]).query)["gsrsearch"][0]
            for call in transport.calls
        ]
        self.assertEqual(
            searches,
            ["file:폭염 경보 확산", "file:서울 폭염 현장", "file:온열질환"],
        )

    def test_internal_category_is_not_used_as_a_topic_when_title_exists(self):
        transport = RoutingTransport(commons_body=json.dumps({"query": {"pages": []}}))
        result = provider_with(transport).discover(
            "A",
            "search_open_images",
            {
                "title": "제주 스타트업 첫 투자",
                "category": "economy_market",
                "search_terms": ["economy_market"],
                "open_media_source": "wikimedia_commons",
            },
        )

        self.assertEqual(result["queries"], ["제주 스타트업 첫 투자"])
        self.assertEqual(result["query"], "제주 스타트업 첫 투자")

    def test_unsupported_operation_is_refused_without_network(self):
        transport = RoutingTransport()
        result = provider_with(transport).discover(
            "A",
            "collect_real_comments",
            REQUEST,
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "unsupported_operation")
        self.assertFalse(result["network_used"])
        self.assertEqual(result["assets"], [])
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()

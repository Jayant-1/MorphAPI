"""
Unit Tests for MorphAPI V2 Network Sniffer
"""

import pytest
from morphapi_v2.browser.network_sniffer import NetworkSniffer


def test_network_sniffer_algolia_payload():
    sniffer = NetworkSniffer(target_fields=["company_name", "description", "link"])

    mock_algolia_payload = {
        "results": [
            {
                "index": "YCCompany_production",
                "hits": [
                    {
                        "name": "Stripe",
                        "one_liner": "Payments infrastructure for the internet",
                        "website": "https://stripe.com",
                        "batch": "S10",
                    },
                    {
                        "name": "Airbnb",
                        "one_liner": "Book accommodations around the world",
                        "website": "https://airbnb.com",
                        "batch": "W09",
                    },
                    {
                        "name": "Coinbase",
                        "one_liner": "Buy and sell crypto",
                        "website": "https://coinbase.com",
                        "batch": "S12",
                    },
                ]
            }
        ]
    }

    sniffer._search_arrays(mock_algolia_payload, "https://algolia.net/1/indexes/*/queries")
    best = sniffer.get_best_match()

    assert best is not None
    assert best["score"] >= 0.6
    assert len(best["records"]) == 3
    assert best["records"][0]["name"] == "Stripe"
    assert "companyname" in best["field_mapping"] or "company_name" in best["field_mapping"]

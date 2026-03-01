from BadBunny.src.ticketswap_monitor import _extract_next_data_json, fetch_listings


def test_extract_next_data_json():
    html = '<html><script id="__NEXT_DATA__" type="application/json">{"ok":true}</script></html>'
    data = _extract_next_data_json(html)
    assert data["ok"] is True


def test_fetch_listings_from_next_data(monkeypatch):
    html = '''
    <html><script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "listings": [
            {
              "id": "abc123",
              "title": "Bad Bunny Madrid",
              "formatted_price": "120 EUR",
              "number_of_tickets": 2,
              "url": "/event/foo/listing/abc123"
            }
          ]
        }
      }
    }
    </script></html>
    '''

    class FakeResponse:
        status_code = 200
        text = html

        def raise_for_status(self):
            return None

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("BadBunny.src.ticketswap_monitor.requests.get", fake_get)

    listings = fetch_listings("https://www.ticketswap.com/event/bad-bunny-madrid")
    assert len(listings) == 1
    assert listings[0].listing_id == "abc123"
    assert listings[0].url.startswith("https://www.ticketswap.com/")

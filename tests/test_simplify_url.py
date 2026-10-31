from events_ai import simplify_url


def test_simplify_url():
    response = simplify_url.get("https://google.com")
    print(response)


def test_simplify_url_with_selenium():
    response = simplify_url.get("https://google.com", use_selenium=True)
    print(response)

import time


def fetch_json_with_retry(session, url, timeout=30, tries=4):
    last_error = None
    for i in range(tries):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as error:
            last_error = error
            time.sleep(0.6 * (i + 1))
    raise last_error


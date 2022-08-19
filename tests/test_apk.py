import responses

from tgtg.google_play_scraper import get_last_apk_version


def test_get_latest_apk_version():
    responses.add_passthru("https://play.google.com/store/apps/details")
    get_last_apk_version()

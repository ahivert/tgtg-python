import json
import re

import requests

RE_SCRIPT = re.compile(
    r"AF_initDataCallback\({key:\s*'ds:5'.*?data:([\s\S]*?), sideChannel:.+<\/script"
)


def get_last_apk_version():
    response = requests.get(
        "https://play.google.com/store/apps/details?id=com.app.tgtg&hl=en&gl=US"
    )
    match = RE_SCRIPT.search(response.text)
    data = json.loads(match.group(1))
    return data[1][2][140][0][0][0]

"""Client JSON-RPC pentru serviciul de memorie (pmorg-memory/1.0)."""

import json
import urllib.request

CONTRACT = "pmorg-memory/1.0"


class MemoryClient:
    def __init__(self, url):
        self.url = url
        self._counter = 0

    def call(self, method, **params):
        self._counter += 1
        params["contract"] = CONTRACT
        request = {
            "jsonrpc": "2.0",
            "id": self._counter,
            "method": method,
            "params": params,
        }
        data = json.dumps(request).encode()
        req = urllib.request.Request(
            self.url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def ok(self, method, **params):
        resp = self.call(method, **params)
        if "error" in resp:
            raise RuntimeError(f"{method}: {resp['error']}")
        return resp["result"]

    def expect_error(self, method, expected_code, **params):
        resp = self.call(method, **params)
        return resp.get("error", {}).get("code") == expected_code

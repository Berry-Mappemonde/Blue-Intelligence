#!/usr/bin/env python3
"""Vérifie le login CDSE (jeton). N'imprime jamais le mot de passe."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from cdse_auth import credentials

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)


def main() -> int:
    user, password = credentials()
    body = urllib.parse.urlencode({
        "client_id": "cdse-public",
        "grant_type": "password",
        "username": user,
        "password": password,
    }).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"CDSE login refusé (HTTP {exc.code})", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"CDSE injoignable : {exc.reason}", file=sys.stderr)
        return 3
    token_type = payload.get("token_type") or "?"
    expires = payload.get("expires_in")
    has_access = bool(payload.get("access_token"))
    if not has_access:
        print("CDSE : réponse sans jeton", file=sys.stderr)
        return 2
    print(f"CDSE : connexion OK ({token_type}, {expires}s) pour {user}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import http.server
import json
import secrets
import socketserver
import urllib.parse
import webbrowser

import requests


AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    code: str | None = None
    state_error: str | None = None
    expected_state: str = ""

    def do_GET(self) -> None:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        state = query.get("state", [""])[0]
        if state != self.expected_state:
            self.__class__.state_error = "OAuth state mismatch"
            self._write_response("OAuth state mismatch. You can close this tab.")
            return
        self.__class__.code = query.get("code", [None])[0]
        self._write_response("OAuth complete. You can close this tab and return to the terminal.")

    def log_message(self, format: str, *args) -> None:
        return

    def _write_response(self, message: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Get a YouTube OAuth refresh token for this project.")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--env-out", help="Write GitHub Secret values to this local env file.")
    parser.add_argument("--code", help="Exchange a copied OAuth authorization code instead of running localhost callback.")
    parser.add_argument("--print-token-response", action="store_true", help="Print the raw token response. Avoid in normal use.")
    parser.add_argument("--include-sheets", action="store_true", help="Request Google Sheets write scope too.")
    args = parser.parse_args()

    redirect_uri = f"http://localhost:{args.port}/oauth2callback"
    state = secrets.token_urlsafe(24)
    OAuthCallbackHandler.expected_state = state
    scope = f"{YOUTUBE_SCOPE} {SHEETS_SCOPE}" if args.include_sheets else YOUTUBE_SCOPE

    if args.code:
        code = args.code
    else:
        params = {
            "client_id": args.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

        print("Open this URL if the browser does not open automatically:")
        print(url)
        webbrowser.open(url)

        with ReusableTCPServer(("localhost", args.port), OAuthCallbackHandler) as server:
            server.handle_request()

        if OAuthCallbackHandler.state_error:
            raise RuntimeError(OAuthCallbackHandler.state_error)
        if not OAuthCallbackHandler.code:
            raise RuntimeError("No OAuth code was received")
        code = OAuthCallbackHandler.code

    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"error": response.text}
        raise RuntimeError(f"Token exchange failed: {response.status_code} {error_payload}")
    token_payload = response.json()

    refresh_token = token_payload.get("refresh_token", "")
    if args.env_out:
        with open(args.env_out, "w", encoding="utf-8") as f:
            f.write(f"YOUTUBE_CLIENT_ID={args.client_id}\n")
            f.write(f"YOUTUBE_CLIENT_SECRET={args.client_secret}\n")
            f.write(f"YOUTUBE_REFRESH_TOKEN={refresh_token}\n")
        print(f"\nSecret values were written to {args.env_out}")
    else:
        print("\nAdd these values to GitHub Secrets:")
        print(f"YOUTUBE_CLIENT_ID={args.client_id}")
        print("YOUTUBE_CLIENT_SECRET=<hidden>")
        print("YOUTUBE_REFRESH_TOKEN=<hidden>")
    if args.print_token_response:
        print("\nFull token response:")
        print(json.dumps(token_payload, ensure_ascii=False, indent=2))
    else:
        print("\nToken exchange succeeded. Raw tokens were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

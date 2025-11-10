# Discord Adapter

Adapter package that implements the `chat_client_api.ChatClient` interface by calling the
`discord_client_service_api_client` generated client which talks to the running `discord_service`.

This mirrors the approach used by `service_client_adapter` for the mail service.

Usage example:

```
from discord_adapter.main import DiscordAdapter

adapter = DiscordAdapter(base_url="http://127.0.0.1:8000")
# Provide an access token previously obtained via OAuth2 callback
adapter.set_token("<access-token>")
for m in adapter.get_messages(channel_id="123", max_results=10):
    print(m.content)
```

```
python3.11 - <<PY
from discord_adapter.main import DiscordAdapter
# create adapter pointing at running service
adapter = DiscordAdapter(base_url="http://127.0.0.1:8000")
print("adapter ready:", adapter)
# If you have a token:
# adapter.set_token("<ACCESS_TOKEN>")
PY
```

To run the adapter and test it manually:

1. Start the Discord service the adapter talks to (defaults to http://127.0.0.1:8000):

```bash
cd src/discord_service
# activate your virtualenv if you use one, then:
uvicorn discord_service.main:app --reload --port 8000
```

2. Quick verify the service `/login` endpoint is reachable:

```bash
curl -v "http://127.0.0.1:8000/login"
```

Look for either a 3xx redirect with a `Location` header (authorization URL) or a JSON body containing a URL key (for example `url` or `authorization_url`).

3. Run the adapter from the repo (without installing) to call `login` and get the auth URL:

```bash
PYTHONPATH=src/discord_adapter/src python - <<'PY'
from discord_adapter.main import DiscordAdapter
ad = DiscordAdapter(base_url="http://127.0.0.1:8000")
result = ad.login(follow=False)  # follow=True will attempt to open your browser
print("login returned:", result)
PY
```

If `result` is a string it is the authorization URL you can visit or redirect a browser to. If it's an HTTP status (e.g. `200` or `302`) inspect the service response (see step 2).

4. Open the browser automatically (convenience):

```bash
PYTHONPATH=src/discord_adapter/src python - <<'PY'
from discord_adapter.main import DiscordAdapter
ad = DiscordAdapter(base_url="http://127.0.0.1:8000")
print("returned:", ad.login(follow=True))
PY
```

This calls Python's `webbrowser.open(...)` as a best-effort convenience; failures to open the browser are ignored and the URL is still returned.

5. Optional: install the adapter in editable mode for repeated use:

```bash
pip install -e src/discord_adapter
```

6. Testing the OAuth callback / token exchange:

- Visit the authorization URL returned by `login` and complete the OAuth flow with the provider. The provider will redirect to the service's `/auth/callback?code=...` which exchanges the code for a token and stores an authenticated client in the running service.
- For local testing without real Discord credentials you can mock the service endpoints or run the integration tests that stub `DiscordClient.get_authorization_url` and related flows.

Notes

- The service and adapter expect environment variables for a real OAuth flow: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, and `DISCORD_REDIRECT_URI` (the `discord_service` reads these when constructing `DiscordClient`).
- The adapter's `login` returns either an authorization URL (string) or an `HTTPStatus` for backward compatibility. Pass `follow=True` to open the URL in your browser automatically.

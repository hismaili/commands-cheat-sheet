# API Testing

## CORS

A browser blocking a POST with an opaque "CORS error" isn't telling you what the server actually returned. Skip the browser and send the preflight yourself — the response headers say exactly which origin, method, and headers the server will allow.

```bash
# Send the OPTIONS preflight a browser would send before a cross-origin POST
curl -X OPTIONS -i -H "Origin: <ORIGIN>" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: Content-Type" <API_URL>
```

## OAuth2

Testing an endpoint behind OAuth2 means getting a token first — the resource owner password credentials grant does this in one request, trading a username and password directly for an access token.

```bash
# Exchange user credentials for an access token via the password grant
curl -X POST '<TOKEN_URL>' -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=<USERNAME>' -d 'password=<PASSWORD>' -d 'grant_type=password' -d 'client_id=<CLIENT_ID>'
```

## Key Patterns

| Symptom | Move |
|---|---|
| Browser reports a CORS failure with no useful detail | Run the OPTIONS preflight manually and inspect the `Access-Control-Allow-*` response headers |
| Need a bearer token before you can test a protected endpoint | Request one via the password grant against the token endpoint |

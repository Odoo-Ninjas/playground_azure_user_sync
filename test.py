from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

client_id = 'dc36c06c-1763-4d53-a858-9ec98491a2f2'
client_secret = 'jEj8Q~hrC6SCu9orr94ChMHyUXFi89nGIZ4X2bw.'
client_secret = '-aF8Q~2ra6ThjcMO0XgTAV-_wlw6gLV1Ke3MddxH'
client_secret = 'bKi8Q~w8C7hlLdD3bsOhnTi1DeboPLYzeHhF5a_O'
token_url = 'https://login.microsoftonline.com/b2732c7d-5061-402c-81eb-879997aa61f2/oauth2/v2.0/token'
scope = ['https://graph.microsoft.com/.default']  # Use .default to get all permissions defined in your app registration

client = BackendApplicationClient(client_id=client_id)
oauth = OAuth2Session(client=client)
token = oauth.fetch_token(
    token_url=token_url,
    client_id=client_id,
    client_secret=client_secret,
    scope=scope,
)
print(token)

graph_api_url = 'https://graph.microsoft.com/v1.0/users'
headers = {
    'Authorization': f'Bearer {token["access_token"]}',
    'Content-Type': 'application/json'
}

response = oauth.get(graph_api_url, headers=headers)

if response.status_code == 200:
    users_data = response.json()
    for user in users_data.get('value', []):
        print(f'User: {user["displayName"]}')
else:
    print(f'Error: {response.status_code} - {response.text}')
"""OAuth2 social login: Google and LinkedIn using Authlib."""

import os
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

# Google
google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

if google_client_id:
    oauth.register(
        name="google",
        client_id=google_client_id,
        client_secret=google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# LinkedIn
linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

if linkedin_client_id:
    oauth.register(
        name="linkedin",
        client_id=linkedin_client_id,
        client_secret=linkedin_client_secret,
        access_token_url="https://www.linkedin.com/oauth/v2/accessToken",
        authorize_url="https://www.linkedin.com/oauth/v2/authorization",
        api_base_url="https://api.linkedin.com/",
        client_kwargs={"scope": "openid profile email"},
    )

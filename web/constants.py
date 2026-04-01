"""Constants for OAuth and API."""

# Discord OAuth scopes
DISCORD_SCOPES = {
    "identify": "View your account information",
    "guilds": "View your Discord servers",
    "guilds.members.read": "View members in servers",
    "email": "View your email (if verified)",
}

# Required scopes for this app (guilds.members.read: GET /users/@me/guilds/{id}/member)
REQUIRED_DISCORD_SCOPES = ["identify", "guilds", "guilds.members.read"]

# Token type
TOKEN_TYPE = "bearer"

# API routes
API_PREFIX = "/api"
AUTH_PREFIX = "/api/auth"
WEB_PREFIX = "/web"

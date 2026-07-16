"""Supabase client factories.

Two clients serve two different purposes:

- ``user_client`` — created from the user's JWT; all DB operations run under
  that user's Supabase session, so RLS policies are enforced automatically.
  Use this in any request-path code that reads or writes on behalf of the
  authenticated user.

- ``service_client`` — created once at module load with the service-role key;
  bypasses RLS.  Use this only for backend-initiated work (ingestion, cascade
  deletes, admin reads) where there is no user context.
"""

from supabase import AsyncClient, acreate_client

from app.config import settings

# ---------------------------------------------------------------------------
# Service-role client — module-level singleton, created lazily on first use
# ---------------------------------------------------------------------------

_service_client: AsyncClient | None = None


async def service_client() -> AsyncClient:
    """Return the shared service-role Supabase client.

    Initialised on the first call; reused on every subsequent call.
    The service-role key bypasses RLS — only use this for ingestion and
    other server-initiated operations with no per-user context.
    """
    global _service_client
    if _service_client is None:
        _service_client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _service_client


# ---------------------------------------------------------------------------
# User-scoped client — constructed per request from the caller's JWT
# ---------------------------------------------------------------------------


async def user_client(jwt: str) -> AsyncClient:
    """Return a Supabase client scoped to *jwt*.

    Creates a fresh client and sets the session from the provided JWT so that
    every subsequent DB call runs as that user.  RLS policies are enforced.

    ``jwt`` is the raw bearer token from the ``Authorization`` header — the
    auth dependency in ``app/auth/dependencies.py`` is responsible for
    validating it before passing it here.
    """
    client = await acreate_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )
    # set_session expects (access_token, refresh_token); we only have the
    # access token here, so pass an empty string for refresh — the client will
    # still forward the correct Authorization header for every DB request.
    await client.auth.set_session(access_token=jwt, refresh_token="")
    return client

"""FastAPI auth dependency — verify Supabase JWTs and expose the current user.

Usage in a route::

    from app.auth.dependencies import CurrentUser

    @router.get("/threads")
    async def list_threads(user: CurrentUser) -> ...:
        ...  # user.id is the authenticated Supabase user UUID

The dependency extracts the bearer token from the ``Authorization`` header,
calls Supabase Auth to validate it, and returns the user object.  Any
missing, malformed, or expired token yields a 401 before the handler runs.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AsyncClient

from app.database.supabase import service_client

_bearer = HTTPBearer()


async def _get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
):
    """Validate the bearer JWT with Supabase Auth and return the User.

    ``HTTPBearer`` already rejects requests with no ``Authorization`` header
    or a non-Bearer scheme with a 403, so by the time we get here the token
    string is guaranteed to be present.
    """
    token = credentials.credentials
    client: AsyncClient = await service_client()

    try:
        response = await client.auth.get_user(token)
    except Exception as exc:
        # Supabase raises for expired / invalid tokens; surface as 401.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if response is None or response.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return response.user


# Convenience alias — annotate route parameters with this type to inject the
# validated user without repeating the Depends() boilerplate everywhere.
# The concrete type is gotrue.types.User (inferred via supabase's stubs).
CurrentUser = Annotated[object, Depends(_get_current_user)]

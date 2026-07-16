"""GET /auth/me — test endpoint that validates the bearer token and echoes
the authenticated user's ID and email.

Used during Phase 2 verification to confirm:
  - the JWT from Supabase Auth reaches the backend correctly
  - the CurrentUser dependency validates and extracts the user
  - the 401 path fires on missing/bad tokens
"""

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(user: CurrentUser) -> dict[str, str]:
    """Return the authenticated user's basic profile.

    Requires a valid Supabase JWT in the Authorization header.
    Returns 401 if missing, expired, or invalid.
    """
    return {
        "id": user.id,  # type: ignore[union-attr]
        "email": user.email or "",  # type: ignore[union-attr]
    }

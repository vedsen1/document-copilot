/**
 * Wraps any route that requires authentication.
 *
 * - While the initial session check is in flight: renders nothing (avoids
 *   a redirect flash before we know if the user is actually signed in).
 * - Unauthenticated: redirects to /login, preserving the intended URL so
 *   we can send the user back after they sign in.
 * - Authenticated: renders children as-is.
 */

import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

export default function ProtectedRoute() {
  const { session, loading } = useAuth()
  const location = useLocation()

  if (loading) return null

  if (!session) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}

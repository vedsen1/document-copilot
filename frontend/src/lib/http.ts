/**
 * Thin fetch wrapper that automatically attaches the Supabase bearer token.
 *
 * All API calls to the FastAPI backend should go through `apiFetch` so that:
 *   - The `Authorization: Bearer <token>` header is always present.
 *   - The base URL is taken from the validated `env` module.
 *   - Non-2xx responses are thrown as `Error` with the server message.
 *
 * For streaming endpoints use `apiFetch` directly and read `response.body`.
 */

import { env } from '@/lib/env'
import { supabase } from '@/lib/supabase'

async function getToken(): Promise<string> {
  const { data, error } = await supabase.auth.getSession()
  if (error || !data.session) {
    throw new Error('Not authenticated')
  }
  return data.session.access_token
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await getToken()

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init.headers,
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    // Attempt to surface the server error message; fall back to status text.
    let message: string
    try {
      const body = await response.json()
      message = body?.detail ?? response.statusText
    } catch {
      message = response.statusText
    }
    throw new Error(`API error ${response.status}: ${message}`)
  }

  return response
}

import { createClient } from '@supabase/supabase-js'
import { env } from '@/lib/env'

/**
 * Browser-side Supabase client.
 *
 * Single instance for the whole app — handles Auth session storage,
 * token refresh, and realtime subscriptions.  Use this wherever you
 * need to interact with Supabase from React (auth state, sign-in, sign-out).
 *
 * Never use the service-role key here; the anon key is intentionally
 * restricted to what RLS permits for the authenticated user.
 */
export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey)

/**
 * Single source of truth for environment variables.
 *
 * Throws at module load if any required variable is missing, so the
 * developer gets a clear error immediately rather than a cryptic runtime
 * failure deep inside a fetch call.
 *
 * Import `env` everywhere instead of reading `import.meta.env` directly.
 */

function require(key: string): string {
  const value = import.meta.env[key]
  if (!value) {
    throw new Error(
      `Missing required environment variable: ${key}\n` +
        `Add it to your .env file and restart the dev server.`,
    )
  }
  return value as string
}

export const env = {
  apiBaseUrl: require('VITE_API_BASE_URL'),
  supabaseUrl: require('VITE_SUPABASE_URL'),
  supabaseAnonKey: require('VITE_SUPABASE_ANON_KEY'),
} as const

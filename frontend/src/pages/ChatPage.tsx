/**
 * Placeholder chat shell — will be replaced in Phase 3.
 * Exists now so the post-login redirect to /chat lands somewhere real.
 */

import { useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/context/AuthContext'

export default function ChatPage() {
  const { session } = useAuth()
  const navigate = useNavigate()

  async function handleSignOut() {
    await supabase.auth.signOut()
    navigate('/login', { replace: true })
  }

  return (
    <div className="chat-placeholder">
      <p>Signed in as <strong>{session?.user.email}</strong></p>
      <button id="signout-button" type="button" onClick={handleSignOut}>
        Sign out
      </button>
    </div>
  )
}

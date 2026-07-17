/**
 * ChatLanding — shown at /chat (no thread selected).
 * Empty-state prompt to create a first thread.
 */

import { MessageSquare } from 'lucide-react'

export default function ChatLanding() {
  return (
    <div className="chat-landing">
      <div className="chat-landing-icon">
        <MessageSquare size={40} strokeWidth={1.5} />
      </div>
      <h2 className="chat-landing-title">Document Copilot</h2>
      <p className="chat-landing-sub">
        Select a conversation from the sidebar or start a new one.
      </p>
    </div>
  )
}

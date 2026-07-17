/**
 * ThreadSidebar — purely presentational thread list.
 *
 * Receives threads from ChatLayout and highlights the active one via
 * useParams. Does not fetch or mutate anything directly.
 */

import { useNavigate, useParams } from 'react-router-dom'
import { MessageSquare, Plus, Loader2 } from 'lucide-react'
import type { ChatThread } from '@/lib/api'

interface Props {
  threads: ChatThread[]
  loading: boolean
  onNewChat: () => void
}

function relativeDate(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

export default function ThreadSidebar({ threads, loading, onNewChat }: Props) {
  const { threadId: activeId } = useParams<{ threadId?: string }>()
  const navigate = useNavigate()

  return (
    <aside className="chat-sidebar">
      <div className="sidebar-header">
        <span className="sidebar-title">
          <MessageSquare size={16} />
          Chats
        </span>
        <button
          id="new-chat-button"
          type="button"
          className="new-chat-btn"
          onClick={onNewChat}
          title="New chat"
        >
          <Plus size={16} />
          New
        </button>
      </div>

      <div className="sidebar-list">
        {loading && (
          <div className="sidebar-loading">
            <Loader2 size={18} className="sidebar-spinner" />
          </div>
        )}

        {!loading && threads.length === 0 && (
          <p className="sidebar-empty">No conversations yet.</p>
        )}

        {!loading &&
          threads.map(thread => (
            <button
              key={thread.id}
              id={`thread-${thread.id}`}
              type="button"
              className={`sidebar-item${thread.id === activeId ? ' sidebar-item--active' : ''}`}
              onClick={() => navigate(`/chat/${thread.id}`)}
            >
              <span className="sidebar-item-title">
                {thread.title ?? 'Untitled'}
              </span>
              <span className="sidebar-item-date">
                {relativeDate(thread.created_at)}
              </span>
            </button>
          ))}
      </div>
    </aside>
  )
}

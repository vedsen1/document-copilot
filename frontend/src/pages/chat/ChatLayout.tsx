/**
 * ChatLayout — persistent shell for all /chat routes.
 *
 * Renders the thread sidebar on the left and the active thread (via <Outlet>)
 * on the right. Owns the thread list: fetches once on mount and exposes a
 * refresh callback so child pages can trigger a reload after creating a thread.
 */

import { useCallback, useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { createThread, listThreads, type ChatThread } from '@/lib/api'
import ThreadSidebar from '@/components/ThreadSidebar'

export default function ChatLayout() {
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [loadingThreads, setLoadingThreads] = useState(true)

  const fetchThreads = useCallback(async () => {
    try {
      const data = await listThreads()
      setThreads(data)
    } catch {
      // Non-fatal — sidebar just stays empty or stale
    } finally {
      setLoadingThreads(false)
    }
  }, [])

  useEffect(() => {
    void fetchThreads()
  }, [fetchThreads])

  async function handleNewChat() {
    try {
      const thread = await createThread('New chat')
      await fetchThreads()
      navigate(`/chat/${thread.id}`)
    } catch {
      // TODO: surface error in a toast in a later phase
    }
  }

  return (
    <div className="chat-layout">
      <ThreadSidebar
        threads={threads}
        loading={loadingThreads}
        onNewChat={handleNewChat}
      />
      <main className="chat-main">
        <Outlet context={{ refreshThreads: fetchThreads }} />
      </main>
    </div>
  )
}

/**
 * ThreadPage — rendered at /chat/:threadId.
 *
 * Owns all message state for the active thread:
 * - loads persisted messages from the backend on mount / threadId change
 * - handles the send → stream → persist cycle
 * - passes messages + streamed partial content down to MessageList
 */

import { useEffect, useRef, useState } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import { listMessages, streamChat, type ChatMessage } from '@/lib/api'
import MessageList from '@/components/MessageList'
import ChatInput from '@/components/ChatInput'

interface OutletCtx {
  refreshThreads: () => Promise<void>
}

export default function ThreadPage() {
  const { threadId } = useParams<{ threadId: string }>()
  const { refreshThreads } = useOutletContext<OutletCtx>()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streamedContent, setStreamedContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)

  // Abort streaming when the user navigates away mid-stream
  const abortRef = useRef<AbortController | null>(null)

  // Load message history whenever the active thread changes
  useEffect(() => {
    if (!threadId) return
    setMessages([])
    setStreamedContent('')
    setLoadError(null)

    listMessages(threadId)
      .then(setMessages)
      .catch(() => setLoadError('Failed to load messages. Please try again.'))

    return () => {
      abortRef.current?.abort()
    }
  }, [threadId])

  async function handleSend(text: string) {
    if (!threadId || isStreaming) return
    setSendError(null)

    // Optimistic: show the user's message immediately
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      thread_id: threadId,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setIsStreaming(true)
    setStreamedContent('')

    // Build the message list the backend expects (full history + new user turn)
    const outgoing = [...messages, userMsg].map(m => ({
      role: m.role as 'user' | 'assistant',
      content: m.content,
    }))

    try {
      const ac = new AbortController()
      abortRef.current = ac

      const response = await streamChat(threadId, outgoing)

      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''

      // Read SSE stream: lines are "data: <chunk>\n\n", terminated by "data: [DONE]\n\n"
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        for (const line of chunk.split('\n')) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data:')) continue
          const payload = trimmed.slice('data:'.length).trim()
          if (payload === '[DONE]') break
          accumulated += payload
          setStreamedContent(accumulated)
        }
      }

      // Commit the completed assistant message to the messages list
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        thread_id: threadId,
        role: 'assistant',
        content: accumulated,
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMsg])
      setStreamedContent('')
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setSendError('Failed to send message. Please try again.')
        // Remove the optimistic user message on failure
        setMessages(prev => prev.filter(m => m.id !== userMsg.id))
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
      // Refresh sidebar so updated_at reorders correctly
      void refreshThreads()
    }
  }

  if (loadError) {
    return (
      <div className="thread-error">
        <p>{loadError}</p>
      </div>
    )
  }

  return (
    <div className="thread-page">
      <MessageList
        messages={messages}
        streamedContent={streamedContent}
        isStreaming={isStreaming}
      />
      {sendError && (
        <p className="thread-send-error" role="alert">
          {sendError}
        </p>
      )}
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </div>
  )
}

/**
 * MessageList — renders persisted messages + the in-flight streamed partial.
 *
 * Auto-scrolls to the bottom whenever messages or streamedContent changes.
 * The streaming assistant message is shown with an animated indicator while
 * the stream is active.
 */

import { useEffect, useRef } from 'react'
import type { ChatMessage } from '@/lib/api'
import { Bot, User } from 'lucide-react'

interface Props {
  messages: ChatMessage[]
  streamedContent: string
  isStreaming: boolean
}

export default function MessageList({ messages, streamedContent, isStreaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamedContent])

  const isEmpty = messages.length === 0 && !isStreaming

  return (
    <div className="message-list" role="log" aria-live="polite" aria-label="Chat messages">
      {isEmpty && (
        <div className="message-list-empty">
          <p>Send a message to start the conversation.</p>
        </div>
      )}

      {messages.map(msg => (
        <div
          key={msg.id}
          className={`message message--${msg.role}`}
        >
          <div className="message-avatar">
            {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
          </div>
          <div className="message-bubble">
            <p className="message-content">{msg.content}</p>
          </div>
        </div>
      ))}

      {/* In-flight streamed assistant reply */}
      {isStreaming && (
        <div className="message message--assistant message--streaming">
          <div className="message-avatar">
            <Bot size={16} />
          </div>
          <div className="message-bubble">
            {streamedContent ? (
              <p className="message-content">
                {streamedContent}
                <span className="streaming-cursor" aria-hidden="true" />
              </p>
            ) : (
              <div className="streaming-dots" aria-label="Assistant is typing">
                <span />
                <span />
                <span />
              </div>
            )}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}

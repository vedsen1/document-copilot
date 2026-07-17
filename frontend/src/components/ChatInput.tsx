/**
 * ChatInput — textarea + send button, pinned to the bottom of the chat pane.
 *
 * Enter sends; Shift+Enter inserts a newline.
 * Disabled and visually dimmed while isStreaming (passed as `disabled` prop).
 */

import { useRef, type KeyboardEvent, type FormEvent } from 'react'
import { Send } from 'lucide-react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function submit() {
    const text = textareaRef.current?.value.trim() ?? ''
    if (!text || disabled) return
    onSend(text)
    if (textareaRef.current) {
      textareaRef.current.value = ''
      textareaRef.current.style.height = 'auto'
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function handleInput() {
    const el = textareaRef.current
    if (!el) return
    // Auto-grow up to ~6 lines
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    submit()
  }

  return (
    <form id="chat-form" className="chat-input-bar" onSubmit={handleSubmit}>
      <textarea
        id="chat-input"
        ref={textareaRef}
        className="chat-textarea"
        placeholder={disabled ? 'Assistant is responding…' : 'Message Document Copilot…'}
        rows={1}
        disabled={disabled}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        aria-label="Chat message input"
      />
      <button
        id="chat-send"
        type="submit"
        className="chat-send-btn"
        disabled={disabled}
        aria-label="Send message"
      >
        <Send size={18} />
      </button>
    </form>
  )
}

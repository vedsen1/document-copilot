/**
 * Typed API helpers for every backend endpoint.
 *
 * Each function maps 1-to-1 with a FastAPI route.  Response shapes are typed
 * here; keep them in sync with the backend Pydantic schemas.
 *
 * For streaming chat, `streamChat` returns the raw `Response` so the caller
 * can consume `response.body` as a ReadableStream.
 */

import { apiFetch } from '@/lib/http'

// ---------------------------------------------------------------------------
// Types (mirror backend Pydantic response schemas)
// ---------------------------------------------------------------------------

export interface ChatThread {
  id: string
  title: string | null
  created_at: string
}

export interface ChatMessage {
  id: string
  thread_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface AiSdkMessage {
  role: 'user' | 'assistant'
  content: string
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<{ status: string }> {
  const res = await apiFetch('/health')
  return res.json()
}

// ---------------------------------------------------------------------------
// Chat threads
// ---------------------------------------------------------------------------

export async function listThreads(): Promise<ChatThread[]> {
  const res = await apiFetch('/chat/threads')
  return res.json()
}

export async function createThread(title?: string): Promise<ChatThread> {
  const res = await apiFetch('/chat/threads', {
    method: 'POST',
    body: JSON.stringify({ title: title ?? null }),
  })
  return res.json()
}

export async function getThread(threadId: string): Promise<ChatThread> {
  const res = await apiFetch(`/chat/threads/${threadId}`)
  return res.json()
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

export async function listMessages(threadId: string): Promise<ChatMessage[]> {
  const res = await apiFetch(`/chat/threads/${threadId}/messages`)
  return res.json()
}

// ---------------------------------------------------------------------------
// Streaming chat — returns the raw Response for the caller to stream
// ---------------------------------------------------------------------------

export async function streamChat(
  threadId: string,
  messages: AiSdkMessage[],
): Promise<Response> {
  // Do NOT pass through apiFetch's error-throwing path — streaming responses
  // must be consumed by the caller before the body is read.
  return apiFetch('/chat/stream', {
    method: 'POST',
    body: JSON.stringify({ thread_id: threadId, messages }),
  })
}

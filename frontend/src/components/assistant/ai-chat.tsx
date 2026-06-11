"use client";

import { Bot, MessageSquare, PlusCircle, Send, UserRound } from "lucide-react";
import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  createChatSession,
  getChatSession,
  getChatSessions,
  sendChatMessage,
  type ChatMessage,
  type ChatSession,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const suggestedPrompts = [
  "Why did Tesla move today?",
  "Summarize Nvidia news.",
  "What is Apple's current sentiment?",
];

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function AiChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const loadSession = useCallback(async (sessionId: number) => {
    setError(null);
    const detail = await getChatSession(sessionId);
    setActiveSession({
      id: detail.id,
      title: detail.title,
      created_at: detail.created_at,
      updated_at: detail.updated_at,
    });
    setMessages(detail.messages);
  }, []);

  const loadSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const loadedSessions = await getChatSessions();
      setSessions(loadedSessions);

      if (loadedSessions.length > 0) {
        await loadSession(loadedSessions[0].id);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to load chat history");
    } finally {
      setIsLoading(false);
    }
  }, [loadSession]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function handleNewChat() {
    setError(null);

    try {
      const session = await createChatSession({ title: "New AI chat" });
      setSessions((currentSessions) => [session, ...currentSessions]);
      setActiveSession(session);
      setMessages([]);
      setDraft("");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to create chat");
    }
  }

  async function ensureActiveSession(content: string) {
    if (activeSession) {
      return activeSession;
    }

    const session = await createChatSession({ title: content.slice(0, 80) });
    setSessions((currentSessions) => [session, ...currentSessions]);
    setActiveSession(session);
    return session;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const content = draft.trim();
    if (!content) {
      return;
    }

    setIsSending(true);
    setError(null);
    setDraft("");

    try {
      const session = await ensureActiveSession(content);
      const exchange = await sendChatMessage(session.id, { content });

      setMessages((currentMessages) => [
        ...currentMessages,
        exchange.user_message,
        exchange.assistant_message,
      ]);
      setActiveSession(exchange.session);
      setSessions((currentSessions) => {
        const filteredSessions = currentSessions.filter((item) => item.id !== exchange.session.id);
        return [exchange.session, ...filteredSessions];
      });
    } catch (caughtError) {
      setDraft(content);
      setError(caughtError instanceof Error ? caughtError.message : "Unable to send message");
    } finally {
      setIsSending(false);
    }
  }

  async function handleSuggestedPrompt(prompt: string) {
    setDraft(prompt);
  }

  return (
    <div className="grid min-h-[680px] gap-5 xl:grid-cols-[280px_1fr]">
      <aside className="rounded-lg border bg-card/80">
        <div className="flex items-center justify-between border-b p-4">
          <div>
            <p className="text-sm font-semibold">Chat History</p>
            <p className="text-xs text-muted-foreground">{sessions.length} saved sessions</p>
          </div>
          <Button type="button" size="icon" variant="outline" onClick={handleNewChat} aria-label="New chat">
            <PlusCircle className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        <div className="max-h-[560px] space-y-2 overflow-y-auto p-3">
          {isLoading ? (
            <p className="px-2 py-3 text-sm text-muted-foreground">Loading chats...</p>
          ) : sessions.length === 0 ? (
            <p className="px-2 py-3 text-sm text-muted-foreground">No saved chats yet.</p>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={cn(
                  "flex w-full items-start gap-2 rounded-md px-3 py-3 text-left text-sm transition-colors hover:bg-secondary",
                  activeSession?.id === session.id && "bg-secondary",
                )}
                onClick={() => loadSession(session.id)}
              >
                <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="line-clamp-2">{session.title}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="flex min-h-[680px] flex-col rounded-lg border bg-card/80">
        <div className="border-b p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold">{activeSession?.title ?? "New AI chat"}</p>
              <p className="text-xs text-muted-foreground">
                Answers use stock data, news, and sentiment context from this platform.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {suggestedPrompts.map((prompt) => (
                <Button
                  key={prompt}
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => handleSuggestedPrompt(prompt)}
                >
                  {prompt}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex h-full min-h-[360px] items-center justify-center text-center">
              <div className="max-w-md">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-md bg-primary text-primary-foreground">
                  <Bot className="h-5 w-5" aria-hidden="true" />
                </div>
                <h2 className="mt-4 text-lg font-semibold">Ask a market research question</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Try a ticker-specific question about price moves, recent headlines, or sentiment.
                </p>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3",
                  message.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                {message.role === "assistant" ? (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                    <Bot className="h-4 w-4" aria-hidden="true" />
                  </div>
                ) : null}
                <div
                  className={cn(
                    "max-w-[760px] rounded-lg border px-4 py-3 text-sm leading-6",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-background/50",
                  )}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  <p
                    className={cn(
                      "mt-2 text-xs",
                      message.role === "user" ? "text-primary-foreground/70" : "text-muted-foreground",
                    )}
                  >
                    {formatTime(message.created_at)}
                  </p>
                </div>
                {message.role === "user" ? (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-secondary">
                    <UserRound className="h-4 w-4" aria-hidden="true" />
                  </div>
                ) : null}
              </div>
            ))
          )}

          {isSending ? (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Bot className="h-4 w-4" aria-hidden="true" />
              </div>
              Analyzing stock and news context...
            </div>
          ) : null}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t p-4">
          {error ? (
            <p className="mb-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleSubmit}>
            <textarea
              className="min-h-24 flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              maxLength={2000}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask about a ticker, news, or sentiment..."
              value={draft}
            />
            <Button type="submit" disabled={isSending || !draft.trim()} className="sm:h-24">
              <Send className="h-4 w-4" aria-hidden="true" />
              Send
            </Button>
          </form>
          <p className="mt-3 text-xs text-muted-foreground">
            Informational research only. Verify data and make investment decisions independently.
          </p>
        </div>
      </section>
    </div>
  );
}

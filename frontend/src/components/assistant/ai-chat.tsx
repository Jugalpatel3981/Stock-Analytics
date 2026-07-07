"use client";

import { Bot, ExternalLink, MessageSquare, PlusCircle, Send, Trash2, UserRound } from "lucide-react";
import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast-provider";
import {
  createChatSession,
  deleteChatSession,
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
  "What are investors worried about regarding Apple?",
];

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

type AiChatProps = {
  initialPrompt?: string;
};

export function AiChat({ initialPrompt }: AiChatProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const { showToast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const loadSession = useCallback(async (sessionId: number) => {
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

    try {
      const loadedSessions = await getChatSessions();
      setSessions(loadedSessions);

      if (initialPrompt) {
        setActiveSession(null);
        setMessages([]);
      } else if (loadedSessions.length > 0) {
        await loadSession(loadedSessions[0].id);
      }
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to load chat history" });
    } finally {
      setIsLoading(false);
    }
  }, [initialPrompt, loadSession, showToast]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  useEffect(() => {
    if (initialPrompt) {
      setDraft(initialPrompt);
    }
  }, [initialPrompt]);

  async function handleNewChat() {

    try {
      const session = await createChatSession({ title: "New AI chat" });
      setSessions((currentSessions) => [session, ...currentSessions]);
      setActiveSession(session);
      setMessages([]);
      setDraft("");
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to create chat" });
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
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to send message" });
    } finally {
      setIsSending(false);
    }
  }

  async function handleSuggestedPrompt(prompt: string) {
    setDraft(prompt);
  }

  async function handleDeleteSession(sessionId: number) {
    setDeletingSessionId(sessionId);

    try {
      await deleteChatSession(sessionId);
      const remainingSessions = sessions.filter((session) => session.id !== sessionId);
      setSessions(remainingSessions);

      if (activeSession?.id === sessionId) {
        const nextSession = remainingSessions[0];

        if (nextSession) {
          await loadSession(nextSession.id);
        } else {
          setActiveSession(null);
          setMessages([]);
          setDraft("");
        }
      }

      showToast({ message: "Chat deleted" });
    } catch (caughtError) {
      showToast({ message: caughtError instanceof Error ? caughtError.message : "Unable to delete chat" });
    } finally {
      setDeletingSessionId(null);
    }
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
              <div
                key={session.id}
                className={cn(
                  "group flex items-start gap-1 rounded-md transition-colors hover:bg-secondary",
                  activeSession?.id === session.id && "bg-secondary",
                )}
              >
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-start gap-2 px-3 py-3 text-left text-sm"
                  onClick={() => loadSession(session.id)}
                >
                  <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="line-clamp-2">{session.title}</span>
                </button>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="mr-1 mt-1 h-8 w-8 shrink-0 text-muted-foreground opacity-70 hover:text-destructive hover:opacity-100"
                  onClick={() => handleDeleteSession(session.id)}
                  disabled={deletingSessionId === session.id}
                  aria-label={`Delete ${session.title}`}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
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
                  {message.role === "assistant" && message.sources.length > 0 ? (
                    <div className="mt-4 rounded-md border bg-card/70 p-3">
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase text-muted-foreground">Sources</p>
                        {message.confidence_score ? (
                          <span className="text-xs text-muted-foreground">Confidence {message.confidence_score}%</span>
                        ) : null}
                      </div>
                      <div className="space-y-2">
                        {message.sources.map((source, index) => (
                          <div key={`${source.url ?? source.title}-${index}`} className="text-xs leading-5">
                            <div className="flex flex-wrap items-center gap-2 text-muted-foreground">
                              <span>{source.source_name}</span>
                              {source.stock_symbol ? <span>{source.stock_symbol}</span> : null}
                              {source.published_at ? <span>{source.published_at}</span> : null}
                            </div>
                            {source.url ? (
                              <a
                                className="mt-1 inline-flex items-center gap-1 font-medium text-primary hover:underline"
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                {source.title}
                                <ExternalLink className="h-3 w-3" aria-hidden="true" />
                              </a>
                            ) : (
                              <p className="mt-1 font-medium">{source.title}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
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

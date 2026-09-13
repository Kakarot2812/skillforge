"use client";

import React, { useState, useMemo } from "react";
import {
  Plus,
  MessageSquare,
  Trash2,
  Loader2,
  Clock,
  X,
  AlertCircle,
} from "lucide-react";
import { ConversationItem } from "@/lib/types/chat";

export interface CareerAssistantHistoryProps {
  conversations: ConversationItem[];
  activeConversationId: string | null;
  loading: boolean;
  deletingId: string | null;
  error: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
  onRetryLoad?: () => void;
  onCloseMobileDrawer?: () => void;
}

interface GroupedConversations {
  today: ConversationItem[];
  yesterday: ConversationItem[];
  older: ConversationItem[];
}

export default function CareerAssistantHistory({
  conversations,
  activeConversationId,
  loading,
  deletingId,
  error,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onRetryLoad,
  onCloseMobileDrawer,
}: CareerAssistantHistoryProps) {
  // State for tracking which conversation is pending delete confirmation
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Categorize conversations into Today, Yesterday, Older
  const grouped = useMemo<GroupedConversations>(() => {
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const startOfYesterday = startOfToday - 24 * 60 * 60 * 1000;

    const result: GroupedConversations = {
      today: [],
      yesterday: [],
      older: [],
    };

    conversations.forEach((conv) => {
      const convTime = new Date(conv.updated_at || conv.created_at).getTime();
      if (convTime >= startOfToday) {
        result.today.push(conv);
      } else if (convTime >= startOfYesterday) {
        result.yesterday.push(conv);
      } else {
        result.older.push(conv);
      }
    });

    return result;
  }, [conversations]);

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setConfirmDeleteId(id);
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirmDeleteId(null);
  };

  const handleConfirmDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setConfirmDeleteId(null);
    onDeleteConversation(id);
  };

  const formatTimestamp = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });
    } catch {
      return "";
    }
  };

  const renderConversationGroup = (title: string, items: ConversationItem[]) => {
    if (items.length === 0) return null;

    return (
      <div key={title} className="space-y-1">
        <div className="px-2 py-1 text-[10px] font-semibold tracking-wider text-slate-600 dark:text-neutral-400 uppercase flex items-center gap-1">
          <Clock className="h-2.5 w-2.5" />
          <span>{title}</span>
        </div>
        {items.map((conv) => {
          const isActive = conv.id === activeConversationId;
          const isConfirming = confirmDeleteId === conv.id;
          const isDeleting = deletingId === conv.id;
          const displayTitle = conv.title?.trim() || "New Conversation";

          return (
            <div
              key={conv.id}
              onClick={() => {
                if (!isConfirming && !isDeleting) {
                  onSelectConversation(conv.id);
                  onCloseMobileDrawer?.();
                }
              }}
              className={`group relative flex items-center justify-between gap-2 px-3 py-2 rounded-xl text-xs transition-all cursor-pointer select-none ${
                isActive
                  ? "bg-purple-500/15 dark:bg-purple-500/20 text-purple-900 dark:text-purple-200 font-semibold border border-purple-500/30 shadow-xs"
                  : "text-slate-700 dark:text-neutral-300 hover:bg-slate-200/60 dark:hover:bg-neutral-800/60 hover:text-slate-900 dark:hover:text-white border border-transparent"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <MessageSquare
                  className={`h-3.5 w-3.5 shrink-0 ${
                    isActive
                      ? "text-purple-600 dark:text-purple-400"
                      : "text-slate-400 dark:text-neutral-500 group-hover:text-slate-600 dark:group-hover:text-neutral-300"
                  }`}
                />
                <span className="truncate flex-1 text-left" title={displayTitle}>
                  {displayTitle}
                </span>
              </div>

              {/* Timestamp or Actions */}
              <div className="shrink-0 flex items-center gap-1">
                {isDeleting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-rose-500" />
                ) : isConfirming ? (
                  <div className="flex items-center gap-1 bg-white dark:bg-neutral-900 px-1.5 py-0.5 rounded-lg border border-rose-500/40 shadow-sm z-10 animate-in fade-in zoom-in-95 duration-150">
                    <span className="text-[10px] text-rose-600 dark:text-rose-400 font-medium">
                      Delete?
                    </span>
                    <button
                      type="button"
                      onClick={(e) => handleConfirmDelete(e, conv.id)}
                      className="px-1.5 py-0.5 rounded bg-rose-600 hover:bg-rose-500 text-white text-[10px] font-bold transition-colors cursor-pointer"
                    >
                      Yes
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelDelete}
                      className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-neutral-800 text-slate-700 dark:text-neutral-300 hover:text-slate-900 dark:hover:text-white text-[10px] transition-colors cursor-pointer"
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="text-[10px] text-slate-500 dark:text-neutral-400 group-hover:hidden font-mono">
                      {formatTimestamp(conv.updated_at || conv.created_at)}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => handleDeleteClick(e, conv.id)}
                      title="Delete conversation"
                      aria-label={`Delete conversation ${displayTitle}`}
                      className="hidden group-hover:flex items-center justify-center p-1 rounded-md text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-50/70 dark:bg-neutral-950/60 border border-slate-200/80 dark:border-neutral-800/80 rounded-2xl p-3.5 space-y-3">
      {/* Top Header: New Chat Button & Close (Mobile) */}
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => {
            onNewChat();
            onCloseMobileDrawer?.();
          }}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 active:bg-purple-700 text-white text-xs font-bold transition-all shadow-sm cursor-pointer"
        >
          <Plus className="h-4 w-4" />
          <span>New Chat</span>
        </button>

        {onCloseMobileDrawer && (
          <button
            type="button"
            onClick={onCloseMobileDrawer}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-neutral-200 hover:bg-slate-200 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
            aria-label="Close history drawer"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Error Notice */}
      {error && (
        <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-[11px] flex items-center justify-between gap-1.5">
          <div className="flex items-center gap-1.5 truncate">
            <AlertCircle className="h-3 w-3 shrink-0" />
            <span className="truncate">{error}</span>
          </div>
          {onRetryLoad && (
            <button
              type="button"
              onClick={onRetryLoad}
              className="text-[10px] underline font-semibold cursor-pointer shrink-0"
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Conversation List Container */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-[160px] max-h-[380px] lg:max-h-[460px]">
        {loading && conversations.length === 0 ? (
          <div className="py-8 flex flex-col items-center justify-center gap-2 text-slate-500 dark:text-neutral-400 text-xs">
            <Loader2 className="h-4 w-4 animate-spin text-purple-500" />
            <span>Loading conversations...</span>
          </div>
        ) : conversations.length === 0 ? (
          <div className="py-8 text-center space-y-2 text-slate-600 dark:text-neutral-400">
            <MessageSquare className="h-6 w-6 mx-auto text-slate-400 dark:text-neutral-500 opacity-60" />
            <div className="text-xs font-semibold text-slate-700 dark:text-neutral-300">
              No conversations yet
            </div>
            <p className="text-[11px] text-slate-500 dark:text-neutral-400 max-w-[180px] mx-auto leading-relaxed">
              Start a new chat to ask career questions and save your discussion.
            </p>
          </div>
        ) : (
          <>
            {renderConversationGroup("Today", grouped.today)}
            {renderConversationGroup("Yesterday", grouped.yesterday)}
            {renderConversationGroup("Older", grouped.older)}
          </>
        )}
      </div>
    </div>
  );
}

/**
 * History & Favorites Store
 * Manages run history and favorites with localStorage persistence (client-only)
 */

'use client';

import { create } from 'zustand';

export interface RunHistoryItem {
  runId: string;
  prompt: string;
  language: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  halluckinationScore: number;
  verdict: 'accept' | 'warn' | 'repair' | 'reject' | null;
  createdAt: number;
  duration: number;
  generatedCode?: string;
}

interface HistoryStore {
  // History management
  history: RunHistoryItem[];
  addToHistory: (item: RunHistoryItem) => void;
  removeFromHistory: (runId: string) => void;
  clearHistory: () => void;
  getHistoryItem: (runId: string) => RunHistoryItem | undefined;

  // Favorites
  favorites: Set<string>;
  toggleFavorite: (runId: string) => void;
  isFavorite: (runId: string) => boolean;
  getFavorites: () => RunHistoryItem[];

  // Filtering
  filters: {
    language?: string;
    status?: string;
    verdict?: string;
    dateRange?: { from: number; to: number };
    riskLevel?: 'low' | 'medium' | 'high';
  };
  setFilters: (filters: HistoryStore['filters']) => void;
  clearFilters: () => void;

  // Computed
  getFilteredHistory: () => RunHistoryItem[];
}

export const useHistoryStore = create<HistoryStore>((set, get) => ({
  history: [],
  favorites: new Set(),
  filters: {},

  addToHistory: (item: RunHistoryItem) => {
    set((state) => ({
      history: [item, ...state.history].slice(0, 100), // Keep last 100 runs
    }));
    
    // Persist to localStorage if available
    if (typeof window !== 'undefined') {
      try {
        const state = get();
        localStorage.setItem(
          'dehalu-history',
          JSON.stringify(state.history)
        );
      } catch (e) {
        console.warn('Failed to persist history:', e);
      }
    }
  },

  removeFromHistory: (runId: string) => {
    set((state) => ({
      history: state.history.filter((h) => h.runId !== runId),
    }));
  },

  clearHistory: () => {
    set({ history: [] });
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('dehalu-history');
      } catch (e) {
        console.warn('Failed to clear history:', e);
      }
    }
  },

  getHistoryItem: (runId: string) => {
    return get().history.find((h) => h.runId === runId);
  },

  toggleFavorite: (runId: string) => {
    set((state) => {
      const newFavorites = new Set(state.favorites);
      if (newFavorites.has(runId)) {
        newFavorites.delete(runId);
      } else {
        newFavorites.add(runId);
      }
      return { favorites: newFavorites };
    });

    // Persist to localStorage if available
    if (typeof window !== 'undefined') {
      try {
        const state = get();
        localStorage.setItem(
          'dehalu-favorites',
          JSON.stringify(Array.from(state.favorites))
        );
      } catch (e) {
        console.warn('Failed to persist favorites:', e);
      }
    }
  },

  isFavorite: (runId: string) => {
    return get().favorites.has(runId);
  },

  getFavorites: () => {
    const state = get();
    return state.history.filter((h) => state.favorites.has(h.runId));
  },

  setFilters: (filters) => {
    set({ filters });
  },

  clearFilters: () => {
    set({ filters: {} });
  },

  getFilteredHistory: () => {
    const state = get();
    const { history, filters } = state;

    return history.filter((item) => {
      if (filters.language && item.language !== filters.language) return false;
      if (filters.status && item.status !== filters.status) return false;
      if (filters.verdict && item.verdict !== filters.verdict) return false;

      if (filters.dateRange) {
        if (item.createdAt < filters.dateRange.from || item.createdAt > filters.dateRange.to) {
          return false;
        }
      }

      if (filters.riskLevel) {
        const score = item.halluckinationScore;
        if (filters.riskLevel === 'low' && score > 0.3) return false;
        if (filters.riskLevel === 'medium' && (score < 0.3 || score > 0.7)) return false;
        if (filters.riskLevel === 'high' && score < 0.7) return false;
      }

      return true;
    });
  },
}));

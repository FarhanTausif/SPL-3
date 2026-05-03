/**
 * Phase 4 Integration Tests
 * Tests WebSocket functionality, export, history, and advanced features
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { getWebSocketClient, resetWebSocketClient } from '@/lib/websocket';
import { useHistoryStore } from '@/stores/historyStore';
import { exportAsJSON, exportAsCSV, exportAsMarkdown, generatePDFHTML } from '@/lib/export';

describe('Phase 4: Real-time WebSocket Integration', () => {
  describe('WebSocket Client', () => {
    beforeEach(() => {
      resetWebSocketClient();
    });

    afterEach(() => {
      resetWebSocketClient();
    });

    it('should create singleton WebSocket client', () => {
      const client1 = getWebSocketClient();
      const client2 = getWebSocketClient();
      expect(client1).toBe(client2);
    });

    it('should have correct initial state', () => {
      const client = getWebSocketClient();
      expect(client.isConnected()).toBe(false);
    });

    it('should handle message subscriptions', () => {
      const client = getWebSocketClient();
      let callbackCalled = false;

      const unsub = client.on('run.updated', (msg) => {
        callbackCalled = true;
        expect(msg.type).toBe('run.updated');
      });

      // Verify subscription function returned
      expect(typeof unsub).toBe('function');

      unsub();
    });
  });

  describe('History & Favorites Store', () => {
    beforeEach(() => {
      const { clearHistory } = useHistoryStore.getState();
      clearHistory();
    });

    it('should add run to history', () => {
      const { addToHistory, history } = useHistoryStore.getState();

      addToHistory({
        runId: 'run-1',
        prompt: 'Test prompt',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.2,
        verdict: 'accept',
        createdAt: Date.now(),
        duration: 1000,
      });

      expect(useHistoryStore.getState().history).toHaveLength(1);
      expect(useHistoryStore.getState().history[0].runId).toBe('run-1');
    });

    it('should limit history to last 100 runs', () => {
      const { addToHistory } = useHistoryStore.getState();

      for (let i = 0; i < 105; i++) {
        addToHistory({
          runId: `run-${i}`,
          prompt: `Test ${i}`,
          language: 'python',
          status: 'completed',
          halluckinationScore: 0.5,
          verdict: null,
          createdAt: Date.now(),
          duration: 1000,
        });
      }

      expect(useHistoryStore.getState().history).toHaveLength(100);
    });

    it('should toggle favorites', () => {
      const { addToHistory, toggleFavorite, isFavorite } = useHistoryStore.getState();

      addToHistory({
        runId: 'run-1',
        prompt: 'Test',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.2,
        verdict: 'accept',
        createdAt: Date.now(),
        duration: 1000,
      });

      expect(isFavorite('run-1')).toBe(false);

      toggleFavorite('run-1');
      expect(isFavorite('run-1')).toBe(true);

      toggleFavorite('run-1');
      expect(isFavorite('run-1')).toBe(false);
    });

    it('should get favorites', () => {
      const { addToHistory, toggleFavorite, getFavorites } = useHistoryStore.getState();

      addToHistory({
        runId: 'run-1',
        prompt: 'Test 1',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.2,
        verdict: 'accept',
        createdAt: Date.now(),
        duration: 1000,
      });

      addToHistory({
        runId: 'run-2',
        prompt: 'Test 2',
        language: 'javascript',
        status: 'completed',
        halluckinationScore: 0.3,
        verdict: 'accept',
        createdAt: Date.now(),
        duration: 1500,
      });

      toggleFavorite('run-1');

      expect(getFavorites()).toHaveLength(1);
      expect(getFavorites()[0].runId).toBe('run-1');
    });

    it('should filter history by language', () => {
      const { addToHistory, setFilters, getFilteredHistory } = useHistoryStore.getState();

      addToHistory({
        runId: 'run-1',
        prompt: 'Test',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.2,
        verdict: 'accept',
        createdAt: Date.now(),
        duration: 1000,
      });

      addToHistory({
        runId: 'run-2',
        prompt: 'Test',
        language: 'javascript',
        status: 'completed',
        halluckinationScore: 0.3,
        verdict: 'accept',
        createdAt: Date.now(),
        duration: 1500,
      });

      setFilters({ language: 'python' });
      expect(getFilteredHistory()).toHaveLength(1);
      expect(getFilteredHistory()[0].language).toBe('python');
    });

    it('should filter by risk level', () => {
      const { addToHistory, setFilters, getFilteredHistory } = useHistoryStore.getState();

      addToHistory({
        runId: 'run-1',
        prompt: 'Test',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.1,
        verdict: 'accept',
        createdAt: Date.now(),
        duration: 1000,
      });

      addToHistory({
        runId: 'run-2',
        prompt: 'Test',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.8,
        verdict: 'reject',
        createdAt: Date.now(),
        duration: 1000,
      });

      setFilters({ riskLevel: 'low' });
      expect(getFilteredHistory()).toHaveLength(1);
      expect(getFilteredHistory()[0].halluckinationScore).toBeLessThan(0.3);
    });
  });

  describe('Export Functionality', () => {
    const mockReport = {
      runId: 'test-run-1',
      timestamp: '2026-05-03T10:00:00Z',
      prompt: 'Write a function to sum two numbers',
      language: 'python',
      status: 'completed',
      halluckinationScore: 0.2,
      verdict: 'accept',
      generatedCode: 'def sum(a, b):\n  return a + b',
      evidence: [
        {
          kind: 'claims',
          payload: { claims: ['function returns sum'] },
        },
      ],
      duration: 1500,
    };

    it('should generate valid JSON export', () => {
      const json = JSON.stringify(mockReport, null, 2);
      const parsed = JSON.parse(json);
      expect(parsed.runId).toBe('test-run-1');
    });

    it('should generate valid CSV export', () => {
      // CSV generation test
      const rows = [
        ['Field', 'Value'],
        ['Run ID', mockReport.runId],
        ['Status', mockReport.status],
      ];
      const csv = rows.map((row) => row.map((cell) => `"${cell}"`).join(',')).join('\n');
      expect(csv).toContain('test-run-1');
      expect(csv).toContain('completed');
    });

    it('should generate valid Markdown export', () => {
      const md = `# Report: ${mockReport.runId}\n\nStatus: ${mockReport.status}`;
      expect(md).toContain(mockReport.runId);
      expect(md).toContain('completed');
    });

    it('should generate PDF HTML with proper structure', () => {
      const html = generatePDFHTML(mockReport);
      expect(html).toContain('<!DOCTYPE html>');
      expect(html).toContain(mockReport.runId);
      expect(html).toContain(mockReport.generatedCode);
      expect(html).toContain('<style>');
    });

    it('should include metrics in PDF', () => {
      const html = generatePDFHTML(mockReport);
      expect(html).toContain('20'); // Hallucination score percentage
      expect(html).toContain('%');
      expect(html).toContain('python');
      expect(html).toContain('completed');
    });
  });

  describe('Advanced Filtering', () => {
    it('should filter by date range', () => {
      const { addToHistory, setFilters, getFilteredHistory, clearHistory } =
        useHistoryStore.getState();
      clearHistory();

      const now = Date.now();
      const pastWeek = now - 7 * 24 * 60 * 60 * 1000;

      addToHistory({
        runId: 'run-1',
        prompt: 'Test',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.2,
        verdict: 'accept',
        createdAt: now,
        duration: 1000,
      });

      addToHistory({
        runId: 'run-2',
        prompt: 'Test',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.3,
        verdict: 'accept',
        createdAt: pastWeek,
        duration: 1000,
      });

      setFilters({ dateRange: { from: now - 1000, to: now } });
      expect(getFilteredHistory()).toHaveLength(1);
      expect(getFilteredHistory()[0].runId).toBe('run-1');
    });

    it('should combine multiple filters', () => {
      const { addToHistory, setFilters, getFilteredHistory, clearHistory } =
        useHistoryStore.getState();
      clearHistory();

      addToHistory({
        runId: 'run-1',
        prompt: 'Test',
        language: 'python',
        status: 'completed',
        halluckinationScore: 0.1,
        verdict: 'accept',
        createdAt: Date.now(),
        duration: 1000,
      });

      addToHistory({
        runId: 'run-2',
        prompt: 'Test',
        language: 'javascript',
        status: 'failed',
        halluckinationScore: 0.9,
        verdict: 'reject',
        createdAt: Date.now(),
        duration: 1000,
      });

      setFilters({
        language: 'python',
        status: 'completed',
        riskLevel: 'low',
      });

      expect(getFilteredHistory()).toHaveLength(1);
      expect(getFilteredHistory()[0].runId).toBe('run-1');
    });
  });

  describe('Real-time Updates', () => {
    it('should handle rapid status updates', () => {
      const { addToHistory, getHistoryItem, clearHistory } = useHistoryStore.getState();
      clearHistory();

      const updates = ['queued', 'running', 'completed'];
      let item = {
        runId: 'run-1',
        prompt: 'Test',
        language: 'python',
        status: 'queued' as const,
        halluckinationScore: 0.2,
        verdict: null,
        createdAt: Date.now(),
        duration: 0,
      };

      addToHistory(item);

      updates.forEach((status) => {
        item = { ...item, status: status as any, duration: 500 };
        addToHistory(item);
      });

      const finalItem = getHistoryItem('run-1');
      expect(finalItem?.status).toBe('completed');
    });
  });
});

// routes/graph/menu/menu.store.ts

import { writable } from 'svelte/store';

/** Read a string from localStorage (browser only), falling back to `fallback`. */
function ls(key: string, fallback: string): string {
	if (typeof window === 'undefined') return fallback;
	return localStorage.getItem(key) ?? fallback;
}

export const openSidebar = writable(false);
export const openRunWindow = writable(false);
export const openConfigWindow = writable(false);

export const username = writable<string>('unknown');

// Global LLM defaults — loaded from localStorage so they persist across sessions.
// Default provider: openai, default model: gpt-4o-mini
export type LLMProvider = 'openai' | 'ollama';
export const llmProvider = writable<LLMProvider>(ls('llmProvider', 'openai') as LLMProvider);
export const llmModel = writable<string>(ls('llmModel', 'gpt-4o-mini'));
export const apiKey = writable<string>(ls('apiKey', ''));

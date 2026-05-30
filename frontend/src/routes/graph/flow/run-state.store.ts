// run-state.store.ts
import { writable } from 'svelte/store';

// ── Node highlight ────────────────────────────────────────────────────────────
export const runningNodeIds = writable<Set<string>>(new Set<string>());

export function markNodeRunning(id: string) {
	runningNodeIds.update((s) => new Set(s).add(id));
}
export function markNodeDone(id: string) {
	runningNodeIds.update((s) => {
		const n = new Set(s);
		n.delete(id);
		return n;
	});
}
export function clearRunningNodes() {
	runningNodeIds.set(new Set<string>());
}

// ── Execution status ──────────────────────────────────────────────────────────
export type ExecStatus = 'idle' | 'running' | 'done' | 'error';
export const execStatus = writable<ExecStatus>('idle');

// Final result text shown in the result panel
export const execResult = writable<string>('');

// INPUT node request — set when the backend is waiting for user text
export interface InputRequest {
	nodeId: string;
	prompt: string;
}
export const inputRequest = writable<InputRequest | null>(null);

// Whether the result panel is open
export const resultPanelOpen = writable<boolean>(false);

// Per-node output collected during the last run (keyed by node ID)
export const nodeOutputs = writable<Record<string, string>>({});

// Which node's output modal is currently open (null = closed)
export const viewingNodeId = writable<string | null>(null);

export function resetExec() {
	clearRunningNodes();
	execStatus.set('idle');
	execResult.set('');
	inputRequest.set(null);
	resultPanelOpen.set(false);
	nodeOutputs.set({});
	viewingNodeId.set(null);
}

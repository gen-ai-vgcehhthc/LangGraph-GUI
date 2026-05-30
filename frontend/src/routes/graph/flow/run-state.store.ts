// run-state.store.ts
// Tracks which node IDs are currently executing so node-texture can highlight them.

import { writable } from 'svelte/store';

export const runningNodeIds = writable<Set<string>>(new Set<string>());

export function markNodeRunning(id: string) {
	runningNodeIds.update((s) => new Set(s).add(id));
}

export function markNodeDone(id: string) {
	runningNodeIds.update((s) => {
		const next = new Set(s);
		next.delete(id);
		return next;
	});
}

export function clearRunningNodes() {
	runningNodeIds.set(new Set<string>());
}

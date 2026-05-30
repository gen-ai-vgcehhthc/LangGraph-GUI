// run-workflow.ts — headless execution service
// Call runWorkflow() from anywhere; stores drive the UI.

import { get } from 'svelte/store';
import { username, llmModel, apiKey } from '../menu/menu.store';
import { graphs } from './graphs.store.svelte';
import { GraphsToJson } from '$lib/util/serialization';
import {
	markNodeRunning,
	markNodeDone,
	clearRunningNodes,
	execStatus,
	execResult,
	inputRequest,
	resultPanelOpen
} from './run-state.store';

const SERVER_URL = import.meta.env.VITE_BACKEND_URL;

// ── Marker patterns ───────────────────────────────────────────────────────────
const RE_NODE_START = /__NODE_START__(.+?)__/g;
const RE_NODE_END = /__NODE_END__(.+?)__/g;
const INPUT_PREFIX = '__INPUT_REQUEST__';
const RESULT_START = '__RESULT_START__';
const RESULT_END = '__RESULT_END__';

function stripMarkers(raw: string): string {
	return raw.replace(/__NODE_(START|END)__.+?__/g, '').replace(/__INPUT_(REQUEST|DONE)__.+?__/g, '');
}

function parseInputRequest(raw: string): { nodeId: string; prompt: string } | null {
	const idx = raw.indexOf(INPUT_PREFIX);
	if (idx === -1) return null;
	const after = raw.slice(idx + INPUT_PREFIX.length);
	// find matching closing __
	const end = after.indexOf('__');
	if (end === -1) return null;
	try {
		return JSON.parse(after.slice(0, end));
	} catch {
		return null;
	}
}

// ── Main function ─────────────────────────────────────────────────────────────
export async function runWorkflow(): Promise<void> {
	clearRunningNodes();
	execStatus.set('running');
	execResult.set('');
	inputRequest.set(null);
	resultPanelOpen.set(false);

	const user = get(username);

	try {
		// 1. Serialize & upload workflow
		const workflowArray = GraphsToJson(get(graphs));
		const blob = new Blob([JSON.stringify(workflowArray, null, 2)], {
			type: 'application/json'
		});
		const fd = new FormData();
		fd.append('files', new File([blob], 'workflow.json', { type: 'application/json' }));

		const uploadRes = await fetch(`${SERVER_URL}/upload/${encodeURIComponent(user)}`, {
			method: 'POST',
			body: fd
		});
		if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.statusText}`);

		// 2. Start run (SSE stream)
		const runRes = await fetch(`${SERVER_URL}/run/${encodeURIComponent(user)}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ username: user, llm_model: get(llmModel), api_key: get(apiKey) })
		});
		if (!runRes.ok || !runRes.body)
			throw new Error(`Run failed: ${runRes.statusText}`);

		// 3. Parse stream
		const reader = runRes.body.getReader();
		const decoder = new TextDecoder();
		let resultBuf = '';
		let collectingResult = false;

		while (true) {
			const { value, done } = await reader.read();
			if (done) break;
			if (!value) continue;

			const raw = decoder.decode(value, { stream: true });

			// Node highlight markers
			for (const m of raw.matchAll(new RegExp(RE_NODE_START.source, 'g'))) markNodeRunning(m[1]);
			for (const m of raw.matchAll(new RegExp(RE_NODE_END.source, 'g'))) markNodeDone(m[1]);

			// Input request
			const req = parseInputRequest(raw);
			if (req) inputRequest.set(req);

			// Result collection
			for (const line of raw.split('\n')) {
				if (line.includes(RESULT_START)) { collectingResult = true; continue; }
				if (line.includes(RESULT_END))   { collectingResult = false; continue; }
				if (collectingResult) resultBuf += line + '\n';
			}
		}

		execResult.set(resultBuf.trim() || '(workflow completed — no output captured)');
		execStatus.set('done');
		resultPanelOpen.set(true);
	} catch (err) {
		execResult.set(err instanceof Error ? err.message : String(err));
		execStatus.set('error');
		resultPanelOpen.set(true);
	} finally {
		clearRunningNodes();
		inputRequest.set(null);
	}
}

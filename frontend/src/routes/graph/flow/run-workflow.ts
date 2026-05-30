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
	resultPanelOpen,
	nodeOutputs
} from './run-state.store';

const SERVER_URL = import.meta.env.VITE_BACKEND_URL;

// ── SSE line cleaning ─────────────────────────────────────────────────────────
// ProcessHandler prefixes every stdout line with "STDOUT: ".
// main.py wraps each queue item as "data: <item>\n\n".
// So every content line arrives as:  "data: STDOUT: <actual content>"
function cleanLine(line: string): string {
	let s = line;
	if (s.startsWith('data: ')) s = s.slice(6);
	if (s.startsWith('STDOUT: ')) s = s.slice(8);
	return s;
}

// ── Marker strings ────────────────────────────────────────────────────────────
const RESULT_START = '__RESULT_START__';
const RESULT_END = '__RESULT_END__';
const INPUT_PREFIX = '__INPUT_REQUEST__';

function parseInputRequest(line: string) {
	const idx = line.indexOf(INPUT_PREFIX);
	if (idx === -1) return null;
	const after = line.slice(idx + INPUT_PREFIX.length);
	const end = after.indexOf('__');
	if (end === -1) return null;
	try {
		return JSON.parse(after.slice(0, end)) as { nodeId: string; prompt: string };
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
	nodeOutputs.set({});

	const user = get(username);

	try {
		// 1. Serialize & upload
		const workflowArray = GraphsToJson(get(graphs));
		const blob = new Blob([JSON.stringify(workflowArray, null, 2)], { type: 'application/json' });
		const fd = new FormData();
		fd.append('files', new File([blob], 'workflow.json', { type: 'application/json' }));

		const uploadRes = await fetch(`${SERVER_URL}/upload/${encodeURIComponent(user)}`, {
			method: 'POST',
			body: fd
		});
		if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.statusText}`);

		// 2. Start SSE run
		const runRes = await fetch(`${SERVER_URL}/run/${encodeURIComponent(user)}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ username: user, llm_model: get(llmModel), api_key: get(apiKey) })
		});
		if (!runRes.ok || !runRes.body) throw new Error(`Run failed: ${runRes.statusText}`);

		// 3. Stream + parse
		const reader = runRes.body.getReader();
		const decoder = new TextDecoder();

		let resultBuf = '';
		let collectingResult = false;

		// Per-node output tracking
		let activeNodeId: string | null = null;
		const nodeOutBuf: Record<string, string> = {};

		while (true) {
			const { value, done } = await reader.read();
			if (done) break;
			if (!value) continue;

			const raw = decoder.decode(value, { stream: true });

			// Process line by line after stripping the SSE + STDOUT prefix
			for (const rawLine of raw.split('\n')) {
				const line = cleanLine(rawLine);
				if (!line.trim()) continue; // skip empty

				// ── Node highlight markers ────────────────────────────────
				const startM = line.match(/__NODE_START__(.+?)__/);
				if (startM) {
					activeNodeId = startM[1];
					markNodeRunning(startM[1]);
					continue;
				}
				const endM = line.match(/__NODE_END__(.+?)__/);
				if (endM) {
					markNodeDone(endM[1]);
					activeNodeId = null;
					continue;
				}

				// ── Per-node output ───────────────────────────────────────
				if (activeNodeId) {
					nodeOutBuf[activeNodeId] = (nodeOutBuf[activeNodeId] ?? '') + line + '\n';
				}

				// ── Result collection ─────────────────────────────────────
				if (line.includes(RESULT_START)) { collectingResult = true; continue; }
				if (line.includes(RESULT_END))   { collectingResult = false; continue; }
				if (collectingResult) { resultBuf += line + '\n'; continue; }

				// ── INPUT node request ────────────────────────────────────
				const req = parseInputRequest(line);
				if (req) inputRequest.set(req);

				// ── Subprocess exit status ────────────────────────────────
				const statusM = line.match(/__STATUS__(\{.+\})__/);
				if (statusM) {
					try {
						const st = JSON.parse(statusM[1]) as { status: string; message: string };
						if (st.status === 'error' && !resultBuf.trim()) {
							resultBuf = `Process error: ${st.message}\n\nCheck the "View Output" button on individual nodes for details.`;
						}
					} catch { /* ignore */ }
				}
			}
		}

		nodeOutputs.set(nodeOutBuf);
		const finalResult = resultBuf.trim();
		execResult.set(finalResult || '(workflow completed — no output captured)');
		execStatus.set(finalResult ? 'done' : 'error');
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

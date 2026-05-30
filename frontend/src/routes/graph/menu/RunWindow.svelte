<!-- src/routes/graph/menu/RunWindow.svelte -->
<script lang="ts">
	import { openRunWindow, username, llmModel, apiKey } from './menu.store';
	import { get } from 'svelte/store';
	import { graphs } from '../flow/graphs.store.svelte';
	import type { ExportedGraph } from '../flow/graphs-algo.svelte';
	import { GraphsToJson } from '../flow/graphs-algo.svelte';
	import { markNodeRunning, markNodeDone, clearRunningNodes } from '../flow/run-state.store';

	const SERVER_URL = import.meta.env.VITE_BACKEND_URL;

	// Markers the backend embeds in its log stream
	const NODE_START_RE = /__NODE_START__(.+?)__/g;
	const NODE_END_RE = /__NODE_END__(.+?)__/g;

	let isRunning = $state(false);
	let responseMessage = $state('');

	function processChunk(chunk: string) {
		// Parse and strip node-start markers
		for (const m of chunk.matchAll(NODE_START_RE)) markNodeRunning(m[1]);
		for (const m of chunk.matchAll(NODE_END_RE)) markNodeDone(m[1]);
		// Remove the markers from the visible log
		return chunk.replace(/__NODE_(START|END)__.+?__/g, '');
	}

	async function handleRun() {
		isRunning = true;
		responseMessage = '';
		clearRunningNodes();

		try {
			const gm = get(graphs);
			const workflowJsonArray: ExportedGraph[] = GraphsToJson(gm);
			const jsonString = JSON.stringify(workflowJsonArray, null, 2);

			const blob = new Blob([jsonString], { type: 'application/json' });
			const workflowFile = new File([blob], 'workflow.json', { type: 'application/json' });
			const formData = new FormData();
			formData.append('files', workflowFile);

			const user = get(username);
			let res = await fetch(`${SERVER_URL}/upload/${encodeURIComponent(user)}`, {
				method: 'POST',
				body: formData
			});

			if (!res.ok) {
				let errMsg = res.statusText;
				try {
					const err = await res.json();
					errMsg = err.error || errMsg;
				} catch (err) {
					responseMessage = err instanceof Error ? err.message : `${err}`;
				}
				throw new Error(`Upload failed: ${errMsg}`);
			}

			const payload = {
				username: user,
				llm_model: get(llmModel),
				api_key: get(apiKey)
			};

			res = await fetch(`${SERVER_URL}/run/${encodeURIComponent(user)}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});

			if (!res.ok || !res.body) {
				const text = await res.text();
				throw new Error(`Run failed: ${text || res.statusText}`);
			}

			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let done = false;
			let buffer = '';

			while (!done) {
				const { value, done: doneReading } = await reader.read();
				done = doneReading;
				if (value) {
					const raw = decoder.decode(value, { stream: true });
					buffer += processChunk(raw);
					responseMessage = buffer;
				}
			}

			buffer += processChunk(decoder.decode());
			responseMessage = buffer;
		} catch (err) {
			responseMessage = err instanceof Error ? err.message : `${err}`;
		} finally {
			isRunning = false;
			clearRunningNodes();
		}
	}

	function handleLeave() {
		openRunWindow.set(false);
	}
</script>

{#if $openRunWindow}
	<div class="bg-opacity-50 fixed inset-0 z-11 flex items-center justify-center">
		<div class="flex h-4/5 w-4/5 flex-col rounded bg-white p-5 shadow-md">
			<h2 class="mb-4 text-lg font-bold">Run Script</h2>

			<div class="mb-4 flex justify-end">
				<button
					onclick={handleRun}
					disabled={isRunning}
					class={`mr-2 rounded px-4 py-2 font-bold text-white ${
						isRunning ? 'cursor-not-allowed bg-gray-400' : 'bg-blue-500 hover:bg-blue-700'
					}`}
				>
					Run
				</button>
				<button
					onclick={handleLeave}
					disabled={isRunning}
					class={`rounded px-4 py-2 font-bold text-white ${
						isRunning ? 'cursor-not-allowed bg-gray-400' : 'bg-orange-500 hover:bg-orange-700'
					}`}
				>
					Leave
				</button>
			</div>

			<div class="mt-4 flex-1 overflow-y-auto rounded bg-gray-100 p-2">
				<pre class="whitespace-pre-wrap text-black">{responseMessage}</pre>
			</div>
		</div>
	</div>
{/if}

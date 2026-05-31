<!-- src/routes/graph/menu/DraftWindow.svelte -->
<!-- Generates a workflow graph from a plain-text prompt via /draft endpoint. -->
<script lang="ts">
	import { get } from 'svelte/store';
	import { username, llmModel, apiKey } from './menu.store';
	import { JsonToGraphs } from '../flow/graphs-algo.svelte';
	import { graphs, serial_number, usingSubgraph } from '../flow/graphs.store.svelte';
	import { backendUrl } from '$lib/backend';

	let { open = $bindable(false) } = $props();

	const SERVER_URL = backendUrl();

	let prompt = $state('');
	let isGenerating = $state(false);
	let errorMsg = $state('');

	async function handleGenerate() {
		if (!prompt.trim()) return;
		isGenerating = true;
		errorMsg = '';

		try {
			const res = await fetch(`${SERVER_URL}/draft/${encodeURIComponent(get(username))}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					prompt: prompt.trim(),
					llm_model: get(llmModel),
					api_key: get(apiKey)
				})
			});

			if (!res.ok) {
				const err = await res.json().catch(() => ({ detail: res.statusText }));
				throw new Error(err.detail || res.statusText);
			}

			const workflowArray = await res.json();
			// JsonToGraphs returns { graphs: Record<string,FlowNode[]>, nextSerialId }
			// — set all three stores atomically so the canvas re-renders correctly.
			const { graphs: newGraphs, nextSerialId } = JsonToGraphs(workflowArray);
			graphs.set(newGraphs);
			serial_number.set(nextSerialId);
			usingSubgraph.set('root');
			open = false;
			prompt = '';
		} catch (err) {
			errorMsg = err instanceof Error ? err.message : String(err);
		} finally {
			isGenerating = false;
		}
	}

	function handleClose() {
		open = false;
		errorMsg = '';
	}
</script>

{#if open}
	<!-- backdrop -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
		role="dialog"
		aria-modal="true"
	>
		<div class="flex w-[520px] flex-col rounded-xl bg-white p-6 shadow-2xl">
			<!-- header -->
			<div class="mb-4 flex items-center justify-between">
				<h2 class="text-lg font-bold">✨ AI Draft Generator</h2>
				<button
					class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
					onclick={handleClose}
				>
					✕
				</button>
			</div>

			<p class="mb-3 text-sm text-gray-500">
				Describe what you want the workflow to do. The board will be cleared and replaced with the
				generated graph.
			</p>

			<textarea
				class="mb-3 h-36 w-full resize-none rounded border border-gray-300 p-3 text-sm focus:border-blue-400 focus:outline-none"
				placeholder="e.g. Search the web for news about AI, summarise the top 3 articles, then write a tweet thread."
				bind:value={prompt}
				disabled={isGenerating}
			></textarea>

			{#if errorMsg}
				<div class="mb-3 rounded bg-red-50 p-2 text-xs text-red-600">{errorMsg}</div>
			{/if}

			<div class="flex justify-end space-x-2">
				<button
					class="rounded bg-gray-200 px-4 py-2 text-sm font-medium hover:bg-gray-300 disabled:opacity-50"
					onclick={handleClose}
					disabled={isGenerating}
				>
					Cancel
				</button>
				<button
					class="flex items-center gap-2 rounded bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
					onclick={handleGenerate}
					disabled={isGenerating || !prompt.trim()}
				>
					{#if isGenerating}
						<span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
						Generating…
					{:else}
						✨ Generate
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

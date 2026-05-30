<!-- InputOverlay.svelte — blocks canvas when an INPUT node is waiting for user text -->
<script lang="ts">
	import { get } from 'svelte/store';
	import { inputRequest } from '../flow/run-state.store';
	import { username } from './menu.store';

	const SERVER_URL = import.meta.env.VITE_BACKEND_URL;

	let userText = $state('');
	let submitting = $state(false);
	let error = $state('');

	async function handleSubmit() {
		if (!userText.trim() || submitting) return;
		submitting = true;
		error = '';
		try {
			const res = await fetch(
				`${SERVER_URL}/input/${encodeURIComponent(get(username))}`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ text: userText.trim() })
				}
			);
			if (!res.ok) throw new Error(await res.text());
			inputRequest.set(null);
			userText = '';
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			submitting = false;
		}
	}
</script>

{#if $inputRequest}
	<!-- full-screen backdrop -->
	<div class="pointer-events-auto fixed inset-0 z-50 flex items-center justify-center bg-black/50">
		<div class="w-[480px] max-w-[95vw] rounded-xl bg-white p-6 shadow-2xl">
			<!-- Header -->
			<div class="mb-1 flex items-center gap-2">
				<span class="text-2xl">💬</span>
				<h2 class="text-lg font-bold text-gray-800">Input Required</h2>
			</div>
			<p class="mb-1 text-xs text-gray-400">
				Node <code class="rounded bg-gray-100 px-1">{$inputRequest.nodeId}</code> is waiting
			</p>

			<!-- Prompt from the INPUT node -->
			<div class="mb-4 rounded border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
				{$inputRequest.prompt}
			</div>

			<!-- User textarea -->
			<textarea
				class="mb-3 h-28 w-full resize-none rounded border border-gray-300 p-3 text-sm
				       focus:border-blue-400 focus:outline-none"
				placeholder="Type your response here…"
				bind:value={userText}
				disabled={submitting}
				onkeydown={(e) => {
					if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit();
				}}
			></textarea>

			{#if error}
				<div class="mb-2 rounded bg-red-50 p-2 text-xs text-red-600">{error}</div>
			{/if}

			<div class="flex items-center justify-between">
				<span class="text-xs text-gray-400">Ctrl+Enter to submit</span>
				<button
					class="flex items-center gap-2 rounded bg-blue-600 px-5 py-2 text-sm font-bold
					       text-white hover:bg-blue-700 disabled:opacity-50"
					onclick={handleSubmit}
					disabled={submitting || !userText.trim()}
				>
					{#if submitting}
						<span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
						Sending…
					{:else}
						Send ↵
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

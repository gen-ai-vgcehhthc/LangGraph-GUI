<!-- ResultPanel.svelte — right-side slide-in result panel -->
<script lang="ts">
	import { execResult, execStatus, resultPanelOpen, resetExec } from '../flow/run-state.store';
	import { parseResultEntries, unescapeText } from '$lib/util/resultParser';
	import type { ResultEntry } from '$lib/util/resultParser';

	let showRaw = $state(false);
	let entries = $derived(parseResultEntries($execResult));

	type ValKind = 'string' | 'array' | 'object' | 'primitive';
	function valKind(v: unknown): ValKind {
		if (typeof v === 'string') return 'string';
		if (Array.isArray(v)) return 'array';
		if (typeof v === 'object' && v !== null) return 'object';
		return 'primitive';
	}
</script>

{#if $resultPanelOpen}
	<!-- Backdrop -->
	<div
		class="pointer-events-auto fixed inset-0 z-40 bg-black/10"
		onclick={() => resultPanelOpen.set(false)}
		role="presentation"
	></div>

	<!-- Panel -->
	<div
		class="pointer-events-auto fixed right-0 top-0 z-50 flex h-full w-[520px] max-w-full
		       flex-col border-l border-gray-200 bg-white shadow-2xl"
	>
		<!-- Header -->
		<div
			class="flex shrink-0 items-center justify-between border-b border-gray-200 px-5 py-3"
			class:bg-green-50={$execStatus === 'done'}
			class:bg-red-50={$execStatus === 'error'}
		>
			<div class="flex items-center gap-2">
				{#if $execStatus === 'done'}
					<span>✓</span><h2 class="font-bold text-green-800">Workflow Result</h2>
				{:else}
					<span>✗</span><h2 class="font-bold text-red-800">Execution Error</h2>
				{/if}
			</div>
			<div class="flex items-center gap-2">
				<button
					class="rounded border px-2.5 py-1 text-xs font-medium transition-colors
					       {showRaw ? 'border-gray-400 bg-gray-700 text-white' : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-100'}"
					onclick={() => (showRaw = !showRaw)}
				>
					{showRaw ? '✦ Formatted' : '{ } View Raw'}
				</button>
				<button class="rounded border border-gray-300 px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-100" onclick={resetExec}>Clear</button>
				<button class="rounded p-1 text-gray-400 hover:bg-gray-100" onclick={() => resultPanelOpen.set(false)}>✕</button>
			</div>
		</div>

		<!-- Body -->
		<div class="flex-1 overflow-y-auto p-4">
			{#if showRaw}
				<pre class="whitespace-pre-wrap break-words rounded bg-gray-900 p-4 text-xs leading-relaxed text-green-300">{$execResult}</pre>
			{:else if entries.length === 0}
				<p class="italic text-gray-400">No output captured.</p>
			{:else}
				{#each entries as entry, i (i)}
					{#if entry.kind === 'json'}
						<div class="mb-4 overflow-hidden rounded-lg border border-slate-200 shadow-sm">
							<div class="border-b border-slate-200 bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-500">
								Node output
							</div>
							<div class="divide-y divide-slate-100">
								{#each Object.entries(entry.data) as [key, val]}
									<div class="flex text-sm">
										<div class="w-36 shrink-0 border-r border-slate-100 bg-slate-50 px-3 py-2 font-mono text-xs font-semibold text-slate-600 break-all">
											{key}
										</div>
										<div class="min-w-0 flex-1 px-3 py-2 text-gray-800">
											{#if valKind(val) === 'string'}
												<span class="whitespace-pre-wrap break-words">{unescapeText(val as string)}</span>
											{:else if valKind(val) === 'array'}
												<ul class="space-y-1">
													{#each (val as unknown[]) as item, j (j)}
														<li class="flex gap-1.5">
															<span class="mt-0.5 shrink-0 text-slate-400">•</span>
															<span class="whitespace-pre-wrap break-words">{typeof item === 'string' ? unescapeText(item) : JSON.stringify(item, null, 2)}</span>
														</li>
													{/each}
												</ul>
											{:else if valKind(val) === 'object'}
												<pre class="whitespace-pre-wrap break-words rounded bg-slate-50 p-2 text-xs text-slate-700">{JSON.stringify(val, null, 2)}</pre>
											{:else}
												<span class="font-mono text-blue-700">{String(val)}</span>
											{/if}
										</div>
									</div>
								{/each}
							</div>
						</div>
					{:else}
						<p class="mb-1.5 whitespace-pre-wrap break-words text-sm text-gray-600">{unescapeText(entry.content)}</p>
					{/if}
				{/each}
			{/if}
		</div>
	</div>
{/if}

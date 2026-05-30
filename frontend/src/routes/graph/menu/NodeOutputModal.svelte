<!-- NodeOutputModal.svelte — floating modal showing one node's execution output -->
<script lang="ts">
	import { nodeOutputs, viewingNodeId } from '../flow/run-state.store';

	let showRaw = $state(false);

	// ── Entry parsing (same logic as ResultPanel) ─────────────────────────────
	type JsonEntry = { kind: 'json'; data: Record<string, unknown> };
	type TextEntry = { kind: 'text'; content: string };
	type Entry = JsonEntry | TextEntry;

	function parseEntries(text: string): Entry[] {
		const out: Entry[] = [];
		for (const line of text.split('\n')) {
			const t = line.trim();
			if (!t) continue;
			if (t.startsWith('{') || t.startsWith('[')) {
				try {
					const d = JSON.parse(t);
					if (typeof d === 'object' && d !== null) {
						out.push({ kind: 'json', data: d as Record<string, unknown> });
						continue;
					}
				} catch { /* fall through */ }
			}
			out.push({ kind: 'text', content: t });
		}
		return out;
	}

	function unescape(s: string) {
		return s.replace(/\\n/g, '\n').replace(/\\t/g, '\t');
	}

	type ValKind = 'string' | 'array' | 'object' | 'primitive';
	function valKind(v: unknown): ValKind {
		if (typeof v === 'string') return 'string';
		if (Array.isArray(v)) return 'array';
		if (typeof v === 'object' && v !== null) return 'object';
		return 'primitive';
	}

	let rawText = $derived($viewingNodeId ? ($nodeOutputs[$viewingNodeId] ?? '') : '');
	let entries = $derived(parseEntries(rawText));

	function close() {
		viewingNodeId.set(null);
		showRaw = false;
	}
</script>

{#if $viewingNodeId !== null}
	<!-- Backdrop -->
	<div
		class="pointer-events-auto fixed inset-0 z-50 flex items-center justify-center bg-black/40"
		onclick={close}
		role="presentation"
	></div>

	<!-- Modal -->
	<div
		class="pointer-events-auto fixed left-1/2 top-1/2 z-50 flex max-h-[80vh] w-[560px] max-w-[95vw]
		       -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-xl bg-white shadow-2xl"
	>
		<!-- Header -->
		<div class="flex shrink-0 items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
			<div>
				<h2 class="font-bold text-gray-800">Node Output</h2>
				<p class="text-xs text-gray-400">
					<code class="rounded bg-gray-100 px-1">{$viewingNodeId}</code>
				</p>
			</div>
			<div class="flex items-center gap-2">
				<button
					class="rounded border px-2.5 py-1 text-xs font-medium transition-colors
					       {showRaw
						       ? 'border-gray-400 bg-gray-700 text-white'
						       : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-100'}"
					onclick={() => (showRaw = !showRaw)}
				>
					{showRaw ? '✦ Formatted' : '{ } View Raw'}
				</button>
				<button
					class="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
					onclick={close}
				>
					✕
				</button>
			</div>
		</div>

		<!-- Body -->
		<div class="flex-1 overflow-y-auto p-4">
			{#if !rawText}
				<p class="italic text-gray-400">No output recorded for this node.</p>
			{:else if showRaw}
				<pre class="whitespace-pre-wrap break-words rounded bg-gray-900 p-4 text-xs leading-relaxed text-green-300">{rawText}</pre>
			{:else}
				{#each entries as entry, i (i)}
					{#if entry.kind === 'json'}
						<div class="mb-3 overflow-hidden rounded-lg border border-slate-200 shadow-sm">
							<div class="border-b border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">
								JSON output
							</div>
							<div class="divide-y divide-slate-100">
								{#each Object.entries(entry.data) as [key, val]}
									<div class="flex text-sm">
										<div class="w-32 shrink-0 border-r border-slate-100 bg-slate-50 px-3 py-2 font-mono text-xs font-semibold text-slate-600">
											{key}
										</div>
										<div class="min-w-0 flex-1 px-3 py-2 text-gray-800">
											{#if valKind(val) === 'string'}
												<span class="whitespace-pre-wrap break-words">{unescape(val as string)}</span>
											{:else if valKind(val) === 'array'}
												<ul class="space-y-1">
													{#each (val as unknown[]) as item, j (j)}
														<li class="flex gap-1.5">
															<span class="mt-0.5 shrink-0 text-slate-400">•</span>
															<span class="whitespace-pre-wrap break-words">{typeof item === 'string' ? unescape(item) : JSON.stringify(item, null, 2)}</span>
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
						<p class="mb-1 whitespace-pre-wrap break-words text-sm text-gray-600">{entry.content}</p>
					{/if}
				{/each}
			{/if}
		</div>
	</div>
{/if}

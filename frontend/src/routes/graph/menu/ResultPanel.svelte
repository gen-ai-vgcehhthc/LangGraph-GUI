<!-- ResultPanel.svelte — right-side slide-in panel showing workflow result -->
<script lang="ts">
	import { execResult, execStatus, resultPanelOpen, resetExec } from '../flow/run-state.store';

	/** Try to pretty-print a line if it looks like JSON, else return it as-is. */
	function formatLine(line: string): { type: 'json' | 'text'; content: string } {
		const t = line.trim();
		if ((t.startsWith('{') || t.startsWith('[')) && (t.endsWith('}') || t.endsWith(']'))) {
			try {
				return { type: 'json', content: JSON.stringify(JSON.parse(t), null, 2) };
			} catch {
				/* fall through */
			}
		}
		return { type: 'text', content: line };
	}

	let lines = $derived(
		$execResult
			.split('\n')
			.filter((l) => l.trim().length > 0)
			.map(formatLine)
	);
</script>

{#if $resultPanelOpen}
	<!-- Backdrop (only on mobile / narrow) -->
	<div
		class="pointer-events-auto fixed inset-0 z-40 bg-black/10"
		onclick={() => resultPanelOpen.set(false)}
		role="presentation"
	></div>

	<!-- Panel -->
	<div
		class="pointer-events-auto fixed right-0 top-0 z-50 flex h-full w-[480px] max-w-full
		       flex-col border-l border-gray-200 bg-white shadow-2xl"
	>
		<!-- Header -->
		<div
			class="flex items-center justify-between border-b border-gray-200 px-5 py-4"
			class:bg-green-50={$execStatus === 'done'}
			class:bg-red-50={$execStatus === 'error'}
		>
			<div class="flex items-center gap-2">
				{#if $execStatus === 'done'}
					<span class="text-xl">✓</span>
					<h2 class="font-bold text-green-800">Workflow Result</h2>
				{:else}
					<span class="text-xl">✗</span>
					<h2 class="font-bold text-red-800">Execution Error</h2>
				{/if}
			</div>
			<div class="flex gap-2">
				<button
					class="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-100"
					onclick={resetExec}
				>
					Clear & Close
				</button>
				<button
					class="rounded p-1 text-gray-400 hover:bg-gray-100"
					onclick={() => resultPanelOpen.set(false)}
				>
					✕
				</button>
			</div>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-5 text-sm">
			{#if lines.length === 0}
				<p class="text-gray-400 italic">No output captured.</p>
			{:else}
				{#each lines as line, i (i)}
					{#if line.type === 'json'}
						<div class="mb-3 rounded border border-blue-100 bg-blue-50">
							<div class="border-b border-blue-100 px-3 py-1 text-xs font-semibold text-blue-500">
								JSON output
							</div>
							<pre class="overflow-x-auto whitespace-pre-wrap break-words p-3 text-xs text-blue-900">{line.content}</pre>
						</div>
					{:else}
						<p class="mb-1 text-gray-700">{line.content}</p>
					{/if}
				{/each}
			{/if}
		</div>
	</div>
{/if}

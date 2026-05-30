<!-- RunStatusBar.svelte — fixed bottom-of-canvas status bar, visible while running/done/error -->
<script lang="ts">
	import { execStatus, resultPanelOpen, resetExec } from '../flow/run-state.store';
</script>

{#if $execStatus !== 'idle'}
	<div
		class="pointer-events-auto fixed bottom-0 left-0 right-0 z-40 flex items-center justify-between
		       border-t px-6 py-2 text-sm shadow-lg transition-all duration-300
		       {$execStatus === 'running'
			       ? 'border-blue-300 bg-blue-50 text-blue-800'
			       : $execStatus === 'done'
				       ? 'border-green-300 bg-green-50 text-green-800'
				       : 'border-red-300 bg-red-50 text-red-800'}"
	>
		<!-- Left: status message -->
		<div class="flex items-center gap-2">
			{#if $execStatus === 'running'}
				<span class="inline-block h-3 w-3 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></span>
				<span class="font-medium">Running workflow…</span>
				<span class="text-xs text-blue-500">nodes are highlighted as they execute</span>
			{:else if $execStatus === 'done'}
				<span class="text-lg">✓</span>
				<span class="font-medium">Workflow complete</span>
			{:else}
				<span class="text-lg">✗</span>
				<span class="font-medium">Execution error</span>
			{/if}
		</div>

		<!-- Right: actions -->
		<div class="flex items-center gap-2">
			{#if $execStatus !== 'running'}
				<button
					class="rounded px-3 py-1 text-xs font-semibold
					       {$execStatus === 'done'
						       ? 'bg-green-600 text-white hover:bg-green-700'
						       : 'bg-red-600 text-white hover:bg-red-700'}"
					onclick={() => resultPanelOpen.set(true)}
				>
					View Result
				</button>
				<button
					class="rounded border border-gray-300 bg-white px-3 py-1 text-xs text-gray-600 hover:bg-gray-100"
					onclick={resetExec}
				>
					Dismiss
				</button>
			{/if}
		</div>
	</div>
{/if}

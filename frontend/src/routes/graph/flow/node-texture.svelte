<!-- routes/graph/flow/node-teature.svelte -->
<script lang="ts">
	import type { NodeProps } from '@xyflow/svelte';
	import { useSvelteFlow, NodeResizer } from '@xyflow/svelte';
	import NodeHandles from './node-handles.svelte';
	import { NodeType } from './node-schema';
	import { openCrewDesigner } from './graphs-algo.svelte';

	let { id, data, selected, width, height }: NodeProps = $props();
	const { updateNodeData } = useSvelteFlow();

	let localDescription = $state(data.description);

	// CrewAI config helpers
	let crewMaxTokens = $state(data.crew_config?.max_tokens ?? 4096);
	let crewMaxApiCalls = $state(data.crew_config?.max_api_calls ?? 10);
	let crewProcess = $state(data.crew_config?.process ?? 'sequential');

	function saveCrewConfig() {
		updateNodeData(id, {
			crew_config: {
				max_tokens: crewMaxTokens,
				max_api_calls: crewMaxApiCalls,
				process: crewProcess,
				crew_subgraph: `__crew__${id}`
			}
		});
	}
</script>

<div
	class="relative rounded-md border border-gray-300 bg-gray-200 p-2.5 text-center"
	style="width: {width}px; height: {height}px;"
>
	<NodeResizer minWidth={260} minHeight={280} isVisible={selected} color="rgb(255,64,0)" />

	<NodeHandles node_type={data.type} />

	<!-- NAME INPUT -->
	{#if data.type !== NodeType.START && data.type !== NodeType.TOOL}
		<div class="mt-2 flex items-center space-x-2">
			<label for="node-name-{id}" class="text-left text-sm text-gray-700"> Name: </label>
			<input
				id="node-name-{id}"
				type="text"
				class="w-full bg-white p-1 text-sm focus:outline-none"
				value={data.name}
				oninput={(e) => {
					const val = (e.currentTarget as HTMLInputElement).value;
					updateNodeData(id, { name: val });
				}}
			/>
		</div>
	{/if}

	<!-- TYPE DROPDOWN -->
	<div class="mt-2 flex items-center space-x-2">
		<label for="node-type-{id}" class="text-sm text-gray-700"> Type: </label>
		<select
			id="node-type-{id}"
			class="flex-1 bg-white p-1 text-sm focus:outline-none"
			value={data.type}
			onchange={(e) => {
				const newType = (e.currentTarget as HTMLSelectElement).value as NodeType;
				updateNodeData(id, { type: newType });
			}}
		>
			{#each Object.values(NodeType) as type (type)}
				<option value={type} selected={type === data.type}>
					{type}
				</option>
			{/each}
		</select>
	</div>

	<!-- TOOL INPUT -->
	{#if data.type === NodeType.STEP}
		<div class="mt-2 flex items-center space-x-2">
			<label for="tool-input-{id}" class="text-left text-sm text-gray-700">Tool: </label>

			<input
				id="tool-input-{id}"
				type="text"
				class="w-full cursor-text bg-white p-1 text-sm focus:outline-none"
				value={data.tool}
				oninput={(e) => {
					const val = (e.currentTarget as HTMLInputElement).value;
					updateNodeData(id, { tool: val });
				}}
			/>
		</div>
	{/if}

	<!-- CREWAI CONFIG -->
	{#if data.type === NodeType.CREWAI}
		<div class="mt-2 space-y-1 rounded border border-purple-300 bg-purple-50 p-2 text-left text-xs">
			<div class="font-semibold text-purple-700">CrewAI Settings</div>

			<div class="flex items-center space-x-2">
				<label class="w-28 shrink-0 text-gray-600">Max Tokens:</label>
				<input
					type="number"
					min="256"
					class="w-full bg-white p-1 focus:outline-none"
					bind:value={crewMaxTokens}
					onblur={saveCrewConfig}
				/>
			</div>

			<div class="flex items-center space-x-2">
				<label class="w-28 shrink-0 text-gray-600">Max API Calls:</label>
				<input
					type="number"
					min="1"
					class="w-full bg-white p-1 focus:outline-none"
					bind:value={crewMaxApiCalls}
					onblur={saveCrewConfig}
				/>
			</div>

			<div class="flex items-center space-x-2">
				<label class="w-28 shrink-0 text-gray-600">Process:</label>
				<select class="w-full bg-white p-1 focus:outline-none" bind:value={crewProcess} onchange={saveCrewConfig}>
					<option value="sequential">Sequential</option>
					<option value="hierarchical">Hierarchical</option>
				</select>
			</div>

			<button
				class="mt-1 w-full rounded bg-purple-600 py-1 text-xs font-semibold text-white hover:bg-purple-700"
				onclick={() => openCrewDesigner(id)}
			>
				Open Crew Designer
			</button>
		</div>
	{/if}

	<!-- AGENT CONFIG (used inside crew designer subgraphs) -->
	{#if data.type === NodeType.AGENT}
		<div class="mt-2 rounded border border-blue-300 bg-blue-50 p-1 text-left text-xs">
			<div class="font-semibold text-blue-700">Agent — describe as JSON:</div>
			<div class="text-gray-500">
				{"{"}"role":"...", "goal":"...", "backstory":"...", "tools":[]&#125;
			</div>
		</div>
	{/if}

	<!-- DESCRIPTION -->
	{#if data.type !== NodeType.START && data.type !== NodeType.SUBGRAPH && data.type !== NodeType.CREWAI}
		<div class="mt-2 flex h-[calc(100%-120px)] min-h-0 flex-grow flex-col">
			<label for="node-description-{id}" class="mb-1 block text-left text-sm text-gray-700">
				{data.type === NodeType.AGENT ? 'Agent JSON:' : 'Description:'}
			</label>

			<textarea
				id="node-description-{id}"
				class="h-full w-full flex-grow resize-none overflow-y-auto
               rounded border border-gray-300 bg-white p-1 text-sm
               focus:outline-none"
				bind:value={localDescription}
				onblur={() => updateNodeData(id, { description: localDescription })}
			></textarea>
		</div>
	{/if}

	<!-- CREWAI TASK DESCRIPTION -->
	{#if data.type === NodeType.CREWAI}
		<div class="mt-2 flex h-[calc(100%-260px)] min-h-0 flex-grow flex-col">
			<label for="node-description-{id}" class="mb-1 block text-left text-sm text-gray-700">
				Crew Task:
			</label>
			<textarea
				id="node-description-{id}"
				class="h-full w-full flex-grow resize-none overflow-y-auto
               rounded border border-gray-300 bg-white p-1 text-sm
               focus:outline-none"
				bind:value={localDescription}
				onblur={() => updateNodeData(id, { description: localDescription })}
			></textarea>
		</div>
	{/if}
</div>

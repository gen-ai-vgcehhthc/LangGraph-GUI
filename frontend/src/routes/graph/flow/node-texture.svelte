<!-- routes/graph/flow/node-texture.svelte -->
<script lang="ts">
	import type { NodeProps } from '@xyflow/svelte';
	import { useSvelteFlow, NodeResizer } from '@xyflow/svelte';
	import NodeHandles from './node-handles.svelte';
	import { NodeType } from './node-schema';
	import type { NodeLLMConfig } from './node-schema';
	import { openCrewDesigner } from './graphs-algo.svelte';
	import { llmProvider, llmModel, apiKey } from '../menu/menu.store';
	import { runningNodeIds, nodeOutputs, viewingNodeId } from './run-state.store';
	import { get } from 'svelte/store';
	import { untrack } from 'svelte';

	let { id, data, selected, width, height }: NodeProps = $props();
	const { updateNodeData } = useSvelteFlow();

	// ── description (local editable copy) ──────────────────────────────
	let localDescription = $state(untrack(() => data.description));

	// ── CrewAI config ───────────────────────────────────────────────────
	let crewMaxTokens = $state(untrack(() => data.crew_config?.max_tokens ?? 4096));
	let crewMaxApiCalls = $state(untrack(() => data.crew_config?.max_api_calls ?? 10));
	let crewProcess = $state(untrack(() => data.crew_config?.process ?? 'sequential'));

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

	// ── Per-node LLM config ─────────────────────────────────────────────
	type LLMMode = 'default' | 'openai' | 'ollama';

	function modeFromConfig(cfg: NodeLLMConfig | null): LLMMode {
		if (!cfg || cfg.use_default) return 'default';
		return cfg.provider === 'openai' ? 'openai' : 'ollama';
	}

	let llmMode = $state<LLMMode>(untrack(() => modeFromConfig(data.llm_config)));
	let nodeLLMModel = $state(untrack(() => data.llm_config?.model ?? ''));
	let nodeLLMKey = $state(untrack(() => data.llm_config?.api_key ?? ''));

	function saveLLMConfig() {
		if (llmMode === 'default') {
			updateNodeData(id, { llm_config: null });
			return;
		}
		const cfg: NodeLLMConfig = {
			use_default: false,
			provider: llmMode,
			model: nodeLLMModel || get(llmModel),
			api_key: nodeLLMKey || (llmMode === 'openai' ? get(apiKey) : '')
		};
		updateNodeData(id, { llm_config: cfg });
	}

	// Running state — true while this node is executing on the backend
	let isRunning = $derived($runningNodeIds.has(id));

	// Whether this node has recorded output from the last run
	let hasOutput = $derived(!!$nodeOutputs[id]);

	// hint showing global default in the dropdown
	let globalHint = $derived(
		`Default (${get(llmProvider) === 'openai' ? 'OpenAI' : 'Ollama'}: ${get(llmModel)})`
	);
</script>

<div
	class="relative flex flex-col overflow-hidden rounded-md border p-2.5 text-center transition-colors duration-300
		{isRunning
			? 'animate-pulse border-yellow-400 bg-yellow-100 shadow-lg shadow-yellow-300'
			: 'border-gray-300 bg-gray-200'}"
	style="width: {width}px; height: {height}px;"
>
	<NodeResizer minWidth={260} minHeight={320} isVisible={selected} color="rgb(255,64,0)" />

	<NodeHandles node_type={data.type} />

	<!-- NAME INPUT -->
	{#if data.type !== NodeType.START && data.type !== NodeType.TOOL}
		<div class="mt-2 flex shrink-0 items-center space-x-2">
			<label for="node-name-{id}" class="text-left text-sm text-gray-700">Name:</label>
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
	<div class="mt-2 flex shrink-0 items-center space-x-2">
		<label for="node-type-{id}" class="text-sm text-gray-700">Type:</label>
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
				<option value={type} selected={type === data.type}>{type}</option>
			{/each}
		</select>
	</div>

	<!-- TOOL INPUT (STEP only) -->
	{#if data.type === NodeType.STEP}
		<div class="mt-2 flex shrink-0 items-center space-x-2">
			<label for="tool-input-{id}" class="text-left text-sm text-gray-700">Tool:</label>
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

	<!-- INPUT NODE hint -->
	{#if data.type === NodeType.INPUT}
		<div class="mt-2 shrink-0 rounded border border-cyan-300 bg-cyan-50 p-2 text-left text-xs">
			<div class="font-semibold text-cyan-700">💬 User Input Node</div>
			<div class="text-gray-500">The description is shown to the user as a prompt at runtime.</div>
		</div>
	{/if}

	<!-- CREWAI CONFIG -->
	{#if data.type === NodeType.CREWAI}
		<div class="mt-2 shrink-0 space-y-1 rounded border border-purple-300 bg-purple-50 p-2 text-left text-xs">
			<div class="font-semibold text-purple-700">CrewAI Settings</div>
			<div class="flex items-center space-x-2">
				<label for="crew-tokens-{id}" class="w-28 shrink-0 text-gray-600">Max Tokens:</label>
				<input
					id="crew-tokens-{id}"
					type="number"
					min="256"
					class="w-full bg-white p-1 focus:outline-none"
					bind:value={crewMaxTokens}
					onblur={saveCrewConfig}
				/>
			</div>
			<div class="flex items-center space-x-2">
				<label for="crew-calls-{id}" class="w-28 shrink-0 text-gray-600">Max API Calls:</label>
				<input
					id="crew-calls-{id}"
					type="number"
					min="1"
					class="w-full bg-white p-1 focus:outline-none"
					bind:value={crewMaxApiCalls}
					onblur={saveCrewConfig}
				/>
			</div>
			<div class="flex items-center space-x-2">
				<label for="crew-process-{id}" class="w-28 shrink-0 text-gray-600">Process:</label>
				<select
					id="crew-process-{id}"
					class="w-full bg-white p-1 focus:outline-none"
					bind:value={crewProcess}
					onchange={saveCrewConfig}
				>
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

	<!-- TOOL node hint -->
	{#if data.type === NodeType.TOOL}
		<div class="mt-2 shrink-0 rounded border border-emerald-300 bg-emerald-50 p-2 text-left text-xs">
			<div class="font-semibold text-emerald-700">🔧 Tool Node — write Python here</div>
			<div class="mt-0.5 font-mono text-gray-500">def my_func(arg1, arg2):<br>&nbsp;&nbsp;&nbsp;&nbsp;"""docstring"""<br>&nbsp;&nbsp;&nbsp;&nbsp;return result</div>
			<div class="mt-1 text-gray-500">Set the function name in a STEP node's <span class="font-semibold">Tool</span> field.</div>
		</div>
	{/if}

	<!-- AGENT hint -->
	{#if data.type === NodeType.AGENT}
		<div class="mt-2 shrink-0 rounded border border-blue-300 bg-blue-50 p-1 text-left text-xs">
			<div class="font-semibold text-blue-700">Agent — paste JSON in description:</div>
			<div class="font-mono text-gray-500">{"{"}"role":"…","goal":"…","backstory":"…"&#125;</div>
		</div>
	{/if}

	<!-- DESCRIPTION (all except START, SUBGRAPH, CREWAI) -->
	{#if data.type !== NodeType.START && data.type !== NodeType.SUBGRAPH && data.type !== NodeType.CREWAI}
		<div class="mt-2 flex min-h-0 flex-1 flex-col">
			<label for="node-description-{id}" class="mb-1 block text-left text-sm text-gray-700">
				{data.type === NodeType.AGENT ? 'Agent JSON:' : data.type === NodeType.INPUT ? 'Prompt shown to user:' : data.type === NodeType.TOOL ? 'Python code:' : 'Description:'}
			</label>
			<textarea
				id="node-description-{id}"
				class="h-full w-full flex-grow resize-none overflow-y-auto rounded border border-gray-300 bg-white p-1 text-sm focus:outline-none
					{data.type === NodeType.TOOL ? 'font-mono text-xs leading-relaxed' : ''}"
				bind:value={localDescription}
				onblur={() => updateNodeData(id, { description: localDescription })}
			></textarea>
		</div>
	{/if}

	<!-- CREWAI task description -->
	{#if data.type === NodeType.CREWAI}
		<div class="mt-2 flex min-h-0 flex-1 flex-col">
			<label for="crew-desc-{id}" class="mb-1 block text-left text-sm text-gray-700">
				Crew Task:
			</label>
			<textarea
				id="crew-desc-{id}"
				class="h-full w-full flex-grow resize-none overflow-y-auto rounded border border-gray-300 bg-white p-1 text-sm focus:outline-none"
				bind:value={localDescription}
				onblur={() => updateNodeData(id, { description: localDescription })}
			></textarea>
		</div>
	{/if}

	<!-- PER-NODE LLM SELECTOR (all nodes that execute LLM — TOOL nodes run plain Python, no LLM) -->
	{#if data.type !== NodeType.START && data.type !== NodeType.INFO && data.type !== NodeType.SUBGRAPH && data.type !== NodeType.INPUT && data.type !== NodeType.TOOL}
		<div class="mt-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-1.5 text-xs">
			<div class="flex items-center space-x-1">
				<span class="shrink-0 font-medium text-gray-500">LLM:</span>
				<select
					class="flex-1 bg-transparent p-0.5 text-xs focus:outline-none"
					bind:value={llmMode}
					onchange={saveLLMConfig}
				>
					<option value="default">{globalHint}</option>
					<option value="openai">OpenAI (custom)</option>
					<option value="ollama">Ollama (local)</option>
				</select>
			</div>

			{#if llmMode !== 'default'}
				<div class="mt-1 flex items-center space-x-1">
					<span class="w-9 shrink-0 text-gray-400">Model</span>
					<input
						type="text"
						placeholder={llmMode === 'openai' ? 'gpt-4o-mini' : 'llama3'}
						class="w-full rounded border border-gray-200 bg-gray-50 p-0.5 text-xs focus:outline-none"
						bind:value={nodeLLMModel}
						onblur={saveLLMConfig}
					/>
				</div>
				{#if llmMode === 'openai'}
					<div class="mt-1 flex items-center space-x-1">
						<span class="w-9 shrink-0 text-gray-400">Key</span>
						<input
							type="password"
							placeholder="sk-… (blank = use global)"
							class="w-full rounded border border-gray-200 bg-gray-50 p-0.5 text-xs focus:outline-none"
							bind:value={nodeLLMKey}
							onblur={saveLLMConfig}
						/>
					</div>
				{/if}
			{/if}
		</div>
	{/if}

	<!-- "View" button — shown after a run when this node has recorded output -->
	{#if hasOutput}
		<button
			class="mt-1.5 w-full shrink-0 rounded border border-indigo-200 bg-indigo-50 py-1 text-xs
			       font-semibold text-indigo-700 hover:bg-indigo-100 active:bg-indigo-200"
			onclick={() => viewingNodeId.set(id)}
		>
			👁 View Output
		</button>
	{/if}
</div>

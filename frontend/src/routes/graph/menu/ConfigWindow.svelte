<!-- src/routes/graph/menu/ConfigWindow.svelte -->
<script lang="ts">
	import { get } from 'svelte/store';
	import { openConfigWindow, username, llmProvider, llmModel, apiKey } from './menu.store';
	import type { LLMProvider } from './menu.store';

	let providerValue = $state<LLMProvider>(get(llmProvider));
	let llmModelValue = $state(get(llmModel));
	let apiKeyValue = $state(get(apiKey));

	function handleSave() {
		llmProvider.set(providerValue);
		llmModel.set(llmModelValue);
		apiKey.set(apiKeyValue);
		localStorage.setItem('llmProvider', providerValue);
		localStorage.setItem('llmModel', llmModelValue);
		localStorage.setItem('apiKey', apiKeyValue);
		openConfigWindow.set(false);
	}

	function handleCancel() {
		openConfigWindow.set(false);
	}
</script>

{#if $openConfigWindow}
	<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center">
		<div class="w-96 rounded-lg bg-white p-6 shadow-lg">
			<h2 class="mb-4 text-xl font-semibold">Settings</h2>

			<!-- Username (read-only) -->
			<div class="mb-3">
				<label for="username" class="mb-1 block text-sm">Username:</label>
				<input
					type="text"
					id="username"
					bind:value={$username}
					readonly
					class="w-full cursor-not-allowed rounded border border-gray-300 bg-gray-100 p-2 text-gray-600"
				/>
			</div>

			<!-- Default LLM Provider -->
			<div class="mb-3">
				<label for="llmProvider" class="mb-1 block text-sm">Default LLM Provider:</label>
				<select
					id="llmProvider"
					bind:value={providerValue}
					class="w-full rounded border border-gray-300 p-2 focus:outline-none"
				>
					<option value="openai">OpenAI (API)</option>
					<option value="ollama">Ollama (Local)</option>
				</select>
			</div>

			<!-- Default LLM Model -->
			<div class="mb-3">
				<label for="llmModel" class="mb-1 block text-sm">Default Model:</label>
				<input
					type="text"
					id="llmModel"
					bind:value={llmModelValue}
					placeholder="e.g. gpt-4o-mini or llama3"
					class="w-full rounded border border-gray-300 p-2 focus:outline-none"
				/>
			</div>

			<!-- API Key (only relevant for online providers) -->
			{#if providerValue === 'openai'}
				<div class="mb-4">
					<label for="apiKey" class="mb-1 block text-sm">API Key:</label>
					<input
						type="password"
						id="apiKey"
						bind:value={apiKeyValue}
						placeholder="sk-..."
						class="w-full rounded border border-gray-300 p-2 focus:outline-none"
					/>
				</div>
			{/if}

			<!-- Actions -->
			<div class="flex justify-end space-x-2">
				<button
					onclick={handleSave}
					class="rounded bg-blue-500 px-4 py-2 font-bold text-white hover:bg-blue-700"
				>
					Save
				</button>
				<button
					onclick={handleCancel}
					class="rounded bg-gray-500 px-4 py-2 font-bold text-white hover:bg-gray-700"
				>
					Cancel
				</button>
			</div>
		</div>
	</div>
{/if}

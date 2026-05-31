// vite.config.ts

/// <reference types="vitest" />

import tailwindcss from '@tailwindcss/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig(() => {
	// Leave empty by default so the client derives the backend URL from the
	// page's own host at runtime (see src/lib/backend.ts). This is what makes
	// remote access work without hard-coding an IP. Set VITE_BACKEND_URL in the
	// environment only when you need to force a specific backend origin.
	const backendUrl = process.env.VITE_BACKEND_URL ?? '';

	return {
		plugins: [tailwindcss(), sveltekit()],
		optimizeDeps: {
			exclude: ['clsx', '@xyflow/system', 'classcat']
		},
		server: {
			host: '0.0.0.0',
			port: 3000,
			// Allow any Host header so the dev server is reachable via a remote
			// machine's IP or hostname, not just localhost.
			allowedHosts: true,
			// Proxy backend calls through this same origin so only port 3000
			// needs to be exposed remotely. Target defaults to the docker
			// service name; override with BACKEND_PROXY_TARGET for bare-metal.
			proxy: {
				'/backend': {
					target: process.env.BACKEND_PROXY_TARGET ?? 'http://backend:5000',
					changeOrigin: true,
					rewrite: (path) => path.replace(/^\/backend/, '')
				}
			},
		},
		define: {
			'import.meta.env.VITE_BACKEND_URL': JSON.stringify(backendUrl)
		},
		test: {
			workspace: [
				{
					extends: './vite.config.ts',
					plugins: [svelteTesting()],
					test: {
						name: 'client',
						environment: 'jsdom',
						clearMocks: true,
						include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
						exclude: ['src/lib/server/**'],
						setupFiles: ['./vitest-setup-client.ts']
					}
				},
				{
					extends: './vite.config.ts',
					test: {
						name: 'server',
						environment: 'node',
						include: ['src/**/*.{test,spec}.{js,ts}'],
						exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
					}
				}
			]
		}
	};
});

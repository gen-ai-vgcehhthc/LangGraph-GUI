// Resolves the backend base URL used by the client.
//
// Priority:
//   1. VITE_BACKEND_URL build-time override (set via env), when non-empty —
//      an absolute URL pointing straight at a backend origin.
//   2. The same-origin "/backend" path, which the dev server (see
//      server.proxy in vite.config.ts) or nginx proxies to the backend.
//
// Going through a same-origin path is what makes remote access reliable: only
// the frontend port (3000) needs to be reachable — no second open port, no
// CORS, and no HTTP/HTTPS mixed-content issues.
export function backendUrl(): string {
	const override = import.meta.env.VITE_BACKEND_URL;
	if (override) return override;

	return '/backend';
}

// Resolves the backend base URL at runtime.
//
// Priority:
//   1. VITE_BACKEND_URL build-time override (set via env), when non-empty.
//   2. The page's own host on the backend port — so the app works from
//      localhost, a LAN IP, or a remote server IP without rebuilding.
//
// Deriving from window.location is what makes remote access work: a browser
// loading the page from http://<remote-ip>:3000 will call
// http://<remote-ip>:5000, instead of a hard-coded localhost that would point
// back at the user's own machine.
import { browser } from '$app/environment';

const BACKEND_PORT = 5000;

export function backendUrl(): string {
	const override = import.meta.env.VITE_BACKEND_URL;
	if (override) return override;

	if (browser) {
		return `${window.location.protocol}//${window.location.hostname}:${BACKEND_PORT}`;
	}

	return `http://localhost:${BACKEND_PORT}`;
}

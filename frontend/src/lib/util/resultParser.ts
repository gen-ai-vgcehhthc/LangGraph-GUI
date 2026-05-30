// resultParser.ts — robust parser for workflow result strings
//
// The history string from the backend may arrive with:
//   • Actual newlines     (0x0A) — normal case
//   • Literal \n (2 chars) — when the SSE stream sends the history
//     as a single line with JSON-style escape sequences
//
// We use a character-by-character pass so:
//   1. Both newline forms are treated as entry separators
//   2. Literal \n INSIDE a JSON string is never treated as a separator
//      (bracket + string-state tracking)

export type JsonEntry = { kind: 'json'; data: Record<string, unknown> };
export type TextEntry = { kind: 'text'; content: string };
export type ResultEntry = JsonEntry | TextEntry;

/** Skip actual newlines and literal \\n sequences. */
function skipSep(s: string, pos: number): number {
	while (pos < s.length) {
		if (s[pos] === '\n' || s[pos] === '\r') { pos++; continue; }
		if (s[pos] === '\\' && s[pos + 1] === 'n') { pos += 2; continue; }
		break;
	}
	return pos;
}

/**
 * Read text until the next separator (actual or literal newline).
 * Returns [text, nextPos].
 */
function readText(s: string, start: number): [string, number] {
	let pos = start;
	while (pos < s.length) {
		if (s[pos] === '\n' || s[pos] === '\r') break;
		if (s[pos] === '\\' && s[pos + 1] === 'n') break;
		pos++;
	}
	return [s.slice(start, pos).trim(), pos];
}

/**
 * Read a complete JSON object/array starting at `pos` using bracket-depth
 * matching.  Returns [jsonString, nextPos] or null if the bracket can't be
 * closed before end-of-string.
 */
function readJson(s: string, start: number): [string, number] | null {
	const open = s[start];
	if (open !== '{' && open !== '[') return null;
	const close = open === '{' ? '}' : ']';

	let depth = 0;
	let inStr = false;
	let esc = false;

	for (let i = start; i < s.length; i++) {
		if (esc) { esc = false; continue; }
		const ch = s[i];
		if (ch === '\\') { esc = true; continue; }
		if (ch === '"') { inStr = !inStr; continue; }
		if (inStr) continue;
		if (ch === open) depth++;
		else if (ch === close) {
			depth--;
			if (depth === 0) return [s.slice(start, i + 1), i + 1];
		}
	}
	return null; // unclosed
}

/** Parse a raw result string into displayable entries. */
export function parseResultEntries(raw: string): ResultEntry[] {
	const entries: ResultEntry[] = [];
	let pos = 0;

	while (pos < raw.length) {
		pos = skipSep(raw, pos);
		if (pos >= raw.length) break;

		const ch = raw[pos];

		if (ch === '{' || ch === '[') {
			const result = readJson(raw, pos);
			if (result) {
				const [jsonStr, next] = result;
				try {
					const d = JSON.parse(jsonStr);
					if (d && typeof d === 'object') {
						entries.push({ kind: 'json', data: d as Record<string, unknown> });
						pos = next;
						continue;
					}
				} catch { /* fall through to text */ }
			}
		}

		// Plain text line
		const [text, next] = readText(raw, pos);
		if (text) entries.push({ kind: 'text', content: text });
		pos = next;
	}

	return entries;
}

/** Display helper: convert literal \\n sequences to real newlines. */
export function unescapeText(s: string): string {
	return s.replace(/\\n/g, '\n').replace(/\\t/g, '\t');
}

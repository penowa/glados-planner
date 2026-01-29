"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.apiGet = apiGet;
exports.apiPost = apiPost;
const API_BASE = 'http://127.0.0.1:8000';
async function apiGet(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok)
        throw new Error(res.statusText);
    return res.json();
}
async function apiPost(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined
    });
    if (!res.ok)
        throw new Error(res.statusText);
    return res.json();
}

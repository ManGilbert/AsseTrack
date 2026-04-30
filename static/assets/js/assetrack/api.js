import { clearSession, getAccessToken, getRefreshToken, saveSession } from "./auth-store.js";

const API_BASE = "/api";

function collectErrorMessages(value) {
    if (value == null) {
        return [];
    }

    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
        return [String(value)];
    }

    if (Array.isArray(value)) {
        return value.flatMap((item) => collectErrorMessages(item));
    }

    if (typeof value === "object") {
        return Object.entries(value).flatMap(([key, nestedValue]) => {
            const messages = collectErrorMessages(nestedValue);
            if (!messages.length) {
                return [];
            }
            return messages.map((message) => `${key}: ${message}`);
        });
    }

    return [];
}

function formatErrorPayload(payload, status) {
    if (typeof payload === "object" && payload !== null) {
        const detailMessages = collectErrorMessages(payload.detail);
        const payloadMessages = collectErrorMessages(payload);
        const messages = detailMessages.length ? detailMessages : payloadMessages;
        return messages.join(" ") || `Request failed with status ${status}.`;
    }

    return payload || `Request failed with status ${status}.`;
}

function buildHeaders({ authenticated = true, hasBody = false } = {}) {
    const headers = {};

    if (hasBody) {
        headers["Content-Type"] = "application/json";
    }

    if (authenticated) {
        const token = getAccessToken();
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
    }

    return headers;
}

async function parseResponse(response) {
    const type = response.headers.get("content-type") || "";
    const payload = type.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
        throw new Error(formatErrorPayload(payload, response.status));
    }

    return payload;
}

async function refreshAccessToken() {
    const refresh = getRefreshToken();
    if (!refresh) {
        throw new Error("Session expired. Please login again.");
    }

    const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
        method: "POST",
        headers: buildHeaders({ hasBody: true, authenticated: false }),
        body: JSON.stringify({ refresh }),
    });

    const payload = await parseResponse(response);
    saveSession({ access: payload.access, refresh: payload.refresh || refresh });
}

export async function apiRequest(path, options = {}) {
    const { method = "GET", body, authenticated = true, retry = true } = options;

    const send = () =>
        fetch(`${API_BASE}${path}`, {
            method,
            headers: buildHeaders({ authenticated, hasBody: body !== undefined }),
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });

    let response = await send();

    if (response.status === 401 && authenticated && retry) {
        try {
            await refreshAccessToken();
            response = await send();
        } catch (error) {
            clearSession();
            throw error;
        }
    }

    return parseResponse(response);
}

export async function fetchAllPages(path) {
    const initial = await apiRequest(path);
    if (!initial || !Array.isArray(initial.results)) {
        return initial;
    }

    const items = [...initial.results];
    let next = initial.next;

    while (next) {
        const url = new URL(next, window.location.origin);
        const relativePath = url.pathname.startsWith(API_BASE)
            ? url.pathname.slice(API_BASE.length)
            : url.pathname;
        const page = await apiRequest(`${relativePath}${url.search}`);
        items.push(...page.results);
        next = page.next;
    }

    return items;
}

export async function login(payload) {
    return apiRequest("/auth/login/", {
        method: "POST",
        body: payload,
        authenticated: false,
        retry: false,
    });
}

export async function logout() {
    const refresh = getRefreshToken();
    if (!refresh) {
        clearSession();
        return;
    }

    try {
        await apiRequest("/auth/logout/", {
            method: "POST",
            body: { refresh },
        });
    } finally {
        clearSession();
    }
}

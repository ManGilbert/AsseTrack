const ACCESS_KEY = "assetrack_access_token";
const REFRESH_KEY = "assetrack_refresh_token";
const USER_KEY = "assetrack_user";
const EXPIRES_AT_KEY = "assetrack_session_expires_at";

function decodeJwtPayload(token) {
    try {
        const [, payload] = token.split(".");
        const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
        return JSON.parse(atob(normalized));
    } catch {
        return null;
    }
}

export function saveSession({ access, refresh, user }) {
    if (access) {
        localStorage.setItem(ACCESS_KEY, access);
        const payload = decodeJwtPayload(access);
        if (payload?.exp) {
            localStorage.setItem(EXPIRES_AT_KEY, String(payload.exp * 1000));
        }
    }
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(EXPIRES_AT_KEY);
}

export function getAccessToken() {
    return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
    return localStorage.getItem(REFRESH_KEY);
}

export function getStoredUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
}

export function getSessionExpiresAt() {
    const raw = localStorage.getItem(EXPIRES_AT_KEY);
    return raw ? Number(raw) : null;
}

export function isSessionValid() {
    const token = getAccessToken();
    const expiresAt = getSessionExpiresAt();

    if (!token || !expiresAt) {
        return false;
    }

    return Date.now() < expiresAt;
}

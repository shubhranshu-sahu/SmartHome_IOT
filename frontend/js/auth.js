// ============================================
// auth.js — Shared authentication utility
//
// Loaded by home.html, index.html, stats.html.
// Provides: getAuthToken, setAuthToken, clearAuthToken,
//           verifyAuthToken, requireAuth, logoutAndRedirect
// ============================================

const _AUTH_KEY = 'iot_auth_token';

function getAuthToken()        { return sessionStorage.getItem(_AUTH_KEY); }
function setAuthToken(token)   { sessionStorage.setItem(_AUTH_KEY, token); }
function clearAuthToken()      { sessionStorage.removeItem(_AUTH_KEY); }

/**
 * Verify token with backend. Returns true if valid.
 * Silently returns false on network error (ESP32/backend offline).
 */
async function verifyAuthToken() {
    const token = getAuthToken();
    if (!token) return false;
    try {
        const r = await fetch(CONFIG.API_BASE + '/auth/verify', {
            headers: { 'X-Auth-Token': token }
        });
        return r.ok;
    } catch (e) {
        return false;
    }
}

/**
 * Call at the top of protected pages (index.html, stats.html).
 * Redirects to home.html if token missing or invalid.
 */
async function requireAuth() {
    const valid = await verifyAuthToken();
    if (!valid) {
        clearAuthToken();
        window.location.replace('home.html');
        // Throw so the rest of the page JS doesn't execute during redirect
        throw new Error('AUTH_REDIRECT');
    }
}

/**
 * Logout: invalidate server session, clear local token, redirect home.
 */
async function logoutAndRedirect() {
    const token = getAuthToken();
    if (token) {
        try {
            await fetch(CONFIG.API_BASE + '/auth/logout', {
                method:  'POST',
                headers: { 'X-Auth-Token': token }
            });
        } catch (e) { /* silent — session expires anyway on restart */ }
    }
    clearAuthToken();
    window.location.replace('home.html');
}

// Yamen Academy WebApp v7 - Unstuck
console.log("[app] === START v7 ===");

(function() {
    console.log("[app] IIFE started");

    const isTelegram = !!(window.Telegram && window.Telegram.WebApp);
    const tg = isTelegram ? window.Telegram.WebApp : null;
    if (tg) { try { tg.ready(); tg.expand(); } catch(e) {} }

    let currentUser = null, isAdmin = false;
    const API_BASE = CONFIG.API_BASE || window.location.origin;
    console.log("[app] API_BASE:", API_BASE);

    // === FORCE SHOW UI AFTER 5 SECONDS MAX ===
    let uiShown = false;
    const FORCE_TIMEOUT = 5000;

    function forceShowUI() {
        if (uiShown) return;
        uiShown = true;
        console.log("[app] FORCE showing UI (timeout or early)");
        var loadingEl = document.getElementById("loading");
        var appEl = document.getElementById("app");
        var adminEl = document.getElementById("adminApp");
        if (loadingEl) loadingEl.style.display = "none";
        if (isAdmin && adminEl) {
            adminEl.style.display = "block";
        } else if (appEl) {
            appEl.style.display = "block";
        }
        console.log("[app] UI forced visible");
    }

    // Start timeout immediately
    setTimeout(forceShowUI, FORCE_TIMEOUT);
    console.log("[app] Force timeout set for", FORCE_TIMEOUT, "ms");

    // === API helper ===
    async function api(path, opts = {}) {
        const url = path.startsWith("http") ? path : (API_BASE + path);
        console.log("[api] GET", url);
        try {
            const res = await fetch(url, {
                headers: { "Content-Type": "application/json", ...opts.headers },
                ...opts,
                signal: AbortSignal.timeout(4000)
            });
            console.log("[api]", url, "->", res.status);
            if (!res.ok) return { error: "HTTP " + res.status };
            return await res.json();
        } catch (e) {
            console.warn("[api] FAILED:", url, e.message);
            return { error: "offline", message: e.message };
        }
    }

    // === Main ===
    async function loadUserData() {
        console.log("[app] loadUserData started");

        var uid = null;

        if (isTelegram && tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            currentUser = tg.initDataUnsafe.user;
            uid = currentUser.id;
            isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
            console.log("[app] Telegram user:", uid, "admin:", isAdmin);
        }

        // SHOW UI FIRST
        forceShowUI();

        if (!uid) {
            console.log("[app] No user - public view shown");
            return;
        }

        // Background: try to fetch user data
        try {
            console.log("[app] Fetching user data for:", uid);
            var me = await api("/api/me?user_id=" + uid);
            console.log("[app] User data result:", me.error ? me.error : "ok");
            if (!me.error && me.full_name) {
                currentUser = currentUser || {};
                currentUser.full_name = me.full_name;
            }
        } catch (e) {
            console.log("[app] User fetch exception:", e.message);
        }

        // Update admin view if needed
        if (isAdmin && !uiShown) {
            var adminEl = document.getElementById("adminApp");
            if (adminEl) adminEl.style.display = "block";
            if (typeof initAdmin === "function") initAdmin();
        }

        console.log("[app] Ready! User:", uid, "Admin:", isAdmin);
    }

    // START
    console.log("[app] document.readyState:", document.readyState);
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadUserData);
    } else {
        loadUserData();
    }

    console.log("[app] IIFE completed");
})();

console.log("[app] === Script end ===");

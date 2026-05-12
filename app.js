// Yamen Academy WebApp v6 - Emergency Fix
console.log("[app] START - v6");
console.log("[app] isTelegram:", !!(window.Telegram && window.Telegram.WebApp));

(function() {
    console.log("[app] IIFE started");

    const isTelegram = !!(window.Telegram && window.Telegram.WebApp);
    const tg = isTelegram ? window.Telegram.WebApp : null;
    if (tg) { try { tg.ready(); tg.expand(); } catch(e) { console.log("[app] tg error:", e.message); } }

    let currentUser = null;
    let isAdmin = false;

    async function api(path, opts = {}) {
        console.log("[api] calling:", path);
        const url = path.startsWith("http") ? path : path;
        try {
            const res = await fetch(url, {
                headers: { "Content-Type": "application/json", ...opts.headers },
                ...opts
            });
            console.log("[api] response:", path, res.status);
            if (!res.ok) throw new Error("HTTP " + res.status);
            return await res.json();
        } catch (e) {
            console.warn("[api] FAILED:", path, e.message);
            return { error: "offline", message: e.message };
        }
    }

    function hideLoading() {
        console.log("[ui] hiding loading");
        var el = document.getElementById("loading");
        if (el) { el.style.display = "none"; console.log("[ui] loading hidden"); }
        else { console.log("[ui] loading element not found"); }
    }

    function showApp() {
        console.log("[ui] showing app");
        var el = document.getElementById("app");
        if (el) { el.style.display = "block"; console.log("[ui] app shown"); }
        else { console.log("[ui] app element not found"); }
    }

    function showAdmin() {
        console.log("[ui] showing admin");
        var el = document.getElementById("adminApp");
        if (el) { el.style.display = "block"; if (typeof initAdmin === "function") initAdmin(); }
    }

    async function loadUserData() {
        console.log("[app] loadUserData started");

        var uid = null;

        if (isTelegram && tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            currentUser = tg.initDataUnsafe.user;
            uid = currentUser.id;
            isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
            console.log("[app] Telegram user detected:", uid, "admin:", isAdmin);
        }

        // ALWAYS show UI first, then fetch data
        hideLoading();

        if (!uid) {
            console.log("[app] No user - showing public view");
            showApp();
            return;
        }

        // Show UI immediately, don't wait for API
        if (isAdmin) {
            showAdmin();
        } else {
            showApp();
            if (typeof showMainMenu === "function") {
                console.log("[app] calling showMainMenu");
                showMainMenu();
            }
        }

        // Fetch user data in background
        try {
            console.log("[app] fetching user data for:", uid);
            var me = await api("/api/me?user_id=" + uid);
            console.log("[app] user data:", me.error ? "error: " + me.error : "ok");
            if (!me.error && me.full_name) {
                currentUser = currentUser || {};
                currentUser.full_name = me.full_name;
            }
        } catch (e) {
            console.log("[app] user data fetch failed:", e.message);
        }

        console.log("[app] Ready. User:", uid, "Admin:", isAdmin);
    }

    // START IMMEDIATELY
    console.log("[app] document.readyState:", document.readyState);
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadUserData);
        console.log("[app] waiting for DOMContentLoaded");
    } else {
        console.log("[app] DOM already ready, starting now");
        loadUserData();
    }

    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js").catch(function(e) {
            console.log("[app] SW registration failed:", e.message);
        });
    }

    console.log("[app] IIFE completed");
})();

console.log("[app] Script end");

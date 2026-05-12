// Yamen Academy WebApp v4 - Final
(function() {
    const isTelegram = !!(window.Telegram && window.Telegram.WebApp);
    const tg = isTelegram ? window.Telegram.WebApp : null;
    if (tg) { try { tg.ready(); tg.expand(); } catch(e) {} }

    let currentUser = null;
    let isAdmin = false;
    const API_BASE = (window.CONFIG && CONFIG.API_BASE) || "";

    async function api(path, opts = {}) {
        const base = API_BASE ? API_BASE : window.location.origin;
        const url = base + (path.startsWith("/") ? path : "/" + path);
        try {
            const res = await fetch(url, {
                headers: { "Content-Type": "application/json", ...opts.headers },
                ...opts
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        } catch (e) {
            console.warn("API unavailable:", path, e.message);
            return { error: "offline", message: e.message };
        }
    }

    function hideLoading() {
        const el = document.getElementById("loading");
        if (el) el.style.display = "none";
    }

    function showApp() {
        const el = document.getElementById("app");
        if (el) el.style.display = "block";
    }

    function showAdmin() {
        const el = document.getElementById("adminApp");
        if (el) el.style.display = "block";
        if (typeof initAdmin === "function") initAdmin();
    }

    async function loadUserData() {
        let uid = null;

        // Telegram user
        if (isTelegram && tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            currentUser = tg.initDataUnsafe.user;
            uid = currentUser.id;
            isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
        }
        // Browser with user_id parameter
        else {
            const params = new URLSearchParams(window.location.search);
            const userIdParam = params.get("user_id");
            if (userIdParam) {
                uid = parseInt(userIdParam);
                currentUser = { id: uid, first_name: "User" };
                isAdmin = CONFIG.ADMIN_IDS.includes(uid);
            }
        }

        // No user - show public view immediately
        if (!uid) {
            hideLoading();
            showApp();
            console.log("Yamen Academy - public mode");
            return;
        }

        // Try loading user data from API
        try {
            const me = await api("/api/me?user_id=" + uid);
            if (!me.error && me.full_name) {
                currentUser = { ...currentUser, full_name: me.full_name, level: me.level };
            }
        } catch (e) {
            console.log("Could not fetch user data, continuing offline");
        }

        hideLoading();

        if (isAdmin) {
            showAdmin();
        } else {
            showApp();
            if (typeof showMainMenu === "function") showMainMenu();
        }

        console.log("Yamen Academy ready | User:", uid, "| Admin:", isAdmin);
    }

    // Start immediately - don't wait for DOMContentLoaded if DOM is already ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadUserData);
    } else {
        loadUserData();
    }

    // Service worker
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js").catch(function() {});
    }
})();

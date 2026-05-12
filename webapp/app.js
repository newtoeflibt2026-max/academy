// Yamen Academy WebApp v3 - Browser + Telegram
(function() {
    const isTelegram = !!(window.Telegram && window.Telegram.WebApp);
    const tg = isTelegram ? window.Telegram.WebApp : null;
    if (tg) { try { tg.ready(); tg.expand(); } catch(e) {} }

    let currentUser = null;
    let isAdmin = false;
    const API_BASE = (window.CONFIG && CONFIG.API_BASE) || "";

    async function api(path, opts = {}) {
        const url = API_BASE ? (API_BASE + path) : path;
        try {
            const res = await fetch(url, {
                headers: { "Content-Type": "application/json", ...opts.headers },
                ...opts
            });
            return await res.json();
        } catch (e) {
            console.warn("API offline:", path, e.message);
            return { error: "offline" };
        }
    }

    async function loadUserData() {
        let uid = null;

        if (isTelegram && tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            currentUser = tg.initDataUnsafe.user;
            uid = currentUser.id;
            isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
        } else {
            const params = new URLSearchParams(window.location.search);
            uid = params.get("user_id");
            if (uid) {
                uid = parseInt(uid);
                currentUser = { id: uid, first_name: "User" };
                isAdmin = CONFIG.ADMIN_IDS.includes(uid);
            }
        }

        // Hide loading
        const loadingEl = document.getElementById("loading");
        const appEl = document.getElementById("app");
        const adminEl = document.getElementById("adminApp");

        if (!uid) {
            if (loadingEl) loadingEl.style.display = "none";
            if (appEl) appEl.style.display = "block";
            console.log("Yamen Academy - public visitor mode");
            return;
        }

        // Try to fetch user data
        try {
            const me = await api("/api/me?user_id=" + uid);
            if (!me.error && me.full_name) {
                currentUser = { ...currentUser, full_name: me.full_name, level: me.level };
            }
        } catch (e) {}

        if (loadingEl) loadingEl.style.display = "none";

        if (isAdmin && adminEl) {
            adminEl.style.display = "block";
            if (typeof initAdmin === "function") initAdmin();
        } else if (appEl) {
            appEl.style.display = "block";
            if (typeof showMainMenu === "function") showMainMenu();
        }

        console.log("Yamen Academy ready | User:", uid, "| Admin:", isAdmin);
    }

    document.addEventListener("DOMContentLoaded", loadUserData);

    // Register service worker
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
})();

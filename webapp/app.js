// Yamen Academy WebApp - v2 (Telegram + Browser)
(function() {
    const isTelegram = !!(window.Telegram && window.Telegram.WebApp);
    const tg = isTelegram ? window.Telegram.WebApp : null;
    if (tg) { tg.ready(); tg.expand(); }

    let currentUser = null;
    let isAdmin = false;
    const API_BASE = CONFIG.API_BASE || "";

    async function api(path, opts = {}) {
        const url = (API_BASE + path).replace(/\/\//g, "/").replace(":/", "://");
        try {
            const res = await fetch(url, {
                headers: { "Content-Type": "application/json", ...opts.headers },
                ...opts
            });
            return await res.json();
        } catch (e) {
            console.warn("API offline:", path);
            return { error: "offline" };
        }
    }

    async function loadUserData() {
        let uid = null;
        if (isTelegram && tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            currentUser = tg.initDataUnsafe.user;
            isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
            uid = currentUser.id;
        } else {
            const params = new URLSearchParams(window.location.search);
            uid = params.get("user_id");
            if (uid) {
                currentUser = { id: parseInt(uid), first_name: "User" };
                isAdmin = CONFIG.ADMIN_IDS.includes(parseInt(uid));
            }
        }

        const loadingEl = document.getElementById("loading");
        const appEl = document.getElementById("app");
        const adminEl = document.getElementById("adminApp");

        if (!uid) {
            if (loadingEl) loadingEl.style.display = "none";
            if (appEl) appEl.style.display = "block";
            console.log("Yamen Academy - no user, showing public view");
            return;
        }

        try {
            const me = await api("/api/me?user_id=" + uid);
            if (!me.error) {
                currentUser = currentUser || { id: uid, first_name: me.full_name || "Student" };
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
        console.log("Yamen Academy ready | User:", currentUser?.id, "| Admin:", isAdmin);
    }

    document.addEventListener("DOMContentLoaded", loadUserData);
})();

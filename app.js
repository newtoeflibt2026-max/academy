// Yamen Academy WebApp v5 - Root Only
(function() {
    const isTelegram = !!(window.Telegram && window.Telegram.WebApp);
    const tg = isTelegram ? window.Telegram.WebApp : null;
    if (tg) { try { tg.ready(); tg.expand(); } catch(e) {} }

    let currentUser = null;
    let isAdmin = false;

    async function api(path, opts = {}) {
        const url = path.startsWith("http") ? path : path;
        try {
            const res = await fetch(url, {
                headers: { "Content-Type": "application/json", ...opts.headers },
                ...opts
            });
            if (!res.ok) throw new Error("HTTP " + res.status);
            return await res.json();
        } catch (e) {
            console.warn("API offline:", path);
            return { error: "offline" };
        }
    }

    function hideLoading() {
        var el = document.getElementById("loading");
        if (el) el.style.display = "none";
    }

    function showApp() {
        var el = document.getElementById("app");
        if (el) el.style.display = "block";
    }

    function showAdmin() {
        var el = document.getElementById("adminApp");
        if (el) el.style.display = "block";
        if (typeof initAdmin === "function") initAdmin();
    }

    async function loadUserData() {
        var uid = null;

        if (isTelegram && tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            currentUser = tg.initDataUnsafe.user;
            uid = currentUser.id;
            isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
        }

        if (!uid) {
            hideLoading();
            showApp();
            console.log("Yamen Academy - public view");
            return;
        }

        try {
            var me = await api("/api/me?user_id=" + uid);
            if (!me.error && me.full_name) {
                currentUser = currentUser || {};
                currentUser.full_name = me.full_name;
                currentUser.level = me.level;
            }
        } catch (e) {}

        hideLoading();

        if (isAdmin) {
            showAdmin();
        } else {
            showApp();
            if (typeof showMainMenu === "function") showMainMenu();
        }
        console.log("Yamen Academy ready | User:", uid);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadUserData);
    } else {
        loadUserData();
    }

    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js").catch(function() {});
    }
})();

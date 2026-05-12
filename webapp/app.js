// Yamen Academy WebApp
const isTelegram = !!(window.Telegram && window.Telegram.WebApp);
const tg = isTelegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); }

let currentUser = null;
let isAdmin = false;

const API_BASE = CONFIG.API_BASE || window.location.origin;

async function api(path, options = {}) {
    const url = path.startsWith("http") ? path : API_BASE + path;
    const res = await fetch(url, {
        headers: { "Content-Type": "application/json", ...options.headers },
        ...options
    });
    return res.json();
}

async function loadUserData() {
    // In browser mode, try to get user_id from URL
    const params = new URLSearchParams(window.location.search);
    const uid = currentUser ? currentUser.id : params.get("user_id");

    if (!uid) {
        document.getElementById("app").style.display = "block";
        document.getElementById("loading").style.display = "none";
        return;
    }

    try {
        const data = await api("/api/me?user_id=" + uid);
        if (!data.error) {
            currentUser = currentUser || { id: uid, first_name: data.full_name || "Student" };
            isAdmin = CONFIG.ADMIN_IDS.includes(parseInt(uid));
        }
    } catch (e) {
        console.log("API not available, running offline");
    }

    document.getElementById("loading").style.display = "none";

    if (isAdmin) {
        document.getElementById("adminApp").style.display = "block";
        if (typeof initAdmin === "function") initAdmin();
    } else {
        document.getElementById("app").style.display = "block";
        if (typeof showMainMenu === "function") showMainMenu();
    }
}

// ====== INIT ======
document.addEventListener("DOMContentLoaded", async () => {
    if (isTelegram) {
        const initData = tg.initDataUnsafe;
        if (initData && initData.user) {
            currentUser = initData.user;
            isAdmin = CONFIG.ADMIN_IDS.includes(currentUser.id);
        }
    }

    await loadUserData();
    console.log("Yamen Academy WebApp ready");
});

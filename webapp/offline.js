// Yamen Academy — Offline Manager
const OfflineDB = {
    db: null,

    async init() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open('yamen-offline', 1);
            req.onupgradeneeded = () => {
                const db = req.result;
                if (!db.objectStoreNames.contains('lessons')) {
                    db.createObjectStore('lessons', { keyPath: 'id' });
                }
                if (!db.objectStoreNames.contains('mediaCache')) {
                    db.createObjectStore('mediaCache', { keyPath: 'url' });
                }
                if (!db.objectStoreNames.contains('pendingQuizAnswers')) {
                    db.createObjectStore('pendingQuizAnswers', { keyPath: 'id', autoIncrement: true });
                }
            };
            req.onsuccess = () => { this.db = req.result; resolve(); };
            req.onerror = reject;
        });
    },

    async saveLesson(lesson) {
        const tx = this.db.transaction('lessons', 'readwrite');
        tx.objectStore('lessons').put(lesson);
        return tx.complete;
    },

    async getLesson(id) {
        const tx = this.db.transaction('lessons', 'readonly');
        return new Promise((rs, rj) => {
            const req = tx.objectStore('lessons').get(id);
            req.onsuccess = () => rs(req.result);
            req.onerror = rj;
        });
    },

    async getAllLessons() {
        const tx = this.db.transaction('lessons', 'readonly');
        return new Promise((rs, rj) => {
            const req = tx.objectStore('lessons').getAll();
            req.onsuccess = () => rs(req.result);
            req.onerror = rj;
        });
    },

    async cacheMedia(url, blob) {
        const tx = this.db.transaction('mediaCache', 'readwrite');
        tx.objectStore('mediaCache').put({ url, blob, timestamp: Date.now() });
        return tx.complete;
    },

    async getCachedMedia(url) {
        const tx = this.db.transaction('mediaCache', 'readonly');
        return new Promise((rs, rj) => {
            const req = tx.objectStore('mediaCache').get(url);
            req.onsuccess = () => {
                if (req.result) {
                    // Check cache age (7 days max)
                    if (Date.now() - req.result.timestamp < 7 * 24 * 3600 * 1000) {
                        rs(req.result.blob);
                    } else {
                        rs(null);
                    }
                } else {
                    rs(null);
                }
            };
            req.onerror = rj;
        });
    },

    async savePendingAnswer(answer) {
        const tx = this.db.transaction('pendingQuizAnswers', 'readwrite');
        tx.objectStore('pendingQuizAnswers').add(answer);
        return tx.complete;
    },

    async getPendingAnswers() {
        const tx = this.db.transaction('pendingQuizAnswers', 'readonly');
        return new Promise((rs, rj) => {
            const req = tx.objectStore('pendingQuizAnswers').getAll();
            req.onsuccess = () => rs(req.result);
            req.onerror = rj;
        });
    },

    async clearPendingAnswers() {
        const tx = this.db.transaction('pendingQuizAnswers', 'readwrite');
        tx.objectStore('pendingQuizAnswers').clear();
        return tx.complete;
    }
};

// Preload media when online
async function preloadLessonMedia(lesson) {
    const urls = [];
    if (lesson.image_file_id) urls.push(`https://api.telegram.org/file/bot${CONFIG.BOT_TOKEN}/${lesson.image_file_id}`);
    if (lesson.audio_file_id) urls.push(`https://api.telegram.org/file/bot${CONFIG.BOT_TOKEN}/${lesson.audio_file_id}`);
    if (lesson.video_file_id) urls.push(`https://api.telegram.org/file/bot${CONFIG.BOT_TOKEN}/${lesson.video_file_id}`);

    for (const url of urls) {
        const cached = await OfflineDB.getCachedMedia(url);
        if (!cached) {
            try {
                const response = await fetch(url);
                if (response.ok) {
                    const blob = await response.blob();
                    await OfflineDB.cacheMedia(url, blob);
                    console.log('Cached:', url);
                }
            } catch (e) {
                console.log('Cannot preload (offline?):', url);
            }
        }
    }
}

// Get media URL (from cache or network)
async function getMediaUrl(telegramFileId) {
    const url = `https://api.telegram.org/file/bot${CONFIG.BOT_TOKEN}/${telegramFileId}`;
    const cached = await OfflineDB.getCachedMedia(url);
    if (cached) return URL.createObjectURL(cached);
    return url;
}

// Check if online
function isOnline() {
    return navigator.onLine;
}

// Register connectivity listeners
window.addEventListener('online', () => {
    console.log('Back online! Syncing...');
    syncPendingAnswers();
});
window.addEventListener('offline', () => {
    console.log('Offline mode');
});

async function syncPendingAnswers() {
    if (!navigator.onLine) return;
    const pending = await OfflineDB.getPendingAnswers();
    for (const answer of pending) {
        try {
            await api('/quizzes/answer', 'POST', answer);
        } catch (e) {
            console.log('Sync failed:', e);
            return;
        }
    }
    await OfflineDB.clearPendingAnswers();
}

// Init on load
OfflineDB.init();

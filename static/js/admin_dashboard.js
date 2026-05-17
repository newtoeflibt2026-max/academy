/**
 * Yamen Academy — Admin Dashboard Controller
 * ===========================================
 * Pure vanilla JavaScript (no jQuery).
 * Binds admin HTML elements to /api/admin endpoints.
 *
 * Features:
 *   • Programmatic toast notification system
 *   • Real-time stats from /api/admin/stats
 *   • Payment‑status filter on card click
 *   • Toggle‑active button state switching
 *   • Extend‑subscription prompt with validation
 *   • AbortController timeouts for every fetch
 *
 * Location: static/js/admin_dashboard.js
 */

(function () {
    "use strict";

    // ─────────────────────────────────────────────
    // CONSTANTS
    // ─────────────────────────────────────────────
    var API_BASE      = "/api/admin";
    var TOAST_DURATION = 3500;         // ms
    var FETCH_TIMEOUT  = 10000;        // 10 s

    // ─────────────────────────────────────────────
    // 1. TOAST NOTIFICATION SYSTEM
    // ─────────────────────────────────────────────
    function showToast(message, type) {
        type = type || "info";

        var bgColor;
        if (type === "success")       bgColor = "#16a34a";  // green-600
        else if (type === "error")    bgColor = "#dc2626";  // red-600
        else if (type === "warning")  bgColor = "#d97706";  // amber-600
        else                          bgColor = "#2563eb";  // blue-600

        var container = document.createElement("div");
        container.textContent = message;

        // Inline styles — no external CSS needed
        var styles = {
            position: "fixed",
            bottom: "24px",
            right: "24px",
            maxWidth: "380px",
            padding: "14px 22px",
            backgroundColor: bgColor,
            color: "#ffffff",
            fontFamily: "'Segoe UI', Tahoma, sans-serif",
            fontSize: "14px",
            fontWeight: "500",
            lineHeight: "1.4",
            borderRadius: "10px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
            zIndex: "99999",
            opacity: "0",
            transform: "translateY(12px)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: "none",
            wordBreak: "break-word"
        };

        Object.keys(styles).forEach(function (key) {
            container.style[key] = styles[key];
        });

        document.body.appendChild(container);

        // Animate in
        requestAnimationFrame(function () {
            container.style.opacity = "1";
            container.style.transform = "translateY(0)";
        });

        // Animate out & remove
        setTimeout(function () {
            container.style.opacity = "0";
            container.style.transform = "translateY(12px)";
            setTimeout(function () {
                if (container.parentNode) {
                    container.parentNode.removeChild(container);
                }
            }, 300);
        }, TOAST_DURATION);
    }

    // ─────────────────────────────────────────────
    // 2. SAFE FETCH WRAPPER (with timeout & JSON)
    // ─────────────────────────────────────────────
    function apiFetch(url, options) {
        options = options || {};

        // Attach an AbortController timeout
        var controller;
        if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
            // Modern browsers (Baseline 2024)
            options.signal = AbortSignal.timeout(FETCH_TIMEOUT);
        } else {
            // Fallback for older browsers
            controller = new AbortController();
            options.signal = controller.signal;
            setTimeout(function () {
                controller.abort();
            }, FETCH_TIMEOUT);
        }

        return fetch(url, options)
            .then(function (response) {
                // Always parse JSON (even on error — the server sends JSON)
                return response.json().then(function (data) {
                    return { ok: response.ok, status: response.status, data: data };
                });
            })
            .catch(function (err) {
                // Network error, timeout, or abort
                var msg = "Network error";
                if (err.name === "TimeoutError" || err.name === "AbortError") {
                    msg = "Request timed out. Please check your connection.";
                } else if (err.message) {
                    msg = err.message;
                }
                showToast(msg, "error");
                return { ok: false, status: 0, data: { status: "error", message: msg } };
            });
    }

    // ─────────────────────────────────────────────
    // 3. REAL-TIME STATS SYNCHRONIZATION
    // ─────────────────────────────────────────────
    function refreshStats() {
        apiFetch(API_BASE + "/stats", { method: "GET" }).then(function (result) {
            if (!result.ok || !result.data || result.data.status !== "success") {
                // Silently fail — toast is handled by apiFetch on network error
                return;
            }

            var d = result.data.data;
            setTextContent("counter-total-students",  d.total_students);
            setTextContent("counter-pending-payments", d.pending_payments);
        });
    }

    function setTextContent(id, value) {
        var el = document.getElementById(id);
        if (el) {
            el.textContent = (value !== undefined && value !== null) ? value : "0";
        }
    }

    // ─────────────────────────────────────────────
    // 4. PAYMENT-STATUS FILTER (card click)
    // ─────────────────────────────────────────────
    function bindPaymentFilter() {
        var card = document.getElementById("card-pending-payments");
        if (!card) return;

        card.style.cursor = "pointer";
        card.addEventListener("click", function () {
            var rows = document.querySelectorAll(".student-row");
            var showingAll = card.getAttribute("data-filter-active") !== "true";

            rows.forEach(function (row) {
                var status = row.getAttribute("data-payment-status");
                if (showingAll && status !== "pending") {
                    row.style.display = "none";
                } else {
                    row.style.display = "";
                }
            });

            // Toggle state
            if (showingAll) {
                card.setAttribute("data-filter-active", "true");
                card.style.boxShadow = "0 0 0 3px #f59e0b";
                showToast("Showing only pending payments", "warning");
            } else {
                card.setAttribute("data-filter-active", "false");
                card.style.boxShadow = "";
                showToast("Showing all students", "success");
            }
        });
    }

    // ═════════════════════════════════════════════
    // 5. TOGGLE ACTIVE BUTTON
    // ═════════════════════════════════════════════
    function bindToggleButtons() {
        // Use event delegation — works even if rows are added dynamically
        document.addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-toggle-active");
            if (!btn) return;

            e.preventDefault();

            var studentId = btn.getAttribute("data-student-id");
            if (!studentId) return;

            // Disable button during request
            btn.disabled = true;
            btn.style.opacity = "0.6";

            apiFetch(API_BASE + "/student/toggle_active/" + studentId, {
                method: "POST"
            }).then(function (result) {
                btn.disabled = false;
                btn.style.opacity = "1";

                if (!result.ok || !result.data || result.data.status !== "success") {
                    showToast(
                        (result.data && result.data.message) || "Toggle failed",
                        "error"
                    );
                    return;
                }

                var isActive = result.data.is_active;

                // Swap styling instantly
                if (isActive) {
                    btn.textContent  = "❌ Deactivate Account";
                    btn.className    = btn.className.replace(/btn-success/gi, "").replace(/btn-danger/gi, "").trim();
                    btn.className   += " btn-danger";
                    btn.style.backgroundColor = "#dc2626";
                    btn.style.color            = "#ffffff";
                } else {
                    btn.textContent  = "✅ Activate Account";
                    btn.className    = btn.className.replace(/btn-danger/gi, "").replace(/btn-success/gi, "").trim();
                    btn.className   += " btn-success";
                    btn.style.backgroundColor = "#16a34a";
                    btn.style.color            = "#ffffff";
                }

                showToast(
                    "Student " + studentId + " " + (isActive ? "activated" : "deactivated"),
                    "success"
                );

                // Refresh stats counters
                refreshStats();
            });
        });
    }

    // ═════════════════════════════════════════════
    // 6. EXTEND SUBSCRIPTION BUTTON
    // ═════════════════════════════════════════════
    function bindExtendButtons() {
        document.addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-extend-sub");
            if (!btn) return;

            e.preventDefault();

            var studentId   = btn.getAttribute("data-student-id");
            var studentName = btn.getAttribute("data-student-name") || ("#" + studentId);

            if (!studentId) return;

            // Secure native prompt
            var input = window.prompt(
                "Enter number of days to extend for " + studentName + ":",
                "30"
            );

            // User clicked Cancel
            if (input === null) return;

            // Trim & validate
            input = input.trim();
            var days = Number(input);

            if (isNaN(days) || !Number.isInteger(days) || days <= 0) {
                showToast("Please enter a valid positive integer (e.g. 30)", "warning");
                return;
            }

            // Disable button
            btn.disabled = true;
            btn.style.opacity = "0.6";

            apiFetch(API_BASE + "/student/extend", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ student_id: Number(studentId), days: days })
            }).then(function (result) {
                btn.disabled = false;
                btn.style.opacity = "1";

                if (!result.ok || !result.data || result.data.status !== "success") {
                    showToast(
                        (result.data && result.data.message) || "Extension failed",
                        "error"
                    );
                    return;
                }

                showToast(
                    "Extended " + studentName + " by " + days + " day(s)",
                    "success"
                );

                refreshStats();
            });
        });
    }

    // ─────────────────────────────────────────────
    // 7. INITIALISATION
    // ─────────────────────────────────────────────
    function init() {
        // 1) Load stats immediately
        refreshStats();

        // 2) Bind payment-filter card
        bindPaymentFilter();

        // 3) Bind toggle-active buttons (event delegation)
        bindToggleButtons();

        // 4) Bind extend-subscription buttons (event delegation)
        bindExtendButtons();

        // 5) Auto-refresh stats every 45 seconds
        setInterval(refreshStats, 45000);

        console.log("[AdminDashboard] Initialised — v1.0");
    }

    // ── Run on DOM ready ─────────────────────────
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();

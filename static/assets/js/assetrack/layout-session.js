import { apiRequest, logout } from "./api.js";
import { clearSession, getStoredUser, isSessionValid, saveSession } from "./auth-store.js";

const roleHomeMap = {
    head_office_manager: "/head-office/",
    branch_manager: "/branch-manager/",
    employee: "/employee/",
};

function updateRoleNavigation() {
    const user = getStoredUser();
    const navByRole = {
        head_office_manager: document.getElementById("headOfficeNav"),
        branch_manager: document.getElementById("branchManagerNav"),
        employee: document.getElementById("employeeNav"),
    };

    Object.values(navByRole).forEach((node) => {
        if (node) {
            node.style.display = "none";
        }
    });

    if (user?.role && navByRole[user.role]) {
        navByRole[user.role].style.display = "block";
    }
}

function updateLayoutUser() {
    const user = getStoredUser();
    const nameNode = document.getElementById("layoutUserName");
    const emailNode = document.getElementById("layoutUserEmail");
    const roleNode = document.getElementById("layoutUserRole");
    const logoutLink = document.getElementById("layoutLogoutLink");
    const apiDocsNav = document.getElementById("apiDocsNav");

    if (!nameNode || !emailNode || !roleNode || !logoutLink) {
        return;
    }

    if (user) {
        nameNode.textContent = user.employee?.full_name || user.email;
        emailNode.textContent = user.email;
        roleNode.textContent = String(user.role || "user")
            .replaceAll("_", " ")
            .replace(/\b\w/g, (letter) => letter.toUpperCase());
        logoutLink.querySelector("span").textContent = "Logout";
        logoutLink.href = roleHomeMap[user.role] || "/";
        if (apiDocsNav) {
            apiDocsNav.style.display = user.role === "head_office_manager" ? "block" : "none";
        }
    } else {
        nameNode.textContent = "Guest User";
        emailNode.textContent = "guest@example.com";
        roleNode.textContent = "Not Signed In";
        logoutLink.querySelector("span").textContent = "Login";
        logoutLink.href = "/login/";
        if (apiDocsNav) {
            apiDocsNav.style.display = "none";
        }
    }
    updateRoleNavigation();
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function formatDateTime(value) {
    if (!value) return "N/A";
    return new Intl.DateTimeFormat("en-RW", {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(value));
}

async function updateNotificationsPanel() {
    const badge = document.getElementById("layoutNotificationBadge");
    const list = document.getElementById("layoutNotificationList");

    if (!badge || !list || !isSessionValid()) {
        return;
    }

    try {
        const [notifications, unread] = await Promise.all([
            apiRequest("/notifications/"),
            apiRequest("/notifications/unread_count/"),
        ]);
        const items = Array.isArray(notifications.results) ? notifications.results : notifications;
        const unreadCount = unread.unread_count || 0;

        badge.textContent = unreadCount;
        badge.classList.toggle("d-none", unreadCount === 0);

        list.innerHTML = items.length
            ? items.slice(0, 5).map((item) => `
                <div class="notifications-item">
                    <div class="notifications-desc w-100">
                        <a href="javascript:void(0);" class="font-body text-truncate-2-line">
                            <span class="fw-semibold text-dark">${escapeHtml(item.title)}</span>
                            ${escapeHtml(item.message)}
                        </a>
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="notifications-date text-muted border-bottom border-bottom-dashed">${formatDateTime(item.created_at)}</div>
                            <span class="wd-8 ht-8 rounded-circle ${item.is_read ? "bg-gray-300" : "bg-primary"}"></span>
                        </div>
                    </div>
                </div>
            `).join("")
            : `
                <div class="notifications-item">
                    <div class="notifications-desc">
                        <span class="font-body text-muted">No notifications yet.</span>
                    </div>
                </div>
            `;
    } catch (error) {
        list.innerHTML = `
            <div class="notifications-item">
                <div class="notifications-desc">
                    <span class="font-body text-muted">Unable to load notifications.</span>
                </div>
            </div>
        `;
    }
}

async function syncLayoutUserFromApi() {
    if (!isSessionValid()) {
        clearSession();
        updateLayoutUser();
        return null;
    }

    try {
        const user = await apiRequest("/auth/me/");
        saveSession({ user });
        updateLayoutUser();
        return user;
    } catch (error) {
        clearSession();
        updateLayoutUser();
        return null;
    }
}

function enforceProtectedPageAccess() {
    const body = document.body;
    const authRequired = body.dataset.authRequired === "true";
    const allowedRole = body.dataset.allowedRole;
    const user = getStoredUser();

    if (!authRequired) {
        return;
    }

    if (!isSessionValid() || !user) {
        clearSession();
        updateLayoutUser();
        window.location.href = "/login/";
        return;
    }

    if (allowedRole && user.role !== allowedRole) {
        clearSession();
        updateLayoutUser();
        window.location.href = "/login/";
    }
}

async function handleLogout(event) {
    const logoutLink = event.target.closest("#layoutLogoutLink");
    if (!logoutLink) {
        return;
    }

    const user = getStoredUser();
    if (!user) {
        return;
    }

    event.preventDefault();
    await logout();
    updateLayoutUser();
    window.location.href = "/login/";
}

async function handleMarkNotificationsRead(event) {
    const link = event.target.closest("#layoutMarkNotificationsRead");
    if (!link) {
        return;
    }

    event.preventDefault();
    if (!isSessionValid()) {
        return;
    }
    await apiRequest("/notifications/mark_all_as_read/", { method: "POST", body: {} });
    await updateNotificationsPanel();
}

document.addEventListener("click", handleLogout);
document.addEventListener("click", handleMarkNotificationsRead);
enforceProtectedPageAccess();
updateLayoutUser();
syncLayoutUserFromApi();
updateNotificationsPanel();

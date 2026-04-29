import { apiRequest, logout } from "./api.js";
import { clearSession, getStoredUser, isSessionValid, saveSession } from "./auth-store.js";

const roleHomeMap = {
    head_office_manager: "/head-office/",
    branch_manager: "/",
    employee: "/",
};

function updateLayoutUser() {
    const user = getStoredUser();
    const nameNode = document.getElementById("layoutUserName");
    const emailNode = document.getElementById("layoutUserEmail");
    const roleNode = document.getElementById("layoutUserRole");
    const logoutLink = document.getElementById("layoutLogoutLink");

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
    } else {
        nameNode.textContent = "Guest User";
        emailNode.textContent = "guest@example.com";
        roleNode.textContent = "Not Signed In";
        logoutLink.querySelector("span").textContent = "Login";
        logoutLink.href = "/login/";
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

document.addEventListener("click", handleLogout);
enforceProtectedPageAccess();
updateLayoutUser();
syncLayoutUserFromApi();

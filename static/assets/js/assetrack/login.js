import { login } from "./api.js";
import { clearSession, getStoredUser, isSessionValid, saveSession } from "./auth-store.js";

const form = document.getElementById("headOfficeLoginForm");
const feedback = document.getElementById("loginFeedback");
const submitButton = document.getElementById("loginSubmitButton");
const roleSelect = document.getElementById("loginRoleSelect");

const roleRedirects = {
    head_office_manager: "/head-office/",
    branch_manager: "/",
    employee: "/",
};

if (window.location.search) {
    window.history.replaceState({}, document.title, window.location.pathname);
}

function showFeedback(message, kind) {
    feedback.textContent = message;
    feedback.className = `alert alert-${kind}`;
    feedback.classList.remove("d-none");
}

function hideFeedback() {
    feedback.classList.add("d-none");
}

async function tryRestoreSession() {
    const user = getStoredUser();

    if (!isSessionValid()) {
        clearSession();
        return;
    }

    if (user?.role) {
        window.location.href = roleRedirects[user.role] || "/";
    }
}

function syncRoleSelection() {
    const selectedRole = roleSelect.value;
    if (selectedRole === "head_office_manager") {
        submitButton.textContent = "Login to Console";
    } else {
        submitButton.textContent = "Login";
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideFeedback();
    submitButton.disabled = true;

    const formData = new FormData(form);
    const payload = {
        email: formData.get("email"),
        password: formData.get("password"),
        role: formData.get("role"),
    };

    try {
        const session = await login(payload);
        saveSession(session);
        const redirectUrl = roleRedirects[session.user.role] || "/";
        const destinationLabel = session.user.role === "head_office_manager" ? "console" : "dashboard";
        showFeedback(`Login successful. Redirecting to ${destinationLabel}...`, "success");
        window.setTimeout(() => {
            window.location.href = redirectUrl;
        }, 450);
    } catch (error) {
        showFeedback(
            error.message || "Incorrect email, password, or role. Please try again.",
            "danger",
        );
    } finally {
        submitButton.disabled = false;
    }
});

roleSelect.addEventListener("change", syncRoleSelection);

syncRoleSelection();
tryRestoreSession();

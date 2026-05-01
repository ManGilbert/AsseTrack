import { apiRequest } from "./api.js";

function displayMessage(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = message;
    element.classList.toggle("d-none", !message);
    element.classList.toggle("alert-danger", isError);
    element.classList.toggle("alert-success", !isError);
}

async function loadAccountDetails() {
    try {
        const user = await apiRequest("/auth/me/");
        const emailField = document.getElementById("accountEmail");
        if (emailField) {
            emailField.value = user.email || "";
        }
    } catch (error) {
        displayMessage("accountEmailError", error.message || String(error), true);
    }
}

async function handleEmailSubmit(event) {
    event.preventDefault();
    displayMessage("accountEmailSuccess", "", false);
    displayMessage("accountEmailError", "", false);

    const email = document.getElementById("accountEmail").value.trim();

    try {
        await apiRequest("/auth/me/", {
            method: "PATCH",
            body: { email },
        });
        displayMessage("accountEmailSuccess", "Email updated successfully.");
    } catch (error) {
        displayMessage("accountEmailError", error.message || String(error), true);
        console.error(error);
    }
}

async function handlePasswordSubmit(event) {
    event.preventDefault();
    displayMessage("accountPasswordSuccess", "", false);
    displayMessage("accountPasswordError", "", false);

    const currentPassword = document.getElementById("currentPassword").value;
    const newPassword = document.getElementById("newPassword").value;

    if (!currentPassword || !newPassword) {
        displayMessage("accountPasswordError", "Both current password and new password are required.", true);
        return;
    }

    try {
        await apiRequest("/auth/me/", {
            method: "PATCH",
            body: {
                current_password: currentPassword,
                password: newPassword,
            },
        });
        displayMessage("accountPasswordSuccess", "Password changed successfully.");
        document.getElementById("currentPassword").value = "";
        document.getElementById("newPassword").value = "";
    } catch (error) {
        displayMessage("accountPasswordError", error.message || String(error), true);
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const emailForm = document.getElementById("accountEmailForm");
    const passwordForm = document.getElementById("accountPasswordForm");

    if (emailForm) {
        emailForm.addEventListener("submit", handleEmailSubmit);
    }
    if (passwordForm) {
        passwordForm.addEventListener("submit", handlePasswordSubmit);
    }

    loadAccountDetails();
});

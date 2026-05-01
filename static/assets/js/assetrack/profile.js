import { apiRequest } from "./api.js";

function displayMessage(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = message;
    element.classList.toggle("d-none", !message);
    element.classList.toggle("alert-danger", isError);
    element.classList.toggle("alert-success", !isError);
}

function setFormValues(data) {
    document.getElementById("profileFirstName").value = data.first_name || "";
    document.getElementById("profileLastName").value = data.last_name || "";
    document.getElementById("profilePhone").value = data.phone || "";
    document.getElementById("profilePosition").value = data.position || "";
    document.getElementById("profileDepartment").value = data.department || "";
    document.getElementById("profileHireDate").value = data.hire_date || "";
    document.getElementById("profileBranch").value = data.branch?.name || "Head Office";
    document.getElementById("profileHeadOffice").value = data.head_office?.name || "";
}

async function loadProfile() {
    try {
        const profile = await apiRequest("/employees/profile/");
        setFormValues(profile);
        return profile;
    } catch (error) {
        displayMessage("profileError", error.message || String(error), true);
        console.error(error);
        return null;
    }
}

async function submitProfile(event) {
    event.preventDefault();
    displayMessage("profileSuccess", "", false);
    displayMessage("profileError", "", false);

    const firstName = document.getElementById("profileFirstName").value.trim();
    const lastName = document.getElementById("profileLastName").value.trim();
    const phone = document.getElementById("profilePhone").value.trim();
    const position = document.getElementById("profilePosition").value.trim();
    const department = document.getElementById("profileDepartment").value.trim();
    const hireDate = document.getElementById("profileHireDate").value;

    try {
        const profile = await apiRequest("/employees/profile/");
        if (!profile?.id) {
            throw new Error("Profile information is unavailable.");
        }

        await apiRequest(`/employees/${profile.id}/`, {
            method: "PATCH",
            body: {
                first_name: firstName,
                last_name: lastName,
                phone,
                position,
                department,
                hire_date: hireDate,
            },
        });

        displayMessage("profileSuccess", "Profile updated successfully.");
    } catch (error) {
        displayMessage("profileError", error.message || String(error), true);
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("profileForm");
    if (form) {
        form.addEventListener("submit", submitProfile);
    }
    loadProfile();
});

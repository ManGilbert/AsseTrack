import { apiRequest } from "./api.js";

function displayMessage(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = message;
    element.classList.toggle("d-none", !message);
    element.classList.toggle("alert-danger", isError);
    element.classList.toggle("alert-success", !isError);
}

async function handleDeviceUpload(event) {
    event.preventDefault();
    displayMessage("registerDevicesSuccess", "", false);
    displayMessage("registerDevicesError", "", false);

    const fileInput = document.getElementById("deviceUploadFile");
    if (!fileInput || !fileInput.files.length) {
        displayMessage("registerDevicesError", "Please select a file to upload.", true);
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/api/devices/bulk_register/", {
            method: "POST",
            headers: {
                Authorization: `Bearer ${localStorage.getItem("assetrack_access_token")}`,
            },
            body: formData,
        });

        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || payload.error || "Upload failed.");
        }

        const summary = `Imported ${payload.created} devices. ${payload.skipped} rows skipped.`;
        displayMessage("registerDevicesSuccess", summary);
    } catch (error) {
        displayMessage("registerDevicesError", error.message || String(error), true);
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("registerDevicesForm");
    if (form) {
        form.addEventListener("submit", handleDeviceUpload);
    }
});

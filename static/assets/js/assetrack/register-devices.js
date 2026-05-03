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

        const downloadButton = document.getElementById("downloadDeviceList");
        if (downloadButton) {
            downloadButton.addEventListener("click", downloadDeviceList);
        }
    });

async function downloadDeviceList() {
    displayMessage("registerDevicesSuccess", "", false);
    displayMessage("registerDevicesError", "", false);

    try {
        const response = await fetch("/api/devices/report/", {
            method: "GET",
            headers: {
                Authorization: `Bearer ${localStorage.getItem("assetrack_access_token")}`,
            },
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || "Unable to download the device list.");
        }

        const blob = await response.blob();
        const fileName = response.headers.get("content-disposition")?.match(/filename="?(.*)"?/)?.[1] || "device-list.csv";
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = fileName;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.URL.revokeObjectURL(url);

        displayMessage("registerDevicesSuccess", "Device list downloaded successfully.");
    } catch (error) {
        displayMessage("registerDevicesError", error.message || String(error), true);
        console.error(error);
    }
}

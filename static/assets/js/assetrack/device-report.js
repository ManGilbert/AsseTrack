import { apiRequest } from "./api.js";

function displayMessage(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.textContent = message;
    element.classList.toggle("d-none", !message);
    element.classList.toggle("alert-danger", isError);
    element.classList.toggle("alert-success", !isError);
}

async function downloadReport() {
    displayMessage("deviceReportSuccess", "", false);
    displayMessage("deviceReportError", "", false);

    try {
        const response = await fetch("/api/devices/report/", {
            method: "GET",
            headers: {
                Authorization: `Bearer ${localStorage.getItem("assetrack_access_token")}`,
            },
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || "Unable to download device report.");
        }

        const blob = await response.blob();
        const fileName = response.headers.get("content-disposition")?.match(/filename="?(.*)"?/)?.[1] || "device-report.csv";
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = fileName;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.URL.revokeObjectURL(url);

        displayMessage("deviceReportSuccess", "Device report downloaded successfully.");
    } catch (error) {
        displayMessage("deviceReportError", error.message || String(error), true);
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("downloadDeviceReport");
    if (button) {
        button.addEventListener("click", downloadReport);
    }
});

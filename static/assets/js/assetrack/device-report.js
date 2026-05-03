import { apiRequest, fetchAllPages } from "./api.js";

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

function formatDeviceRow(device) {
    return `
        <tr>
            <td>${escapeHtml(device.name)}</td>
            <td>${escapeHtml(device.serial_number)}</td>
            <td>${escapeHtml(device.device_type || device.category || "Unknown")}</td>
            <td>${escapeHtml(device.branch?.name || (device.assign_to_all_branches ? "All Branches" : "Head Office"))}</td>
            <td>${escapeHtml(device.brand || device.model || "N/A")}</td>
        </tr>
    `;
}

function escapeHtml(value) {
    return String(value || "").replace(/[&<>"]+/g, (match) => {
        const escapeMap = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
        return escapeMap[match] || match;
    });
}

async function loadDevicePreview() {
    const tableBody = document.getElementById("deviceReportTableBody");
    if (!tableBody) {
        return;
    }

    tableBody.innerHTML = `
        <tr>
            <td colspan="5" class="text-muted">Loading device preview...</td>
        </tr>
    `;

    try {
        const devices = await fetchAllPages("/devices/?page_size=20");
        const previewDevices = Array.isArray(devices) ? devices.slice(0, 20) : [];
        tableBody.innerHTML = previewDevices.length
            ? previewDevices.map(formatDeviceRow).join("")
            : `<tr><td colspan="5" class="text-muted">No devices available.</td></tr>`;
    } catch (error) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-danger">Unable to load device preview.</td>
            </tr>
        `;
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("downloadDeviceReport");
    if (button) {
        button.addEventListener("click", downloadReport);
    }
    loadDevicePreview();
});

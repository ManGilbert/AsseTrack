import { apiRequest, fetchAllPages } from "./api.js";

const PAGE_SIZE = 4;

const state = {
    currentUser: null,
    devices: [],
    requests: [],
    notifications: [],
    devicePage: 1,
    requestPage: 1,
    notificationPage: 1,
    activeForm: null,
};

const elements = {
    deviceCount: document.getElementById("deviceCount"),
    requestCount: document.getElementById("requestCount"),
    notificationCount: document.getElementById("notificationCount"),
    deviceTableBody: document.getElementById("deviceTableBody"),
    requestTableBody: document.getElementById("requestTableBody"),
    notificationTableBody: document.getElementById("notificationTableBody"),
    devicePagination: document.getElementById("devicePagination"),
    requestPagination: document.getElementById("requestPagination"),
    notificationPagination: document.getElementById("notificationPagination"),
    requestDetailPanel: document.getElementById("requestDetailPanel"),
    deviceSearchInput: document.getElementById("deviceSearchInput"),
    requestSearchInput: document.getElementById("requestSearchInput"),
    refreshConsoleButton: document.getElementById("refreshConsoleButton"),
    markAllReadButton: document.getElementById("markAllReadButton"),
    feedback: document.getElementById("employeeConsoleFeedback"),
    entityModalTitle: document.getElementById("entityModalTitle"),
    entityForm: document.getElementById("entityForm"),
    entityFormFields: document.getElementById("entityFormFields"),
    entityFormFeedback: document.getElementById("entityFormFeedback"),
    entityFormSubmitButton: document.getElementById("entityFormSubmitButton"),
};

const entityModalNode = document.getElementById("entityModal");
const entityModal = entityModalNode ? new globalThis.bootstrap.Modal(entityModalNode) : null;

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function showAlert(element, message, kind) {
    if (!element) return;
    element.textContent = message;
    element.className = `alert alert-${kind}`;
    element.classList.remove("d-none");
}

function hideAlert(element) {
    element?.classList.add("d-none");
}

function formatDateTime(value) {
    if (!value) return "N/A";
    return new Intl.DateTimeFormat("en-RW", {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(value));
}

function humanizeStatus(status) {
    return String(status || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusBadge(status) {
    const classes = {
        pending: "asse-status-pill asse-status-pending",
        approved_by_branch: "asse-status-pill asse-status-approved_by_branch",
        approved_by_head_office: "asse-status-pill asse-status-approved_by_head_office",
        resolved: "asse-status-pill asse-status-resolved",
        rejected: "asse-status-pill asse-status-rejected",
    };
    return `<span class="${classes[status] || "asse-status-pill asse-status-approved_by_branch"}">${escapeHtml(humanizeStatus(status))}</span>`;
}

function actionButton(action, id, icon) {
    return `<button type="button" class="btn btn-sm btn-light-brand asse-action-btn" data-action="${action}" data-id="${id}"><i class="${icon}"></i></button>`;
}

function matches(text, query) {
    return text.toLowerCase().includes(query.trim().toLowerCase());
}

function paginate(items, page) {
    const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
    const currentPage = Math.min(page, totalPages);
    const start = (currentPage - 1) * PAGE_SIZE;
    return { totalPages, currentPage, records: items.slice(start, start + PAGE_SIZE) };
}

function renderPagination(element, key, currentPage, totalItems, totalPages) {
    if (!element) return;
    if (!totalItems || totalPages <= 1) {
        element.innerHTML = totalItems ? "" : `<li><a href="javascript:void(0);" class="active">0 Records</a></li>`;
        return;
    }
    element.innerHTML = Array.from({ length: totalPages }, (_, index) => index + 1)
        .map((page) => `<li><a href="javascript:void(0);" data-${key}-page="${page}" class="${page === currentPage ? "active" : ""}">${page}</a></li>`)
        .join("");
}

async function ensureEmployeeSession() {
    const user = await apiRequest("/auth/me/");
    if (user.role !== "employee") {
        window.location.href = "/login/";
        throw new Error("Only employees can access this dashboard.");
    }
    state.currentUser = user;
}

async function loadData() {
    const [devices, requests, notifications] = await Promise.all([
        fetchAllPages("/devices/"),
        fetchAllPages("/requests/"),
        fetchAllPages("/notifications/"),
    ]);
    state.devices = devices;
    state.requests = requests;
    state.notifications = notifications;
}

function renderOverview() {
    elements.deviceCount.textContent = state.devices.length;
    elements.requestCount.textContent = state.requests.length;
    elements.notificationCount.textContent = state.notifications.filter((item) => !item.is_read).length;
}

function renderDevices() {
    const query = elements.deviceSearchInput.value || "";
    const items = state.devices.filter((device) => matches(`${device.name} ${device.serial_number} ${device.device_type}`, query));
    const page = paginate(items, state.devicePage);
    state.devicePage = page.currentPage;

    elements.deviceTableBody.innerHTML = items.length
        ? page.records.map((device) => {
            const ownAssignment = (device.current_assignments || []).find(
                (assignment) => assignment.employee_id === state.currentUser?.employee?.id
            );
            return `
                <tr>
                    <td>${escapeHtml(device.name || "-")}</td>
                    <td>${escapeHtml(device.serial_number || "-")}</td>
                    <td>${escapeHtml(device.device_type || "-")}</td>
                    <td>${formatDateTime(ownAssignment?.assigned_at)}</td>
                    <td class="text-end">
                        <div class="asse-card-action justify-content-end">
                            ${actionButton("view-device", device.id, "feather-eye")}
                            ${actionButton("repair-device", device.id, "feather-tool")}
                        </div>
                    </td>
                </tr>
            `;
        }).join("")
        : `<tr><td colspan="5" class="asse-empty-state">No assigned devices found.</td></tr>`;

    renderPagination(elements.devicePagination, "device", page.currentPage, items.length, page.totalPages);
}

function renderRequests() {
    const query = elements.requestSearchInput.value || "";
    const items = state.requests.filter((request) => matches(`${request.device_detail?.name || ""} ${request.status || ""}`, query));
    const page = paginate(items, state.requestPage);
    state.requestPage = page.currentPage;

    elements.requestTableBody.innerHTML = items.length
        ? page.records.map((request) => `
            <tr>
                <td>${escapeHtml(request.device_detail?.name || "-")}</td>
                <td>${statusBadge(request.status)}</td>
                <td>${formatDateTime(request.created_at)}</td>
                <td class="text-end">
                    <div class="asse-card-action justify-content-end">
                        ${actionButton("view-request", request.id, "feather-eye")}
                    </div>
                </td>
            </tr>
        `).join("")
        : `<tr><td colspan="4" class="asse-empty-state">No repair requests found.</td></tr>`;

    renderPagination(elements.requestPagination, "request", page.currentPage, items.length, page.totalPages);
}

function renderNotifications() {
    const page = paginate(state.notifications, state.notificationPage);
    state.notificationPage = page.currentPage;

    elements.notificationTableBody.innerHTML = state.notifications.length
        ? page.records.map((notification) => `
            <tr>
                <td>${escapeHtml(notification.title)}</td>
                <td>${escapeHtml(notification.message)}</td>
                <td>${notification.is_read ? "Read" : "Unread"}</td>
                <td>${formatDateTime(notification.created_at)}</td>
            </tr>
        `).join("")
        : `<tr><td colspan="4" class="asse-empty-state">No notifications found.</td></tr>`;

    renderPagination(elements.notificationPagination, "notification", page.currentPage, state.notifications.length, page.totalPages);
}

function renderRequestDetail(requestId) {
    const request = state.requests.find((item) => item.id === requestId);
    if (!request) return;

    elements.requestDetailPanel.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-3">
            <div>
                <h5 class="mb-1">${escapeHtml(request.device_detail?.name || "Device")}</h5>
                <p class="text-muted mb-0">${escapeHtml(request.device_detail?.serial_number || "N/A")}</p>
            </div>
            ${statusBadge(request.status)}
        </div>
        <p class="mb-3">${escapeHtml(request.issue_description || "No issue description.")}</p>
        <div class="progress mb-2" style="height: 8px;">
            <div class="progress-bar" style="width: ${request.progress_percentage || 0}%"></div>
        </div>
        <div class="fs-12 text-muted">Progress: ${request.progress_percentage || 0}%</div>
        ${request.rejection_reason ? `<div class="alert alert-danger py-2 mt-3">${escapeHtml(request.rejection_reason)}</div>` : ""}
        ${request.resolution_notes ? `<div class="alert alert-success py-2 mt-3">${escapeHtml(request.resolution_notes)}</div>` : ""}
    `;
}

function renderAll() {
    renderOverview();
    renderDevices();
    renderRequests();
    renderNotifications();
}

function openRepairForm(deviceId) {
    if (!entityModal) return;
    state.activeForm = { kind: "create-request", recordId: deviceId };
    hideAlert(elements.entityFormFeedback);
    elements.entityModalTitle.textContent = "Create Repair Request";
    elements.entityFormSubmitButton.textContent = "Submit Request";
    elements.entityFormSubmitButton.classList.remove("d-none");
    elements.entityFormFields.innerHTML = `
        <div class="col-12">
            <label class="form-label asse-modal-label">Issue Description</label>
            <textarea class="form-control" name="issue_description" rows="4" required placeholder="Describe the damage or issue."></textarea>
        </div>
    `;
    entityModal.show();
}

function openDeviceDetail(deviceId) {
    const device = state.devices.find((item) => item.id === deviceId);
    if (!device || !entityModal) return;
    state.activeForm = null;
    elements.entityModalTitle.textContent = "Device Details";
    elements.entityFormSubmitButton.classList.add("d-none");
    elements.entityFormFields.innerHTML = [
        ["Device", device.name],
        ["Serial Number", device.serial_number],
        ["Type", device.device_type],
        ["Brand", device.brand || "N/A"],
        ["Model", device.model || "N/A"],
        ["Scope", device.assignment_scope || "N/A"],
    ].map(([label, value]) => `
        <div class="col-md-6">
            <label class="form-label asse-modal-label">${escapeHtml(label)}</label>
            <div class="form-control bg-gray-100">${escapeHtml(value)}</div>
        </div>
    `).join("");
    entityModal.show();
}

async function submitEntityForm(event) {
    event.preventDefault();
    if (!state.activeForm) return;
    hideAlert(elements.entityFormFeedback);
    elements.entityFormSubmitButton.disabled = true;

    const formData = new FormData(elements.entityForm);
    try {
        await apiRequest("/requests/", {
            method: "POST",
            body: {
                device: state.activeForm.recordId,
                issue_description: formData.get("issue_description"),
            },
        });
        showAlert(elements.entityFormFeedback, "Repair request submitted.", "success");
        await loadData();
        renderAll();
        window.setTimeout(() => entityModal.hide(), 350);
    } catch (error) {
        showAlert(elements.entityFormFeedback, error.message || "Unable to submit request.", "danger");
    } finally {
        elements.entityFormSubmitButton.disabled = false;
    }
}

function bindEvents() {
    elements.entityForm?.addEventListener("submit", submitEntityForm);
    elements.refreshConsoleButton?.addEventListener("click", refresh);
    elements.markAllReadButton?.addEventListener("click", async () => {
        await apiRequest("/notifications/mark_all_as_read/", { method: "POST", body: {} });
        await refresh();
    });

    [elements.deviceSearchInput, elements.requestSearchInput].filter(Boolean).forEach((input) => {
        input.addEventListener("input", () => {
            if (input === elements.deviceSearchInput) state.devicePage = 1;
            if (input === elements.requestSearchInput) state.requestPage = 1;
            renderAll();
        });
    });

    document.addEventListener("click", (event) => {
        const actionButtonNode = event.target.closest(".asse-action-btn");
        if (actionButtonNode) {
            const id = Number(actionButtonNode.dataset.id);
            const action = actionButtonNode.dataset.action;
            if (action === "repair-device") openRepairForm(id);
            if (action === "view-device") openDeviceDetail(id);
            if (action === "view-request") renderRequestDetail(id);
        }

        const devicePage = event.target.closest("[data-device-page]");
        const requestPage = event.target.closest("[data-request-page]");
        const notificationPage = event.target.closest("[data-notification-page]");
        if (devicePage) {
            event.preventDefault();
            state.devicePage = Number(devicePage.dataset.devicePage);
            renderDevices();
        }
        if (requestPage) {
            event.preventDefault();
            state.requestPage = Number(requestPage.dataset.requestPage);
            renderRequests();
        }
        if (notificationPage) {
            event.preventDefault();
            state.notificationPage = Number(notificationPage.dataset.notificationPage);
            renderNotifications();
        }
    });
}

async function refresh() {
    hideAlert(elements.feedback);
    try {
        await loadData();
        renderAll();
    } catch (error) {
        showAlert(elements.feedback, error.message || "Unable to refresh dashboard data.", "danger");
    }
}

async function initialize() {
    await ensureEmployeeSession();
    await loadData();
    renderAll();
    bindEvents();
}

initialize().catch((error) => {
    showAlert(elements.feedback, error.message || "Unable to load employee dashboard.", "danger");
});

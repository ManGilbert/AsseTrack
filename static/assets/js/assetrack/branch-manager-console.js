import { apiRequest, fetchAllPages, logout } from "./api.js";

const state = {
    currentUser: null,
    branch: null,
    employees: [],
    devices: [],
    requests: [],
    activeForm: null,
    confirmAction: null,
    employeePage: 1,
    devicePage: 1,
    requestPage: 1,
};

const elements = {
    employeeCount: document.getElementById("employeeCount"),
    deviceCount: document.getElementById("deviceCount"),
    requestCount: document.getElementById("requestCount"),
    pendingRequestCount: document.getElementById("pendingRequestCount"),
    employeeTableBody: document.getElementById("employeeTableBody"),
    deviceTableBody: document.getElementById("deviceTableBody"),
    requestTableBody: document.getElementById("requestTableBody"),
    requestDetailPanel: document.getElementById("requestDetailPanel"),
    employeePagination: document.getElementById("employeePagination"),
    devicePagination: document.getElementById("devicePagination"),
    requestPagination: document.getElementById("requestPagination"),
    employeeSearchInput: document.getElementById("employeeSearchInput"),
    deviceSearchInput: document.getElementById("deviceSearchInput"),
    requestSearchInput: document.getElementById("requestSearchInput"),
    refreshConsoleButton: document.getElementById("refreshConsoleButton"),
    branchManagerConsoleFeedback: document.getElementById("branchManagerConsoleFeedback"),
    entityModalTitle: document.getElementById("entityModalTitle"),
    entityForm: document.getElementById("entityForm"),
    entityFormFields: document.getElementById("entityFormFields"),
    entityFormFeedback: document.getElementById("entityFormFeedback"),
    entityFormSubmitButton: document.getElementById("entityFormSubmitButton"),
    confirmMessage: document.getElementById("confirmMessage"),
    confirmFeedback: document.getElementById("confirmFeedback"),
    confirmActionButton: document.getElementById("confirmActionButton"),
};

const entityModalNode = document.getElementById("entityModal");
const confirmModalNode = document.getElementById("confirmModal");

function mountModalToBody(node) {
    if (!node || node.parentElement === document.body) {
        return node;
    }
    document.body.appendChild(node);
    return node;
}

mountModalToBody(entityModalNode);
mountModalToBody(confirmModalNode);

const entityModal = entityModalNode ? new globalThis.bootstrap.Modal(entityModalNode) : null;
const confirmModal = confirmModalNode ? new globalThis.bootstrap.Modal(confirmModalNode) : null;
const DASHBOARD_TABLE_PAGE_SIZE = 4;

const statusClasses = {
    pending: "asse-status-pill asse-status-pending",
    approved_by_branch: "asse-status-pill asse-status-approved_by_branch",
    approved_by_head_office: "asse-status-pill asse-status-approved_by_head_office",
    resolved: "asse-status-pill asse-status-resolved",
    rejected: "asse-status-pill asse-status-rejected",
    assigned: "asse-status-pill asse-status-approved_by_branch",
    shared: "asse-status-pill asse-status-approved_by_branch",
    branch: "asse-status-pill asse-status-resolved",
};

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
    if (!element) return;
    element.classList.add("d-none");
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
    return String(status).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusBadge(status, label = null) {
    const cssClass = statusClasses[status] || "asse-status-pill asse-status-approved_by_branch";
    return `<span class="${cssClass}">${escapeHtml(label || humanizeStatus(status))}</span>`;
}

function actionButton(action, id, icon, extra = "") {
    return `<button type="button" class="btn btn-sm btn-light-brand asse-action-btn" data-action="${action}" data-id="${id}" ${extra}><i class="${icon}"></i></button>`;
}

function sectionSearchMatch(text, query) {
    return text.toLowerCase().includes(query.trim().toLowerCase());
}

async function ensureBranchManagerSession() {
    try {
        const user = await apiRequest("/auth/me/");
        if (user.role !== "branch_manager") {
            throw new Error("Only branch managers can access this console.");
        }
        state.currentUser = user;
        state.branch = {
            id: user.employee?.branch_id,
            name: user.employee?.branch_name || null,
        };
    } catch (error) {
        window.location.href = "/login/";
        throw error;
    }
}

async function loadData() {
    const [employees, devices, requests] = await Promise.all([
        fetchAllPages("/employees/"),
        fetchAllPages("/devices/"),
        fetchAllPages("/requests/"),
    ]);

    state.employees = employees;
    state.devices = devices;
    state.requests = requests;
}

function renderOverview() {
    elements.employeeCount.textContent = state.employees.length;
    elements.deviceCount.textContent = state.devices.length;
    elements.requestCount.textContent = state.requests.length;
    elements.pendingRequestCount.textContent = state.requests.filter((request) => request.status === "pending").length;
}

function renderEmployees() {
    const query = elements.employeeSearchInput.value || "";
    const items = state.employees.filter((employee) =>
        sectionSearchMatch(
            `${employee.full_name || ""} ${employee.user?.email || ""} ${employee.position || ""}`,
            query
        )
    );

    const totalPages = Math.max(1, Math.ceil(items.length / DASHBOARD_TABLE_PAGE_SIZE));
    state.employeePage = Math.min(state.employeePage, totalPages);
    const startIndex = (state.employeePage - 1) * DASHBOARD_TABLE_PAGE_SIZE;
    const paginatedItems = items.slice(startIndex, startIndex + DASHBOARD_TABLE_PAGE_SIZE);

    elements.employeeTableBody.innerHTML = items.length
        ? paginatedItems
              .map(
                  (employee) => `
                    <tr>
                        <td>${escapeHtml(employee.full_name || "-")}</td>
                        <td>${escapeHtml(employee.user?.email || "-")}</td>
                        <td>${escapeHtml(employee.position || "-")}</td>
                        <td>${statusBadge(employee.is_active ? "approved_by_branch" : "rejected", employee.is_active ? "Active" : "Inactive")}</td>
                        <td class="text-end">
                            <div class="asse-card-action justify-content-end">
                                ${actionButton("view-employee", employee.id, "feather-eye")}
                            </div>
                        </td>
                    </tr>
                  `
              )
              .join("")
        : `<tr><td colspan="5" class="asse-empty-state">No employees found.</td></tr>`;

    renderSimplePagination(elements.employeePagination, "employee", state.employeePage, items.length, totalPages);
}

function renderDevices() {
    const query = elements.deviceSearchInput.value || "";
    const items = state.devices.filter((device) =>
        sectionSearchMatch(
            `${device.name || ""} ${device.serial_number || ""} ${device.device_type || ""}`,
            query
        )
    );

    const totalPages = Math.max(1, Math.ceil(items.length / DASHBOARD_TABLE_PAGE_SIZE));
    state.devicePage = Math.min(state.devicePage, totalPages);
    const startIndex = (state.devicePage - 1) * DASHBOARD_TABLE_PAGE_SIZE;
    const paginatedItems = items.slice(startIndex, startIndex + DASHBOARD_TABLE_PAGE_SIZE);

    elements.deviceTableBody.innerHTML = items.length
        ? paginatedItems
              .map(
                  (device) => `
                    <tr>
                        <td>${escapeHtml(device.serial_number ? `${device.name} (${device.serial_number})` : device.name || "-")}</td>
                        <td>${escapeHtml(device.serial_number || "-")}</td>
                        <td>${escapeHtml(device.device_type || "-")}</td>
                        <td>${escapeHtml((device.current_assignments || []).map((assignment) => assignment.employee_name).join(", ") || "Unassigned")}</td>
                        <td class="text-end">
                            <div class="asse-card-action justify-content-end">
                                ${actionButton("view-device", device.id, "feather-eye")}
                                ${actionButton("assign-device", device.id, "feather-arrow-right-circle")}
                                ${(device.current_assignments || []).some((assignment) => assignment.employee_id === state.currentUser?.employee?.id) ? actionButton("repair-device", device.id, "feather-tool") : ""}
                            </div>
                        </td>
                    </tr>
                  `
              )
              .join("")
        : `<tr><td colspan="5" class="asse-empty-state">No devices found.</td></tr>`;

    renderSimplePagination(elements.devicePagination, "device", state.devicePage, items.length, totalPages);
}

function renderRequests() {
    const query = elements.requestSearchInput.value || "";
    const items = state.requests.filter((request) =>
        sectionSearchMatch(
            `${request.employee_detail?.full_name || ""} ${request.device_detail?.name || ""} ${request.device_detail?.serial_number || ""} ${request.status || ""}`,
            query
        )
    );

    const totalPages = Math.max(1, Math.ceil(items.length / DASHBOARD_TABLE_PAGE_SIZE));
    state.requestPage = Math.min(state.requestPage, totalPages);
    const startIndex = (state.requestPage - 1) * DASHBOARD_TABLE_PAGE_SIZE;
    const paginatedItems = items.slice(startIndex, startIndex + DASHBOARD_TABLE_PAGE_SIZE);

    elements.requestTableBody.innerHTML = items.length
        ? paginatedItems
              .map(
                  (request) => `
                    <tr>
                        <td>${escapeHtml(request.employee_detail?.full_name || "-")}</td>
                        <td>${escapeHtml(request.device_detail ? `${request.device_detail.name} (${request.device_detail.serial_number || "N/A"})` : "-")}</td>
                        <td>${statusBadge(request.status)}</td>
                        <td>${formatDateTime(request.created_at)}</td>
                        <td class="text-end">
                            <div class="asse-card-action justify-content-end flex-wrap">
                                ${actionButton("view-request", request.id, "feather-eye")}
                                ${request.status === "pending" ? actionButton("approve-request", request.id, "feather-check-circle") : ""}
                                ${request.status === "pending" ? actionButton("reject-request", request.id, "feather-x-circle") : ""}
                            </div>
                        </td>
                    </tr>
                  `
              )
              .join("")
        : `<tr><td colspan="5" class="asse-empty-state">No requests found.</td></tr>`;

    renderRequestPagination(items.length, totalPages);
}

function renderRequestPagination(totalItems, totalPages) {
    renderDashboardPagination(elements.requestPagination, "request", state.requestPage, totalItems, totalPages);
}

function renderSimplePagination(element, key, currentPage, totalItems, totalPages) {
    renderDashboardPagination(element, key, currentPage, totalItems, totalPages);
}

function renderDashboardPagination(element, key, currentPage, totalItems, totalPages) {
    if (!element) return;

    if (!totalItems) {
        element.innerHTML = `<li><a href="javascript:void(0);" class="active">0 Records</a></li>`;
        return;
    }

    if (totalPages <= 1) {
        element.innerHTML = "";
        return;
    }

    const previousDisabled = currentPage === 1 ? "disabled" : "";
    const nextDisabled = currentPage === totalPages ? "disabled" : "";
    element.innerHTML = Array.from({ length: totalPages }, (_, index) => index + 1)
        .map(
            (page) => `
                <li>
                    <a href="javascript:void(0);" data-${key}-page="${page}" class="${page === currentPage ? "active" : ""}">
                        ${page}
                    </a>
                </li>
            `
        )
        .join("");

    element.innerHTML = `
        <li>
            <a href="javascript:void(0);" data-${key}-page="${currentPage - 1}" class="${previousDisabled}">
                <i class="bi bi-arrow-left"></i>
            </a>
        </li>
        ${element.innerHTML}
        <li>
            <a href="javascript:void(0);" data-${key}-page="${currentPage + 1}" class="${nextDisabled}">
                <i class="bi bi-arrow-right"></i>
            </a>
        </li>
    `;
}

function renderRequestDetail(requestId) {
    const request = state.requests.find((item) => item.id === requestId);
    if (!request) return;

    const timelineSteps = [
        { label: "Pending", value: formatDateTime(request.created_at) },
        { label: "Branch Approved", value: request.approved_by_branch_at ? formatDateTime(request.approved_by_branch_at) : "Waiting" },
        { label: request.status === "rejected" ? "Rejected" : request.status === "resolved" ? "Resolved" : "Current", value: request.rejected_at ? formatDateTime(request.rejected_at) : request.resolved_at ? formatDateTime(request.resolved_at) : "Waiting" },
    ];

    elements.requestDetailPanel.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-3">
            <div>
                <h5 class="mb-1">${escapeHtml(request.employee_detail?.full_name || "Employee")}</h5>
                <p class="text-muted mb-0">${escapeHtml(request.device_detail?.name || "Device")} • ${escapeHtml(request.device_detail?.serial_number || "N/A")}</p>
            </div>
            ${statusBadge(request.status)}
        </div>
        <p class="mb-3">${escapeHtml(request.issue_description || "No issue description.")}</p>
        ${request.rejection_reason ? `<div class="alert alert-danger py-2">${escapeHtml(request.rejection_reason)}</div>` : ""}
        <div class="timeline">
            ${timelineSteps
                .map(
                    (step) => `
                        <div class="timeline-step">
                            <div class="fw-semibold">${escapeHtml(step.label)}</div>
                            <div class="fs-12 text-muted">${escapeHtml(step.value)}</div>
                        </div>
                    `
                )
                .join("")}
        </div>
    `;
}

function renderAll() {
    renderOverview();
    renderEmployees();
    renderDevices();
    renderRequests();
}

function buildInputField({ name, label, type = "text", value = "", required = false, col = "col-md-6" }) {
    return `
        <div class="${col}">
            <label class="form-label asse-modal-label">${label}</label>
            <input type="${type}" class="form-control" name="${name}" value="${escapeHtml(value)}" ${required ? "required" : ""}>
        </div>
    `;
}

function buildSelectField({ name, label, options, value = "", required = false, col = "col-md-6" }) {
    return `
        <div class="${col}">
            <label class="form-label asse-modal-label">${label}</label>
            <select class="form-select" name="${name}" ${required ? "required" : ""}>
                <option value="">Select option</option>
                ${options
                    .map(
                        (option) => `
                            <option value="${option.value}" ${String(option.value) === String(value) ? "selected" : ""}>${escapeHtml(option.label)}</option>
                        `
                    )
                    .join("")}
            </select>
        </div>
    `;
}

function openFormModal(config) {
    if (!entityModal) return;
    state.activeForm = config;
    hideAlert(elements.entityFormFeedback);
    elements.entityModalTitle.textContent = config.title;
    elements.entityFormSubmitButton.textContent = config.submitLabel || "Save";
    elements.entityFormFields.innerHTML = config.fields.join("");
    elements.entityFormSubmitButton.classList.remove("d-none");
    entityModal.show();
}

function openViewModal(title, fields) {
    if (!entityModal) return;
    state.activeForm = null;
    hideAlert(elements.entityFormFeedback);
    elements.entityModalTitle.textContent = title;
    elements.entityFormSubmitButton.classList.add("d-none");
    elements.entityFormFields.innerHTML = fields
        .map(
            (field) => `
                <div class="col-md-6">
                    <label class="form-label asse-modal-label">${escapeHtml(field.label)}</label>
                    <div class="form-control bg-gray-100">${escapeHtml(field.value)}</div>
                </div>
            `
        )
        .join("");
    entityModal.show();
}

if (entityModalNode) {
    entityModalNode.addEventListener("hidden.bs.modal", () => {
        elements.entityFormSubmitButton.classList.remove("d-none");
        elements.entityForm.reset();
        state.activeForm = null;
    });
}

function openConfirmModal(message, action) {
    if (!confirmModal) return;
    state.confirmAction = action;
    hideAlert(elements.confirmFeedback);
    elements.confirmMessage.textContent = message;
    confirmModal.show();
}

function employeeFormConfig() {
    return {
        kind: "create-employee",
        title: "Register New Employee",
        submitLabel: "Create Employee",
        fields: [
            buildInputField({ name: "first_name", label: "First Name", required: true }),
            buildInputField({ name: "last_name", label: "Last Name", required: true }),
            buildInputField({ name: "email", label: "Email", type: "email", required: true }),
            buildInputField({ name: "password", label: "Password", type: "password", required: true }),
            buildInputField({ name: "phone", label: "Phone", required: true }),
            buildInputField({ name: "position", label: "Position", required: true }),
            buildInputField({ name: "department", label: "Department", required: true }),
            buildInputField({ name: "hire_date", label: "Hire Date", type: "date", required: true }),
        ],
    };
}

function assignDeviceFormConfig(deviceId) {
    return {
        kind: "assign-device",
        recordId: deviceId,
        title: "Assign Device to Employee",
        submitLabel: "Assign Device",
        fields: [
            buildSelectField({
                name: "employee",
                label: "Employee",
                required: true,
                options: state.employees.map((employee) => ({ value: employee.id, label: `${employee.full_name} (${employee.user?.email || ""})` })),
            }),
        ],
    };
}

function repairRequestFormConfig(deviceId) {
    return {
        kind: "create-request",
        recordId: deviceId,
        title: "Submit Repair Request",
        submitLabel: "Submit Request",
        fields: [
            `
            <div class="col-12">
                <label class="form-label asse-modal-label">Issue Description</label>
                <textarea class="form-control" name="issue_description" rows="4" required placeholder="Describe the damage or issue."></textarea>
            </div>
            `,
        ],
    };
}

function requestActionFormConfig(request) {
    return {
        kind: "reject-request",
        recordId: request.id,
        title: "Reject Device Request",
        submitLabel: "Reject Request",
        fields: [
            `
            <div class="col-12">
                <label class="form-label asse-modal-label">Rejection Reason</label>
                <textarea class="form-control" name="reason" rows="4" required placeholder="Explain why this request is being rejected."></textarea>
            </div>
            `,
        ],
    };
}

async function submitEntityForm(event) {
    event.preventDefault();
    if (!state.activeForm) return;

    hideAlert(elements.entityFormFeedback);
    elements.entityFormSubmitButton.disabled = true;

    const formData = new FormData(elements.entityForm);

    try {
        if (state.activeForm.kind === "create-employee") {
            await apiRequest("/employees/", {
                method: "POST",
                body: {
                    user: {
                        email: formData.get("email"),
                        password: formData.get("password"),
                        role: "employee",
                        is_active: true,
                    },
                    first_name: formData.get("first_name"),
                    last_name: formData.get("last_name"),
                    phone: formData.get("phone"),
                    position: formData.get("position"),
                    department: formData.get("department"),
                    hire_date: formData.get("hire_date"),
                },
            });
        }

        if (state.activeForm.kind === "assign-device") {
            await apiRequest("/assignments/", {
                method: "POST",
                body: {
                    device: state.activeForm.recordId,
                    employee: Number(formData.get("employee")),
                },
            });
        }

        if (state.activeForm.kind === "reject-request") {
            await apiRequest(`/requests/${state.activeForm.recordId}/reject/`, {
                method: "POST",
                body: { reason: formData.get("reason") },
            });
        }

        if (state.activeForm.kind === "create-request") {
            await apiRequest("/requests/", {
                method: "POST",
                body: {
                    device: state.activeForm.recordId,
                    issue_description: formData.get("issue_description"),
                },
            });
        }

        showAlert(elements.entityFormFeedback, "Saved successfully.", "success");
        await loadData();
        renderAll();
        window.setTimeout(() => entityModal.hide(), 350);
    } catch (error) {
        showAlert(elements.entityFormFeedback, error.message || "Unable to save.", "danger");
    } finally {
        elements.entityFormSubmitButton.disabled = false;
    }
}

async function runConfirmAction() {
    if (!state.confirmAction) return;
    hideAlert(elements.confirmFeedback);
    elements.confirmActionButton.disabled = true;

    try {
        await state.confirmAction();
        await loadData();
        renderAll();
        confirmModal.hide();
    } catch (error) {
        showAlert(elements.confirmFeedback, error.message || "Unable to complete action.", "danger");
    } finally {
        elements.confirmActionButton.disabled = false;
    }
}

function bindActionDelegation() {
    document.addEventListener("click", async (event) => {
        const button = event.target.closest(".asse-action-btn");
        if (!button) return;

        const id = Number(button.dataset.id);
        const action = button.dataset.action;

        if (action === "view-employee") {
            const employee = state.employees.find((item) => item.id === id);
            openViewModal("Employee Details", [
                { label: "Name", value: employee.full_name },
                { label: "Email", value: employee.user?.email || "N/A" },
                { label: "Position", value: employee.position || "N/A" },
                { label: "Department", value: employee.department || "N/A" },
                { label: "Assigned Devices", value: state.devices.filter((device) => (device.current_assignments || []).some((assignment) => assignment.employee_id === employee.id)).map((device) => device.display_name || device.name).join(", ") || "None" },
                { label: "Status", value: employee.is_active ? "Active" : "Inactive" },
            ]);
        }

        if (action === "view-device") {
            const device = state.devices.find((item) => item.id === id);
            openViewModal("Device Details", [
                { label: "Device", value: device.name },
                { label: "Serial Number", value: device.serial_number },
                { label: "Type", value: device.device_type || "N/A" },
                { label: "Scope", value: device.assignment_scope || device.branch_detail?.name || "N/A" },
                { label: "Assigned To", value: (device.current_assignments || []).map((assignment) => assignment.employee_name).join(", ") || "Unassigned" },
            ]);
        }

        if (action === "assign-device") {
            openFormModal(assignDeviceFormConfig(id));
        }

        if (action === "repair-device") {
            openFormModal(repairRequestFormConfig(id));
        }

        if (action === "view-request") {
            renderRequestDetail(id);
            document.getElementById("requests")?.scrollIntoView({ behavior: "smooth", block: "start" });
        }

        if (action === "approve-request") {
            openConfirmModal("Approve this request for branch review?", async () => {
                await apiRequest(`/requests/${id}/approve_branch/`, { method: "POST", body: {} });
            });
        }

        if (action === "reject-request") {
            const request = state.requests.find((item) => item.id === id);
            openFormModal(requestActionFormConfig(request));
        }
    });
}

function wireSearch() {
    [elements.employeeSearchInput, elements.deviceSearchInput, elements.requestSearchInput]
        .filter(Boolean)
        .forEach((input) =>
            input.addEventListener("input", () => {
                if (input === elements.employeeSearchInput) {
                    state.employeePage = 1;
                }
                if (input === elements.deviceSearchInput) {
                    state.devicePage = 1;
                }
                if (input === elements.requestSearchInput) {
                    state.requestPage = 1;
                }
                renderAll();
            })
        );
}

function wirePagination() {
    elements.employeePagination?.addEventListener("click", (event) => {
        const link = event.target.closest("[data-employee-page]");
        if (!link || link.classList.contains("disabled")) return;
        event.preventDefault();
        const requestedPage = Number(link.dataset.employeePage);
        if (!Number.isFinite(requestedPage) || requestedPage < 1) return;
        state.employeePage = requestedPage;
        renderEmployees();
    });

    elements.devicePagination?.addEventListener("click", (event) => {
        const link = event.target.closest("[data-device-page]");
        if (!link || link.classList.contains("disabled")) return;
        event.preventDefault();
        const requestedPage = Number(link.dataset.devicePage);
        if (!Number.isFinite(requestedPage) || requestedPage < 1) return;
        state.devicePage = requestedPage;
        renderDevices();
    });

    elements.requestPagination?.addEventListener("click", (event) => {
        const link = event.target.closest("[data-request-page]");
        if (!link || link.classList.contains("disabled")) return;

        event.preventDefault();
        const requestedPage = Number(link.dataset.requestPage);
        if (!Number.isFinite(requestedPage) || requestedPage < 1) return;

        state.requestPage = requestedPage;
        renderRequests();
    });
}

function wireCreateButtons() {
    document.getElementById("createEmployeeButton")?.addEventListener("click", () => openFormModal(employeeFormConfig()));
}

async function initializeConsole() {
    hideAlert(elements.branchManagerConsoleFeedback);
    await ensureBranchManagerSession();
    await loadData();
    renderAll();
    wireSearch();
    wireCreateButtons();
    bindActionDelegation();
    wirePagination();
}

elements.entityForm?.addEventListener("submit", submitEntityForm);
elements.confirmActionButton?.addEventListener("click", runConfirmAction);
elements.refreshConsoleButton?.addEventListener("click", async () => {
    hideAlert(elements.branchManagerConsoleFeedback);
    try {
        await loadData();
        renderAll();
    } catch (error) {
        showAlert(elements.branchManagerConsoleFeedback, error.message || "Unable to refresh dashboard data.", "danger");
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    try {
        await initializeConsole();
    } catch (error) {
        showAlert(elements.branchManagerConsoleFeedback, error.message || "Unable to load the branch manager dashboard right now.", "danger");
    }
});

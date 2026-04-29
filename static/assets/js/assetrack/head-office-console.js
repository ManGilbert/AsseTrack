import { apiRequest, fetchAllPages, logout } from "./api.js";
import { clearSession, saveSession } from "./auth-store.js";

const state = {
    currentUser: null,
    headOffices: [],
    headOfficePage: 1,
    managers: [],
    branchManagers: [],
    branches: [],
    devices: [],
    requests: [],
    employees: [],
    activeForm: null,
    confirmAction: null,
};

const elements = {
    headOfficeCount: document.getElementById("headOfficeCount"),
    managerCount: document.getElementById("managerCount"),
    branchCount: document.getElementById("branchCount"),
    deviceCount: document.getElementById("deviceCount"),
    pendingRequestCount: document.getElementById("pendingRequestCount"),
    headOfficeTableBody: document.getElementById("headOfficeTableBody"),
    managerTableBody: document.getElementById("managerTableBody"),
    branchTableBody: document.getElementById("branchTableBody"),
    deviceTableBody: document.getElementById("deviceTableBody"),
    requestTableBody: document.getElementById("requestTableBody"),
    requestDetailPanel: document.getElementById("requestDetailPanel"),
    headOfficeActivityList: document.getElementById("headOfficeActivityList"),
    headOfficePagination: document.getElementById("headOfficePagination"),
    headOfficeSearchInput: document.getElementById("headOfficeSearchInput"),
    managerSearchInput: document.getElementById("managerSearchInput"),
    branchSearchInput: document.getElementById("branchSearchInput"),
    deviceSearchInput: document.getElementById("deviceSearchInput"),
    requestSearchInput: document.getElementById("requestSearchInput"),
    refreshConsoleButton: document.getElementById("refreshConsoleButton"),
    pageLogoutButton: document.getElementById("pageLogoutButton"),
    headOfficeConsoleFeedback: document.getElementById("headOfficeConsoleFeedback"),
    layoutUserName: document.getElementById("layoutUserName"),
    layoutUserEmail: document.getElementById("layoutUserEmail"),
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
const entityModal = entityModalNode ? new globalThis.bootstrap.Modal(entityModalNode) : null;
const confirmModal = confirmModalNode ? new globalThis.bootstrap.Modal(confirmModalNode) : null;
const HEAD_OFFICE_PAGE_SIZE = 4;

const avatarPool = [
    "/static/assets/images/avatar/2.png",
    "/static/assets/images/avatar/3.png",
    "/static/assets/images/avatar/4.png",
    "/static/assets/images/avatar/5.png",
    "/static/assets/images/avatar/6.png",
];

const statusClasses = {
    pending: "asse-status-pill asse-status-pending",
    approved_by_branch: "asse-status-pill asse-status-approved_by_branch",
    approved_by_head_office: "asse-status-pill asse-status-approved_by_head_office",
    resolved: "asse-status-pill asse-status-resolved",
    rejected: "asse-status-pill asse-status-rejected",
    active: "asse-status-pill asse-status-resolved",
    inactive: "asse-status-pill asse-status-rejected",
    available: "asse-status-pill asse-status-resolved",
    not_available: "asse-status-pill asse-status-pending",
    assigned: "asse-status-pill asse-status-approved_by_branch",
    unassigned: "asse-status-pill asse-status-pending",
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
    if (!element) {
        return;
    }
    element.textContent = message;
    element.className = `alert alert-${kind}`;
    element.classList.remove("d-none");
}

function hideAlert(element) {
    if (!element) {
        return;
    }
    element.classList.add("d-none");
}

function formatDate(value) {
    if (!value) return "N/A";
    return new Intl.DateTimeFormat("en-RW", {
        year: "numeric",
        month: "short",
        day: "2-digit",
    }).format(new Date(value));
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

function getAvatar(index) {
    return avatarPool[index % avatarPool.length];
}

function userCell({ title, subtitle, avatarIndex = 0 }) {
    return `
        <div class="d-flex align-items-center gap-3">
            <div class="avatar-image">
                <img src="${getAvatar(avatarIndex)}" alt="" class="img-fluid asse-table-avatar">
            </div>
            <div class="asse-user-meta">
                <span class="meta-title">${escapeHtml(title)}</span>
                <span class="meta-subtitle">${escapeHtml(subtitle)}</span>
            </div>
        </div>
    `;
}

function actionButton(action, id, icon, extra = "") {
    return `<button type="button" class="btn btn-sm btn-light-brand asse-action-btn" data-action="${action}" data-id="${id}" ${extra}><i class="${icon}"></i></button>`;
}

function sectionSearchMatch(text, query) {
    return text.toLowerCase().includes(query.trim().toLowerCase());
}

function getManagerOptions(role) {
    return state.employees.filter((employee) => employee.user.role === role);
}

async function ensureHeadOfficeSession() {
    try {
        const user = await apiRequest("/auth/me/");
        if (user.role !== "head_office_manager") {
            throw new Error("Only head office managers can access this console.");
        }
        state.currentUser = user;
        saveSession({ user });
        elements.layoutUserName.textContent = user.employee?.full_name || user.email;
        elements.layoutUserEmail.textContent = user.email;
    } catch (error) {
        clearSession();
        window.location.href = "/login/";
        throw error;
    }
}

async function loadData() {
    const [headOffices, employees, branches, devices, requests] = await Promise.all([
        fetchAllPages("/head-offices/"),
        fetchAllPages("/employees/"),
        fetchAllPages("/branches/"),
        fetchAllPages("/devices/"),
        fetchAllPages("/requests/"),
    ]);

    state.headOffices = headOffices;
    state.employees = employees;
    state.managers = employees.filter((employee) => employee.user.role === "head_office_manager");
    state.branchManagers = employees.filter((employee) => employee.user.role === "branch_manager");
    state.branches = branches;
    state.devices = devices;
    state.requests = requests;
}

function renderOverview() {
    elements.headOfficeCount.textContent = state.headOffices.length;
    elements.managerCount.textContent = state.managers.length;
    elements.branchCount.textContent = state.branches.length;
    elements.deviceCount.textContent = state.devices.length;
    elements.pendingRequestCount.textContent = state.requests.filter(
        (request) => request.status === "approved_by_branch" || request.status === "approved_by_head_office"
    ).length;

    elements.headOfficeActivityList.innerHTML = state.managers.length
        ? state.managers
        .slice(0, 5)
        .map(
            (manager, index) => `
                <div class="asse-list-item">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <div class="fw-semibold">${escapeHtml(manager.full_name || "Manager")}</div>
                            <div class="fs-12 text-muted">${escapeHtml(manager.user?.email || "No email")}</div>
                        </div>
                        ${statusBadge(manager.is_active ? "active" : "inactive", manager.is_active ? "Active" : "Inactive")}
                    </div>
                    <div class="fs-12 text-muted mb-2">${escapeHtml(manager.head_office_detail?.name || "No head office assigned")}</div>
                    <button type="button" class="btn btn-sm btn-light-brand asse-action-btn" data-action="edit-manager" data-id="${manager.id}">
                        <i class="feather-edit-3 me-1"></i> Manage Assignment
                    </button>
                </div>
            `
        )
        .join("")
        : `<div class="text-muted">No head office managers registered yet.</div>`;
}

function renderHeadOffices() {
    const query = elements.headOfficeSearchInput.value || "";
    const items = state.headOffices.filter((office) => sectionSearchMatch(`${office.name}`, query));
    const totalPages = Math.max(1, Math.ceil(items.length / HEAD_OFFICE_PAGE_SIZE));
    state.headOfficePage = Math.min(state.headOfficePage, totalPages);
    const startIndex = (state.headOfficePage - 1) * HEAD_OFFICE_PAGE_SIZE;
    const paginatedItems = items.slice(startIndex, startIndex + HEAD_OFFICE_PAGE_SIZE);

    elements.headOfficeTableBody.innerHTML = items.length
        ? paginatedItems
              .map(
                  (office, index) => `
                    <tr>
                        <td>${userCell({
                            title: office.name,
                            subtitle: `ID: ${office.id}`,
                            avatarIndex: startIndex + index,
                        })}</td>
                        <td><span class="badge bg-gray-200 text-dark">${state.branches.filter((branch) => branch.head_office === office.id).length} Branches</span></td>
                        <td>${formatDateTime(office.created_at)}</td>
                        <td>${statusBadge("active", "Active")}</td>
                        <td class="text-end">
                            <div class="asse-card-action justify-content-end">
                                ${actionButton("view-head-office", office.id, "feather-eye")}
                                ${actionButton("edit-head-office", office.id, "feather-edit-3")}
                                ${actionButton("delete-head-office", office.id, "feather-trash-2")}
                            </div>
                        </td>
                    </tr>
                  `
              )
              .join("")
        : `<tr><td colspan="5" class="asse-empty-state">No head offices found.</td></tr>`;

    renderHeadOfficePagination(items.length, totalPages);
}

function renderHeadOfficePagination(totalItems, totalPages) {
    if (!elements.headOfficePagination) {
        return;
    }

    if (!totalItems) {
        elements.headOfficePagination.innerHTML = `<li><a href="javascript:void(0);" class="active">0 Records</a></li>`;
        return;
    }

    const previousDisabled = state.headOfficePage === 1 ? "disabled" : "";
    const nextDisabled = state.headOfficePage === totalPages ? "disabled" : "";
    const pages = Array.from({ length: totalPages }, (_, index) => index + 1);

    elements.headOfficePagination.innerHTML = `
        <li>
            <a href="javascript:void(0);" data-head-office-page="${state.headOfficePage - 1}" class="${previousDisabled}">
                <i class="bi bi-arrow-left"></i>
            </a>
        </li>
        ${pages
            .map(
                (page) => `
                    <li>
                        <a href="javascript:void(0);" data-head-office-page="${page}" class="${page === state.headOfficePage ? "active" : ""}">
                            ${page}
                        </a>
                    </li>
                `
            )
            .join("")}
        <li>
            <a href="javascript:void(0);" data-head-office-page="${state.headOfficePage + 1}" class="${nextDisabled}">
                <i class="bi bi-arrow-right"></i>
            </a>
        </li>
    `;
}

function renderManagers() {
    const query = elements.managerSearchInput.value || "";
    const items = state.managers.filter((manager) =>
        sectionSearchMatch(
            `${manager.full_name} ${manager.user.email} ${manager.head_office_detail?.name || ""}`,
            query
        )
    );

    elements.managerTableBody.innerHTML = items.length
        ? items
              .map(
                  (manager, index) => `
                    <tr>
                        <td>${userCell({
                            title: manager.full_name,
                            subtitle: manager.user.email,
                            avatarIndex: index + 1,
                        })}</td>
                        <td><span class="badge bg-gray-200 text-dark">${escapeHtml(manager.head_office_detail?.name || "Not assigned")}</span></td>
                        <td>${formatDate(manager.hire_date)}</td>
                        <td>${statusBadge(manager.is_active ? "active" : "inactive", manager.is_active ? "Active" : "Inactive")}</td>
                        <td class="text-end">
                            <div class="asse-card-action justify-content-end">
                                ${actionButton("view-manager", manager.id, "feather-eye")}
                                ${actionButton("edit-manager", manager.id, "feather-edit-3")}
                                ${actionButton("delete-manager", manager.id, "feather-trash-2")}
                            </div>
                        </td>
                    </tr>
                  `
              )
              .join("")
        : `<tr><td colspan="5" class="asse-empty-state">No managers found.</td></tr>`;
}

function renderBranches() {
    const query = elements.branchSearchInput.value || "";
    const items = state.branches.filter((branch) =>
        sectionSearchMatch(
            `${branch.name} ${branch.head_office_detail?.name || ""} ${branch.manager_detail?.full_name || ""}`,
            query
        )
    );

    elements.branchTableBody.innerHTML = items.length
        ? items
              .map(
                  (branch, index) => `
                    <tr>
                        <td>${userCell({
                            title: branch.name,
                            subtitle: branch.head_office_detail?.name || "No head office",
                            avatarIndex: index + 2,
                        })}</td>
                        <td><span class="badge bg-gray-200 text-dark">${escapeHtml(branch.manager_detail?.full_name || "Manager Not Assigned")}</span></td>
                        <td>${formatDateTime(branch.created_at)}</td>
                        <td>${statusBadge(branch.manager ? "assigned" : "unassigned", branch.manager ? "Manager Assigned" : "Pending Assignment")}</td>
                        <td class="text-end">
                            <div class="asse-card-action justify-content-end">
                                ${actionButton("view-branch", branch.id, "feather-eye")}
                                ${actionButton("edit-branch", branch.id, "feather-edit-3")}
                                ${actionButton("delete-branch", branch.id, "feather-trash-2")}
                            </div>
                        </td>
                    </tr>
                  `
              )
              .join("")
        : `<tr><td colspan="5" class="asse-empty-state">No branches found.</td></tr>`;
}

function renderDevices() {
    const query = elements.deviceSearchInput.value || "";
    const items = state.devices.filter((device) =>
        sectionSearchMatch(
            `${device.name} ${device.serial_number} ${device.branch_detail?.name || ""} ${device.device_type}`,
            query
        )
    );

    elements.deviceTableBody.innerHTML = items.length
        ? items
              .map(
                  (device, index) => `
                    <tr>
                        <td>${userCell({
                            title: device.name,
                            subtitle: `${device.serial_number} • ${device.brand || "No brand"}`,
                            avatarIndex: index + 3,
                        })}</td>
                        <td><span class="badge bg-gray-200 text-dark">${escapeHtml(device.branch_detail?.name || "Unassigned Branch")}</span></td>
                        <td>${formatDate(device.purchase_date)}</td>
                        <td>${statusBadge(device.status, humanizeStatus(device.status))}</td>
                        <td class="text-end">
                            <div class="asse-card-action justify-content-end">
                                ${actionButton("view-device", device.id, "feather-eye")}
                                ${actionButton("edit-device", device.id, "feather-edit-3")}
                                ${actionButton("delete-device", device.id, "feather-trash-2")}
                            </div>
                        </td>
                    </tr>
                  `
              )
              .join("")
        : `<tr><td colspan="5" class="asse-empty-state">No devices found.</td></tr>`;
}

function renderRequests() {
    const query = elements.requestSearchInput.value || "";
    const items = state.requests.filter((request) =>
        sectionSearchMatch(
            `${request.employee_detail?.full_name || ""} ${request.device_detail?.name || ""} ${request.device_detail?.serial_number || ""} ${request.status}`,
            query
        )
    );

    elements.requestTableBody.innerHTML = items.length
        ? items
              .map(
                  (request, index) => `
                    <tr>
                        <td>${userCell({
                            title: request.employee_detail?.full_name || "Employee",
                            subtitle: request.employee_detail?.branch_detail?.name || "No branch",
                            avatarIndex: index + 4,
                        })}</td>
                        <td><span class="badge bg-gray-200 text-dark">${escapeHtml(request.device_detail?.name || "Device")} (${escapeHtml(request.device_detail?.serial_number || "N/A")})</span></td>
                        <td>${formatDateTime(request.created_at)}</td>
                        <td>
                            <div class="d-flex flex-column gap-2 align-items-start">
                                ${statusBadge(request.status)}
                                <small class="text-muted">Progress: ${request.progress_percentage}%</small>
                            </div>
                        </td>
                        <td class="text-end">
                            <div class="asse-card-action justify-content-end flex-wrap">
                                ${actionButton("view-request", request.id, "feather-eye")}
                                ${
                                    request.status === "approved_by_branch"
                                        ? actionButton("approve-request", request.id, "feather-check-circle")
                                        : ""
                                }
                                ${
                                    ["approved_by_branch", "approved_by_head_office"].includes(request.status)
                                        ? actionButton("reject-request", request.id, "feather-x-circle")
                                        : ""
                                }
                                ${
                                    request.status === "approved_by_head_office"
                                        ? actionButton("resolve-request", request.id, "feather-check-square")
                                        : ""
                                }
                            </div>
                        </td>
                    </tr>
                  `
              )
              .join("")
        : `<tr><td colspan="5" class="asse-empty-state">No requests found.</td></tr>`;
}

function renderRequestDetail(requestId) {
    const request = state.requests.find((item) => item.id === requestId);
    if (!request) return;

    const timelineSteps = [
        { label: "Pending", value: formatDateTime(request.created_at) },
        { label: "Approved by Branch", value: request.approved_by_branch_at ? formatDateTime(request.approved_by_branch_at) : "Waiting" },
        { label: "Approved by Head Office", value: request.approved_by_head_office_at ? formatDateTime(request.approved_by_head_office_at) : "Waiting" },
        { label: request.status === "rejected" ? "Rejected" : "Resolved", value: request.rejected_at ? formatDateTime(request.rejected_at) : request.resolved_at ? formatDateTime(request.resolved_at) : "Waiting" },
    ];

    elements.requestDetailPanel.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-3">
            <div>
                <h5 class="mb-1">${escapeHtml(request.employee_detail?.full_name || "Employee")}</h5>
                <p class="text-muted mb-0">${escapeHtml(request.device_detail?.name || "Device")} • ${escapeHtml(request.device_detail?.serial_number || "N/A")}</p>
            </div>
            ${statusBadge(request.status)}
        </div>
        <p class="mb-3">${escapeHtml(request.issue_description)}</p>
        <div class="small text-muted mb-2">Branch manager: ${escapeHtml(request.branch_manager_detail?.full_name || "Waiting")}</div>
        <div class="small text-muted mb-2">Head office action: ${escapeHtml(request.head_office_manager_detail?.full_name || "Waiting")}</div>
        ${request.rejection_reason ? `<div class="alert alert-danger py-2">${escapeHtml(request.rejection_reason)}</div>` : ""}
        ${request.resolution_notes ? `<div class="alert alert-success py-2">${escapeHtml(request.resolution_notes)}</div>` : ""}
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
    renderHeadOffices();
    renderManagers();
    renderBranches();
    renderDevices();
    renderRequests();
}

function buildInputField({ name, label, type = "text", value = "", readonly = false, required = false, col = "col-md-6" }) {
    return `
        <div class="${col}">
            <label class="form-label asse-modal-label">${label}</label>
            <input type="${type}" class="form-control" name="${name}" value="${escapeHtml(value)}" ${readonly ? "readonly" : ""} ${required ? "required" : ""}>
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
    if (!entityModal) {
        return;
    }
    state.activeForm = config;
    hideAlert(elements.entityFormFeedback);
    elements.entityModalTitle.textContent = config.title;
    elements.entityFormSubmitButton.textContent = config.submitLabel || "Save";
    elements.entityFormFields.innerHTML = config.fields.join("");
    elements.entityFormSubmitButton.classList.remove("d-none");
    entityModal.show();
}

function openViewModal(title, fields) {
    if (!entityModal) {
        return;
    }
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
    if (!confirmModal) {
        return;
    }
    state.confirmAction = action;
    hideAlert(elements.confirmFeedback);
    elements.confirmMessage.textContent = message;
    confirmModal.show();
}

function managerFormConfig(manager = null) {
    return {
        kind: manager ? "edit-manager" : "create-manager",
        recordId: manager?.id,
        title: manager ? "Update Head Office Manager" : "Register Head Office Manager",
        submitLabel: manager ? "Update Manager" : "Create Manager",
        fields: [
            buildInputField({ name: "first_name", label: "First Name", value: manager?.first_name || "", required: true }),
            buildInputField({ name: "last_name", label: "Last Name", value: manager?.last_name || "", required: true }),
            buildInputField({ name: "email", label: "Email", value: manager?.user?.email || "", required: true }),
            buildInputField({ name: "password", label: manager ? "New Password (optional)" : "Password", type: "password", value: "", required: !manager }),
            buildInputField({ name: "phone", label: "Phone", value: manager?.phone || "", required: true }),
            buildInputField({ name: "position", label: "Position", value: manager?.position || "", required: true }),
            buildInputField({ name: "department", label: "Department", value: manager?.department || "", required: true }),
            buildInputField({ name: "hire_date", label: "Hire Date", type: "date", value: manager?.hire_date || "", required: true }),
            buildSelectField({
                name: "head_office",
                label: "Head Office",
                value: manager?.head_office || "",
                required: true,
                options: state.headOffices.map((office) => ({ value: office.id, label: office.name })),
            }),
            buildSelectField({
                name: "is_active",
                label: "Account Status",
                value: manager ? String(manager.is_active) : "true",
                options: [
                    { value: "true", label: "Active" },
                    { value: "false", label: "Inactive" },
                ],
            }),
        ],
    };
}

function headOfficeFormConfig(office = null) {
    return {
        kind: office ? "edit-head-office" : "create-head-office",
        recordId: office?.id,
        title: office ? "Update Head Office" : "Create Head Office",
        submitLabel: office ? "Update Head Office" : "Create Head Office",
        fields: [
            buildInputField({
                name: "name",
                label: "Head Office Name",
                value: office?.name || "",
                required: true,
                col: "col-12",
            }),
        ],
    };
}

function branchFormConfig(branch = null) {
    return {
        kind: branch ? "edit-branch" : "create-branch",
        recordId: branch?.id,
        title: branch ? "Update Branch" : "Create Branch",
        submitLabel: branch ? "Update Branch" : "Create Branch",
        fields: [
            buildInputField({ name: "name", label: "Branch Name", value: branch?.name || "", required: true }),
            buildSelectField({
                name: "head_office",
                label: "Head Office",
                value: branch?.head_office || "",
                required: true,
                options: state.headOffices.map((office) => ({ value: office.id, label: office.name })),
            }),
            buildSelectField({
                name: "manager",
                label: "Assign Branch Manager",
                value: branch?.manager || "",
                options: state.branchManagers.map((manager) => ({
                    value: manager.id,
                    label: `${manager.full_name} (${manager.user.email})`,
                })),
            }),
        ],
    };
}

function deviceFormConfig(device = null) {
    return {
        kind: device ? "edit-device" : "create-device",
        recordId: device?.id,
        title: device ? "Update Device" : "Create Device",
        submitLabel: device ? "Update Device" : "Create Device",
        fields: [
            buildInputField({ name: "name", label: "Device Name", value: device?.name || "", required: true }),
            buildInputField({ name: "device_type", label: "Device Type", value: device?.device_type || "", required: true }),
            buildSelectField({
                name: "branch",
                label: "Branch",
                value: device?.branch || "",
                options: state.branches.map((branch) => ({ value: branch.id, label: branch.name })),
            }),
            buildInputField({ name: "serial_number", label: "Serial Number", value: device?.serial_number || "", required: true }),
            buildInputField({ name: "brand", label: "Brand", value: device?.brand || "" }),
            buildInputField({ name: "model", label: "Model", value: device?.model || "" }),
            buildInputField({ name: "purchase_date", label: "Purchase Date", type: "date", value: device?.purchase_date || "" }),
            buildSelectField({
                name: "status",
                label: "Status",
                value: device?.status || "available",
                options: [
                    { value: "available", label: "Available" },
                    { value: "not_available", label: "Not Available" },
                ],
            }),
        ],
    };
}

function requestActionFormConfig(request, action) {
    if (action === "reject") {
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

    return {
        kind: "resolve-request",
        recordId: request.id,
        title: "Resolve Device Request",
        submitLabel: "Mark as Resolved",
        fields: [
            `
            <div class="col-12">
                <label class="form-label asse-modal-label">Resolution Notes</label>
                <textarea class="form-control" name="notes" rows="4" required placeholder="Describe how the issue was resolved."></textarea>
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
        if (state.activeForm.kind === "create-head-office" || state.activeForm.kind === "edit-head-office") {
            const payload = { name: formData.get("name") };
            if (state.activeForm.recordId) {
                await apiRequest(`/head-offices/${state.activeForm.recordId}/`, { method: "PATCH", body: payload });
            } else {
                await apiRequest("/head-offices/", { method: "POST", body: payload });
            }
        }

        if (state.activeForm.kind === "create-manager" || state.activeForm.kind === "edit-manager") {
            const userPayload = {
                email: formData.get("email"),
                role: "head_office_manager",
                is_active: formData.get("is_active") === "true",
            };
            const password = formData.get("password");
            if (password) userPayload.password = password;

            const payload = {
                user: userPayload,
                branch: null,
                head_office: Number(formData.get("head_office")),
                first_name: formData.get("first_name"),
                last_name: formData.get("last_name"),
                phone: formData.get("phone"),
                position: formData.get("position"),
                department: formData.get("department"),
                hire_date: formData.get("hire_date"),
                is_active: formData.get("is_active") === "true",
            };

            if (state.activeForm.recordId) {
                await apiRequest(`/employees/${state.activeForm.recordId}/`, { method: "PATCH", body: payload });
            } else {
                await apiRequest("/employees/", { method: "POST", body: payload });
            }
        }

        if (state.activeForm.kind === "create-branch" || state.activeForm.kind === "edit-branch") {
            const branchPayload = {
                name: formData.get("name"),
                head_office: Number(formData.get("head_office")),
            };
            let branch;
            if (state.activeForm.recordId) {
                branch = await apiRequest(`/branches/${state.activeForm.recordId}/`, { method: "PATCH", body: branchPayload });
            } else {
                branch = await apiRequest("/branches/", { method: "POST", body: branchPayload });
            }

            const managerId = formData.get("manager");
            await apiRequest(`/branches/${branch.id}/assign_manager/`, {
                method: "POST",
                body: { manager: managerId ? Number(managerId) : null },
            });
        }

        if (state.activeForm.kind === "create-device" || state.activeForm.kind === "edit-device") {
            const payload = {
                name: formData.get("name"),
                device_type: formData.get("device_type"),
                branch: formData.get("branch") ? Number(formData.get("branch")) : null,
                serial_number: formData.get("serial_number"),
                brand: formData.get("brand"),
                model: formData.get("model"),
                purchase_date: formData.get("purchase_date") || null,
                status: formData.get("status"),
            };

            if (state.activeForm.recordId) {
                await apiRequest(`/devices/${state.activeForm.recordId}/`, { method: "PATCH", body: payload });
            } else {
                await apiRequest("/devices/", { method: "POST", body: payload });
            }
        }

        if (state.activeForm.kind === "reject-request") {
            await apiRequest(`/requests/${state.activeForm.recordId}/reject/`, {
                method: "POST",
                body: { reason: formData.get("reason") },
            });
        }

        if (state.activeForm.kind === "resolve-request") {
            await apiRequest(`/requests/${state.activeForm.recordId}/resolve/`, {
                method: "POST",
                body: { notes: formData.get("notes") },
            });
        }

        showAlert(elements.entityFormFeedback, "Saved successfully.", "success");
        await loadData();
        renderAll();
        window.setTimeout(() => entityModal.hide(), 350);
    } catch (error) {
        showAlert(elements.entityFormFeedback, error.message, "danger");
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
        showAlert(elements.confirmFeedback, error.message, "danger");
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

        if (action === "view-head-office") {
            const office = state.headOffices.find((item) => item.id === id);
            openViewModal("Head Office Details", [
                { label: "Name", value: office.name },
                { label: "Created", value: formatDateTime(office.created_at) },
                { label: "Branches", value: state.branches.filter((branch) => branch.head_office === office.id).length },
            ]);
        }
        if (action === "edit-head-office") {
            openFormModal(headOfficeFormConfig(state.headOffices.find((item) => item.id === id)));
        }
        if (action === "delete-head-office") {
            openConfirmModal("Are you sure you want to delete this head office?", async () => {
                await apiRequest(`/head-offices/${id}/`, { method: "DELETE" });
            });
        }

        if (action === "view-manager") {
            const manager = state.managers.find((item) => item.id === id);
            openViewModal("Head Office Manager Details", [
                { label: "Name", value: manager.full_name },
                { label: "Email", value: manager.user.email },
                { label: "Head Office", value: manager.head_office_detail?.name || "Not assigned" },
                { label: "Position", value: manager.position },
                { label: "Department", value: manager.department },
            ]);
        }
        if (action === "edit-manager") {
            openFormModal(managerFormConfig(state.managers.find((item) => item.id === id)));
        }
        if (action === "delete-manager") {
            openConfirmModal("Are you sure you want to delete this head office manager?", async () => {
                await apiRequest(`/employees/${id}/`, { method: "DELETE" });
            });
        }

        if (action === "view-branch") {
            const branch = state.branches.find((item) => item.id === id);
            openViewModal("Branch Details", [
                { label: "Branch", value: branch.name },
                { label: "Head Office", value: branch.head_office_detail?.name || "N/A" },
                { label: "Manager", value: branch.manager_detail?.full_name || "Not assigned" },
                { label: "Created", value: formatDateTime(branch.created_at) },
            ]);
        }
        if (action === "edit-branch") {
            openFormModal(branchFormConfig(state.branches.find((item) => item.id === id)));
        }
        if (action === "delete-branch") {
            openConfirmModal("Are you sure you want to delete this branch?", async () => {
                await apiRequest(`/branches/${id}/`, { method: "DELETE" });
            });
        }

        if (action === "view-device") {
            const device = state.devices.find((item) => item.id === id);
            openViewModal("Device Details", [
                { label: "Device", value: device.name },
                { label: "Serial Number", value: device.serial_number },
                { label: "Branch", value: device.branch_detail?.name || "Unassigned" },
                { label: "Status", value: humanizeStatus(device.status) },
                { label: "Model", value: device.model || "N/A" },
            ]);
        }
        if (action === "edit-device") {
            openFormModal(deviceFormConfig(state.devices.find((item) => item.id === id)));
        }
        if (action === "delete-device") {
            openConfirmModal("Are you sure you want to delete this device?", async () => {
                await apiRequest(`/devices/${id}/`, { method: "DELETE" });
            });
        }

        if (action === "view-request") {
            renderRequestDetail(id);
            document.getElementById("requests")?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        if (action === "approve-request") {
            openConfirmModal("Approve this request at head office level?", async () => {
                await apiRequest(`/requests/${id}/approve_head_office/`, { method: "POST", body: {} });
            });
        }
        if (action === "reject-request") {
            openFormModal(requestActionFormConfig(state.requests.find((item) => item.id === id), "reject"));
        }
        if (action === "resolve-request") {
            openFormModal(requestActionFormConfig(state.requests.find((item) => item.id === id), "resolve"));
        }
    });
}

async function handleLogout(event) {
    event.preventDefault();
    await logout();
    window.location.href = "/login/";
}

function wireSearch() {
    [
        elements.headOfficeSearchInput,
        elements.managerSearchInput,
        elements.branchSearchInput,
        elements.deviceSearchInput,
        elements.requestSearchInput,
    ]
        .filter(Boolean)
        .forEach((input) =>
            input.addEventListener("input", () => {
                if (input === elements.headOfficeSearchInput) {
                    state.headOfficePage = 1;
                }
                renderAll();
            })
        );
}

function wirePagination() {
    elements.headOfficePagination?.addEventListener("click", (event) => {
        const link = event.target.closest("[data-head-office-page]");
        if (!link || link.classList.contains("disabled")) {
            return;
        }

        event.preventDefault();
        const requestedPage = Number(link.dataset.headOfficePage);
        if (!Number.isFinite(requestedPage) || requestedPage < 1) {
            return;
        }

        state.headOfficePage = requestedPage;
        renderHeadOffices();
    });
}

function wireCreateButtons() {
    document.getElementById("createHeadOfficeButton")?.addEventListener("click", () => openFormModal(headOfficeFormConfig()));
    document.getElementById("createManagerButton")?.addEventListener("click", () => openFormModal(managerFormConfig()));
    document.getElementById("registerManagerButton")?.addEventListener("click", () => openFormModal(managerFormConfig()));
    document.getElementById("createBranchButton")?.addEventListener("click", () => openFormModal(branchFormConfig()));
    document.getElementById("createDeviceButton")?.addEventListener("click", () => openFormModal(deviceFormConfig()));
}

async function initializeConsole() {
    hideAlert(elements.headOfficeConsoleFeedback);
    await ensureHeadOfficeSession();
    await loadData();
    renderAll();
    wireSearch();
    wirePagination();
    wireCreateButtons();
    bindActionDelegation();
}

elements.entityForm?.addEventListener("submit", submitEntityForm);
elements.confirmActionButton?.addEventListener("click", runConfirmAction);
elements.refreshConsoleButton?.addEventListener("click", async () => {
    hideAlert(elements.headOfficeConsoleFeedback);
    try {
        await loadData();
        renderAll();
    } catch (error) {
        showAlert(elements.headOfficeConsoleFeedback, error.message || "Unable to refresh dashboard data.", "danger");
    }
});
elements.pageLogoutButton?.addEventListener("click", handleLogout);

initializeConsole().catch((error) => {
    showAlert(
        elements.headOfficeConsoleFeedback,
        error.message || "Unable to load the head office dashboard right now.",
        "danger",
    );
});

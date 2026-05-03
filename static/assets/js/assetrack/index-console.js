import { apiRequest } from "./api.js";

function createPlaceholderRow() {
    return `
        <tr>
            <td>No active project remainders found.</td>
            <td>—</td>
            <td>—</td>
            <td>—</td>
            <td class="text-end"><span class="badge bg-secondary">No data</span></td>
        </tr>
    `;
}

function formatProjectRow(item) {
    return `
        <tr>
            <td>${item.name}</td>
            <td><span class="badge bg-${item.status === 'Completed' ? 'success' : item.status === 'In Progress' ? 'warning' : 'secondary'}">${item.status}</span></td>
            <td>${item.remaining_days ?? 'TBD'}</td>
            <td>${item.stage ?? 'Planning'}</td>
            <td class="text-end"><a href="javascript:void(0);" class="btn btn-sm btn-outline-primary">View</a></td>
        </tr>
    `;
}

async function loadDashboard() {
    const tableBody = document.getElementById("projectRemaindersTable");
    if (!tableBody || tableBody.children.length) {
        return;
    }

    tableBody.innerHTML = createPlaceholderRow();

    try {
        const user = await apiRequest("/auth/me/");

        const placeholderItems = [
            {
                name: `Welcome back, ${user.employee?.full_name || user.email}`,
                status: "Active",
                remaining_days: 12,
                stage: "Review",
            },
            {
                name: "Device inventory audit",
                status: "In Progress",
                remaining_days: 8,
                stage: "Approval",
            },
            {
                name: "Branch performance review",
                status: "Pending",
                remaining_days: 3,
                stage: "Scheduling",
            },
        ];

        tableBody.innerHTML = placeholderItems.map(formatProjectRow).join("");
    } catch (error) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-danger">Unable to load dashboard items.</td>
            </tr>
        `;
        console.error(error);
    }
}

loadDashboard();

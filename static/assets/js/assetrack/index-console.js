import { apiRequest } from "./api.js";

let dashboardChart = null;

function initChart(stats) {
    const ctx = document.getElementById("social-radar-chart");
    if (!ctx) return;
    
    const chartData = Object.entries(stats.data).map(([key, value]) => ({
        label: key.replace(/_/g, " ").replace(/\b\w/g, char => char.toUpperCase()),
        value
    }));
    
    if (dashboardChart) {
        dashboardChart.destroy();
    }
    
    dashboardChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: chartData.map(d => d.label),
            datasets: [{
                label: 'Count',
                data: chartData.map(d => d.value),
                backgroundColor: [
                    '#4F46E5', '#7C3AED', '#EC4899', '#F59E0B',
                    '#10B981', '#3B82F6', '#8B5CF6', '#EF4444'
                ],
                borderColor: '#ffffff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: `${stats.role.replace(/_/g, " ").toUpperCase()} Dashboard`
                }
            }
        }
    });
}

async function loadDashboard() {
    try {
        const stats = await apiRequest("/auth/dashboard-stats/");
        initChart(stats);
    } catch (error) {
        console.error("Failed to load dashboard:", error);
    }
}

loadDashboard();

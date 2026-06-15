// --- GLOBAL AUTH & SESSION GUARD ---
function checkAuth() {
    const userData = localStorage.getItem('user');
    const path = window.location.pathname;

    // 1. Redirect if not logged in (unless on login/register pages)
    if (!userData) {
        if (!path.includes('login.html') && !path.includes('register.html')) {
            window.location.href = 'login.html';
        }
        return;
    }

    const user = JSON.parse(userData);

    // 2. Protect Admin Page from non-admins
    if (path.includes('admin.html') && !user.is_admin) {
        window.location.href = 'dashboard.html';
        return;
    }

    // 3. Populate Global Account UI (Widget & Nav Tabs)
    if (user) {
        const nameEl = document.getElementById('user-name-display');
        const roleEl = document.getElementById('user-role-badge');
        const adminTab = document.getElementById('admin-nav-tab'); // The tab in the bar
        const navDash = document.getElementById('nav-dash');
        const navSim = document.getElementById('nav-sim');

        // Fill in name and role
        if (nameEl) nameEl.innerText = user.full_name;
        if (roleEl) {
            roleEl.innerText = user.is_admin ? 'ADMIN' : 'STAFF';
            roleEl.className = user.is_admin 
                ? "px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-[9px] font-bold border border-indigo-200"
                : "px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-[9px] font-bold border border-slate-200";
        }
        
        // Show Admin Tab only for Admins
        if (adminTab && user.is_admin) {
            adminTab.classList.remove('hidden');
        }

        // Highlight Active Tab based on URL
        if (path.includes('dashboard.html') && navDash) navDash.classList.add('bg-indigo-50', 'text-indigo-700');
        if (path.includes('simulator.html') && navSim) navSim.classList.add('bg-indigo-50', 'text-indigo-700');
        if (path.includes('admin.html') && adminTab) adminTab.classList.add('bg-indigo-50', 'text-indigo-700');
    }
}

function handleLogout() {
    localStorage.removeItem('user');
    window.location.href = 'login.html';
}

// Run check immediately on every page load
document.addEventListener('DOMContentLoaded', checkAuth);
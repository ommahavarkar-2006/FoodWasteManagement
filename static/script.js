function calculateImpact() {
    const weekly = parseFloat(document.getElementById('wasteAmount').value);
    const annual = weekly * 52;
    document.getElementById('annualWaste').textContent = annual;
    document.getElementById('moneySaved').textContent = '₹' + (annual * 150);
    document.getElementById('co2Impact').textContent = annual * 2.5;
    document.getElementById('mealsEquiv').textContent = annual * 3;
    document.getElementById('results').style.display = 'block';
}

function toggleMenu() {
    document.querySelector('.nav-menu').classList.toggle('open');
}

// Toggle login dropdown
const loginBtn = document.querySelector('.btn-secondary');
if (loginBtn) {
    loginBtn.addEventListener('click', function(e) {
        e.preventDefault();
        const dropdown = document.querySelector('.dropdown-login');
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    });
}

// Close dropdown when clicking elsewhere
window.addEventListener('click', function(e) {
    if (!loginBtn.contains(e.target) && !document.querySelector('.dropdown-login').contains(e.target)) {
        document.querySelector('.dropdown-login').style.display = 'none';
    }
});

function openModal(id) { document.getElementById(id).style.display = "flex"; }
function closeModal(id) { document.getElementById(id).style.display = "none"; }

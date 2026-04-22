function filterMatches() {
    const val = document.getElementById('league-filter').value;
    document.querySelectorAll('.match-card').forEach(card => {
        const link = card.closest('a');
        if (link) {
            link.style.display = val === 'all' || card.dataset.league === val ? '' : 'none';
        }
    });
}

function convertDatesToLocal() {
    document.querySelectorAll('[data-utc]').forEach(el => {
        const matchDate = new Date(el.getAttribute('data-utc'));
        const now = new Date();
        const diff = matchDate - now;
        const oneDayMs = 24 * 60 * 60 * 1000;

        if (diff > 0 && diff <= oneDayMs) {
            el.setAttribute('data-countdown', 'true');
        } else if (diff <= 0) {

        } else {
            el.textContent = matchDate.toLocaleString(navigator.language, {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    });
}

function updateCountdowns() {
    document.querySelectorAll('[data-countdown="true"]').forEach(el => {
        const matchDate = new Date(el.getAttribute('data-utc'));
        const now = new Date();
        const diff = matchDate - now;

        if (diff <= 0) {
            el.removeAttribute('data-countdown');
            el.textContent = ''; 
            el.innerHTML = '<span style="background: #f44336; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; animation: pulse 1s infinite;">LIVE</span>';
            return;
        }

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        el.textContent = `${hours}h ${minutes}m ${seconds}s`;
    });
}

document.addEventListener('DOMContentLoaded', convertDatesToLocal);
setInterval(updateCountdowns, 1000);

function openShareModal(matchId) {
    const url = `${window.location.origin}/match/${matchId}`;
    document.getElementById('share-link-input').value = url;
    document.getElementById('share-modal-overlay').classList.add('active');
}

function closeShareModal() {
    document.getElementById('share-modal-overlay').classList.remove('active');
}

function copyShareLink() {
    const input = document.getElementById('share-link-input');
    navigator.clipboard.writeText(input.value).then(() => {
        const btn = document.querySelector('.share-copy-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy', 2000);
    });
}
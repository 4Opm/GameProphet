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
    document.querySelectorAll('.date, .time').forEach(el => {
        el.style.display = 'none';
    });

    document.querySelectorAll('[data-utc]').forEach(el => {
        const utc = el.getAttribute('data-utc');
        const date = new Date(utc);
        el.textContent = date.toLocaleString(navigator.language, {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    });
}

document.addEventListener('DOMContentLoaded', convertDatesToLocal);

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
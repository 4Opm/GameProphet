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
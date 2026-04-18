function filterMatches() {
    const val = document.getElementById('league-filter').value;
    document.querySelectorAll('.match-card').forEach(card => {
        const link = card.closest('a');
        if (link) {
            link.style.display = val === 'all' || card.dataset.league === val ? '' : 'none';
        }
    });
}
function filterMatches() {
    const val = document.getElementById('league-filter').value;
    document.querySelectorAll('.match-card').forEach(card => {
        card.parentElement.style.display = val === 'all' || card.dataset.league === val ? '' : 'none';
    });
}
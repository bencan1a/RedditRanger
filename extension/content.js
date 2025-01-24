// Cache for user scores to avoid repeated API calls
const userScoreCache = new Map();

async function analyzeUser(username) {
    if (userScoreCache.has(username)) {
        return userScoreCache.get(username);
    }

    try {
        const response = await fetch(`http://localhost:5001/analyze/${username}`);
        const data = await response.json();
        userScoreCache.set(username, data);
        return data;
    } catch (error) {
        console.error(`Error analyzing user ${username}:`, error);
        return null;
    }
}

function createScoreBadge(score) {
    const badge = document.createElement('span');
    badge.className = `user-score-badge ${score > 70 ? 'high-risk' : score > 40 ? 'medium-risk' : 'low-risk'}`;
    badge.textContent = `${Math.round(score)}% sus`;
    return badge;
}

function addScoresToPage() {
    // Find all username links on the page
    const userLinks = document.querySelectorAll('a[href^="/user/"]');

    userLinks.forEach(async (link) => {
        const username = link.href.split('/user/')[1].split('/')[0];
        if (!username || link.querySelector('.user-score-badge')) return;

        const analysis = await analyzeUser(username);
        if (analysis) {
            const badge = createScoreBadge(analysis.probability);
            link.appendChild(badge);
        }
    });
}

// Initial load
addScoresToPage();

// Monitor for new content (e.g., when loading more comments)
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.addedNodes.length) {
            addScoresToPage();
        }
    });
});

observer.observe(document.body, { childList: true, subtree: true });
// Cache for user scores to avoid repeated API calls
const userScoreCache = new Map();
const CACHE_DURATION = 30 * 60 * 1000; // 30 minutes

async function analyzeUser(username) {
    const now = Date.now();
    const cached = userScoreCache.get(username);

    if (cached && (now - cached.timestamp) < CACHE_DURATION) {
        return cached.data;
    }

    try {
        const response = await fetch(`http://localhost:5001/analyze/${username}`);
        const data = await response.json();
        userScoreCache.set(username, {
            data,
            timestamp: now
        });
        return data;
    } catch (error) {
        console.error(`Error analyzing user ${username}:`, error);
        return null;
    }
}

function formatScore(score) {
    return (score * 100).toFixed(0);
}

function createScoreBadge(analysis) {
    const probability = analysis.probability;
    const badge = document.createElement('span');
    const riskLevel = probability > 70 ? 'high-risk' : probability > 40 ? 'medium-risk' : 'low-risk';
    badge.className = `user-score-badge ${riskLevel}`;

    // Create main score display
    const scoreText = document.createElement('span');
    scoreText.textContent = `${probability.toFixed(0)}% risk`;
    badge.appendChild(scoreText);

    // Create tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'user-score-tooltip';

    // Account Info
    const accountInfo = document.createElement('div');
    accountInfo.className = 'tooltip-section';
    accountInfo.innerHTML = `
        <div class="tooltip-title">Account Info</div>
        <div class="score-metric">
            <span>Created:</span>
            <span>${analysis.summary.account_age}</span>
        </div>
        <div class="score-metric">
            <span>Karma:</span>
            <span>${analysis.summary.karma.toLocaleString()}</span>
        </div>
    `;
    tooltip.appendChild(accountInfo);

    // Detailed Scores
    const scoresSection = document.createElement('div');
    scoresSection.className = 'tooltip-section';
    scoresSection.innerHTML = `
        <div class="tooltip-title">Analysis Scores</div>
        ${Object.entries(analysis.summary.scores).map(([key, value]) => `
            <div class="score-metric">
                <span>${key.replace('_score', '')}:</span>
                <span>${formatScore(value)}%</span>
            </div>
        `).join('')}
    `;
    tooltip.appendChild(scoresSection);

    badge.appendChild(tooltip);
    return badge;
}

async function addScoresToPage() {
    // Find all username links on the page
    const userLinks = document.querySelectorAll('a[href^="/user/"]');

    userLinks.forEach(async (link) => {
        const username = link.href.split('/user/')[1].split('/')[0];
        if (!username || link.querySelector('.user-score-badge')) return;

        const analysis = await analyzeUser(username);
        if (analysis) {
            const badge = createScoreBadge(analysis);
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

// Clean up old cache entries periodically
setInterval(() => {
    const now = Date.now();
    for (const [username, cache] of userScoreCache.entries()) {
        if (now - cache.timestamp > CACHE_DURATION) {
            userScoreCache.delete(username);
        }
    }
}, 5 * 60 * 1000); // Clean every 5 minutes
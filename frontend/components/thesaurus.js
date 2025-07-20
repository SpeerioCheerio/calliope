// Thesaurus Component
import { showLoading, hideLoading, showToast, apiCall, getSentimentIcon } from '../utils.js';

export async function findSynonyms() {
    const thesaurusInput = document.getElementById('thesaurus-input');
    const word = thesaurusInput.value.trim();
    
    if (!word) {
        showToast('Please enter a word to find synonyms', 'warning');
        return;
    }
    
    const searchButton = document.getElementById('thesaurus-search-btn');
    searchButton.disabled = true;
    searchButton.textContent = 'Searching...';
    
    try {
        const data = await apiCall('/thesaurus', {
            method: 'POST',
            body: JSON.stringify({ word })
        });
        displayThesaurusResults(data);
    } catch (error) {
        const resultsContainer = document.getElementById('thesaurus-results');
        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = `
            <div class="error-message">
                <p>Failed to find synonyms. Please try again.</p>
            </div>
        `;
    } finally {
        searchButton.disabled = false;
        searchButton.textContent = 'Find Synonyms';
    }
}

function displayThesaurusResults(data) {
    const resultsContainer = document.getElementById('thesaurus-results');
    
    // Show the results container
    resultsContainer.style.display = 'block';
    
    if (data.synonyms.length === 0) {
        resultsContainer.innerHTML = `
            <div class="no-results">
                <p>No synonyms found for "${data.word}" in your vocabulary.</p>
            </div>
        `;
        return;
    }
    
    resultsContainer.innerHTML = `
        <div class="thesaurus-results-header">
            <h3>Synonyms for "${data.word}" (${data.synonyms.length} found)</h3>
        </div>
        <div class="thesaurus-grid">
            ${data.synonyms.map(synonym => `
                <div class="word-card rarity-${synonym.rarity}">
                    <div class="word-header">
                        <span class="word-title">${synonym.word}</span>
                        <div class="word-header-right">
                            <span class="word-pos">${synonym.pos}</span>
                        </div>
                    </div>
                    <div class="word-definition">${synonym.definition}</div>
                    <div class="word-example">"${synonym.example_sentence}"</div>
                    <div class="word-badges">
                        <span class="rarity-badge rarity-${synonym.rarity}">${synonym.rarity}</span>
                        <span class="sentiment-badge">${getSentimentIcon(synonym.sentiment)} ${synonym.sentiment}</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

// Setup event listeners
export function setupThesaurusEventListeners() {
    const thesaurusBtn = document.getElementById('thesaurus-search-btn');
    const thesaurusInput = document.getElementById('thesaurus-input');
    
    if (thesaurusBtn) {
        thesaurusBtn.addEventListener('click', findSynonyms);
    }
    
    if (thesaurusInput) {
        thesaurusInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                findSynonyms();
            }
        });
        
        // Focus the input when the page loads
        thesaurusInput.focus();
    }
} 
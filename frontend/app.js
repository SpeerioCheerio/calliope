// Calliope Vocabulary App - Main Application Controller
import { showLoading, hideLoading, showToast, apiCall, getSentimentIcon } from './utils.js';

// Import all components
import { setupAddWordEventListeners } from './components/addWord.js';
import { setupDatabaseEventListeners } from './components/viewDatabase.js';
import { setupThesaurusEventListeners } from './components/thesaurus.js';
import { setupPredictionEventListeners } from './components/prediction.js';
import { setupFlashcardsEventListeners } from './components/flashcards.js';
import { setupParagraphAnalyzerEventListeners } from './components/paragraphAnalyzer.js';

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Calliope app initializing...');
    
    // Load initial content
    loadWordOfTheDay();
    loadPartsOfSpeech();
    
    // Setup all event listeners
    setupEventListeners();
    
    // Setup keyboard shortcuts
    setupKeyboardShortcuts();
    
    // Make navigation functions global for onclick handlers
    setupGlobalNavigation();
});

// Page Navigation Functions
function openPage(pageName) {
    const overlay = document.getElementById('page-overlay');
    const content = document.getElementById('page-content');
    const pageContainer = document.querySelector('.page-container');
    
    // Remove any previous page-specific classes
    pageContainer.classList.remove('analyzer-container');
    
    // Show loading
    content.innerHTML = '<div class="loading">Loading...</div>';
    overlay.classList.add('active');
    
    // Load page content based on page name
    switch(pageName) {
        case 'add-word':
            loadAddWordPage();
            break;
        case 'database':
            loadDatabasePage();
            break;
        case 'thesaurus':
            loadThesaurusPage();
            break;
        case 'prediction':
            loadPredictionPage();
            break;
        case 'flashcards':
            loadFlashcardsPage();
            break;
        case 'analyzer':
            loadAnalyzerPage();
            break;
        case 'stats':
            loadStatsPage();
            break;
        default:
            content.innerHTML = '<div class="error-message">Page not found</div>';
    }
}

function closePage() {
    const overlay = document.getElementById('page-overlay');
    const pageContainer = document.querySelector('.page-container');
    
    // Remove any page-specific classes
    pageContainer.classList.remove('analyzer-container');
    
    overlay.classList.remove('active');
}

// Make navigation functions available globally
function setupGlobalNavigation() {
    window.openPage = openPage;
    window.closePage = closePage;
}

// Word of the Day
async function loadWordOfTheDay() {
    try {
        const data = await apiCall('/word-of-the-day');
        displayWordOfTheDay(data.word_data);
    } catch (error) {
        document.getElementById('wotd-card').innerHTML = `
            <div class="wotd-error">
                <p>Unable to load Word of the Day</p>
                <button onclick="loadWordOfTheDay()">Retry</button>
            </div>
        `;
    }
}

function displayWordOfTheDay(wordData) {
    const wotdCard = document.getElementById('wotd-card');
    
    // Add rarity class to the card element
    wotdCard.className = `wotd-card rarity-${wordData.rarity}`;
    
    wotdCard.innerHTML = `
        <div class="wotd-word">${wordData.word}</div>
        <div class="wotd-pos">${wordData.pos}</div>
        <div class="wotd-definition">${wordData.definition}</div>
        <div class="wotd-example">"${wordData.example_sentence}"</div>
        <div class="wotd-badges">
            <span class="badge rarity-${wordData.rarity}">${wordData.rarity.toUpperCase()}</span>
            <span class="badge">${getSentimentIcon(wordData.sentiment)} ${wordData.sentiment}</span>
        </div>
    `;
}

// Page Loading Functions
async function loadAddWordPage() {
    const content = document.getElementById('page-content');
    
    content.innerHTML = `
        <h1>Add New Word</h1>
        <input type="text" id="word-input" placeholder="Enter a word..." maxlength="100">
        <button id="add-word-btn">Add Word</button>
        <div id="add-word-result"></div>
    `;
    
    // Setup event listeners for this page
    setupAddWordEventListeners();
}

async function loadDatabasePage() {
    const content = document.getElementById('page-content');
    
    content.innerHTML = `
        <h1>Database</h1>
        <div class="database-controls">
            <div class="controls-row">
                <div class="search-container">
                    <input type="search" id="word-search" placeholder="Search words..." autocomplete="off">
                    <div id="autocomplete-results" class="autocomplete-results"></div>
                </div>
                <select id="pos-filter">
                    <option value="">All Parts of Speech</option>
                </select>
                <select id="rarity-filter">
                    <option value="">All Rarities</option>
                    <option value="notty">Common Advanced (Notty)</option>
                    <option value="luke">Less Common (Luke)</option>
                    <option value="alex">Rare/Archaic (Alex)</option>
                </select>
                <select id="sentiment-filter">
                    <option value="">All Sentiments</option>
                    <option value="positive">Positive</option>
                    <option value="negative">Negative</option>
                    <option value="neutral">Neutral</option>
                    <option value="formal">Formal</option>
                </select>
                <button id="reset-filters-btn">Reset</button>
            </div>
        </div>
        <div class="pagination">
            <div class="pagination-controls">
                <button id="prev-btn">Previous</button>
                <span id="page-info">Page 1 of 1</span>
                <button id="next-btn">Next</button>
            </div>
            <div class="pagination-settings">
                <label for="items-per-page">Show:</label>
                <select id="items-per-page">
                    <option value="10">10 per page</option>
                    <option value="20">20 per page</option>
                    <option value="40">40 per page</option>
                    <option value="50">50 per page</option>
                </select>
            </div>
        </div>
        <div id="words-grid"></div>
    `;
    
    // Setup event listeners using the component
    setupDatabaseEventListeners();
}

async function loadThesaurusPage() {
    const content = document.getElementById('page-content');
    
    content.innerHTML = `
        <h1>Thesaurus</h1>
        <input type="text" id="thesaurus-input" placeholder="Enter a word to find synonyms...">
        <button id="thesaurus-search-btn">Find Synonyms</button>
        <div id="thesaurus-results" style="display: none;"></div>
    `;
    
    setupThesaurusEventListeners();
}

async function loadPredictionPage() {
    const content = document.getElementById('page-content');
    
    content.innerHTML = `
        <h1>Word Prediction</h1>
        <textarea id="sentence-input" placeholder="Enter a sentence with an underscore (_) where you want word suggestions..."></textarea>
        <div class="prediction-controls">
            <select id="sentiment-filter">
                <option value="">All Sentiments (Optional)</option>
                <option value="positive">Positive</option>
                <option value="negative">Negative</option>
                <option value="neutral">Neutral</option>
                <option value="formal">Formal</option>
            </select>
            <button id="predict-btn">Predict Words</button>
        </div>
        <div id="prediction-results" style="display: none;"></div>
    `;
    
    setupPredictionEventListeners();
}

async function loadFlashcardsPage() {
    const content = document.getElementById('page-content');
    
    content.innerHTML = `
        <h1>Flashcards</h1>
        <div class="database-controls">
            <div class="controls-row">
                <select id="flashcard-pos-filter">
                    <option value="">All Parts of Speech</option>
                </select>
                <select id="flashcard-rarity-filter">
                    <option value="">All Rarities</option>
                    <option value="notty">Common Advanced (Notty)</option>
                    <option value="luke">Less Common (Luke)</option>
                    <option value="alex">Rare/Archaic (Alex)</option>
                </select>
                <select id="flashcard-sentiment-filter">
                    <option value="">All Sentiments</option>
                    <option value="positive">Positive</option>
                    <option value="negative">Negative</option>
                    <option value="neutral">Neutral</option>
                    <option value="formal">Formal</option>
                </select>
                <select id="flashcard-count-filter">
                    <option value="">All Available</option>
                    <option value="10">Last 10</option>
                    <option value="20">Last 20</option>
                    <option value="30">Last 30</option>
                    <option value="40">Last 40</option>
                    <option value="50">Last 50</option>
                    <option value="100">Last 100</option>
                </select>
                <button id="load-flashcards-btn">Start Practice</button>
                <button id="shuffle-flashcards-btn">Shuffle</button>
            </div>
        </div>
        <div id="flashcard-container">
            <div class="loading">Click "Start Practice" to begin</div>
        </div>
    `;
    
    // Use setTimeout to ensure DOM is ready before attaching event listeners
    setTimeout(() => {
    setupFlashcardsEventListeners();
    }, 0);
}

async function loadAnalyzerPage() {
    const content = document.getElementById('page-content');
    const pageContainer = document.querySelector('.page-container');
    
    // Add analyzer-specific class to page container
    pageContainer.classList.add('analyzer-container');
    
    content.innerHTML = `
        <h1>Paragraph Analyzer</h1>
        <div id="paragraph-input" 
             contenteditable="true" 
             placeholder="Paste your paragraph here..." 
             data-placeholder="Enter your paragraph here to analyze and enhance vocabulary words. The analyzer will identify simple words that can be upgraded with more sophisticated alternatives from your vocabulary database. Click on highlighted words to see enhancement options."></div>
        <button id="analyze-btn">Analyze Paragraph</button>
        <div id="analysis-results" style="display: none;"></div>
    `;
    
    setupParagraphAnalyzerEventListeners();
}

async function loadStatsPage() {
    const content = document.getElementById('page-content');
    
    content.innerHTML = `
        <h1>Database Statistics</h1>
        <div id="stats-content">
            <div class="loading">Loading statistics...</div>
        </div>
    `;
    
    await loadStats();
}

// Statistics
async function loadStats() {
    try {
        const data = await apiCall('/stats');
        displayStats(data);
    } catch (error) {
        document.getElementById('stats-content').innerHTML = `
            <div class="error-message">
                <p>Failed to load statistics. Please try again.</p>
            </div>
        `;
    }
}

function displayStats(stats) {
    const statsContent = document.getElementById('stats-content');
    
    statsContent.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">${stats.total_words}</div>
                <div class="stat-label">Total Words</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.words_added_today}</div>
                <div class="stat-label">Added Today</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.current_streak}</div>
                <div class="stat-label">Current Streak</div>
            </div>
        </div>
        
        <div class="stats-section">
            <h3>Parts of Speech Distribution</h3>
            <div class="pos-stats">
                ${Object.entries(stats.pos_distribution).map(([pos, count]) => `
                    <div class="pos-stat">
                        <span class="pos-name">${pos}</span>
                        <span class="pos-count">${count}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div class="stats-section">
            <h3>Rarity Distribution</h3>
            <div class="rarity-stats">
                ${Object.entries(stats.rarity_distribution).map(([rarity, count]) => `
                    <div class="rarity-stat">
                        <span class="rarity-badge rarity-${rarity}">${rarity}</span>
                        <span class="rarity-count">${count}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div class="stats-section">
            <h3>Sentiment Distribution</h3>
            <div class="sentiment-stats">
                ${Object.entries(stats.sentiment_distribution).map(([sentiment, count]) => `
                    <div class="sentiment-stat">
                        <span class="sentiment-badge">${getSentimentIcon(sentiment)} ${sentiment}</span>
                        <span class="sentiment-count">${count}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// Load Parts of Speech for filters
async function loadPartsOfSpeech() {
    try {
        const data = await apiCall('/parts-of-speech');
        populateSelectOptions('pos-filter', data.parts_of_speech);
    } catch (error) {
        console.warn('Failed to load parts of speech:', error);
    }
}

function populateSelectOptions(selectId, options) {
    const select = document.getElementById(selectId);
    if (select) {
        select.innerHTML = '<option value="">All</option>';
        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option;
            optionElement.textContent = option.charAt(0).toUpperCase() + option.slice(1);
            select.appendChild(optionElement);
        });
    }
}

// Setup all event listeners
function setupEventListeners() {
    // Close page when clicking outside content
    document.getElementById('page-overlay').addEventListener('click', function(e) {
        if (e.target === this) {
            closePage();
        }
    });
    
    // Close page with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePage();
        }
    });
}

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Only process shortcuts when not in an input field and no page is open
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || 
            document.getElementById('page-overlay').classList.contains('active')) {
            return;
        }
        
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 'a':
                    e.preventDefault();
                    openPage('add-word');
                    break;
                case 'd':
                    e.preventDefault();
                    openPage('database');
                    break;
                case 't':
                    e.preventDefault();
                    openPage('thesaurus');
                    break;
                case 'p':
                    e.preventDefault();
                    openPage('prediction');
                    break;
                case 'f':
                    e.preventDefault();
                    openPage('flashcards');
                    break;
                case 'r':
                    e.preventDefault();
                    openPage('analyzer');
                    break;
                case 's':
                    e.preventDefault();
                    openPage('stats');
                    break;
            }
        }
    });
} 
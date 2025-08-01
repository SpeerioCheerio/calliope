// Flashcards Component
import { showLoading, hideLoading, showToast, apiCall, getSentimentIcon, shuffleArray } from '../utils.js';

let flashcards = [];
let currentFlashcardIndex = 0;
let isFlashcardFlipped = false;

export async function loadFlashcards() {
    const posFilter = document.getElementById('flashcard-pos-filter').value;
    const rarityFilter = document.getElementById('flashcard-rarity-filter').value;
    const sentimentFilter = document.getElementById('flashcard-sentiment-filter').value;
    const countFilter = document.getElementById('flashcard-count-filter').value;
    
    const params = new URLSearchParams({
        limit: countFilter || 500 // If no count filter, use high limit for randomization (backend max is 500)
    });
    
    if (posFilter) params.append('pos', posFilter);
    if (rarityFilter) params.append('rarity', rarityFilter);
    if (sentimentFilter) params.append('sentiment', sentimentFilter);
    
    try {
        const data = await apiCall(`/flashcards?${params}`);
        flashcards = data;
        currentFlashcardIndex = 0;
        isFlashcardFlipped = false;
        
        if (flashcards.length === 0) {
            document.getElementById('flashcard-container').innerHTML = `
                <div class="no-flashcards">
                    <p>No flashcards found matching your criteria.</p>
                </div>
            `;
            return;
        }
        
        displayCurrentFlashcard();
    } catch (error) {
        console.error('Error loading flashcards:', error);
        document.getElementById('flashcard-container').innerHTML = `
            <div class="error-message">
                <p>Failed to load flashcards. Please try again.</p>
            </div>
        `;
    }
}

function displayCurrentFlashcard() {
    if (flashcards.length === 0) return;
    
    const flashcard = flashcards[currentFlashcardIndex];
    const flashcardContainer = document.getElementById('flashcard-container');
    
    flashcardContainer.innerHTML = `
        <div class="flashcard-container">
            <div class="word-card rarity-${flashcard.rarity} flashcard ${isFlashcardFlipped ? 'flipped' : ''}" onclick="window.flipFlashcard()">
                <div class="word-header">
                    <span class="word-title">${flashcard.word}</span>
                    <div class="word-header-right">
                        <span class="word-pos">${flashcard.pos}</span>
                    </div>
                </div>
                <div class="word-definition ${isFlashcardFlipped ? 'visible' : 'hidden'}">${flashcard.definition}</div>
                <div class="word-example ${isFlashcardFlipped ? 'visible' : 'hidden'}">"${flashcard.example_sentence}"</div>
                <div class="word-badges">
                    <span class="rarity-badge rarity-${flashcard.rarity}">${flashcard.rarity}</span>
                    <span class="sentiment-badge">${getSentimentIcon(flashcard.sentiment)} ${flashcard.sentiment}</span>
                </div>
                <div class="flashcard-hint">
                    ${isFlashcardFlipped ? 'Click to hide definition or press Space' : 'Click to reveal definition or press Space'}
                </div>
            </div>
        </div>
        <div class="flashcard-controls">
            <button onclick="window.previousFlashcard()">← Previous</button>
            <span class="flashcard-counter">${currentFlashcardIndex + 1} / ${flashcards.length}</span>
            <button onclick="window.nextFlashcard()">Next →</button>
        </div>
        <div class="flashcard-shortcuts">
            <p><strong>Shortcuts:</strong> ← Previous | → Next | ↑/Space Flip | S Shuffle</p>
        </div>
    `;
    
    // Remove the non-existent function call
    // updateFlashcardDisplay();
}

export function flipFlashcard() {
    isFlashcardFlipped = !isFlashcardFlipped;
    displayCurrentFlashcard();
}

export function nextFlashcard() {
    if (currentFlashcardIndex < flashcards.length - 1) {
        currentFlashcardIndex++;
    } else {
        currentFlashcardIndex = 0; // Loop back to first
    }
    isFlashcardFlipped = false;
    displayCurrentFlashcard();
}

export function previousFlashcard() {
    if (currentFlashcardIndex > 0) {
        currentFlashcardIndex--;
    } else {
        currentFlashcardIndex = flashcards.length - 1; // Loop to last
    }
    isFlashcardFlipped = false;
    displayCurrentFlashcard();
}

export function shuffleFlashcards() {
    flashcards = shuffleArray(flashcards);
    currentFlashcardIndex = 0;
    isFlashcardFlipped = false;
    displayCurrentFlashcard();
    showToast('Flashcards shuffled!');
}

async function loadFlashcardFilters() {
    // Load parts of speech from the API
    try {
        const response = await apiCall('/parts-of-speech');
        const posOptions = response.parts_of_speech || [];
        
        const posFilter = document.getElementById('flashcard-pos-filter');
        if (posFilter) {
            posFilter.innerHTML = '<option value="">All Parts of Speech</option>';
            posOptions.forEach(pos => {
                const option = document.createElement('option');
                option.value = pos;
                option.textContent = pos;
                posFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading parts of speech:', error);
        // Fallback to hardcoded values
        const posOptions = ['NOUN', 'VERB', 'ADJECTIVE', 'ADVERB', 'PREPOSITION', 'CONJUNCTION', 'INTERJECTION'];
        const posFilter = document.getElementById('flashcard-pos-filter');
        if (posFilter) {
            posFilter.innerHTML = '<option value="">All Parts of Speech</option>';
            posOptions.forEach(pos => {
                const option = document.createElement('option');
                option.value = pos;
                option.textContent = pos;
                posFilter.appendChild(option);
            });
        }
    }
}

function populateSelect(selectId, options) {
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

// Setup keyboard shortcuts for flashcards
function setupFlashcardKeyboardShortcuts() {
    // Remove any existing flashcard keyboard event listeners
    if (window.flashcardKeyboardHandler) {
        document.removeEventListener('keydown', window.flashcardKeyboardHandler);
    }
    
    // Create the keyboard handler function
    window.flashcardKeyboardHandler = function(e) {
        // Only process shortcuts when flashcard page is active and not in input field
        if (!document.getElementById('page-overlay').classList.contains('active') ||
            e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
            return;
        }
        
        // Only process when we have flashcards loaded
        if (flashcards.length === 0) return;
        
        switch(e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                previousFlashcard();
                break;
            case 'ArrowRight':
                e.preventDefault();
                nextFlashcard();
                break;
            case 'ArrowUp':
            case ' ':
                e.preventDefault();
                flipFlashcard();
                break;
            case 's':
            case 'S':
                e.preventDefault();
                shuffleFlashcards();
                break;
        }
    };
    
    // Add the new event listener
    document.addEventListener('keydown', window.flashcardKeyboardHandler);
}

// Setup event listeners
export async function setupFlashcardsEventListeners() {
    const loadBtn = document.getElementById('load-flashcards-btn');
    const shuffleBtn = document.getElementById('shuffle-flashcards-btn');
    const filters = ['flashcard-pos-filter', 'flashcard-rarity-filter', 'flashcard-sentiment-filter', 'flashcard-count-filter'];
    
    // Load filters first
    await loadFlashcardFilters();
    
    // Setup keyboard shortcuts
    setupFlashcardKeyboardShortcuts();
    
    if (loadBtn) {
        loadBtn.addEventListener('click', loadFlashcards);
    }
    
    if (shuffleBtn) {
        shuffleBtn.addEventListener('click', shuffleFlashcards);
    }
    
    // Setup filter change listeners
    filters.forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            filterElement.addEventListener('change', loadFlashcards);
        }
    });
}

// Export functions for global access (needed for onclick handlers)
window.flipFlashcard = flipFlashcard;
window.nextFlashcard = nextFlashcard;
window.previousFlashcard = previousFlashcard; 
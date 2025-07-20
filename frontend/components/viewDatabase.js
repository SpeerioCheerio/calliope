// View Database Component
import { showLoading, hideLoading, showToast, apiCall, getSentimentIcon } from '../utils.js';

let currentPage = 0;
let currentWords = [];
let editingWord = null;
let availablePartsOfSpeech = [];
let itemsPerPage = 10;
let totalPages = 0;
let totalCount = 0;
let searchTerm = '';
let autocompleteWords = [];
let selectedAutocompleteIndex = -1;

// Fetch available parts of speech from the database
async function fetchPartsOfSpeech() {
    try {
        const response = await apiCall('/parts-of-speech');
        availablePartsOfSpeech = response.parts_of_speech || [];
        console.log('DEBUG: Loaded parts of speech:', availablePartsOfSpeech);
    } catch (error) {
        console.error('Error fetching parts of speech:', error);
        // Fallback to common parts of speech if API fails
        availablePartsOfSpeech = ['ADJECTIVE', 'ADVERB', 'NOUN', 'VERB', 'PREPOSITION', 'CONJUNCTION', 'INTERJECTION'];
    }
}

// Populate the POS filter dropdown
function populatePOSFilter() {
    const posFilter = document.getElementById('pos-filter');
    if (posFilter && availablePartsOfSpeech.length > 0) {
        // Clear existing options except the first one
        posFilter.innerHTML = '<option value="">All Parts of Speech</option>';
        
        // Add options for each part of speech
        availablePartsOfSpeech.forEach(pos => {
            const option = document.createElement('option');
            option.value = pos;
            option.textContent = pos;
            posFilter.appendChild(option);
        });
    }
}

// Load words for autocomplete
async function loadAutocompleteWords() {
    try {
        const response = await apiCall('/database?limit=1000');
        autocompleteWords = response.words || [];
    } catch (error) {
        console.error('Error loading autocomplete words:', error);
        autocompleteWords = [];
    }
}

// Handle search input
function handleSearchInput(event) {
    const query = event.target.value.trim();
    
    if (query.length === 0) {
        hideAutocomplete();
        searchTerm = '';
        currentPage = 0;
        loadDatabaseWords();
        return;
    }
    
    if (query.length >= 2) {
        showAutocomplete(query);
    } else {
        hideAutocomplete();
    }
}

// Show autocomplete suggestions
function showAutocomplete(query) {
    const autocompleteResults = document.getElementById('autocomplete-results');
    
    // Filter words that match the query
    const matches = autocompleteWords.filter(word => 
        word.word.toLowerCase().includes(query.toLowerCase()) ||
        word.definition.toLowerCase().includes(query.toLowerCase())
    ).slice(0, 10); // Limit to 10 results
    
    if (matches.length === 0) {
        hideAutocomplete();
        return;
    }
    
    // Build HTML for autocomplete results
    const html = matches.map((word, index) => `
        <div class="autocomplete-item" data-index="${index}" data-word="${word.word}">
            <span class="autocomplete-word">${word.word}</span>
            <span class="autocomplete-pos">${word.pos}</span>
        </div>
    `).join('');
    
    autocompleteResults.innerHTML = html;
    autocompleteResults.style.display = 'block';
    selectedAutocompleteIndex = -1;
    
    // Add click listeners to autocomplete items
    autocompleteResults.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('click', () => {
            selectAutocompleteItem(item.dataset.word);
        });
    });
}

// Hide autocomplete
function hideAutocomplete() {
    const autocompleteResults = document.getElementById('autocomplete-results');
    autocompleteResults.style.display = 'none';
    selectedAutocompleteIndex = -1;
}

// Select an autocomplete item
function selectAutocompleteItem(word) {
    const searchInput = document.getElementById('word-search');
    searchInput.value = word;
    searchTerm = word;
    currentPage = 0;
    hideAutocomplete();
    loadDatabaseWords();
}

// Handle keyboard navigation in autocomplete
function handleSearchKeydown(event) {
    const autocompleteResults = document.getElementById('autocomplete-results');
    const items = autocompleteResults.querySelectorAll('.autocomplete-item');
    
    if (items.length === 0) return;
    
    switch (event.key) {
        case 'ArrowDown':
            event.preventDefault();
            selectedAutocompleteIndex = Math.min(selectedAutocompleteIndex + 1, items.length - 1);
            updateAutocompleteSelection(items);
            break;
        case 'ArrowUp':
            event.preventDefault();
            selectedAutocompleteIndex = Math.max(selectedAutocompleteIndex - 1, -1);
            updateAutocompleteSelection(items);
            break;
        case 'Enter':
            event.preventDefault();
            if (selectedAutocompleteIndex >= 0) {
                selectAutocompleteItem(items[selectedAutocompleteIndex].dataset.word);
            } else {
                // Search for the current input value
                searchTerm = event.target.value.trim();
                currentPage = 0;
                hideAutocomplete();
                loadDatabaseWords();
            }
            break;
        case 'Escape':
            hideAutocomplete();
            break;
    }
}

// Update autocomplete selection highlighting
function updateAutocompleteSelection(items) {
    items.forEach((item, index) => {
        item.classList.toggle('selected', index === selectedAutocompleteIndex);
    });
}

export async function loadDatabaseWords() {
    const posFilter = document.getElementById('pos-filter').value;
    const rarityFilter = document.getElementById('rarity-filter').value;
    const sentimentFilter = document.getElementById('sentiment-filter').value;
    const itemsPerPageSelect = document.getElementById('items-per-page');
    
    if (itemsPerPageSelect) {
        itemsPerPage = parseInt(itemsPerPageSelect.value);
    }
    
    const params = new URLSearchParams({
        offset: currentPage * itemsPerPage,
        limit: itemsPerPage
    });
    
    if (posFilter) params.append('pos', posFilter);
    if (rarityFilter) params.append('rarity', rarityFilter);
    if (sentimentFilter) params.append('sentiment', sentimentFilter);
    if (searchTerm) params.append('search', searchTerm);
    
    try {
        const data = await apiCall(`/database?${params}`);
        currentWords = data.words;
        totalPages = data.total_pages;
        totalCount = data.total_count;
        
        displayDatabaseWords(data.words);
        updatePagination(data);
    } catch (error) {
        document.getElementById('words-grid').innerHTML = `
            <div class="error-message">
                <p>Failed to load words. Please try again.</p>
            </div>
        `;
    }
}

function displayDatabaseWords(words) {
    const wordsGrid = document.getElementById('words-grid');
    
    if (words.length === 0) {
        wordsGrid.innerHTML = `
            <div class="no-words-message">
                <p>No words found matching your criteria.</p>
            </div>
        `;
        return;
    }
    
    wordsGrid.innerHTML = words.map(word => `
        <div class="word-card rarity-${word.rarity}" data-word-id="${word.id}">
            <div class="word-header">
                <span class="word-title">${word.word}</span>
                <div class="word-header-right">
                    <span class="word-pos">${word.pos}</span>
                    <div class="word-menu">
                        <button class="menu-btn" onclick="toggleWordMenu(${word.id})">⋯</button>
                        <div class="menu-dropdown" id="menu-${word.id}">
                            <button class="menu-item" onclick="viewWord(${word.id})">View</button>
                            <button class="menu-item" onclick="editWord(${word.id})">Edit</button>
                            <button class="menu-item delete" onclick="deleteWord(${word.id})">Delete</button>
                        </div>
                    </div>
                </div>
            </div>
            <div class="word-definition">${word.definition}</div>
            <div class="word-example">"${word.example_sentence}"</div>
            <div class="word-badges">
                <span class="rarity-badge rarity-${word.rarity}">${word.rarity}</span>
                <span class="sentiment-badge">${getSentimentIcon(word.sentiment)} ${word.sentiment}</span>
            </div>
        </div>
    `).join('');
    
    // Add right-click context menu to each word card
    document.querySelectorAll('.word-card').forEach(card => {
        card.addEventListener('contextmenu', handleWordCardRightClick);
    });
}

function updatePagination(paginationData) {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    
    if (pageInfo) {
        pageInfo.textContent = `Page ${paginationData.current_page} of ${paginationData.total_pages} (${paginationData.total_count} total words)`;
    }
    
    if (prevBtn) {
        prevBtn.disabled = !paginationData.has_previous;
    }
    
    if (nextBtn) {
        nextBtn.disabled = !paginationData.has_next;
    }
}

// Context menu functionality
let contextMenu = null;
let contextMenuWordId = null;

function createContextMenu() {
    if (contextMenu) {
        return contextMenu;
    }
    
    contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.innerHTML = `
        <button class="context-menu-item" onclick="handleContextView()">View</button>
        <button class="context-menu-item" onclick="handleContextEdit()">Edit</button>
        <button class="context-menu-item delete" onclick="handleContextDelete()">Delete</button>
    `;
    
    document.body.appendChild(contextMenu);
    return contextMenu;
}

function handleWordCardRightClick(event) {
    event.preventDefault(); // Prevent default browser context menu
    
    const wordCard = event.currentTarget;
    const wordId = parseInt(wordCard.dataset.wordId);
    
    if (!wordId) return;
    
    contextMenuWordId = wordId;
    
    // Create or get existing context menu
    const menu = createContextMenu();
    
    // Position the context menu at cursor (using clientX/clientY for viewport positioning)
    const x = event.clientX;
    const y = event.clientY;
    
    // Ensure menu doesn't go off screen
    const menuWidth = 120;
    const menuHeight = 80;
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    
    let finalX = x;
    let finalY = y;
    
    if (x + menuWidth > windowWidth) {
        finalX = x - menuWidth;
    }
    
    if (y + menuHeight > windowHeight) {
        finalY = y - menuHeight;
    }
    
    menu.style.left = finalX + 'px';
    menu.style.top = finalY + 'px';
    
    // Close any open ellipses menus
    const allMenus = document.querySelectorAll('.menu-dropdown');
    allMenus.forEach(m => m.classList.remove('active'));
    
    // Show context menu
    menu.classList.add('active');
}

function hideContextMenu() {
    if (contextMenu) {
        contextMenu.classList.remove('active');
    }
    contextMenuWordId = null;
}

// Global functions for context menu actions
window.handleContextView = function() {
    if (contextMenuWordId) {
        viewWord(contextMenuWordId);
        hideContextMenu();
    }
};

window.handleContextEdit = function() {
    if (contextMenuWordId) {
        editWord(contextMenuWordId);
        hideContextMenu();
    }
};

window.handleContextDelete = function() {
    if (contextMenuWordId) {
        deleteWord(contextMenuWordId);
        hideContextMenu();
    }
};

// Close menus when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.word-menu') && !e.target.closest('.context-menu')) {
        const allMenus = document.querySelectorAll('.menu-dropdown');
        allMenus.forEach(menu => menu.classList.remove('active'));
        hideContextMenu();
    }
});

// Close context menu on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideContextMenu();
    }
});

// Global functions for word menu actions
window.toggleWordMenu = function(wordId) {
    const menu = document.getElementById(`menu-${wordId}`);
    const allMenus = document.querySelectorAll('.menu-dropdown');
    
    // Close all other menus
    allMenus.forEach(m => {
        if (m !== menu) {
            m.classList.remove('active');
        }
    });
    
    // Toggle current menu
    menu.classList.toggle('active');
};

window.editWord = function(wordId) {
    const word = currentWords.find(w => w.id === wordId);
    if (!word) {
        console.error('DEBUG: Word not found in currentWords array, ID:', wordId);
        console.log('DEBUG: Available word IDs:', currentWords.map(w => w.id));
        showToast('Error: Word not found. Refreshing list...', 'error');
        loadDatabaseWords(); // Refresh the list
        return;
    }
    
    console.log('DEBUG: Editing word:', word.word, 'with ID:', wordId);
    editingWord = word;
    showEditModal(word);
    closeWordMenu(wordId);
};

window.deleteWord = function(wordId) {
    const word = currentWords.find(w => w.id === wordId);
    if (!word) {
        console.error('DEBUG: Word not found in currentWords array, ID:', wordId);
        console.log('DEBUG: Available word IDs:', currentWords.map(w => w.id));
        showToast('Error: Word not found. Refreshing list...', 'error');
        loadDatabaseWords(); // Refresh the list
        return;
    }
    
    console.log('DEBUG: Attempting to delete word:', word.word, 'with ID:', wordId);
    if (confirm(`Are you sure you want to delete "${word.word}"?`)) {
        performDeleteWord(wordId);
    }
    closeWordMenu(wordId);
};

window.viewWord = function(wordId) {
    const word = currentWords.find(w => w.id === wordId);
    if (!word) {
        console.error('DEBUG: Word not found in currentWords array, ID:', wordId);
        console.log('DEBUG: Available word IDs:', currentWords.map(w => w.id));
        showToast('Error: Word not found. Refreshing list...', 'error');
        loadDatabaseWords(); // Refresh the list
        return;
    }
    
    console.log('DEBUG: Viewing word:', word.word, 'with ID:', wordId);
    showViewModal(word);
    closeWordMenu(wordId);
};

function showViewModal(word) {
    // Create view modal
    const modal = document.createElement('div');
    modal.className = 'view-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>View Word</h2>
                <button class="close-btn" onclick="closeViewModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="word-card view-card">
                    <div class="word-header">
                        <span class="word-title">${word.word}</span>
                        <div class="word-header-right">
                            <span class="word-pos">${word.pos}</span>
                        </div>
                    </div>
                    <div class="word-definition">${word.definition}</div>
                    <div class="word-example">"${word.example_sentence}"</div>
                    <div class="word-badges">
                        <span class="rarity-badge rarity-${word.rarity}">${word.rarity}</span>
                        <span class="sentiment-badge">${getSentimentIcon(word.sentiment)} ${word.sentiment}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeViewModal();
        }
    });
}

function closeWordMenu(wordId) {
    const menu = document.getElementById(`menu-${wordId}`);
    if (menu) {
        menu.classList.remove('active');
    }
}

function showEditModal(word) {
    // Ensure we have parts of speech loaded before showing modal
    const createModal = async () => {
        // Fetch parts of speech if not already loaded
        if (availablePartsOfSpeech.length === 0) {
            await fetchPartsOfSpeech();
        }
        
        // Create edit modal
        const modal = document.createElement('div');
        modal.className = 'edit-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Edit Word</h2>
                    <button class="close-btn" onclick="closeEditModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="edit-word-form">
                        <div class="form-group">
                            <label for="edit-word">Word:</label>
                            <input type="text" id="edit-word" name="word" value="${word.word}" required>
                        </div>
                        <div class="form-group">
                            <label for="edit-pos">Part of Speech:</label>
                            <select id="edit-pos" name="pos" required>
                                ${availablePartsOfSpeech.map(pos => `
                                    <option value="${pos}" ${word.pos.toUpperCase() === pos ? 'selected' : ''}>${pos}</option>
                                `).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="edit-definition">Definition:</label>
                            <textarea id="edit-definition" name="definition" rows="3" required>${word.definition}</textarea>
                        </div>
                        <div class="form-group">
                            <label for="edit-example">Example Sentence:</label>
                            <textarea id="edit-example" name="example_sentence" rows="2" required>${word.example_sentence}</textarea>
                        </div>
                        <div class="form-group">
                            <label for="edit-rarity">Rarity:</label>
                            <select id="edit-rarity" name="rarity" required>
                                <option value="notty" ${word.rarity === 'notty' ? 'selected' : ''}>Common Advanced (Notty)</option>
                                <option value="luke" ${word.rarity === 'luke' ? 'selected' : ''}>Less Common (Luke)</option>
                                <option value="alex" ${word.rarity === 'alex' ? 'selected' : ''}>Rare/Archaic (Alex)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="edit-sentiment">Sentiment:</label>
                            <select id="edit-sentiment" name="sentiment" required>
                                <option value="positive" ${word.sentiment === 'positive' ? 'selected' : ''}>Positive</option>
                                <option value="negative" ${word.sentiment === 'negative' ? 'selected' : ''}>Negative</option>
                                <option value="neutral" ${word.sentiment === 'neutral' ? 'selected' : ''}>Neutral</option>
                                <option value="formal" ${word.sentiment === 'formal' ? 'selected' : ''}>Formal</option>
                            </select>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="save-btn" onclick="saveWordEdit()">Save Changes</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeEditModal();
            }
        });
    };
    
    // Call the async function
    createModal();
}

window.closeEditModal = function() {
    const modal = document.querySelector('.edit-modal');
    if (modal) {
        modal.remove();
    }
    editingWord = null;
};

window.closeViewModal = function() {
    const modal = document.querySelector('.view-modal');
    if (modal) {
        modal.remove();
    }
};

window.saveWordEdit = async function() {
    if (!editingWord) {
        console.error('DEBUG: No word being edited');
        return;
    }
    
    const form = document.getElementById('edit-word-form');
    const formData = new FormData(form);
    
    const updatedWord = {
        word: formData.get('word'),
        pos: formData.get('pos'),
        definition: formData.get('definition'),
        example_sentence: formData.get('example_sentence'),
        rarity: formData.get('rarity'),
        sentiment: formData.get('sentiment')
    };
    
    console.log('DEBUG: Saving word edit for ID:', editingWord.id, 'with data:', updatedWord);
    
    try {
        showLoading();
        const response = await apiCall(`/update-word/${editingWord.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatedWord)
        });
        
        hideLoading();
        showToast('Word updated successfully!', 'success');
        closeEditModal();
        loadDatabaseWords(); // Refresh the list
        
    } catch (error) {
        hideLoading();
        
        // Check if it's a 404 error (word not found)
        if (error.message.includes('Not Found') || error.message.includes('404')) {
            showToast('Word not found. The word may have been deleted. Refreshing list...', 'error');
            closeEditModal();
            loadDatabaseWords(); // Refresh the list to get current data
        } else {
            showToast('Error updating word. Please try again.', 'error');
        }
        
        console.error('Error updating word:', error);
    }
};

async function performDeleteWord(wordId) {
    console.log('DEBUG: Performing delete for word ID:', wordId);
    
    try {
        showLoading();
        const response = await apiCall(`/delete-word/${wordId}`, {
            method: 'DELETE'
        });
        
        hideLoading();
        showToast('Word deleted successfully!', 'success');
        loadDatabaseWords(); // Refresh the list
        
    } catch (error) {
        hideLoading();
        
        // Check if it's a 404 error (word not found)
        if (error.message.includes('Not Found') || error.message.includes('404')) {
            showToast('Word not found. It may have already been deleted. Refreshing list...', 'error');
            loadDatabaseWords(); // Refresh the list to get current data
        } else {
            showToast('Error deleting word. Please try again.', 'error');
        }
        
        console.error('Error deleting word:', error);
    }
}

export function previousPage() {
    if (currentPage > 0) {
        currentPage--;
        loadDatabaseWords();
    }
}

export function nextPage() {
    currentPage++;
    loadDatabaseWords();
}

export function resetFilters() {
    document.getElementById('pos-filter').value = '';
    document.getElementById('rarity-filter').value = '';
    document.getElementById('sentiment-filter').value = '';
    document.getElementById('items-per-page').value = '10';
    document.getElementById('word-search').value = '';
    itemsPerPage = 10;
    currentPage = 0;
    searchTerm = '';
    hideAutocomplete();
    loadDatabaseWords();
}

export function applyFilters() {
    currentPage = 0;
    loadDatabaseWords();
}

function handleItemsPerPageChange() {
    currentPage = 0; // Reset to first page when changing items per page
    loadDatabaseWords();
}

// Setup event listeners
export function setupDatabaseEventListeners() {
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const resetBtn = document.getElementById('reset-filters-btn');
    const itemsPerPageSelect = document.getElementById('items-per-page');
    const searchInput = document.getElementById('word-search');
    const filters = ['pos-filter', 'rarity-filter', 'sentiment-filter'];
    
    if (prevBtn) {
        prevBtn.addEventListener('click', previousPage);
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', nextPage);
    }
    
    if (resetBtn) {
        resetBtn.addEventListener('click', resetFilters);
    }
    
    if (itemsPerPageSelect) {
        itemsPerPageSelect.addEventListener('change', handleItemsPerPageChange);
    }
    
    // Setup search functionality
    if (searchInput) {
        searchInput.addEventListener('input', handleSearchInput);
        searchInput.addEventListener('keydown', handleSearchKeydown);
        searchInput.addEventListener('blur', () => {
            // Delay hiding to allow for clicks on autocomplete items
            setTimeout(() => {
                hideAutocomplete();
            }, 200);
        });
    }
    
    // Setup filter change listeners
    filters.forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            filterElement.addEventListener('change', applyFilters);
        }
    });
    
    // Hide autocomplete when clicking outside
    document.addEventListener('click', (event) => {
        const searchContainer = document.querySelector('.search-container');
        if (searchContainer && !searchContainer.contains(event.target)) {
            hideAutocomplete();
        }
    });
    
    // Preload parts of speech for edit modal and populate filter dropdown
    fetchPartsOfSpeech().then(() => {
        populatePOSFilter();
    });
    
    // Load autocomplete words
    loadAutocompleteWords();
    
    // Load initial data
    loadDatabaseWords();
} 
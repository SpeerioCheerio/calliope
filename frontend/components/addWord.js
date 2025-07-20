// Add Word Component
import { showLoading, hideLoading, showToast, apiCall, getSentimentIcon } from '../utils.js';

// Global variables for word preview
let previewWordData = null;
let availablePartsOfSpeech = [];

export async function addWord() {
    const wordInput = document.getElementById('word-input');
    const word = wordInput.value.trim();
    
    if (!word) {
        showToast('Please enter a word', 'warning');
        return;
    }
    
    const addButton = document.getElementById('add-word-btn');
    addButton.disabled = true;
    addButton.textContent = 'Adding...';
    
    try {
        // Get word definition from OpenAI (this will also add to database for now)
        const data = await apiCall('/add-word', {
            method: 'POST',
            body: JSON.stringify({ word })
        });
        
        if (data.success && data.word_data) {
            // Store the word data for actions
            previewWordData = data.word_data;
            
            // Show preview with action buttons
            displayWordPreview(data.word_data);
            
            // Clear input and show message
            wordInput.value = '';
            showToast('Word created! Please review and choose an action.');
            clearSpellSuggestions();
        } else {
            showToast(data.message, 'warning');
        }
    } catch (error) {
        console.error('Error creating word:', error);
        
        // Try spell checking if word addition failed
        await checkSpellingAndShowSuggestions(word);
    } finally {
        addButton.disabled = false;
        addButton.textContent = 'Add Word';
    }
}

async function checkSpellingAndShowSuggestions(word) {
    try {
        const spellData = await apiCall('/spell-check', {
            method: 'POST',
            body: JSON.stringify({ word })
        });
        
        if (spellData.suggestions && spellData.suggestions.length > 0) {
            displaySpellSuggestions(word, spellData.suggestions);
        } else {
            displayAddWordError('Word not found and no spelling suggestions available.');
        }
    } catch (spellError) {
        console.error('Spell checking failed:', spellError);
        displayAddWordError('Failed to add word. Please check the spelling and try again.');
    }
}

function displaySpellSuggestions(originalWord, suggestions) {
    const resultContainer = document.getElementById('add-word-result');
    
    let suggestionHTML = suggestions.map(suggestion => 
        `<button class="spell-suggestion" onclick="selectSpellSuggestion('${suggestion.word}')" 
                data-word="${suggestion.word}" data-confidence="${suggestion.confidence}">
            ${suggestion.word} 
            <span class="confidence-score">(${Math.round(suggestion.confidence * 100)}%)</span>
        </button>`
    ).join('');
    
    resultContainer.innerHTML = `
        <div class="spell-suggestions-container">
            <div class="spell-suggestions-header">
                <h3>Did you mean?</h3>
                <p>We couldn't find "${originalWord}". Here are some suggestions:</p>
            </div>
            <div class="spell-suggestions-grid">
                ${suggestionHTML}
            </div>
            <div class="spell-suggestions-footer">
                <button class="cancel-suggestions" onclick="clearSpellSuggestions()">Cancel</button>
            </div>
        </div>
    `;
}

function displayAddWordError(message) {
    const resultContainer = document.getElementById('add-word-result');
    resultContainer.innerHTML = `
        <div class="error-message">
            <p>${message}</p>
        </div>
    `;
}

function clearSpellSuggestions() {
    const resultContainer = document.getElementById('add-word-result');
    // Only clear if the container contains spell suggestions, not word cards
    if (resultContainer.querySelector('.spell-suggestions-container')) {
        resultContainer.innerHTML = '';
    }
}

// Function to handle spell suggestion selection
async function selectSpellSuggestion(word) {
    const wordInput = document.getElementById('word-input');
    wordInput.value = word;
    
    // Clear suggestions
    clearSpellSuggestions();
    
    // Automatically try to add the selected word
    await addWord();
}

// Make selectSpellSuggestion available globally for onclick handlers
window.selectSpellSuggestion = selectSpellSuggestion;
window.clearSpellSuggestions = clearSpellSuggestions;

function displayWordPreview(wordData) {
    const resultContainer = document.getElementById('add-word-result');
    
    // Clear any existing content and styles
    resultContainer.innerHTML = '';
    resultContainer.style.cssText = '';
    
    resultContainer.innerHTML = `
        <div class="word-card rarity-${wordData.rarity}" style="margin-top: 2rem; display: block; visibility: visible; opacity: 0; transform: translateY(20px); transition: all 0.5s ease-out;">
            <div class="word-header">
                <span class="word-title">${wordData.word}</span>
                <div class="word-header-right">
                    <span class="word-pos">${wordData.pos}</span>
                </div>
            </div>
            <div class="word-definition">${wordData.definition}</div>
            <div class="word-example">"${wordData.example_sentence}"</div>
            <div class="word-badges">
                <span class="rarity-badge rarity-${wordData.rarity}">${wordData.rarity}</span>
                <span class="sentiment-badge">${getSentimentIcon(wordData.sentiment)} ${wordData.sentiment}</span>
            </div>
        </div>
        
        <div class="preview-actions" style="margin-top: 1.5rem; display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
            <button class="edit-preview-btn" onclick="editPreviewWord()" 
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 25px rgba(33, 150, 243, 0.4)'"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(33, 150, 243, 0.3)'"
                style="background: linear-gradient(135deg, #2196F3 0%, #42A5F5 100%); color: white; border: none; padding: 1rem 2rem; border-radius: 10px; font-family: 'Inter', sans-serif; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(33, 150, 243, 0.3);">Edit Details</button>
            <button class="reject-preview-btn" onclick="rejectPreviewWord()" 
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 25px rgba(244, 67, 54, 0.4)'"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(244, 67, 54, 0.3)'"
                style="background: linear-gradient(135deg, #f44336 0%, #ef5350 100%); color: white; border: none; padding: 1rem 2rem; border-radius: 10px; font-family: 'Inter', sans-serif; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3);">Reject Word</button>
            <button class="accept-preview-btn" onclick="acceptPreviewWord()" 
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 25px rgba(76, 175, 80, 0.4)'"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(76, 175, 80, 0.3)'"
                style="background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%); color: white; border: none; padding: 1rem 2rem; border-radius: 10px; font-family: 'Inter', sans-serif; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);">Add to Database</button>
        </div>
    `;
    
    // Animate the card into view
    setTimeout(() => {
        const card = resultContainer.querySelector('.word-card');
        if (card) {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }
    }, 50);
    
    // Scroll the card into view to ensure it's visible
    setTimeout(() => {
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

function displayAddWordResult(data) {
    const resultContainer = document.getElementById('add-word-result');
    
    // Clear any existing content and styles
    resultContainer.innerHTML = '';
    resultContainer.style.cssText = '';
    
    if (data.word_data) {
        resultContainer.innerHTML = `
            <div class="word-card" style="margin-top: 2rem; display: block; visibility: visible; opacity: 0; transform: translateY(20px); transition: all 0.5s ease-out;">
                <div class="word-header">
                    <span class="word-title">${data.word_data.word}</span>
                    <div class="word-header-right">
                        <span class="word-pos">${data.word_data.pos}</span>
                    </div>
                </div>
                <div class="word-definition">${data.word_data.definition}</div>
                <div class="word-example">"${data.word_data.example_sentence}"</div>
                <div class="word-badges">
                    <span class="rarity-badge rarity-${data.word_data.rarity}">${data.word_data.rarity}</span>
                    <span class="sentiment-badge">${getSentimentIcon(data.word_data.sentiment)} ${data.word_data.sentiment}</span>
                </div>
            </div>
        `;
        
        // Animate the card into view
        setTimeout(() => {
            const card = resultContainer.querySelector('.word-card');
            if (card) {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }
        }, 50);
        
        // Scroll the card into view to ensure it's visible
        setTimeout(() => {
            resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    } else {
        resultContainer.innerHTML = `
            <div class="info-message" style="margin-top: 2rem; padding: 1rem; text-align: center; background: rgba(255, 255, 255, 0.8); border-radius: 10px; border: 2px solid #8B4513;">
                <p>${data.message}</p>
            </div>
        `;
    }
}

// Fetch available parts of speech from the database
async function fetchPartsOfSpeech() {
    try {
        const response = await apiCall('/parts-of-speech');
        availablePartsOfSpeech = response.parts_of_speech || [];
    } catch (error) {
        console.error('Error fetching parts of speech:', error);
        // Fallback to common parts of speech if API fails
        availablePartsOfSpeech = ['ADJECTIVE', 'ADVERB', 'NOUN', 'VERB', 'PREPOSITION', 'CONJUNCTION', 'INTERJECTION'];
    }
}

// Edit preview word function
async function editPreviewWord() {
    if (!previewWordData) return;
    
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
                <button class="close-btn" onclick="closePreviewEditModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="preview-edit-word-form">
                    <div class="form-group">
                        <label for="preview-edit-word">Word:</label>
                        <input type="text" id="preview-edit-word" name="word" value="${previewWordData.word}" required>
                    </div>
                    <div class="form-group">
                        <label for="preview-edit-pos">Part of Speech:</label>
                        <select id="preview-edit-pos" name="pos" required>
                            ${availablePartsOfSpeech.map(pos => `
                                <option value="${pos}" ${previewWordData.pos.toUpperCase() === pos ? 'selected' : ''}>${pos}</option>
                            `).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="preview-edit-definition">Definition:</label>
                        <textarea id="preview-edit-definition" name="definition" rows="3" required>${previewWordData.definition}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="preview-edit-example">Example Sentence:</label>
                        <textarea id="preview-edit-example" name="example_sentence" rows="2" required>${previewWordData.example_sentence}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="preview-edit-rarity">Rarity:</label>
                        <select id="preview-edit-rarity" name="rarity" required>
                            <option value="notty" ${previewWordData.rarity === 'notty' ? 'selected' : ''}>Common Advanced (Notty)</option>
                            <option value="luke" ${previewWordData.rarity === 'luke' ? 'selected' : ''}>Less Common (Luke)</option>
                            <option value="alex" ${previewWordData.rarity === 'alex' ? 'selected' : ''}>Rare/Archaic (Alex)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="preview-edit-sentiment">Sentiment:</label>
                        <select id="preview-edit-sentiment" name="sentiment" required>
                            <option value="positive" ${previewWordData.sentiment === 'positive' ? 'selected' : ''}>Positive</option>
                            <option value="negative" ${previewWordData.sentiment === 'negative' ? 'selected' : ''}>Negative</option>
                            <option value="neutral" ${previewWordData.sentiment === 'neutral' ? 'selected' : ''}>Neutral</option>
                            <option value="formal" ${previewWordData.sentiment === 'formal' ? 'selected' : ''}>Formal</option>
                        </select>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="save-btn" onclick="savePreviewWordEdit()">Save Changes</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closePreviewEditModal();
        }
    });
}

// Close preview edit modal
function closePreviewEditModal() {
    const modal = document.querySelector('.edit-modal');
    if (modal) {
        modal.remove();
    }
}

// Save preview word edit
async function savePreviewWordEdit() {
    const form = document.getElementById('preview-edit-word-form');
    const formData = new FormData(form);
    
    const updatedWord = {
        word: formData.get('word'),
        pos: formData.get('pos'),
        definition: formData.get('definition'),
        example_sentence: formData.get('example_sentence'),
        rarity: formData.get('rarity'),
        sentiment: formData.get('sentiment')
    };
    
    try {
        showLoading();
        const response = await apiCall(`/update-word/${previewWordData.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatedWord)
        });
        
        hideLoading();
        
        // Update the preview data
        previewWordData = { ...previewWordData, ...updatedWord };
        
        // Update the preview display
        displayWordPreview(previewWordData);
        
        showToast('Word updated successfully!', 'success');
        closePreviewEditModal();
        
    } catch (error) {
        hideLoading();
        showToast('Error updating word. Please try again.', 'error');
        console.error('Error updating word:', error);
    }
}

// Reject preview word (delete from database)
async function rejectPreviewWord() {
    if (!previewWordData) return;
    
    if (confirm(`Are you sure you want to reject "${previewWordData.word}"? This will remove it from the database.`)) {
        try {
            showLoading();
            await apiCall(`/delete-word/${previewWordData.id}`, {
                method: 'DELETE'
            });
            
            hideLoading();
            
            // Clear the preview
            const resultContainer = document.getElementById('add-word-result');
            resultContainer.innerHTML = `
                <div class="info-message" style="margin-top: 2rem; padding: 1rem; text-align: center; background: rgba(255, 255, 255, 0.8); border-radius: 10px; border: 2px solid #8B4513;">
                    <p>Word "${previewWordData.word}" has been rejected and removed.</p>
                </div>
            `;
            
            previewWordData = null;
            showToast('Word rejected successfully!', 'success');
            
        } catch (error) {
            hideLoading();
            showToast('Error rejecting word. Please try again.', 'error');
            console.error('Error rejecting word:', error);
        }
    }
}

// Accept preview word (word is already in database)
function acceptPreviewWord() {
    if (!previewWordData) return;
    
    // Clear the preview and show success message
    const resultContainer = document.getElementById('add-word-result');
    resultContainer.innerHTML = `
        <div class="info-message" style="margin-top: 2rem; padding: 1rem; text-align: center; background: rgba(76, 175, 80, 0.1); border-radius: 10px; border: 2px solid #4CAF50; color: #4CAF50;">
            <p>Word "${previewWordData.word}" has been added to the database successfully!</p>
        </div>
    `;
    
    previewWordData = null;
    showToast('Word added to database successfully!', 'success');
}

// Make functions global for onclick handlers
window.editPreviewWord = editPreviewWord;
window.rejectPreviewWord = rejectPreviewWord;
window.acceptPreviewWord = acceptPreviewWord;
window.closePreviewEditModal = closePreviewEditModal;
window.savePreviewWordEdit = savePreviewWordEdit;

// Setup event listeners
export function setupAddWordEventListeners() {
    const addWordBtn = document.getElementById('add-word-btn');
    const wordInput = document.getElementById('word-input');
    
    if (addWordBtn) {
        addWordBtn.addEventListener('click', addWord);
    }
    
    if (wordInput) {
        wordInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addWord();
            }
        });
        
        // Focus the input when the page loads
        wordInput.focus();
    }
} 
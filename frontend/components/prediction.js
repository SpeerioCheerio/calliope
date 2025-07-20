// Word Prediction Component
import { showLoading, hideLoading, showToast, apiCall, getSentimentIcon } from '../utils.js';

// Store original sentence and delimiter position for word swapping
let originalSentence = '';
let delimiterPosition = -1;

export async function predictWords() {
    const sentenceInput = document.getElementById('sentence-input');
    const sentence = sentenceInput.value.trim();
    
    if (!sentence) {
        showToast('Please enter a sentence with a blank (_)', 'warning');
        return;
    }
    
    if (!sentence.includes('_')) {
        showToast('Please include an underscore (_) to mark where you want word suggestions', 'warning');
        return;
    }
    
    // Find the position of the underscore
    const words = sentence.split(' ');
    delimiterPosition = words.findIndex(word => word.includes('_'));
    
    if (delimiterPosition === -1) {
        showToast('Please include an underscore (_) to mark where you want word suggestions', 'warning');
        return;
    }
    
    // Store original sentence for word swapping
    originalSentence = sentence;
    
    // Remove the underscore for the clean sentence
    const cleanSentence = sentence.replace('_', '').trim();
    
    const predictButton = document.getElementById('predict-btn');
    predictButton.disabled = true;
    predictButton.textContent = 'Predicting...';
    
    try {
        // Get selected sentiment
        const sentimentFilter = document.getElementById('sentiment-filter');
        const selectedSentiment = sentimentFilter ? sentimentFilter.value : '';
        
        const data = await apiCall('/predict', {
            method: 'POST',
            body: JSON.stringify({ 
                sentence: cleanSentence,
                delimiter_position: delimiterPosition,
                sentiment: selectedSentiment || null
            })
        });
        
        displayPredictionResults(data);
    } catch (error) {
        const resultsContainer = document.getElementById('prediction-results');
        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = `
            <div class="error-message">
                <p>Failed to predict words. Please try again.</p>
            </div>
        `;
    } finally {
        predictButton.disabled = false;
        predictButton.textContent = 'Predict Words';
    }
}

function displayPredictionResults(data) {
    const resultsContainer = document.getElementById('prediction-results');
    
    // Show the results container
    resultsContainer.style.display = 'block';
    
    if (data.suggestions.length === 0) {
        resultsContainer.innerHTML = `
            <div class="no-results">
                <p>No suitable words found for this context.</p>
            </div>
        `;
        return;
    }
    
    resultsContainer.innerHTML = `
        <div class="prediction-results-header">
            <h3>Word Suggestions (${data.suggestions.length} found)</h3>
            <p>Click any word to insert it into your sentence</p>
        </div>
        <div class="predictions-grid">
            ${data.suggestions.map(prediction => `
                <div class="word-card rarity-${prediction.rarity}" onclick="insertWordInSentence('${prediction.word}')" style="cursor: pointer;">
                    <div class="word-header">
                        <span class="word-title">${prediction.word}</span>
                        <div class="word-header-right">
                            <span class="word-pos">${prediction.pos}</span>
                        </div>
                    </div>
                    <div class="word-definition">${prediction.definition}</div>
                    <div class="word-example">"${prediction.example_sentence}"</div>
                    <div class="word-badges">
                        <span class="rarity-badge rarity-${prediction.rarity}">${prediction.rarity}</span>
                        <span class="sentiment-badge">${getSentimentIcon(prediction.sentiment)} ${prediction.sentiment}</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

export function insertWordInSentence(word) {
    const sentenceInput = document.getElementById('sentence-input');
    
    if (originalSentence && delimiterPosition !== -1) {
        // Split the original sentence into words
        const words = originalSentence.split(' ');
        
        // Replace the word at the delimiter position with the new word
        words[delimiterPosition] = word;
        
        // Join the words back into a sentence
        const newSentence = words.join(' ');
        
        // Update the input field
        sentenceInput.value = newSentence;
        
        // Show success message
        showToast(`Inserted "${word}" into your sentence!`);
        
        // Update visual feedback - highlight the selected card
        highlightSelectedCard(word);
    } else {
        showToast('Please generate predictions first', 'warning');
    }
}

function highlightSelectedCard(selectedWord) {
    // Remove previous highlights
    const cards = document.querySelectorAll('.predictions-grid .word-card');
    cards.forEach(card => {
        card.classList.remove('selected-prediction');
    });
    
    // Add highlight to selected card
    cards.forEach(card => {
        const wordTitle = card.querySelector('.word-title');
        if (wordTitle && wordTitle.textContent === selectedWord) {
            card.classList.add('selected-prediction');
        }
    });
}

// Setup event listeners
export function setupPredictionEventListeners() {
    const predictBtn = document.getElementById('predict-btn');
    const sentenceInput = document.getElementById('sentence-input');
    
    if (predictBtn) {
        predictBtn.addEventListener('click', predictWords);
    }
    
    if (sentenceInput) {
        sentenceInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                predictWords();
            }
        });
        
        // Focus the input when the page loads
        sentenceInput.focus();
    }
}

// Export functions for global access (needed for onclick handlers)
window.insertWordInSentence = insertWordInSentence; 
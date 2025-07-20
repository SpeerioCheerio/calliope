// Paragraph Analyzer Component
import { showLoading, hideLoading, showToast, apiCall, getSentimentIcon } from '../utils.js';

let originalText = '';
let currentEnhancements = [];
let currentSelectedWord = '';
let currentSelectedOptions = new Set();

export async function analyzeParagraph() {
    const paragraphInput = document.getElementById('paragraph-input');
    const text = paragraphInput.textContent.trim();
    
    if (!text) {
        showToast('Please enter some text to analyze', 'warning');
        return;
    }
    
    const analyzeButton = document.getElementById('analyze-btn');
    analyzeButton.disabled = true;
    analyzeButton.textContent = 'Analyzing...';
    
    try {
        const data = await apiCall('/analyze-paragraph', {
            method: 'POST',
            body: JSON.stringify({ text })
        });
        
        originalText = text;
        currentEnhancements = data.enhancements || [];
        displayHighlightedParagraph(data);
    } catch (error) {
        const resultsContainer = document.getElementById('analysis-results');
        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = `
            <div class="error-message">
                <p>Failed to analyze paragraph. Please try again.</p>
            </div>
        `;
    } finally {
        analyzeButton.disabled = false;
        analyzeButton.textContent = 'Analyze Paragraph';
    }
}

function displayHighlightedParagraph(data) {
    const resultsContainer = document.getElementById('analysis-results');
    const paragraphInput = document.getElementById('paragraph-input');
    
    if (!data.enhancements || data.enhancements.length === 0) {
        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = `
            <div class="no-results">
                <p>No vocabulary enhancements found for this text.</p>
            </div>
        `;
        return;
    }
    
    // Create a map of original words to enhancements for quick lookup
    const enhancementMap = new Map();
    data.enhancements.forEach(enhancement => {
        enhancementMap.set(enhancement.original_word.toLowerCase(), enhancement);
    });
    
    // Highlight words in the original text
    let highlightedText = originalText;
    
    // Sort enhancements by word length (longest first) to avoid partial replacements
    const sortedEnhancements = data.enhancements.sort((a, b) => 
        b.original_word.length - a.original_word.length
    );
    
    sortedEnhancements.forEach(enhancement => {
        const originalWord = enhancement.original_word;
        const regex = new RegExp(`\\b${originalWord}\\b`, 'gi');
        highlightedText = highlightedText.replace(regex, 
            `<span class="highlighted-word" onclick="openWordModal('${originalWord}')">${originalWord}</span>`
        );
    });
    
    // Replace the input content with enhanced text, keeping same dimensions
    paragraphInput.innerHTML = highlightedText;
    paragraphInput.contentEditable = 'false';
    paragraphInput.style.cursor = 'default';
    
    // Replace the analyze button with copy and back buttons
    const analyzeBtn = document.getElementById('analyze-btn');
    analyzeBtn.style.display = 'none';
    
    // Create button container
    const buttonContainer = document.createElement('div');
    buttonContainer.id = 'enhanced-buttons';
    buttonContainer.style.display = 'flex';
    buttonContainer.style.gap = '1rem';
    buttonContainer.style.marginTop = '1rem';
    
    buttonContainer.innerHTML = `
        <button onclick="backToOriginal()">Back</button>
        <button onclick="copyEnhancedText()">Copy Sentence</button>
    `;
    
    // Insert the button container after the analyze button
    analyzeBtn.parentNode.insertBefore(buttonContainer, analyzeBtn.nextSibling);
    
    // Hide results container
    resultsContainer.style.display = 'none';
}

export function openWordModal(originalWord) {
    const enhancement = currentEnhancements.find(e => 
        e.original_word.toLowerCase() === originalWord.toLowerCase()
    );
    
    if (!enhancement) return;
    
    currentSelectedWord = originalWord;
    currentSelectedOptions.clear();
    
    const modal = document.createElement('div');
    modal.className = 'modal-overlay view-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>Enhance "${originalWord}"</h2>
                <button class="close-modal" onclick="closeWordModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="enhancement-options">
                    ${enhancement.suggested_words.map(word => `
                        <div class="word-card rarity-${word.rarity}" 
                             onclick="toggleWordSelection('${word.word}')"
                             data-word="${word.word}">
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
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add click outside to close
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeWordModal();
        }
    });
    
    // Show modal with animation
    setTimeout(() => {
        modal.style.opacity = '1';
        modal.style.visibility = 'visible';
        const content = modal.querySelector('.modal-content');
        if (content) {
            content.style.transform = 'scale(1)';
        }
    }, 10);
}

export function closeWordModal() {
    const modal = document.querySelector('.view-modal');
    if (modal) {
        modal.style.opacity = '0';
        modal.style.visibility = 'hidden';
        const content = modal.querySelector('.modal-content');
        if (content) {
            content.style.transform = 'scale(0.9)';
        }
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
}

export function toggleWordSelection(selectedWord) {
    const wordCard = document.querySelector(`[data-word="${selectedWord}"]`);
    if (!wordCard) return;
    
    // Toggle selection
    if (currentSelectedOptions.has(selectedWord)) {
        currentSelectedOptions.delete(selectedWord);
        wordCard.classList.remove('selected-prediction');
    } else {
        // Clear previous selection (single selection mode)
        currentSelectedOptions.forEach(word => {
            const prevCard = document.querySelector(`[data-word="${word}"]`);
            if (prevCard) {
                prevCard.classList.remove('selected-prediction');
            }
        });
        currentSelectedOptions.clear();
        
        // Add new selection
        currentSelectedOptions.add(selectedWord);
        wordCard.classList.add('selected-prediction');
        
        // Replace word in paragraph
        replaceWordInParagraph(currentSelectedWord, selectedWord);
    }
}

function replaceWordInParagraph(originalWord, newWord) {
    const paragraphInput = document.getElementById('paragraph-input');
    
    if (paragraphInput) {
        // Replace in the paragraph input display
        const regex = new RegExp(`\\b${originalWord}\\b`, 'gi');
        paragraphInput.innerHTML = paragraphInput.innerHTML.replace(regex, newWord);
        
        // Also update the original text for future replacements
        originalText = originalText.replace(regex, newWord);
        
        // Update current enhancements to reflect the change
        currentEnhancements = currentEnhancements.map(enhancement => {
            if (enhancement.original_word.toLowerCase() === originalWord.toLowerCase()) {
                return {
                    ...enhancement,
                    original_word: newWord,
                    suggested_words: enhancement.suggested_words.filter(w => w.word !== newWord)
                };
            }
            return enhancement;
        }).filter(enhancement => enhancement.suggested_words.length > 0);
    }
    
    showToast(`Replaced "${originalWord}" with "${newWord}"`);
}

// Legacy functions for backward compatibility
export function replaceWordInText(originalWord, suggestedWord) {
    replaceWordInParagraph(originalWord, suggestedWord);
}

export function copyEnhancedText() {
    const paragraphInput = document.getElementById('paragraph-input');
    if (paragraphInput) {
        const textToCopy = paragraphInput.textContent || paragraphInput.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
            showToast('Enhanced text copied to clipboard!');
        }).catch(() => {
            showToast('Failed to copy text', 'error');
        });
    }
}

export function backToOriginal() {
    const paragraphInput = document.getElementById('paragraph-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const enhancedButtons = document.getElementById('enhanced-buttons');
    
    // Restore original text to input field
    paragraphInput.innerHTML = originalText;
    paragraphInput.contentEditable = 'true';
    paragraphInput.style.cursor = 'text';
    
    // Show the analyze button and hide enhanced buttons
    analyzeBtn.style.display = 'block';
    if (enhancedButtons) {
        enhancedButtons.remove();
    }
    
    // Focus the input
    paragraphInput.focus();
}

export function resetAnalyzer() {
    const paragraphInput = document.getElementById('paragraph-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const resultsContainer = document.getElementById('analysis-results');
    const enhancedButtons = document.getElementById('enhanced-buttons');
    
    // Reset the input field to original state
    paragraphInput.innerHTML = '';
    paragraphInput.contentEditable = 'true';
    paragraphInput.style.cursor = 'text';
    paragraphInput.style.display = 'block';
    
    // Show the analyze button and remove enhanced buttons
    analyzeBtn.style.display = 'block';
    if (enhancedButtons) {
        enhancedButtons.remove();
    }
    
    // Hide the results
    resultsContainer.style.display = 'none';
    resultsContainer.innerHTML = '';
    
    // Reset variables
    originalText = '';
    currentEnhancements = [];
    currentSelectedWord = '';
    currentSelectedOptions.clear();
    
    // Focus the input
    paragraphInput.focus();
}

export function useEnhancedText() {
    showToast('Text is already updated in the input field!');
}

// Setup event listeners
export function setupParagraphAnalyzerEventListeners() {
    const analyzeBtn = document.getElementById('analyze-btn');
    const paragraphInput = document.getElementById('paragraph-input');
    
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeParagraph);
    }
    
    if (paragraphInput) {
        paragraphInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                analyzeParagraph();
            }
        });
        
        // Focus the input when the page loads
        paragraphInput.focus();
    }
}

// Export functions for global access (needed for onclick handlers)
window.openWordModal = openWordModal;
window.closeWordModal = closeWordModal;
window.toggleWordSelection = toggleWordSelection;
window.replaceWordInText = replaceWordInText;
window.copyEnhancedText = copyEnhancedText;
window.resetAnalyzer = resetAnalyzer;
window.backToOriginal = backToOriginal; 
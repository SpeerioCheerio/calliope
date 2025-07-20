// Frontend Utilities for Calliope Vocabulary App

// API Configuration
export const API_BASE = '/api';

// Utility Functions
export function showLoading() {
    document.getElementById('loading-overlay').classList.remove('hidden');
}

export function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

export function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // Remove toast after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

export async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Network error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showToast(`Error: ${error.message}`, 'error');
        throw error;
    }
}

// Navigation Functions
export function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show target section
    document.getElementById(sectionId).classList.add('active');
}

// Word Display Utilities
export function getSentimentIcon(sentiment) {
    const icons = {
        positive: '<span class="sentiment-positive"></span>',
        negative: '<span class="sentiment-negative"></span>',
        neutral: '<span class="sentiment-neutral"></span>',
        formal: '<span class="sentiment-formal"></span>'
    };
    return icons[sentiment] || '';
}

export function formatWordCard(word) {
    return `
        <div class="word-card rarity-${word.rarity}">
            <div class="word-header">
                <span class="word-title">${word.word}</span>
                <span class="word-pos">${word.pos}</span>
            </div>
            <div class="word-definition">${word.definition}</div>
            <div class="word-example">"${word.example_sentence}"</div>
            <div class="word-badges">
                <span class="rarity-badge rarity-${word.rarity}">${word.rarity}</span>
                <span class="sentiment-icon">${getSentimentIcon(word.sentiment)}</span>
            </div>
        </div>
    `;
}

// DOM Utilities
export function createElement(tag, className = '', textContent = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (textContent) element.textContent = textContent;
    return element;
}

export function clearContainer(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '';
    }
}

// Form Utilities
export function validateWordInput(word) {
    if (!word || word.trim().length === 0) {
        return { valid: false, message: 'Please enter a word' };
    }
    
    if (word.length > 100) {
        return { valid: false, message: 'Word is too long (max 100 characters)' };
    }
    
    if (!/^[a-zA-Z\s\-']+$/.test(word)) {
        return { valid: false, message: 'Word contains invalid characters' };
    }
    
    return { valid: true, message: '' };
}

// Local Storage Utilities
export function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
        console.warn('Failed to save to localStorage:', error);
    }
}

export function loadFromLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.warn('Failed to load from localStorage:', error);
        return defaultValue;
    }
}

// Array Utilities
export function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

// Text Processing Utilities
export function sanitizeText(text) {
    return text.replace(/[<>\"']/g, '').trim();
}

export function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

// Error Display Utilities
export function displayError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="error-message">
                <p>${message}</p>
            </div>
        `;
    }
}

export function displayNoResults(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="no-results">
                <p>${message}</p>
            </div>
        `;
    }
}

// Keyboard Event Utilities
export function setupEnterKeyHandler(elementId, callback) {
    const element = document.getElementById(elementId);
    if (element) {
        element.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                callback();
            }
        });
    }
}

// Animation Utilities
export function fadeIn(element, duration = 300) {
    element.style.opacity = '0';
    element.style.display = 'block';
    
    let start = null;
    function animate(timestamp) {
        if (!start) start = timestamp;
        const progress = timestamp - start;
        const opacity = Math.min(progress / duration, 1);
        
        element.style.opacity = opacity;
        
        if (progress < duration) {
            requestAnimationFrame(animate);
        }
    }
    
    requestAnimationFrame(animate);
}

export function fadeOut(element, duration = 300) {
    let start = null;
    const initialOpacity = parseFloat(window.getComputedStyle(element).opacity);
    
    function animate(timestamp) {
        if (!start) start = timestamp;
        const progress = timestamp - start;
        const opacity = initialOpacity * (1 - Math.min(progress / duration, 1));
        
        element.style.opacity = opacity;
        
        if (progress < duration) {
            requestAnimationFrame(animate);
        } else {
            element.style.display = 'none';
        }
    }
    
    requestAnimationFrame(animate);
} 
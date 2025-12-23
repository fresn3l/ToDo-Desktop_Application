/**
 * Utility Functions Module
 * 
 * Provides common utility functions used throughout the application.
 */

/**
 * Escape HTML special characters to prevent XSS attacks
 * 
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML-safe text
 */
export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Display a success notification to the user
 * 
 * Creates a temporary notification that appears at the top of the screen,
 * fades in, displays for 3 seconds, then fades out and removes itself.
 * 
 * @param {string} message - Success message to display
 */
export function showSuccessFeedback(message) {
    const feedback = document.createElement('div');
    feedback.className = 'feedback feedback-success';
    feedback.textContent = message;
    
    document.body.appendChild(feedback);
    
    setTimeout(() => {
        feedback.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        feedback.classList.remove('show');
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}

/**
 * Display an error notification to the user
 * 
 * Creates a temporary notification that appears at the top of the screen,
 * fades in, displays for 3 seconds, then fades out and removes itself.
 * 
 * @param {string} message - Error message to display
 */
export function showErrorFeedback(message) {
    const feedback = document.createElement('div');
    feedback.className = 'feedback feedback-error';
    feedback.textContent = message;
    
    document.body.appendChild(feedback);
    
    setTimeout(() => {
        feedback.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        feedback.classList.remove('show');
        setTimeout(() => feedback.remove(), 300);
    }, 3000);
}

/**
 * Format a date string for display
 * 
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
export function formatDate(dateString) {
    if (!dateString) return '';
    try {
        return new Date(dateString).toLocaleDateString();
    } catch (e) {
        return dateString;
    }
}

/**
 * Check if a date is overdue
 * 
 * @param {string} dueDate - ISO date string
 * @param {boolean} completed - Whether task is completed
 * @returns {boolean} True if overdue
 */
export function isOverdue(dueDate, completed) {
    if (!dueDate || completed) return false;
    try {
        return new Date(dueDate) < new Date();
    } catch (e) {
        return false;
    }
}

/**
 * Debounce function to limit how often a function can be called
 * 
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

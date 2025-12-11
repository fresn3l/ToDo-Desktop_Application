/**
 * Utility Functions Module
 * 
 * Common utility functions used throughout the application.
 */

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML string
 */
export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format date for display
 * @param {string} dateString - Date string to format
 * @returns {string} Formatted date string
 */
export function formatDate(dateString) {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString();
}

/**
 * Check if a date is overdue
 * @param {string} dateString - Date string to check
 * @param {boolean} completed - Whether the task is completed
 * @returns {boolean} True if overdue
 */
export function isOverdue(dateString, completed) {
    if (!dateString || completed) return false;
    return new Date(dateString) < new Date();
}

/**
 * Priority order mapping
 */
export const PRIORITY_ORDER = { 
    Today: 4, 
    Now: 3, 
    Next: 2, 
    Later: 1, 
    Someday: 0 
};


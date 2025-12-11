/**
 * Tabs Module
 * 
 * Handles tab switching functionality.
 */

import { loadAnalytics, setupAnalytics } from './analytics.js';

/**
 * Setup tab buttons
 */
export function setupTabs() {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

/**
 * Switch to a specific tab
 */
export function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    const activeTab = document.getElementById(`${tabName}Tab`);
    if (activeTab) {
        activeTab.classList.add('active');
    }
    
    // If switching to analytics tab, load analytics data
    if (tabName === 'analytics') {
        loadAnalytics();
        setupAnalytics();
    }
}


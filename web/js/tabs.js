/**
 * Tabs Module
 * 
 * Handles tab navigation system
 */

import { loadAnalytics, setupAnalytics } from './analytics.js';
import { loadPastEntries } from './journal.js';
import { loadNotificationSettings } from './notifications.js';

// ============================================
// TAB NAVIGATION
// ============================================

// Store reference to tabs container for event delegation
let tabsContainer = null;

/**
 * Initialize tab navigation system using event delegation
 */
export function setupTabs() {
    // Find the tabs container
    tabsContainer = document.querySelector('.tabs');
    
    if (!tabsContainer) {
        setTimeout(setupTabs, 100);
        return;
    }
    
    // Get all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    
    if (tabButtons.length === 0) {
        setTimeout(setupTabs, 100);
        return;
    }
    
    // Use event delegation - single listener on container (more efficient)
    if (tabsContainer._tabClickHandler) {
        tabsContainer.removeEventListener('click', tabsContainer._tabClickHandler);
    }
    
    tabsContainer._tabClickHandler = (e) => {
        const button = e.target.closest('.tab-button');
        
        if (button) {
            e.preventDefault();
            e.stopPropagation();
            
            const tabName = button.getAttribute('data-tab');
            
            if (tabName) {
                switchTab(tabName).catch(err => {
                    console.error('Error switching tab:', err);
                });
            }
        }
    };
    
    tabsContainer.addEventListener('click', tabsContainer._tabClickHandler);
    
    // Ensure buttons are accessible
    tabButtons.forEach((button) => {
        button.style.pointerEvents = 'auto';
        button.style.cursor = 'pointer';
        button.setAttribute('tabindex', '0');
    });
}

/**
 * Switch to a different tab
 */
export async function switchTab(tabName) {
    try {
        // Update tab button active states
        const allButtons = document.querySelectorAll('.tab-button');
        allButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (!activeButton) {
            console.warn('Tab button not found for:', tabName);
            return;
        }
        
        activeButton.classList.add('active');
        
        // Update tab content visibility
        const allTabs = document.querySelectorAll('.tab-content');
        allTabs.forEach(content => {
            content.classList.remove('active');
        });
        
        const activeTab = document.getElementById(`${tabName}Tab`);
        if (!activeTab) {
            console.warn('Tab content not found for:', tabName);
            return;
        }
        
        activeTab.classList.add('active');
        
        // Load tab-specific data if needed
        try {
            if (tabName === 'analytics') {
                await loadAnalytics();
                setupAnalytics();
            } else if (tabName === 'journal') {
                await loadPastEntries();
            } else if (tabName === 'settings') {
                await loadNotificationSettings();
            }
        } catch (err) {
            console.error(`Error loading data for ${tabName} tab:`, err);
        }
    } catch (error) {
        console.error('Error in switchTab:', error);
        throw error;
    }
}

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
        console.warn('Tabs container not found, retrying...');
        setTimeout(setupTabs, 100);
        return;
    }
    
    // Get all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    
    if (tabButtons.length === 0) {
        console.warn('No tab buttons found, retrying...');
        setTimeout(setupTabs, 100);
        return;
    }
    
    console.log('Setting up tabs:', tabButtons.length, 'buttons found');
    
    // Remove any existing listeners
    if (tabsContainer._tabClickHandler) {
        tabsContainer.removeEventListener('click', tabsContainer._tabClickHandler);
        delete tabsContainer._tabClickHandler;
    }
    
    // Use event delegation - single listener on container
    tabsContainer._tabClickHandler = (e) => {
        const button = e.target.closest('.tab-button');
        
        if (button) {
            e.preventDefault();
            e.stopPropagation();
            
            const tabName = button.getAttribute('data-tab');
            console.log('Tab clicked:', tabName);
            
            if (tabName) {
                switchTab(tabName).catch(err => {
                    console.error('Error switching tab:', err);
                });
            }
        }
    };
    
    tabsContainer.addEventListener('click', tabsContainer._tabClickHandler, true);
    
    // Also add direct listeners to each button as backup
    tabButtons.forEach((button) => {
        const tabName = button.getAttribute('data-tab');
        
        // Ensure button is accessible
        button.style.pointerEvents = 'auto';
        button.style.cursor = 'pointer';
        button.setAttribute('tabindex', '0');
        
        // Remove old listener if exists
        if (button._directHandler) {
            button.removeEventListener('click', button._directHandler);
        }
        
        // Direct click handler as backup
        button._directHandler = (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Direct tab click:', tabName);
            switchTab(tabName).catch(err => {
                console.error('Error switching tab:', err);
            });
        };
        
        button.addEventListener('click', button._directHandler, true);
    });
    
    console.log('Tabs setup complete');
}

/**
 * Switch to a different tab
 */
export async function switchTab(tabName) {
    try {
        console.log('Switching to tab:', tabName);
        
        // Update tab button active states
        const allButtons = document.querySelectorAll('.tab-button');
        allButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (!activeButton) {
            console.error('Tab button not found for:', tabName);
            return;
        }
        
        activeButton.classList.add('active');
        console.log('Tab button activated');
        
        // Update tab content visibility
        const allTabs = document.querySelectorAll('.tab-content');
        allTabs.forEach(content => {
            content.classList.remove('active');
        });
        
        const activeTab = document.getElementById(`${tabName}Tab`);
        if (!activeTab) {
            console.error('Tab content not found for:', tabName, 'Looking for:', `${tabName}Tab`);
            // List available tabs for debugging
            const availableTabs = Array.from(allTabs).map(t => t.id);
            console.log('Available tab contents:', availableTabs);
            return;
        }
        
        activeTab.classList.add('active');
        console.log('Tab content activated:', activeTab.id);
        
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
        console.error('Stack:', error.stack);
        throw error;
    }
}

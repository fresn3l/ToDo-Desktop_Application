/**
 * Notifications Module
 * 
 * Handles notification settings UI and management
 */

import * as utils from './utils.js';

// ============================================
// NOTIFICATION SETTINGS
// ============================================

/**
 * Load and display current notification settings
 */
export async function loadNotificationSettings() {
    try {
        const settings = await eel.get_notification_settings()();
        
        const enabledCheckbox = document.getElementById('notificationsEnabled');
        const emailInput = document.getElementById('notificationEmail');
        const smtpPortInput = document.getElementById('smtpPort');
        const emailUsernameInput = document.getElementById('emailUsername');
        const emailPasswordInput = document.getElementById('emailPassword');
        const checkIntervalInput = document.getElementById('checkInterval');
        
        if (enabledCheckbox) enabledCheckbox.checked = settings.enabled || false;
        if (emailInput) emailInput.value = settings.email || '';
        if (smtpPortInput) smtpPortInput.value = settings.smtp_port || 587;
        if (emailUsernameInput) emailUsernameInput.value = settings.email_username || '';
        if (emailPasswordInput) emailPasswordInput.value = settings.email_password || '';
        if (checkIntervalInput) checkIntervalInput.value = settings.check_interval_hours || 1;
        
        const smtpSelect = document.getElementById('smtpServer');
        const customSmtpGroup = document.getElementById('customSmtpGroup');
        const customSmtpInput = document.getElementById('customSmtpServer');
        
        if (smtpSelect && settings.smtp_server) {
            const presetOptions = ['smtp.gmail.com', 'smtp.mail.me.com', 'smtp-mail.outlook.com'];
            if (presetOptions.includes(settings.smtp_server)) {
                smtpSelect.value = settings.smtp_server;
                if (customSmtpGroup) customSmtpGroup.style.display = 'none';
            } else {
                smtpSelect.value = 'custom';
                if (customSmtpGroup) customSmtpGroup.style.display = 'block';
                if (customSmtpInput) customSmtpInput.value = settings.smtp_server;
            }
        }
    } catch (error) {
        console.error('Error loading notification settings:', error);
    }
}

/**
 * Setup notification settings form event listeners
 */
export function setupNotificationSettings() {
    const form = document.getElementById('notificationSettingsForm');
    const smtpSelect = document.getElementById('smtpServer');
    const customSmtpGroup = document.getElementById('customSmtpGroup');
    const testBtn = document.getElementById('testNotificationBtn');
    
    if (smtpSelect) {
        smtpSelect.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                customSmtpGroup.style.display = 'block';
            } else {
                customSmtpGroup.style.display = 'none';
            }
        });
    }
    
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveNotificationSettings();
        });
    }
    
    if (testBtn) {
        testBtn.addEventListener('click', async () => {
            await testNotification();
        });
    }
}

/**
 * Save notification settings
 */
async function saveNotificationSettings() {
    try {
        const enabledCheckbox = document.getElementById('notificationsEnabled');
        const emailInput = document.getElementById('notificationEmail');
        const smtpSelect = document.getElementById('smtpServer');
        const customSmtpInput = document.getElementById('customSmtpServer');
        const smtpPortInput = document.getElementById('smtpPort');
        const emailUsernameInput = document.getElementById('emailUsername');
        const emailPasswordInput = document.getElementById('emailPassword');
        const checkIntervalInput = document.getElementById('checkInterval');
        
        if (!enabledCheckbox || !emailInput || !smtpSelect || !smtpPortInput || 
            !emailUsernameInput || !emailPasswordInput || !checkIntervalInput) {
            utils.showErrorFeedback('Settings form not found. Please refresh the page.');
            return;
        }
        
        const enabled = enabledCheckbox.checked;
        const email = emailInput.value.trim();
        const smtpPort = parseInt(smtpPortInput.value) || 587;
        const emailUsername = emailUsernameInput.value.trim();
        const emailPassword = emailPasswordInput.value;
        const checkInterval = parseInt(checkIntervalInput.value) || 1;
        
        let smtpServer = smtpSelect.value;
        if (smtpServer === 'custom') {
            if (!customSmtpInput) {
                utils.showErrorFeedback('Custom SMTP server input not found.');
                return;
            }
            smtpServer = customSmtpInput.value.trim();
        }
        
        if (enabled) {
            if (!email) {
                utils.showErrorFeedback('Please enter your email address');
                return;
            }
            if (!smtpServer) {
                utils.showErrorFeedback('Please enter SMTP server');
                return;
            }
            if (!emailUsername) {
                utils.showErrorFeedback('Please enter email username');
                return;
            }
            if (!emailPassword) {
                utils.showErrorFeedback('Please enter email password');
                return;
            }
        }
        
        await eel.update_notification_settings(
            enabled,
            email,
            smtpServer,
            smtpPort,
            emailUsername,
            emailPassword,
            checkInterval
        )();
        
        utils.showSuccessFeedback('Notification settings saved successfully!');
    } catch (error) {
        console.error('Error saving notification settings:', error);
        utils.showErrorFeedback('Failed to save settings. Please try again.');
    }
}

/**
 * Send a test notification
 */
async function testNotification() {
    try {
        const emailInput = document.getElementById('notificationEmail');
        const testBtn = document.getElementById('testNotificationBtn');
        
        if (!emailInput || !testBtn) {
            utils.showErrorFeedback('Notification form elements not found. Please refresh the page.');
            return;
        }
        
        const email = emailInput.value.trim();
        if (!email) {
            utils.showErrorFeedback('Please enter your email address first');
            return;
        }
        
        const originalText = testBtn.textContent;
        testBtn.textContent = 'Sending...';
        testBtn.disabled = true;
        
        const result = await eel.test_notification(email)();
        
        if (result && result.success) {
            utils.showSuccessFeedback(result.message || 'Test notification sent successfully!');
        } else {
            utils.showErrorFeedback(result?.message || 'Failed to send test notification. Please check your settings.');
        }
        
        testBtn.textContent = originalText;
        testBtn.disabled = false;
    } catch (error) {
        console.error('Error sending test notification:', error);
        utils.showErrorFeedback('Failed to send test notification. Please check your settings.');
        const testBtn = document.getElementById('testNotificationBtn');
        if (testBtn) {
            testBtn.disabled = false;
            testBtn.textContent = 'Send Test Notification';
        }
    }
}


/**
 * UI Utilities Module
 * 
 * Functions for UI interactions, animations, and feedback.
 */

/**
 * Show loading state in containers
 */
export function showLoadingState() {
    const containers = ['tasksContainer', 'goalsContainer'];
    containers.forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Loading...</p></div>';
        }
    });
}

/**
 * Hide loading state (content will replace it)
 */
export function hideLoadingState() {
    // Loading state will be replaced by actual content
}

/**
 * Animate elements on load with staggered entrance
 */
export function animateElements() {
    const elements = document.querySelectorAll('.task-item, .goal-item, .category-header');
    elements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        setTimeout(() => {
            el.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 50);
    });
}

/**
 * Add ripple effect to buttons on click
 * @param {HTMLElement} button - Button element to add ripple to
 */
export function addRippleEffect(button) {
    button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        this.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
}

/**
 * Show success feedback toast
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
 * Show error feedback toast
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


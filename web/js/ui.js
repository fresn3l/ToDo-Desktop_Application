/**
 * UI Utility Functions Module
 * 
 * Provides UI-related helper functions for loading states, animations, and visual effects.
 */

/**
 * Display loading indicators in specified containers
 * Shows a spinner and "Loading..." text while data is being fetched
 * 
 * @param {string[]} containerIds - Array of container IDs to show loading state
 */
export function showLoadingState(containerIds = ['tasksContainer', 'goalsContainer']) {
    containerIds.forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Loading...</p></div>';
        }
    });
}

/**
 * Hide loading indicators
 * Loading state is automatically replaced when actual content is rendered
 */
export function hideLoadingState() {
    // Loading state will be replaced by actual content when render functions are called
}

/**
 * Animate elements on page load for smooth entrance effect
 * 
 * Animation sequence:
 * 1. Elements start invisible and slightly below their final position
 * 2. Each element fades in and slides up with a staggered delay
 * 3. Creates a cascading entrance effect
 * 
 * Elements animated:
 * - .task-item: Individual task cards
 * - .goal-item: Individual goal cards
 * - .category-header: Category/group headers
 */
export function animateElements() {
    const elements = document.querySelectorAll('.task-item, .goal-item, .category-header');
    elements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 50);
    });
}

/**
 * Add ripple effect to buttons for visual feedback
 * 
 * Creates a ripple animation when a button is clicked, providing
 * tactile feedback similar to Material Design.
 * 
 * @param {HTMLElement} button - Button element to add ripple effect to
 */
export function addRippleEffect(button) {
    if (!button) return;
    
    button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        ripple.classList.add('ripple-effect');
        
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
 * Scroll element into view smoothly
 * 
 * @param {HTMLElement|string} element - Element or selector to scroll to
 */
export function scrollToElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

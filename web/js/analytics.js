/**
 * Analytics Module
 * 
 * Handles analytics rendering and drag/resize functionality
 */

import * as utils from './utils.js';

// ============================================
// ANALYTICS DATA LOADING
// ============================================

/**
 * Load analytics data from backend and render it
 */
export async function loadAnalytics() {
    try {
        const analytics = await eel.get_analytics()();
        renderAnalytics(analytics);
    } catch (error) {
        console.error('Error loading analytics:', error);
        const container = document.getElementById('analyticsContainer');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Error loading analytics</h3>
                    <p>Please try again later.</p>
                </div>
            `;
        }
    }
}

// ============================================
// ANALYTICS RENDERING
// ============================================

/**
 * Render analytics data in the analytics container
 */
function renderAnalytics(analytics) {
    const container = document.getElementById('analyticsContainer');
    
    if (!container) {
        console.error('Analytics container not found');
        return;
    }
    
    if (!analytics || !analytics.overall || analytics.overall.total === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No Data Available</h3>
                <p>Create some tasks to see analytics!</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    // Overall Statistics Card
    html += `
        <div class="analytics-card draggable-card resizable-card" data-card-id="overall-stats">
            <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
            <div class="card-resize-handle" title="Drag to resize"></div>
            <div class="analytics-card-header">
                <h3>📊 Overall Statistics</h3>
            </div>
            <div class="analytics-card-content">
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-value">${analytics.overall.total}</div>
                        <div class="stat-label">Total Tasks</div>
                    </div>
                    <div class="stat-item stat-success">
                        <div class="stat-value">${analytics.overall.completed}</div>
                        <div class="stat-label">Completed</div>
                    </div>
                    <div class="stat-item stat-warning">
                        <div class="stat-value">${analytics.overall.incomplete || 0}</div>
                        <div class="stat-label">Incomplete</div>
                    </div>
                    ${analytics.overall.not_completed !== undefined ? `
                    <div class="stat-item stat-danger">
                        <div class="stat-value">${analytics.overall.not_completed || 0}</div>
                        <div class="stat-label">Not Completed (Overdue)</div>
                    </div>
                    ` : ''}
                    <div class="stat-item stat-primary">
                        <div class="stat-value">${(analytics.overall.completion_percentage || 0).toFixed(1)}%</div>
                        <div class="stat-label">Completion Rate</div>
                    </div>
                </div>
                <div class="progress-bar-large">
                    <div class="progress-fill-large" style="width: ${analytics.overall.completion_percentage}%"></div>
                </div>
            </div>
        </div>
    `;
    
    // Goal Statistics Card
    if (analytics.by_goal && analytics.by_goal.goals && 
        typeof analytics.by_goal.goals === 'object' && 
        Object.keys(analytics.by_goal.goals).length > 0) {
        html += `
            <div class="analytics-card draggable-card resizable-card" data-card-id="goal-breakdown">
                <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
                <div class="card-resize-handle" title="Drag to resize"></div>
                <div class="analytics-card-header">
                    <h3>🎯 Goal Breakdown</h3>
                </div>
                <div class="analytics-card-content">
        `;
        
        const sortedGoals = Object.entries(analytics.by_goal.goals)
            .sort((a, b) => b[1].completion_percentage - a[1].completion_percentage);
        
        sortedGoals.forEach(([goalId, stats]) => {
            html += `
                <div class="category-stat-row">
                    <div class="category-stat-header">
                        <span class="category-name">${utils.escapeHtml(stats.goal_name)}</span>
                        <span class="category-percentage">${stats.completion_percentage}%</span>
                    </div>
                    <div class="category-stat-details">
                        <span>${stats.completed} of ${stats.total} completed</span>
                        <span>${stats.incomplete} remaining</span>
                    </div>
                    <div class="progress-bar-small">
                        <div class="progress-fill-small" style="width: ${stats.completion_percentage}%"></div>
                    </div>
                </div>
            `;
        });
        
        html += `</div></div>`;
    }
    
    // Priority Statistics Card
    html += `
        <div class="analytics-card draggable-card resizable-card" data-card-id="priority-analysis">
            <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
            <div class="card-resize-handle" title="Drag to resize"></div>
            <div class="analytics-card-header">
                <h3>⚡ Priority Analysis</h3>
            </div>
            <div class="analytics-card-content">
    `;
    
    const priorities = ['Now', 'Next', 'Later'];
    priorities.forEach(priority => {
        const stats = analytics.by_priority && analytics.by_priority[priority];
        if (stats) {
            const priorityClass = priority === 'Now' ? 'priority-now' : priority === 'Next' ? 'priority-next' : 'priority-later';
            html += `
                <div class="priority-stat-row ${priorityClass}">
                    <div class="priority-stat-header">
                        <span class="priority-name">${priority}</span>
                        <span class="priority-count">${stats.total} tasks</span>
                    </div>
                    <div class="priority-stat-details">
                        <span>✅ ${stats.completed} completed</span>
                        <span>⏳ ${stats.incomplete} incomplete</span>
                        <span class="priority-percentage">${stats.completion_percentage}%</span>
                    </div>
                    <div class="progress-bar-small">
                        <div class="progress-fill-small" style="width: ${stats.completion_percentage}%"></div>
                    </div>
                </div>
            `;
        }
    });
    
    html += `</div></div>`;
    
    // Goal Progress Card
    if (analytics.by_goal.total_goals > 0) {
        html += `
            <div class="analytics-card draggable-card resizable-card" data-card-id="goal-progress">
                <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
                <div class="card-resize-handle" title="Drag to resize"></div>
                <div class="analytics-card-header">
                    <h3>🎯 Goal Progress</h3>
                </div>
                <div class="analytics-card-content">
                    <div class="goal-stats-summary">
                        <div class="goal-stat-summary-item">
                            <span class="summary-label">Total Goals:</span>
                            <span class="summary-value">${analytics.by_goal.total_goals}</span>
                        </div>
                        <div class="goal-stat-summary-item">
                            <span class="summary-label">Tasks with Goals:</span>
                            <span class="summary-value">${analytics.by_goal.tasks_with_goals}</span>
                        </div>
                        <div class="goal-stat-summary-item">
                            <span class="summary-label">Tasks without Goals:</span>
                            <span class="summary-value">${analytics.by_goal.tasks_without_goals}</span>
                        </div>
                    </div>
        `;
        
        Object.values(analytics.by_goal.goals).forEach(goalStat => {
            html += `
                <div class="goal-stat-row">
                    <div class="goal-stat-header">
                        <span class="goal-name">${utils.escapeHtml(goalStat.goal_name)}</span>
                        <span class="goal-percentage">${goalStat.completion_percentage}%</span>
                    </div>
                    <div class="goal-stat-details">
                        <span>${goalStat.completed} of ${goalStat.total} tasks completed</span>
                    </div>
                    <div class="progress-bar-small">
                        <div class="progress-fill-small" style="width: ${goalStat.completion_percentage}%"></div>
                    </div>
                </div>
            `;
        });
        
        html += `</div></div>`;
    }
    
    // Time Statistics Card
    if (analytics.time_stats) {
        html += `
            <div class="analytics-card draggable-card resizable-card" data-card-id="time-analysis">
                <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
                <div class="card-resize-handle" title="Drag to resize"></div>
                <div class="analytics-card-header">
                    <h3>⏰ Time Analysis</h3>
                </div>
                <div class="analytics-card-content">
                    <div class="time-stats-grid">
                        <div class="time-stat-item ${(analytics.time_stats.overdue_count || 0) > 0 ? 'stat-danger' : ''}">
                            <div class="time-stat-icon">🚨</div>
                            <div class="time-stat-value">${analytics.time_stats.overdue_count || 0}</div>
                            <div class="time-stat-label">Overdue Tasks</div>
                        </div>
                        <div class="time-stat-item ${(analytics.time_stats.due_soon_count || 0) > 0 ? 'stat-warning' : ''}">
                            <div class="time-stat-icon">⏳</div>
                            <div class="time-stat-value">${analytics.time_stats.due_soon_count || 0}</div>
                            <div class="time-stat-label">Due Soon (7 days)</div>
                        </div>
                        <div class="time-stat-item stat-success">
                            <div class="time-stat-icon">✅</div>
                            <div class="time-stat-value">${analytics.time_stats.completed_today || 0}</div>
                            <div class="time-stat-label">Completed Today</div>
                        </div>
                        <div class="time-stat-item stat-primary">
                            <div class="time-stat-icon">➕</div>
                            <div class="time-stat-value">${analytics.time_stats.created_today || 0}</div>
                            <div class="time-stat-label">Created Today</div>
                        </div>
                        <div class="time-stat-item">
                            <div class="time-stat-icon">📅</div>
                            <div class="time-stat-value">${(analytics.time_stats.avg_completion_days || 0).toFixed(1)}</div>
                            <div class="time-stat-label">Avg Days to Complete</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Productivity Metrics Card
    if (analytics.productivity) {
        html += `
            <div class="analytics-card draggable-card resizable-card" data-card-id="productivity-insights">
                <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
                <div class="card-resize-handle" title="Drag to resize"></div>
                <div class="analytics-card-header">
                    <h3>🚀 Productivity Insights</h3>
                </div>
                <div class="analytics-card-content">
        `;
        
        if (analytics.productivity.most_productive_goal) {
            html += `
                <div class="insight-item">
                    <div class="insight-icon">🏆</div>
                    <div class="insight-content">
                        <div class="insight-title">Most Productive Goal</div>
                        <div class="insight-value">${utils.escapeHtml(analytics.productivity.most_productive_goal)}</div>
                        <div class="insight-detail">${(analytics.productivity.most_productive_completion_rate || 0).toFixed(1)}% completion rate</div>
                    </div>
                </div>
            `;
        }
        
        if (analytics.productivity.goal_with_most_tasks) {
            html += `
                <div class="insight-item">
                    <div class="insight-icon">📊</div>
                    <div class="insight-content">
                        <div class="insight-title">Most Active Goal</div>
                        <div class="insight-value">${utils.escapeHtml(analytics.productivity.goal_with_most_tasks)}</div>
                        <div class="insight-detail">${analytics.productivity.max_tasks_in_goal || 0} tasks</div>
                    </div>
                </div>
            `;
        }
        
        if (analytics.productivity.goal_distribution && 
            typeof analytics.productivity.goal_distribution === 'object' &&
            Object.keys(analytics.productivity.goal_distribution).length > 0) {
            html += `
                <div class="insight-item">
                    <div class="insight-icon">📈</div>
                    <div class="insight-content">
                        <div class="insight-title">Task Distribution</div>
                        <div class="distribution-list">
            `;
            
            const sortedDist = Object.entries(analytics.productivity.goal_distribution)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);
            
            sortedDist.forEach(([goalName, percentage]) => {
                html += `
                    <div class="distribution-item">
                        <span class="dist-category">${utils.escapeHtml(goalName)}</span>
                        <span class="dist-percentage">${percentage}%</span>
                    </div>
                `;
            });
            
            html += `</div></div></div>`;
        }
        
        html += `</div></div>`;
    }
    
    container.innerHTML = html;
    
    loadCardPositions();
    initializeDragAndResize();
}

/**
 * Load saved card positions and sizes from localStorage
 */
function loadCardPositions() {
    try {
        const savedPositions = localStorage.getItem('analyticsCardPositions');
        const savedSizes = localStorage.getItem('analyticsCardSizes');
        
        if (savedPositions) {
            const positions = JSON.parse(savedPositions);
            Object.entries(positions).forEach(([cardId, pos]) => {
                const card = document.querySelector(`[data-card-id="${cardId}"]`);
                if (card) {
                    card.style.position = 'absolute';
                    card.style.left = pos.x + 'px';
                    card.style.top = pos.y + 'px';
                }
            });
        }
        
        if (savedSizes) {
            const sizes = JSON.parse(savedSizes);
            Object.entries(sizes).forEach(([cardId, size]) => {
                const card = document.querySelector(`[data-card-id="${cardId}"]`);
                if (card) {
                    card.style.width = size.width + 'px';
                    card.style.height = size.height + 'px';
                }
            });
        }
    } catch (error) {
        console.error('Error loading card positions:', error);
    }
}

/**
 * Initialize drag and resize functionality for analytics cards
 */
function initializeDragAndResize() {
    const cards = document.querySelectorAll('.draggable-card');
    
    cards.forEach(card => {
        const dragHandle = card.querySelector('.card-drag-handle');
        const resizeHandle = card.querySelector('.card-resize-handle');
        
        card.addEventListener('mouseenter', () => {
            if (dragHandle) dragHandle.style.opacity = '1';
            if (resizeHandle) resizeHandle.style.opacity = '1';
        });
        
        card.addEventListener('mouseleave', () => {
            if (dragHandle) dragHandle.style.opacity = '0';
            if (resizeHandle) resizeHandle.style.opacity = '0';
        });
        
        if (dragHandle) {
            let isDragging = false;
            let startX, startY, initialX, initialY;
            
            dragHandle.addEventListener('mousedown', (e) => {
                isDragging = true;
                card.classList.add('dragging');
                startX = e.clientX;
                startY = e.clientY;
                
                const rect = card.getBoundingClientRect();
                initialX = rect.left;
                initialY = rect.top;
                
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                
                const deltaX = e.clientX - startX;
                const deltaY = e.clientY - startY;
                
                card.style.position = 'absolute';
                card.style.left = (initialX + deltaX) + 'px';
                card.style.top = (initialY + deltaY) + 'px';
                card.style.zIndex = '1000';
            });
            
            document.addEventListener('mouseup', () => {
                if (isDragging) {
                    isDragging = false;
                    card.classList.remove('dragging');
                    card.style.zIndex = '';
                    saveCardPosition(card);
                }
            });
        }
        
        if (resizeHandle) {
            let isResizing = false;
            let startX, startY, startWidth, startHeight;
            
            resizeHandle.addEventListener('mousedown', (e) => {
                isResizing = true;
                card.classList.add('resizing');
                startX = e.clientX;
                startY = e.clientY;
                
                const rect = card.getBoundingClientRect();
                startWidth = rect.width;
                startHeight = rect.height;
                
                e.preventDefault();
                e.stopPropagation();
            });
            
            document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;
                
                const deltaX = e.clientX - startX;
                const deltaY = e.clientY - startY;
                
                const newWidth = Math.max(300, startWidth + deltaX);
                const newHeight = Math.max(200, startHeight + deltaY);
                
                card.style.width = newWidth + 'px';
                card.style.height = newHeight + 'px';
            });
            
            document.addEventListener('mouseup', () => {
                if (isResizing) {
                    isResizing = false;
                    card.classList.remove('resizing');
                    saveCardSize(card);
                }
            });
        }
    });
}

/**
 * Save card position to localStorage
 */
function saveCardPosition(card) {
    try {
        const cardId = card.getAttribute('data-card-id');
        if (!cardId) return;
        
        const rect = card.getBoundingClientRect();
        const positions = JSON.parse(localStorage.getItem('analyticsCardPositions') || '{}');
        positions[cardId] = { x: rect.left, y: rect.top };
        localStorage.setItem('analyticsCardPositions', JSON.stringify(positions));
    } catch (error) {
        console.error('Error saving card position:', error);
    }
}

/**
 * Save card size to localStorage
 */
function saveCardSize(card) {
    try {
        const cardId = card.getAttribute('data-card-id');
        if (!cardId) return;
        
        const sizes = JSON.parse(localStorage.getItem('analyticsCardSizes') || '{}');
        sizes[cardId] = { 
            width: parseInt(card.style.width) || card.offsetWidth,
            height: parseInt(card.style.height) || card.offsetHeight
        };
        localStorage.setItem('analyticsCardSizes', JSON.stringify(sizes));
    } catch (error) {
        console.error('Error saving card size:', error);
    }
}

// ============================================
// ANALYTICS EVENT LISTENERS
// ============================================

/**
 * Setup analytics tab functionality
 */
export function setupAnalytics() {
    const refreshBtn = document.getElementById('refreshAnalytics');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            refreshBtn.textContent = 'Refreshing...';
            refreshBtn.disabled = true;
            
            await loadAnalytics();
            
            refreshBtn.textContent = 'Refresh Data';
            refreshBtn.disabled = false;
        });
    }
    
    const resetBtn = document.getElementById('resetCardLayout');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (confirm('Reset all card positions and sizes to default? This cannot be undone.')) {
                localStorage.removeItem('analyticsCardPositions');
                localStorage.removeItem('analyticsCardSizes');
                
                loadAnalytics();
                
                utils.showSuccessFeedback('Layout reset to default');
            }
        });
    }
}

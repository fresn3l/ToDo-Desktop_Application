/**
 * Analytics Module
 * 
 * Handles analytics data loading, rendering, and drag/resize functionality.
 */

import * as utils from './utils.js';
import * as ui from './ui.js';

/**
 * Load and display analytics data
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
                    <h3>Error Loading Analytics</h3>
                    <p>Unable to load analytics data. Please try again.</p>
                </div>
            `;
        }
    }
}

/**
 * Render analytics data in the UI
 */
function renderAnalytics(analytics) {
    const container = document.getElementById('analyticsContainer');
    if (!container) return;
    
    if (!analytics || analytics.overall.total === 0) {
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
                        <div class="stat-value">${analytics.overall.incomplete}</div>
                        <div class="stat-label">Incomplete</div>
                    </div>
                    <div class="stat-item stat-primary">
                        <div class="stat-value">${analytics.overall.completion_percentage}%</div>
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
    if (analytics.by_goal && analytics.by_goal.total_goals > 0) {
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
        
        if (analytics.by_goal.goals) {
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
        }
        
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
    
    const priorities = ['Today', 'Now', 'Next', 'Later', 'Someday'];
    priorities.forEach(priority => {
        const stats = analytics.by_priority[priority];
        if (stats) {
            const priorityClass = priority === 'Today' ? 'priority-today' : 
                                 priority === 'Now' ? 'priority-now' : 
                                 priority === 'Next' ? 'priority-next' : 
                                 priority === 'Later' ? 'priority-later' : 'priority-someday';
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
    
    // Time-Based Statistics Card
    html += `
        <div class="analytics-card draggable-card resizable-card" data-card-id="time-analysis">
            <div class="card-drag-handle" title="Drag to move">⋮⋮</div>
            <div class="card-resize-handle" title="Drag to resize"></div>
            <div class="analytics-card-header">
                <h3>⏰ Time Analysis</h3>
            </div>
            <div class="analytics-card-content">
                <div class="time-stats-grid">
                    <div class="time-stat-item ${analytics.time_stats.overdue_count > 0 ? 'stat-danger' : ''}">
                        <div class="time-stat-icon">🚨</div>
                        <div class="time-stat-value">${analytics.time_stats.overdue_count}</div>
                        <div class="time-stat-label">Overdue Tasks</div>
                    </div>
                    <div class="time-stat-item ${analytics.time_stats.due_soon_count > 0 ? 'stat-warning' : ''}">
                        <div class="time-stat-icon">⏳</div>
                        <div class="time-stat-value">${analytics.time_stats.due_soon_count}</div>
                        <div class="time-stat-label">Due Soon (7 days)</div>
                    </div>
                    <div class="time-stat-item stat-success">
                        <div class="time-stat-icon">✅</div>
                        <div class="time-stat-value">${analytics.time_stats.completed_today}</div>
                        <div class="time-stat-label">Completed Today</div>
                    </div>
                    <div class="time-stat-item stat-primary">
                        <div class="time-stat-icon">➕</div>
                        <div class="time-stat-value">${analytics.time_stats.created_today}</div>
                        <div class="time-stat-label">Created Today</div>
                    </div>
                    <div class="time-stat-item">
                        <div class="time-stat-icon">📅</div>
                        <div class="time-stat-value">${analytics.time_stats.avg_completion_days}</div>
                        <div class="time-stat-label">Avg Days to Complete</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Productivity Metrics Card
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
                    <div class="insight-detail">${analytics.productivity.most_productive_completion_rate}% completion rate</div>
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
                    <div class="insight-detail">${analytics.productivity.max_tasks_in_goal} tasks</div>
                </div>
            </div>
        `;
    }
    
    if (analytics.productivity.goal_distribution && Object.keys(analytics.productivity.goal_distribution).length > 0) {
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
        
        sortedDist.forEach(([goal, percentage]) => {
            html += `
                <div class="distribution-item">
                    <span class="dist-category">${utils.escapeHtml(goal)}</span>
                    <span class="dist-percentage">${percentage}%</span>
                </div>
            `;
        });
        
        html += `</div></div></div>`;
    }
    
    html += `</div></div>`;
    
    container.innerHTML = html;
    
    // Load saved positions and sizes
    loadCardPositions();
    
    // Initialize drag and resize functionality
    initializeDragAndResize();
}

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
                ui.showSuccessFeedback('Layout reset to default');
            }
        });
    }
}

/**
 * Initialize drag and resize functionality
 */
function initializeDragAndResize() {
    const cards = document.querySelectorAll('.draggable-card');
    
    cards.forEach(card => {
        const dragHandle = card.querySelector('.card-drag-handle');
        if (dragHandle) {
            dragHandle.style.cursor = 'move';
            dragHandle.addEventListener('mousedown', (e) => {
                startDragging(e, card);
            });
        }
        
        const resizeHandle = card.querySelector('.card-resize-handle');
        if (resizeHandle) {
            resizeHandle.style.cursor = 'nwse-resize';
            resizeHandle.addEventListener('mousedown', (e) => {
                startResizing(e, card);
            });
        }
    });
}

/**
 * Start dragging a card
 */
function startDragging(e, card) {
    e.preventDefault();
    
    const rect = card.getBoundingClientRect();
    const container = document.getElementById('analyticsContainer');
    const containerRect = container.getBoundingClientRect();
    
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;
    
    card.style.opacity = '0.8';
    card.style.zIndex = '1000';
    card.style.cursor = 'move';
    
    function handleMouseMove(e) {
        const newX = e.clientX - containerRect.left - offsetX;
        const newY = e.clientY - containerRect.top - offsetY;
        
        const maxX = containerRect.width - rect.width;
        const maxY = containerRect.height - rect.height;
        
        const clampedX = Math.max(0, Math.min(newX, maxX));
        const clampedY = Math.max(0, Math.min(newY, maxY));
        
        card.style.position = 'absolute';
        card.style.left = clampedX + 'px';
        card.style.top = clampedY + 'px';
        card.style.margin = '0';
    }
    
    function handleMouseUp() {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        card.style.opacity = '1';
        card.style.cursor = 'default';
        saveCardPosition(card);
    }
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
}

/**
 * Start resizing a card
 */
function startResizing(e, card) {
    e.preventDefault();
    e.stopPropagation();
    
    const rect = card.getBoundingClientRect();
    const container = document.getElementById('analyticsContainer');
    const containerRect = container.getBoundingClientRect();
    
    const startWidth = rect.width;
    const startHeight = rect.height;
    const startX = e.clientX;
    const startY = e.clientY;
    
    const minWidth = 300;
    const minHeight = 200;
    const maxWidth = containerRect.width - 20;
    const maxHeight = containerRect.height - 20;
    
    card.style.opacity = '0.8';
    card.style.zIndex = '1000';
    
    function handleMouseMove(e) {
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        
        let newWidth = startWidth + deltaX;
        let newHeight = startHeight + deltaY;
        
        newWidth = Math.max(minWidth, Math.min(newWidth, maxWidth));
        newHeight = Math.max(minHeight, Math.min(newHeight, maxHeight));
        
        card.style.width = newWidth + 'px';
        card.style.height = 'auto';
        card.style.minHeight = newHeight + 'px';
    }
    
    function handleMouseUp() {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        card.style.opacity = '1';
        saveCardSize(card);
    }
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
}

/**
 * Save card position to localStorage
 */
function saveCardPosition(card) {
    const cardId = card.getAttribute('data-card-id');
    if (!cardId) return;
    
    const left = card.style.left;
    const top = card.style.top;
    
    const savedPositions = JSON.parse(localStorage.getItem('analyticsCardPositions') || '{}');
    
    if (!savedPositions[cardId]) {
        savedPositions[cardId] = {};
    }
    savedPositions[cardId].left = left;
    savedPositions[cardId].top = top;
    
    localStorage.setItem('analyticsCardPositions', JSON.stringify(savedPositions));
}

/**
 * Save card size to localStorage
 */
function saveCardSize(card) {
    const cardId = card.getAttribute('data-card-id');
    if (!cardId) return;
    
    const width = card.style.width;
    const minHeight = card.style.minHeight;
    
    const savedSizes = JSON.parse(localStorage.getItem('analyticsCardSizes') || '{}');
    
    if (!savedSizes[cardId]) {
        savedSizes[cardId] = {};
    }
    savedSizes[cardId].width = width;
    savedSizes[cardId].minHeight = minHeight;
    
    localStorage.setItem('analyticsCardSizes', JSON.stringify(savedSizes));
}

/**
 * Load saved card positions and sizes from localStorage
 */
function loadCardPositions() {
    const savedPositions = JSON.parse(localStorage.getItem('analyticsCardPositions') || '{}');
    const savedSizes = JSON.parse(localStorage.getItem('analyticsCardSizes') || '{}');
    
    document.querySelectorAll('.draggable-card').forEach(card => {
        const cardId = card.getAttribute('data-card-id');
        if (!cardId) return;
        
        if (savedPositions[cardId]) {
            card.style.position = 'absolute';
            card.style.left = savedPositions[cardId].left || '';
            card.style.top = savedPositions[cardId].top || '';
            card.style.margin = '0';
        }
        
        if (savedSizes[cardId]) {
            card.style.width = savedSizes[cardId].width || '';
            card.style.minHeight = savedSizes[cardId].minHeight || '';
        }
    });
}


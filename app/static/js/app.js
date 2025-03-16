/**
 * Main application JavaScript for Family Management Solution
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initApp();
});

/**
 * Initialize the application
 */
function initApp() {
    // Set up UI components
    setupUI();
    
    // Initialize theme
    initTheme();
    
    // Handle page-specific initialization
    const currentPath = window.location.pathname;
    
    if (currentPath.includes('/checklists')) {
        initChecklistPage();
    } else if (currentPath.includes('/carpool')) {
        initCarpoolPage();
    } else if (currentPath.includes('/meals')) {
        initMealPage();
    }
}

/**
 * Set up UI components
 */
function setupUI() {
    // Set up tooltips
    setupTooltips();
    
    // Set up modals
    setupModals();
    
    // Set up confirmation dialogs
    setupConfirmations();
    
    // Set up theme toggle
    setupThemeToggle();
}

/**
 * Set up tooltip functionality
 */
function setupTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseenter', function() {
            const text = this.getAttribute('data-tooltip');
            const tooltipElement = document.createElement('div');
            
            tooltipElement.className = 'absolute bg-gray-800 text-white text-xs rounded px-2 py-1 z-50';
            tooltipElement.style.top = (this.offsetTop - 30) + 'px';
            tooltipElement.style.left = this.offsetLeft + 'px';
            tooltipElement.textContent = text;
            tooltipElement.setAttribute('id', 'active-tooltip');
            
            document.body.appendChild(tooltipElement);
        });
        
        tooltip.addEventListener('mouseleave', function() {
            const activeTooltip = document.getElementById('active-tooltip');
            if (activeTooltip) {
                activeTooltip.remove();
            }
        });
    });
}

/**
 * Set up modal dialog functionality
 */
function setupModals() {
    // Modal triggers
    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal-target');
            const modal = document.getElementById(modalId);
            
            if (modal) {
                modal.classList.remove('hidden');
                
                // Setup close button
                const closeButtons = modal.querySelectorAll('[data-modal-close]');
                closeButtons.forEach(button => {
                    button.addEventListener('click', function() {
                        modal.classList.add('hidden');
                    });
                });
                
                // Close on background click
                modal.addEventListener('click', function(e) {
                    if (e.target === modal) {
                        modal.classList.add('hidden');
                    }
                });
            }
        });
    });
}

/**
 * Set up confirmation dialog functionality
 */
function setupConfirmations() {
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure?';
            
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Show a notification message
 * @param {string} message - The message to display
 * @param {string} type - Message type (success, error, warning, info)
 * @param {number} duration - Duration in milliseconds
 */
function showNotification(message, type = 'info', duration = 5000) {
    try {
        // First try to use the notification container if it exists
        const container = document.getElementById('notification-container');
        
        // Create notification element
        const notification = document.createElement('div');
        let bgColor = 'bg-blue-500';
        
        switch (type) {
            case 'success':
                bgColor = 'bg-green-500';
                break;
            case 'error':
                bgColor = 'bg-red-500';
                break;
            case 'warning':
                bgColor = 'bg-yellow-500';
                break;
        }
        
        notification.className = `${bgColor} text-white py-2 px-4 rounded shadow-lg flex items-center`;
        notification.innerHTML = `
            <span>${message}</span>
            <button class="ml-4 focus:outline-none">×</button>
        `;
        
        // Add to DOM - either to the container or directly to the body
        if (container) {
            notification.className += ' mb-2'; // Add margin between stacked notifications
            container.appendChild(notification);
        } else {
            notification.className += ' fixed top-4 right-4 z-50'; // Position for body
            document.body.appendChild(notification);
        }
        
        // Set up close button
        const closeButton = notification.querySelector('button');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                notification.remove();
            });
        }
        
        // Auto-close after duration
        setTimeout(() => {
            if (document.body.contains(notification)) {
                notification.remove();
            }
        }, duration);
    } catch (error) {
        // Fallback to console if DOM manipulation fails
        console.error(`${type.toUpperCase()}: ${message}`);
        console.error('Error showing notification:', error);
    }
}

/**
 * Format a date for display
 * @param {string|Date} date - The date to format
 * @param {boolean} includeTime - Whether to include time
 * @returns {string} Formatted date string
 */
function formatDate(date, includeTime = false) {
    const d = new Date(date);
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };
    
    if (includeTime) {
        options.hour = '2-digit';
        options.minute = '2-digit';
    }
    
    return d.toLocaleDateString('en-US', options);
}

/**
 * Initialize the Checklist page
 */
function initChecklistPage() {
    // This will be implemented in checklist.js
    console.log('Checklist page initialized');
}

/**
 * Initialize the Carpool page
 */
function initCarpoolPage() {
    // This will be implemented in carpool.js
    console.log('Carpool page initialized');
}

/**
 * Initialize the Meal Planning page
 */
function initMealPage() {
    // This will be implemented in meal.js
    console.log('Meal Planning page initialized');
}

/**
 * Initialize theme based on saved preference or system preference
 */
function initTheme() {
    // Check if user has a saved preference
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme === 'dark') {
        // User has explicitly chosen dark mode
        document.documentElement.classList.add('dark');
    } else if (savedTheme === 'light') {
        // User has explicitly chosen light mode
        document.documentElement.classList.remove('dark');
    } else {
        // No saved preference, check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            // System prefers dark mode
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            // System prefers light mode or doesn't have a preference
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }
}

/**
 * Set up the theme toggle button functionality
 */
function setupThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            // Toggle dark class on html element
            document.documentElement.classList.toggle('dark');
            
            // Save preference to localStorage
            const isDark = document.documentElement.classList.contains('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        });
    }
}

// Export utilities for other scripts
window.app = window.app || {};
window.app.showNotification = showNotification;
window.app.formatDate = formatDate; 
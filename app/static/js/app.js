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
 * Set up the theme toggle button functionality
 */
function setupThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            // Toggle dark class on html and body elements
            document.documentElement.classList.toggle('dark');
            document.body.classList.toggle('dark');
            
            // Apply dark mode to all relevant elements via comprehensive selectors
            const elementSelectors = [
                // Base elements
                '.bg-white', '.bg-gray-50', '.bg-gray-100', '.bg-gray-200',
                '[class*="text-gray-"]', '[class*="border"]', '[class*="shadow"]',
                '.card', '.rounded-lg', '.meal-item', '.calendar-day', '.checklist-item',
                
                // Form elements
                'input', 'select', 'textarea', 'label', 'button',
                
                // Table elements
                'table', 'th', 'td', 'tr',
                
                // Text elements
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'a',
                
                // Modal elements
                '.modal-content', '.modal-header', '.modal-body', '.modal-footer',
                
                // Additional colored elements
                '[class*="text-slate-"]', '[class*="text-blue-"]', 
                '[class*="text-green-"]', '[class*="text-indigo-"]', 
                '[class*="text-purple-"]'
            ];
            
            // Join all selectors for a single powerful query
            const allElements = document.querySelectorAll(elementSelectors.join(','));
            
            // Toggle dark mode classes on all elements
            const isDark = document.documentElement.classList.contains('dark');
            allElements.forEach(el => {
                if (isDark) {
                    el.classList.add('dark-content');
                } else {
                    el.classList.remove('dark-content');
                }
            });
            
            // Save preference to localStorage
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            
            // Update UI based on current theme
            updateUIForTheme(isDark);
            
            // Check if on mobile and refresh page to ensure styles are properly applied
            if (window.innerWidth < 768) {
                setTimeout(() => {
                    window.location.reload();
                }, 100);
            }
        });
    }
}

/**
 * Update UI components for the current theme
 * @param {boolean} isDark - Whether dark mode is active
 */
function updateUIForTheme(isDark) {
    // Update background elements
    updateElementClasses('.bg-white, .bg-gray-50, .bg-gray-100, .card, .rounded-lg, .shadow-md', 
        isDark, 'dark-bg', 'bg-white');
    
    // Update text elements
    updateElementClasses('[class*="text-gray-"], [class*="text-slate-"], [class*="text-blue-"], [class*="text-green-"], [class*="text-indigo-"], [class*="text-purple-"]', 
        isDark, 'dark-text');
    
    // Update border elements
    updateElementClasses('[class*="border"]', 
        isDark, 'dark-border');
    
    // Update meal planning and checklist items
    updateElementClasses('.meal-item, .meal-day, .checklist-item, .calendar-day, .calendar-event', 
        isDark, 'dark-content');
    
    // Specifically target meal planning text to ensure visibility
    if (isDark) {
        document.querySelectorAll('.meal-item *, .meal-day *').forEach(el => {
            el.style.color = 'var(--color-text)';
        });
    } else {
        document.querySelectorAll('.meal-item *, .meal-day *').forEach(el => {
            el.style.color = '';  // Reset to default
        });
    }
    
    // Fix form elements
    updateElementClasses('input, select, textarea', 
        isDark, 'dark-content');
    
    // Table styling
    updateElementClasses('table, th, td', 
        isDark, 'dark-content');
        
    // Modal content
    updateElementClasses('.modal-content, .modal-header, .modal-body, .modal-footer', 
        isDark, 'dark-content');
    
    // Refresh components
    setupTooltips();
    setupModals();
}

/**
 * Helper function to update classes for a set of elements
 * @param {string} selector - CSS selector for elements to update
 * @param {boolean} isDark - Whether dark mode is active
 * @param {string} darkClass - Class to add in dark mode
 * @param {string} lightClass - Optional class to add in light mode
 */
function updateElementClasses(selector, isDark, darkClass, lightClass = null) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
        if (isDark) {
            el.classList.add(darkClass);
            if (lightClass) el.classList.remove(lightClass);
        } else {
            el.classList.remove(darkClass);
            if (lightClass) el.classList.add(lightClass);
        }
    });
}

/**
 * Initialize theme based on saved preference or system preference
 * By default, this will use the operating system's dark/light mode preference
 * unless the user has explicitly set a preference in localStorage
 */
function initTheme() {
    // Check if user has a saved preference
    const savedTheme = localStorage.getItem('theme');
    
    // Check if system prefers dark mode
    const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Apply the appropriate theme - uses OS preference if no saved preference exists
    const shouldUseDarkMode = savedTheme === 'dark' || (savedTheme === null && prefersDarkMode);
    
    if (shouldUseDarkMode) {
        // Apply dark mode
        document.documentElement.classList.add('dark');
        document.body.classList.add('dark');
        updateUIForTheme(true);
    } else {
        // Apply light mode
        document.documentElement.classList.remove('dark');
        document.body.classList.remove('dark');
        updateUIForTheme(false);
    }
    
    // Add listener for system theme changes
    if (window.matchMedia) {
        const colorSchemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
        
        // Add change listener if supported
        if (colorSchemeQuery.addEventListener) {
            colorSchemeQuery.addEventListener('change', e => {
                // Only apply if user hasn't set a preference
                if (localStorage.getItem('theme') === null) {
                    if (e.matches) {
                        document.documentElement.classList.add('dark');
                        document.body.classList.add('dark');
                        updateUIForTheme(true);
                    } else {
                        document.documentElement.classList.remove('dark');
                        document.body.classList.remove('dark');
                        updateUIForTheme(false);
                    }
                }
            });
        }
    }
}

// Export utilities for other scripts
window.app = window.app || {};
window.app.showNotification = showNotification;
window.app.formatDate = formatDate; 
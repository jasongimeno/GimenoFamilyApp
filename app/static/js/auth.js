/**
 * Authentication utilities for Family Management Solution
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication state
    checkAuthState();
    
    // Set up event listeners
    setupAuthListeners();
});

/**
 * Check if user is authenticated and update UI accordingly
 */
function checkAuthState() {
    const token = localStorage.getItem('accessToken');
    const userEmail = localStorage.getItem('userEmail');
    const userControls = document.getElementById('user-controls');
    const authControls = document.getElementById('auth-controls');
    const userEmailElement = document.getElementById('user-email');
    
    if (token && userEmail) {
        // User is logged in
        if (userControls) userControls.classList.remove('hidden');
        if (authControls) authControls.classList.add('hidden');
        if (userEmailElement) userEmailElement.textContent = userEmail;
        
        // Verify token with server periodically (optional)
        verifyToken(token);
    } else {
        // User is not logged in
        if (userControls) userControls.classList.add('hidden');
        if (authControls) authControls.classList.remove('hidden');
    }
}

/**
 * Verify token validity with server
 * @param {string} token - The JWT token to verify
 */
async function verifyToken(token) {
    try {
        // This is a placeholder for token verification
        // In a real app, you might want to call an endpoint to verify the token
        
        // Check token expiration based on JWT structure
        const payload = JSON.parse(atob(token.split('.')[1]));
        const expiry = payload.exp * 1000; // Convert to milliseconds
        const now = Date.now();
        
        if (now >= expiry) {
            // Token has expired
            logout();
        }
    } catch (error) {
        console.error('Token verification error:', error);
        logout();
    }
}

/**
 * Set up authentication-related event listeners
 */
function setupAuthListeners() {
    const logoutButton = document.getElementById('logout-button');
    
    if (logoutButton) {
        logoutButton.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }
}

/**
 * Log the user out
 */
function logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('userEmail');
    window.location.href = '/login';
}

/**
 * Get the authentication headers for API requests
 * @returns {Object} Headers object with Authorization
 */
function getAuthHeaders() {
    const token = localStorage.getItem('accessToken');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

/**
 * Make an authenticated API request
 * @param {string} url - The API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise} Fetch promise
 */
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('accessToken');
    
    if (!token) {
        // Redirect to login if no token is available
        window.location.href = '/login';
        return;
    }
    
    // Set default headers
    const headers = options.headers || {};
    headers['Authorization'] = `Bearer ${token}`;
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    
    try {
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        if (response.status === 401) {
            // Unauthorized, token might be invalid
            logout();
            return;
        }
        
        return response;
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

// Export utilities for other scripts
window.auth = {
    checkAuthState,
    logout,
    getAuthHeaders,
    apiRequest
}; 
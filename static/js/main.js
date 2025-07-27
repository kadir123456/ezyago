// Global variables
let isLoggedIn = false;
let currentUser = null;
let botStatus = 'stopped';
let botSettings = {
    symbol: 'BTCUSDT',
    orderSize: 25,
    leverage: 10,
    stopLoss: 4,
    takeProfit: 8,
    timeframe: '15m'
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    // Hide loading screen
    setTimeout(() => {
        document.getElementById('loading-screen').style.display = 'none';
    }, 1500);

    // Initialize FAQ toggles
    initializeFAQ();
    
    // Initialize dashboard navigation
    initializeDashboardNav();
    
    // Initialize forms
    initializeForms();
    
    // Check login status
    checkLoginStatus();
    
    // Initialize demo chart
    initializeDemoChart();
    
    // Initialize mobile menu
    initial

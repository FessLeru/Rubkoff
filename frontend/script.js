// Initialize Telegram WebApp
const tg = window.Telegram?.WebApp;
let userId = null;
let currentHouses = [];

// Configuration - auto-detect local or production
const CONFIG = {
    // Auto-detect API URL based on current location
    API_BASE_URL: (() => {
        if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') {
            return 'http://127.0.0.1:8000/api';
        }
        return '/api'; // Production relative URL
    })(),
    
    // Mock user ID for local testing
    DEFAULT_USER_ID: 1899077005,
    
    // Default limit for houses
    DEFAULT_LIMIT: 10
};

console.log('🔧 Frontend Config:', CONFIG);

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeTelegramWebApp();
    initializeApp();
});

function initializeTelegramWebApp() {
    if (tg) {
        tg.ready();
        tg.expand();
        
        // Get user ID from Telegram WebApp or URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        userId = urlParams.get('user_id') || tg.initDataUnsafe?.user?.id;
        
        // Set up main button
        if (tg.MainButton) {
            tg.MainButton.text = "Вернуться в бот";
            tg.MainButton.show();
            tg.MainButton.onClick(() => tg.close());
        }
        
        // Set up back button
        if (tg.BackButton) {
            tg.BackButton.show();
            tg.BackButton.onClick(() => tg.close());
        }
        
        // Apply Telegram theme
        applyTelegramTheme();
    } else {
        // Fallback for testing without Telegram
        userId = new URLSearchParams(window.location.search).get('user_id') || '123456789';
        console.warn('Running without Telegram WebApp');
    }
}

function applyTelegramTheme() {
    if (!tg) return;
    
    const root = document.documentElement;
    
    // Apply Telegram theme colors
    if (tg.themeParams.bg_color) {
        root.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color);
    }
    if (tg.themeParams.text_color) {
        root.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color);
    }
    if (tg.themeParams.hint_color) {
        root.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color);
    }
    if (tg.themeParams.button_color) {
        root.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color);
    }
    if (tg.themeParams.button_text_color) {
        root.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color);
    }
    if (tg.themeParams.secondary_bg_color) {
        root.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color);
    }
}

async function initializeApp() {
    try {
        // Check API health and get mode
        await checkApiHealth();
        
        // Load houses
        await loadHouses();
    } catch (error) {
        console.error('Failed to initialize app:', error);
        showError('Ошибка инициализации приложения');
    }
}

async function checkApiHealth() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            config.MOCK_MODE = data.mock_mode;
            updateModeIndicator(data.mock_mode);
        }
    } catch (error) {
        console.warn('Could not check API health:', error);
    }
}

function updateModeIndicator(mockMode) {
    const indicator = document.getElementById('modeIndicator');
    if (indicator) {
        if (mockMode) {
            indicator.textContent = 'Тестовый режим';
            indicator.style.display = 'inline-block';
        } else {
            indicator.style.display = 'none';
        }
    }
}

async function loadHouses() {
    showLoading();
    
    try {
        // Get user ID - fallback to default for local testing
        const userId = tg?.initDataUnsafe?.user?.id || CONFIG.DEFAULT_USER_ID;
        console.log('👤 Loading houses for user:', userId);
        
        let houses = [];
        
        if (userId) {
            try {
                // Try to get user recommendations first
                const response = await fetch(`${CONFIG.API_BASE_URL}/user/${userId}/recommendations`);
                if (response.ok) {
                    const data = await response.json();
                    houses = data.recommendations || [];
                    console.log('✅ Loaded user recommendations:', houses.length);
                }
            } catch (e) {
                console.warn('⚠️ User recommendations failed:', e);
            }
            
            // Fallback to mock recommendations
            if (houses.length === 0) {
                try {
                    const mockResponse = await fetch(`${CONFIG.API_BASE_URL}/houses/mock/recommendations?user_id=${userId}&limit=${CONFIG.DEFAULT_LIMIT}`);
                    if (mockResponse.ok) {
                        houses = await mockResponse.json();
                        console.log('✅ Loaded mock recommendations:', houses.length);
                    }
                } catch (e) {
                    console.warn('⚠️ Mock recommendations failed:', e);
                }
            }
        }
        
        if (houses.length === 0) {
            throw new Error('No houses available');
        }
        
        hideLoading();
        displayHouses(houses);
        
    } catch (error) {
        console.error('❌ Error loading houses:', error);
        hideLoading();
        showError(`Ошибка загрузки домов: ${error.message}`);
    }
}

function displayHouses(houses) {
    const housesGrid = document.querySelector('.houses-grid');
    if (!housesGrid) return;
    
    // Store current houses for sharing functionality
    currentHouses = houses;
    
    housesGrid.innerHTML = '';
    
    houses.forEach((house, index) => {
        const card = createHouseCard(house, index);
        housesGrid.appendChild(card);
    });
}

function createHouseCard(house, index) {
    const card = document.createElement('div');
    card.className = 'house-card slide-up';
    card.style.animationDelay = `${index * 0.1}s`;
    
    // Create badges HTML if they exist
    const badgesHtml = house.badges ? `
        <div class="house-badges">
            ${house.badges.split(',').map(badge => `<span class="badge">${badge.trim()}</span>`).join('')}
        </div>
    ` : '';
    
    card.innerHTML = `
        <div class="house-image">
            ${house.image_url 
                ? `<img src="${house.image_url}" alt="${house.name}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                   <div class="house-image-placeholder" style="display: none;">🏠</div>`
                : '<div class="house-image-placeholder">🏠</div>'
            }
            ${badgesHtml}
        </div>
        
        <div class="house-content">
            <h3 class="house-name">${house.name}</h3>
            
            ${house.recommendation_score ? `
                <div class="recommendation-score">
                    Соответствие: ${house.recommendation_score}%
                </div>
            ` : ''}
            
            <div class="house-details">
                <div class="detail-item">
                    <span class="detail-icon">💰</span>
                    <span class="price">${formatPrice(house.price)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-icon">📏</span>
                    <span>${house.area} м²</span>
                </div>
                ${house.house_size ? `
                    <div class="detail-item">
                        <span class="detail-icon">📐</span>
                        <span>${house.house_size}</span>
                    </div>
                ` : ''}
                ${house.bedrooms ? `
                    <div class="detail-item">
                        <span class="detail-icon">🛏</span>
                        <span>${house.bedrooms} спал${getBedroomSuffix(house.bedrooms)}</span>
                    </div>
                ` : ''}
                ${house.floors ? `
                    <div class="detail-item">
                        <span class="detail-icon">🏗</span>
                        <span>${house.floors} этаж${getFloorSuffix(house.floors)}</span>
                    </div>
                ` : ''}
            </div>
            
            ${house.description ? `
                <p class="house-description">${house.description}</p>
            ` : ''}
            
            ${house.match_reasons && house.match_reasons.length > 0 ? `
                <div class="match-reasons">
                    <div class="match-reasons-title">Почему этот дом вам подходит:</div>
                    <ul class="match-reasons-list">
                        ${house.match_reasons.map(reason => `<li>${reason}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            <div class="house-actions">
                <button class="btn btn-primary" onclick="openHouse('${house.url}', ${house.id})">
                    Подробнее
                </button>
                <button class="btn btn-secondary" onclick="shareHouse(${house.id})">
                    Поделиться
                </button>
            </div>
        </div>
    `;
    
    return card;
}

function showLoading() {
    document.getElementById('loadingSection').style.display = 'block';
    document.getElementById('errorSection').style.display = 'none';
    document.getElementById('emptySection').style.display = 'none';
    document.getElementById('housesSection').style.display = 'none';
}

function hideLoading() {
    document.getElementById('loadingSection').style.display = 'none';
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorSection').style.display = 'block';
    document.getElementById('loadingSection').style.display = 'none';
    document.getElementById('emptySection').style.display = 'none';
    document.getElementById('housesSection').style.display = 'none';
}

function showEmpty() {
    document.getElementById('emptySection').style.display = 'block';
    document.getElementById('loadingSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';
    document.getElementById('housesSection').style.display = 'none';
}

async function openHouse(url, houseId) {
    try {
        // Log house view for analytics
        const userId = tg?.initDataUnsafe?.user?.id || CONFIG.DEFAULT_USER_ID;
        if (userId) {
            fetch(`${CONFIG.API_BASE_URL}/houses/${houseId}/view?user_id=${userId}`, {
                method: 'POST'
            }).catch(e => console.warn('Failed to log house view:', e));
        }
        
        hapticFeedback('medium');
        
        // Open URL
        if (tg?.openLink) {
            tg.openLink(url);
        } else {
            // Fallback for web version
            window.open(url, '_blank');
        }
    } catch (error) {
        console.error('Error opening house:', error);
        // Fallback - just open the URL
        window.open(url, '_blank');
    }
}

function shareHouse(houseId) {
    const house = currentHouses.find(h => h.id === houseId);
    if (!house) return;
    
    try {
        hapticFeedback('light');
        
        const shareText = `🏠 ${house.name}\n📏 ${house.area} м²\n💰 ${formatPrice(house.price)}\n\n🔗 ${house.url}`;
        
        if (tg?.shareUrl) {
            tg.shareUrl(house.url, shareText);
        } else if (navigator.share) {
            // Web Share API
            navigator.share({
                title: house.name,
                text: shareText,
                url: house.url
            }).catch(e => console.log('Share failed:', e));
        } else {
            // Fallback - copy to clipboard
            navigator.clipboard.writeText(shareText).then(() => {
                alert('Ссылка скопирована в буфер обмена!');
            }).catch(e => {
                console.error('Copy failed:', e);
                // Final fallback - just show the text
                alert(`Поделиться:\n${shareText}`);
            });
        }
    } catch (error) {
        console.error('Error sharing house:', error);
    }
}

// Modal functions
function showHouseDetails(houseId) {
    const house = currentHouses.find(h => h.id === houseId);
    if (!house) return;
    
    const modal = document.getElementById('houseModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const modalViewBtn = document.getElementById('modalViewBtn');
    
    modalTitle.textContent = house.name;
    modalViewBtn.onclick = () => openHouse(house.url, house.id);
    
    modalBody.innerHTML = `
        <div class="house-image" style="margin-bottom: 20px;">
            ${house.image_url 
                ? `<img src="${house.image_url}" alt="${house.name}" style="width: 100%; height: 200px; object-fit: cover; border-radius: 8px;">`
                : '<div class="house-image-placeholder">🏠</div>'
            }
        </div>
        
        <div class="house-details" style="margin-bottom: 20px;">
            <div class="detail-item"><span class="detail-icon">💰</span> <strong>Цена:</strong> ${formatPrice(house.price)}</div>
            <div class="detail-item"><span class="detail-icon">📏</span> <strong>Площадь:</strong> ${house.area} м²</div>
            ${house.bedrooms ? `<div class="detail-item"><span class="detail-icon">🛏</span> <strong>Спальни:</strong> ${house.bedrooms}</div>` : ''}
            ${house.bathrooms ? `<div class="detail-item"><span class="detail-icon">🚿</span> <strong>Санузлы:</strong> ${house.bathrooms}</div>` : ''}
            ${house.floors ? `<div class="detail-item"><span class="detail-icon">🏗</span> <strong>Этажи:</strong> ${house.floors}</div>` : ''}
        </div>
        
        ${house.description ? `<p style="margin-bottom: 20px; line-height: 1.6;">${house.description}</p>` : ''}
        
        ${house.match_reasons && house.match_reasons.length > 0 ? `
            <div class="match-reasons">
                <div class="match-reasons-title">Почему этот дом вам подходит:</div>
                <ul class="match-reasons-list">
                    ${house.match_reasons.map(reason => `<li>${reason}</li>`).join('')}
                </ul>
            </div>
        ` : ''}
    `;
    
    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('houseModal').style.display = 'none';
}

// Utility functions
function formatPrice(price) {
    if (!price) return 'По запросу';
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0
    }).format(price);
}

function getFloorSuffix(floors) {
    if (floors === 1) return '';
    if (floors < 5) return 'а';
    return 'ей';
}

function getBedroomSuffix(bedrooms) {
    if (bedrooms === 1) return 'ьня';
    if (bedrooms < 5) return 'ьни';
    return 'ен';
}

// Event listeners
document.addEventListener('click', function(e) {
    // Close modal on outside click
    if (e.target.id === 'houseModal') {
        closeModal();
    }
});

document.addEventListener('keydown', function(e) {
    // Close modal on Escape key
    if (e.key === 'Escape') {
        closeModal();
    }
});

// Haptic feedback for Telegram
function hapticFeedback(type = 'light') {
    if (tg && tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred(type);
    }
}

// Add haptic feedback to buttons
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('btn')) {
        hapticFeedback('light');
    }
});

// Handle network errors gracefully
window.addEventListener('online', function() {
    if (currentHouses.length === 0) {
        loadHouses();
    }
});

window.addEventListener('offline', function() {
    console.warn('App is offline');
});

// Export functions for global access
window.loadHouses = loadHouses;
window.openHouse = openHouse;
window.shareHouse = shareHouse;
window.showHouseDetails = showHouseDetails;
window.closeModal = closeModal; 
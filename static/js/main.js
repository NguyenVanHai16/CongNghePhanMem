// BarberShop TNUT - Main JavaScript

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeTooltips();
    initializeAlerts();
    initializeFormValidation();
    initializeAnimations();
    initializeTableSorting();
    initializeTimeSlots();
});

// Tooltip Initialization
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Alert Auto-dismiss
function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        // Auto-dismiss success alerts after 5 seconds
        if (alert.classList.contains('alert-success')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });
}

// Form Validation Enhancement
function initializeFormValidation() {
    const forms = document.querySelectorAll('form[novalidate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus on first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            
            form.classList.add('was-validated');
        });
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    });
}

// Animation on Scroll
function initializeAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe cards and sections
    const animatedElements = document.querySelectorAll('.feature-card, .shop-card, .stat-card, .service-card');
    animatedElements.forEach(el => {
        observer.observe(el);
    });
}

// Table Sorting
function initializeTableSorting() {
    const sortableHeaders = document.querySelectorAll('th[data-sortable]');
    
    sortableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="fas fa-sort text-muted"></i>';
        
        header.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const columnIndex = Array.from(this.parentNode.children).indexOf(this);
            const currentSort = this.dataset.sort || 'asc';
            const newSort = currentSort === 'asc' ? 'desc' : 'asc';
            
            // Update sort indicators
            table.querySelectorAll('th i').forEach(icon => {
                icon.className = 'fas fa-sort text-muted';
            });
            this.querySelector('i').className = newSort === 'asc' ? 'fas fa-sort-up text-primary' : 'fas fa-sort-down text-primary';
            this.dataset.sort = newSort;
            
            // Sort rows
            rows.sort((a, b) => {
                const aVal = a.children[columnIndex].textContent.trim();
                const bVal = b.children[columnIndex].textContent.trim();
                
                // Try to parse as numbers
                const aNum = parseFloat(aVal.replace(/[^\d.-]/g, ''));
                const bNum = parseFloat(bVal.replace(/[^\d.-]/g, ''));
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return newSort === 'asc' ? aNum - bNum : bNum - aNum;
                } else {
                    return newSort === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                }
            });
            
            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}

// Time Slot Management
function initializeTimeSlots() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    
    dateInputs.forEach(dateInput => {
        // Set minimum date to today
        const today = new Date();
        const todayStr = today.toISOString().split('T')[0];
        dateInput.min = todayStr;
        
        // Set maximum date to 30 days from now
        const maxDate = new Date();
        maxDate.setDate(maxDate.getDate() + 30);
        dateInput.max = maxDate.toISOString().split('T')[0];
    });
}

// Booking Status Management
function updateBookingStatus(bookingId, status) {
    const data = new FormData();
    data.append('booking_id', bookingId);
    data.append('status', status);
    
    fetch('/update-booking-status', {
        method: 'POST',
        body: data,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Cập nhật trạng thái thành công!', 'success');
            // Refresh the page or update the UI
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Có lỗi xảy ra. Vui lòng thử lại.', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Có lỗi xảy ra. Vui lòng thử lại.', 'error');
    });
}

// Toast Notification System
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center border-0';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // Set toast color based on type
    const colorClass = {
        'success': 'text-bg-success',
        'error': 'text-bg-danger',
        'warning': 'text-bg-warning',
        'info': 'text-bg-info'
    }[type] || 'text-bg-info';
    
    toast.classList.add(colorClass);
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 5000
    });
    bsToast.show();
    
    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Loading State Management
function setLoadingState(element, loading = true) {
    if (loading) {
        element.classList.add('loading');
        element.disabled = true;
        
        // Store original content
        if (!element.dataset.originalContent) {
            element.dataset.originalContent = element.innerHTML;
        }
        
        // Add spinner
        const spinner = '<i class="fas fa-spinner fa-spin me-2"></i>';
        if (element.tagName === 'BUTTON') {
            element.innerHTML = spinner + 'Đang xử lý...';
        }
    } else {
        element.classList.remove('loading');
        element.disabled = false;
        
        // Restore original content
        if (element.dataset.originalContent) {
            element.innerHTML = element.dataset.originalContent;
        }
    }
}

// Confirmation Dialog
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Search and Filter Functions
function initializeSearch() {
    const searchInputs = document.querySelectorAll('[data-search]');
    
    searchInputs.forEach(input => {
        const targetSelector = input.dataset.search;
        const targets = document.querySelectorAll(targetSelector);
        
        input.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            
            targets.forEach(target => {
                const text = target.textContent.toLowerCase();
                const match = text.includes(query);
                
                target.style.display = match ? '' : 'none';
                
                // Add highlight
                if (match && query) {
                    target.classList.add('search-highlight');
                } else {
                    target.classList.remove('search-highlight');
                }
            });
        });
    });
}

// Phone Number Formatting
function formatPhoneNumber(input) {
    let value = input.value.replace(/\D/g, '');
    
    // Limit to 11 digits
    if (value.length > 11) {
        value = value.slice(0, 11);
    }
    
    // Format: 0123 456 789 or 0123 456 7890
    if (value.length >= 10) {
        if (value.length === 10) {
            value = value.replace(/(\d{4})(\d{3})(\d{3})/, '$1 $2 $3');
        } else {
            value = value.replace(/(\d{4})(\d{3})(\d{4})/, '$1 $2 $3');
        }
    } else if (value.length >= 7) {
        value = value.replace(/(\d{4})(\d{3})/, '$1 $2');
    } else if (value.length >= 4) {
        value = value.replace(/(\d{4})/, '$1');
    }
    
    input.value = value;
}

// Price Formatting
function formatPrice(amount) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND'
    }).format(amount);
}

// Date Formatting
function formatDate(date, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    };
    
    return new Intl.DateTimeFormat('vi-VN', { ...defaultOptions, ...options }).format(new Date(date));
}

// Time Formatting
function formatTime(time) {
    return new Intl.DateTimeFormat('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    }).format(new Date(`1970-01-01T${time}`));
}

// Distance Calculation (Haversine formula)
function calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = toRadians(lat2 - lat1);
    const dLng = toRadians(lng2 - lng1);
    
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) *
              Math.sin(dLng / 2) * Math.sin(dLng / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function toRadians(degrees) {
    return degrees * (Math.PI / 180);
}

// Local Storage Helpers
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('Error saving to localStorage:', error);
        return false;
    }
}

function getFromLocalStorage(key, defaultValue = null) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
    } catch (error) {
        console.error('Error reading from localStorage:', error);
        return defaultValue;
    }
}

// Auto-save Form Data
function initializeAutoSave() {
    const forms = document.querySelectorAll('[data-autosave]');
    
    forms.forEach(form => {
        const formId = form.dataset.autosave;
        const inputs = form.querySelectorAll('input, textarea, select');
        
        // Load saved data
        const savedData = getFromLocalStorage(`form_${formId}`, {});
        Object.keys(savedData).forEach(name => {
            const input = form.querySelector(`[name="${name}"]`);
            if (input && input.type !== 'password') {
                input.value = savedData[name];
            }
        });
        
        // Save on input
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (this.type !== 'password') {
                    const formData = getFromLocalStorage(`form_${formId}`, {});
                    formData[this.name] = this.value;
                    saveToLocalStorage(`form_${formId}`, formData);
                }
            });
        });
        
        // Clear on submit
        form.addEventListener('submit', function() {
            localStorage.removeItem(`form_${formId}`);
        });
    });
}

// Initialize auto-save when DOM is ready
document.addEventListener('DOMContentLoaded', initializeAutoSave);

// Service Worker Registration (for future PWA support)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // navigator.serviceWorker.register('/sw.js')
        //     .then(function(registration) {
        //         console.log('ServiceWorker registration successful');
        //     })
        //     .catch(function(error) {
        //         console.log('ServiceWorker registration failed');
        //     });
    });
}

// Export functions for use in other scripts
window.BarberShopTNUT = {
    showToast,
    setLoadingState,
    confirmAction,
    formatPrice,
    formatDate,
    formatTime,
    calculateDistance,
    updateBookingStatus
};

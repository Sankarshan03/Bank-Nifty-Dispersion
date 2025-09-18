// BankNifty Dispersion Trade Monitor - Frontend Application

class DispersionMonitor {
    constructor() {
        this.autoRefreshInterval = null;
        this.isLoading = false;
        this.lastUpdateTime = null;
        this.currentData = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshData();
        });
        
        // Auto refresh toggle
        document.getElementById('autoRefresh').addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });
        
        // OTM levels selector
        document.getElementById('otmLevels').addEventListener('change', (e) => {
            this.handleOTMLevelsChange(e.target.value);
        });
        
        // Export button
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportData();
        });
    }
    
    async loadInitialData() {
        await this.refreshData();
    }
    
    async refreshData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const response = await fetch('/api/dispersion-data');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.currentData = result.data;
                this.updateUI(result.data);
                this.updateConnectionStatus(true);
                this.lastUpdateTime = new Date();
                this.updateLastUpdateTime();
            } else {
                throw new Error(result.message || 'Failed to fetch data');
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            this.showError('Failed to fetch market data: ' + error.message);
            this.updateConnectionStatus(false);
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    updateUI(data) {
        this.updateNetPremium(data);
        this.updateBankNiftyPosition(data.banknifty_position);
        this.updateConstituentsPosition(data.constituents_positions);
        this.updateConstituentsTable(data.constituents_positions, data.normalized_lots);
        this.updatePortfolioValue(data.portfolio_value);
    }
    
    updateNetPremium(data) {
        const netPremium = data.net_premium || 0;
        const netPremiumElement = document.getElementById('netPremium');
        
        // Format currency
        netPremiumElement.textContent = this.formatCurrency(netPremium);
        
        // Update color based on value
        netPremiumElement.className = netPremium > 0 ? 'display-4 text-success' : 'display-4 text-danger';
        
        // Update progress bar (assuming target of 100,000)
        const targetPremium = 100000;
        const percentage = Math.min(Math.abs(netPremium) / targetPremium * 100, 100);
        
        const progressBar = document.getElementById('premiumProgress');
        progressBar.style.width = percentage + '%';
        progressBar.className = netPremium > 0 ? 'progress-bar bg-success' : 'progress-bar bg-danger';
        
        document.getElementById('premiumPercentage').textContent = percentage.toFixed(1) + '% of target';
        
        // Add animation
        netPremiumElement.classList.add('data-update');
        setTimeout(() => netPremiumElement.classList.remove('data-update'), 500);
    }
    
    updateBankNiftyPosition(position) {
        if (!position) return;
        
        document.getElementById('bnSpotPrice').textContent = this.formatNumber(position.strike || 0);
        document.getElementById('bnAtmStrike').textContent = this.formatNumber(position.strike || 0);
        document.getElementById('bnStraddlePremium').textContent = this.formatNumber(position.straddle_price || 0);
        document.getElementById('bnLots').textContent = this.formatNumber(position.lots || 0);
        document.getElementById('bnTotalPremium').textContent = this.formatCurrency(position.premium || 0);
    }
    
    updateConstituentsPosition(positions) {
        if (!positions) return;
        
        const totalStocks = Object.keys(positions.positions || {}).length;
        document.getElementById('totalStocks').textContent = totalStocks;
        document.getElementById('constituentsTotalPremium').textContent = this.formatCurrency(positions.total_premium || 0);
    }
    
    updateConstituentsTable(positions, normalizedLots) {
        const tableBody = document.getElementById('constituentsTable');
        tableBody.innerHTML = '';
        
        if (!positions || !positions.positions) return;
        
        Object.entries(positions.positions).forEach(([symbol, data]) => {
            const row = document.createElement('tr');
            
            const status = data.premium > 0 ? 'Active' : 'Inactive';
            const statusClass = data.premium > 0 ? 'badge bg-success' : 'badge bg-danger';
            
            row.innerHTML = `
                <td><strong>${symbol}</strong></td>
                <td>${data.weight?.toFixed(2) || '--'}%</td>
                <td>${this.formatNumber(data.spot_price || 0)}</td>
                <td>${this.formatNumber(data.strike || 0)}</td>
                <td>${this.formatNumber(data.straddle_price || 0)}</td>
                <td>${this.formatNumber(data.lot_size || 0)}</td>
                <td>${this.formatNumber(data.lots || 0)}</td>
                <td>${this.formatCurrency(data.premium || 0)}</td>
                <td><span class="${statusClass}">${status}</span></td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    updatePortfolioValue(portfolioData) {
        if (!portfolioData) return;
        
        const portfolioValue = portfolioData.total_value || 0;
        document.getElementById('portfolioValue').textContent = this.formatCurrency(portfolioValue, true);
    }
    
    async handleOTMLevelsChange(levels) {
        const otmSection = document.getElementById('otmSection');
        
        if (levels === '0') {
            otmSection.style.display = 'none';
            return;
        }
        
        otmSection.style.display = 'block';
        
        try {
            const response = await fetch(`/api/otm-levels?levels=${levels}`);
            const result = await response.json();
            
            if (result.status === 'success') {
                this.updateOTMSection(result.data);
            } else {
                throw new Error(result.message || 'Failed to fetch OTM data');
            }
        } catch (error) {
            console.error('Error fetching OTM data:', error);
            this.showError('Failed to fetch OTM data: ' + error.message);
        }
    }
    
    updateOTMSection(otmData) {
        const otmContent = document.getElementById('otmContent');
        otmContent.innerHTML = '';
        
        Object.entries(otmData).forEach(([level, data]) => {
            const levelCard = document.createElement('div');
            levelCard.className = 'card otm-level-card mb-3';
            
            levelCard.innerHTML = `
                <div class="card-header">
                    <h6 class="mb-0">OTM Level ${data.level || level.split('_')[2]}</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6>BankNifty Position</h6>
                            <p>Call Strike: ${this.formatNumber(data.banknifty_position?.call_strike || 0)}</p>
                            <p>Put Strike: ${this.formatNumber(data.banknifty_position?.put_strike || 0)}</p>
                        </div>
                        <div class="col-md-6">
                            <h6>Net Premium</h6>
                            <p class="h5">${this.formatCurrency(data.net_premium || 0)}</p>
                            <small class="text-muted">${data.note || ''}</small>
                        </div>
                    </div>
                </div>
            `;
            
            otmContent.appendChild(levelCard);
        });
    }
    
    startAutoRefresh() {
        this.stopAutoRefresh(); // Clear any existing interval
        this.autoRefreshInterval = setInterval(() => {
            this.refreshData();
        }, 4000); // 4 seconds
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (connected) {
            statusElement.textContent = 'Connected';
            statusElement.className = 'badge bg-success';
        } else {
            statusElement.textContent = 'Disconnected';
            statusElement.className = 'badge bg-danger';
        }
    }
    
    updateLastUpdateTime() {
        if (this.lastUpdateTime) {
            const timeString = this.lastUpdateTime.toLocaleTimeString();
            document.getElementById('lastUpdate').textContent = `Last Update: ${timeString}`;
        }
    }
    
    showLoading() {
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        modal.show();
    }
    
    hideLoading() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (modal) {
            modal.hide();
        }
    }
    
    showError(message) {
        // Create and show error alert
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
        alertDiv.innerHTML = `
            <strong>Error!</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    }
    
    exportData() {
        if (!this.currentData) {
            this.showError('No data available to export');
            return;
        }
        
        // Create CSV content
        const csvContent = this.generateCSV(this.currentData);
        
        // Create and trigger download
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dispersion_data_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
    
    generateCSV(data) {
        const headers = [
            'Symbol', 'Weight%', 'Spot Price', 'ATM Strike', 'Straddle Premium', 
            'Lot Size', 'Normalized Lots', 'Total Premium', 'Type'
        ];
        
        let csvContent = headers.join(',') + '\n';
        
        // Add BankNifty row
        const bnPosition = data.banknifty_position;
        csvContent += [
            'BANKNIFTY',
            '100.00',
            bnPosition?.strike || 0,
            bnPosition?.strike || 0,
            bnPosition?.straddle_price || 0,
            '15',
            bnPosition?.lots || 0,
            bnPosition?.premium || 0,
            'BUY'
        ].join(',') + '\n';
        
        // Add constituents rows
        if (data.constituents_positions && data.constituents_positions.positions) {
            Object.entries(data.constituents_positions.positions).forEach(([symbol, position]) => {
                csvContent += [
                    symbol,
                    position.weight?.toFixed(2) || 0,
                    position.spot_price || 0,
                    position.strike || 0,
                    position.straddle_price || 0,
                    position.lot_size || 0,
                    position.lots || 0,
                    position.premium || 0,
                    'SELL'
                ].join(',') + '\n';
            });
        }
        
        // Add summary
        csvContent += '\n';
        csvContent += `Net Premium,${data.net_premium || 0}\n`;
        csvContent += `Timestamp,${data.timestamp || new Date().toISOString()}\n`;
        
        return csvContent;
    }
    
    formatCurrency(amount, abbreviated = false) {
        if (abbreviated && Math.abs(amount) >= 10000000) {
            return '₹' + (amount / 10000000).toFixed(1) + 'Cr';
        } else if (abbreviated && Math.abs(amount) >= 100000) {
            return '₹' + (amount / 100000).toFixed(1) + 'L';
        }
        return '₹' + amount.toLocaleString('en-IN', { maximumFractionDigits: 0 });
    }
    
    formatNumber(number) {
        return number.toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DispersionMonitor();
});

// Handle page visibility change to pause/resume auto refresh
document.addEventListener('visibilitychange', () => {
    const monitor = window.dispersionMonitor;
    if (monitor) {
        if (document.hidden) {
            monitor.stopAutoRefresh();
        } else if (document.getElementById('autoRefresh').checked) {
            monitor.startAutoRefresh();
        }
    }
});

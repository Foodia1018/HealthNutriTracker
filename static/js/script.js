document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // QR Code generation
    const qrContainer = document.getElementById('qr-code');
    if (qrContainer) {
        const walletAddress = qrContainer.dataset.address;
        if (walletAddress) {
            new QRCode(qrContainer, {
                text: walletAddress,
                width: 128,
                height: 128,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.H
            });
        }
    }

    // Copy wallet address functionality
    const copyButton = document.getElementById('copy-address');
    if (copyButton) {
        copyButton.addEventListener('click', function() {
            const walletAddress = this.dataset.address;
            navigator.clipboard.writeText(walletAddress).then(function() {
                // Show success message
                const originalText = copyButton.innerHTML;
                copyButton.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(function() {
                    copyButton.innerHTML = originalText;
                }, 2000);
            });
        });
    }

    // Withdrawal form with loading animation
    const withdrawForm = document.getElementById('withdraw-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    if (withdrawForm && loadingOverlay) {
        withdrawForm.addEventListener('submit', function(e) {
            // Validate form
            const amount = parseFloat(document.getElementById('amount').value);
            const address = document.getElementById('address').value;
            const maxAmount = parseFloat(document.getElementById('amount').dataset.max);
            
            if (!amount || amount <= 0 || amount > maxAmount) {
                e.preventDefault();
                alert('Please enter a valid withdrawal amount');
                return;
            }
            
            if (!address) {
                e.preventDefault();
                alert('Please enter a valid Bitcoin address');
                return;
            }
            
            // Show loading animation for 5 seconds
            loadingOverlay.classList.add('show');
            setTimeout(function() {
                // Form will be submitted after the timeout
                withdrawForm.submit();
            }, 5000);
            
            e.preventDefault();
        });
    }

    // Initialize balance chart if the element exists
    const balanceChartElement = document.getElementById('balance-chart');
    if (balanceChartElement) {
        const ctx = balanceChartElement.getContext('2d');
        const transactions = JSON.parse(balanceChartElement.dataset.transactions);
        
        // Prepare data for chart
        const labels = [];
        const data = [];
        let balance = 0;
        
        // Sort transactions by timestamp (oldest to newest)
        transactions.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // Add initial balance point
        labels.push('Start');
        data.push(balance);
        
        // Process transactions to build balance history
        transactions.forEach(tx => {
            const date = new Date(tx.timestamp);
            const formattedDate = `${date.getMonth()+1}/${date.getDate()}`;
            
            if (tx.tx_type === 'deposit' || tx.tx_type === 'bonus' || tx.tx_type === 'growth') {
                balance += tx.amount;
            } else if (tx.tx_type === 'withdrawal') {
                balance -= tx.amount;
            }
            
            labels.push(formattedDate);
            data.push(balance);
        });
        
        // Create the chart
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Balance (BTC)',
                    data: data,
                    backgroundColor: 'rgba(30, 144, 255, 0.2)',
                    borderColor: 'rgba(30, 144, 255, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toFixed(2);
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return '$' + context.raw.toFixed(2) + ' BTC';
                            }
                        }
                    }
                }
            }
        });
    }
});

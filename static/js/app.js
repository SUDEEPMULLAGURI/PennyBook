// ==========================================
// PENNYBOOK SIMPLIFIED CLIENT JAVASCRIPT
// ==========================================

// Global App State
const state = {
    accounts: [],
    categories: {
        expense: ['Food', 'Fuel', 'Shopping', 'Medical', 'Rent', 'Education', 'Entertainment', 'Travel'],
        income: ['Salary', 'Freelance', 'Business', 'Interest', 'Refunds', 'Other']
    },
    activeGroup: null,
    flowChart: null
};

// Start application on page load
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    // Set standard dates in form inputs
    const todayStr = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(input => {
        if (!input.value) input.value = todayStr;
    });

    // Setup router
    window.addEventListener('hashchange', router);
    router();

    // Load initial global statistics
    loadGlobalStats();
    
    // Set categories list for forms
    setupConsolidatedCategorySelectors();
}

// Router - Consolidated 5-Tab Navigation
function router() {
    const hash = window.location.hash || '#dashboard';
    const tabName = hash.replace('#', '');
    
    // Update active tab styling
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('data-tab') === tabName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Update active screen panel
    document.querySelectorAll('.screen').forEach(screen => {
        if (screen.id === `screen-${tabName}`) {
            screen.classList.add('active');
        } else {
            screen.classList.remove('active');
        }
    });

    // Set Header Title
    const screenTitles = {
        dashboard: "Dashboard & Insights",
        ledger: "Transactions Ledger & Accounts",
        split: "Shared Split Groups",
        planning: "Planning Targets (Budgets, Goals, Subs)",
        balance: "Balance Sheet (Assets & Debts)"
    };
    document.getElementById('current-section-title').textContent = screenTitles[tabName] || "PennyBook";

    // Call Screen-Specific Loaders
    if (tabName === 'dashboard') loadDashboard();
    else if (tabName === 'ledger') loadLedgerScreen();
    else if (tabName === 'split') loadSplitScreen();
    else if (tabName === 'planning') loadPlanningScreen();
    else if (tabName === 'balance') loadBalanceScreen();

    // Auto-focus key interaction input fields to support mouse-free usage
    setTimeout(() => {
        if (tabName === 'dashboard') {
            const lcPrincipal = document.getElementById('lc-principal');
            if (lcPrincipal) lcPrincipal.focus();
        } else if (tabName === 'ledger') {
            const filterSearch = document.getElementById('filter-search');
            if (filterSearch) filterSearch.focus();
        } else if (tabName === 'split') {
            const firstGroup = document.querySelector('.group-menu-item');
            if (firstGroup) {
                firstGroup.focus();
            } else {
                const addGpBtn = document.querySelector('#screen-split .split-sidebar-header button');
                if (addGpBtn) addGpBtn.focus();
            }
        } else if (tabName === 'planning') {
            const setPlanBtn = document.querySelector('#screen-planning button');
            if (setPlanBtn) setPlanBtn.focus();
        } else if (tabName === 'balance') {
            const addBalBtn = document.querySelector('#screen-balance button');
            if (addBalBtn) addBalBtn.focus();
        }
    }, 150);
}

// ----------------- GLOBAL STATS LOADER -----------------
function loadGlobalStats() {
    fetch('/api/stats/global')
        .then(res => res.json())
        .then(data => {
            document.getElementById('header-net-worth').textContent = formatCurrency(data.net_worth);
            document.getElementById('header-savings-rate').textContent = `${data.savings_rate}%`;
            document.getElementById('header-cash-flow').textContent = 
                (data.net_cash_flow >= 0 ? '+' : '') + formatCurrency(data.net_cash_flow);
            
            // Cash Flow Color
            const flowEl = document.getElementById('header-cash-flow');
            if (data.net_cash_flow >= 0) {
                flowEl.className = "value green-text";
            } else {
                flowEl.className = "value orange-text";
            }

            // Savings Rate Color
            const rateEl = document.getElementById('header-savings-rate');
            if (data.savings_rate >= 20) {
                rateEl.className = "value green-text";
            } else if (data.savings_rate >= 0) {
                rateEl.className = "value cyan-text";
            } else {
                rateEl.className = "value orange-text";
            }
        });
}

// ----------------- 1. DASHBOARD SCREEN -----------------
function loadDashboard() {
    loadGlobalStats();
    
    // Load Dashboard Stats
    fetch('/api/stats/dashboard')
        .then(res => res.json())
        .then(data => {
            document.getElementById('dash-assets').textContent = formatCurrency(data.assets);
            document.getElementById('dash-liabilities').textContent = formatCurrency(data.liabilities);
            document.getElementById('dash-burn-rate').textContent = `${formatCurrency(data.burn_rate)}/day`;
            document.getElementById('dash-days-elapsed').textContent = data.days_elapsed;
            document.getElementById('dash-remaining-daily-budget').textContent = `${formatCurrency(data.remaining_daily)}/day`;
            document.getElementById('dash-days-left').textContent = data.days_left;

            // Mathematical Insights list
            const insightsContainer = document.getElementById('dash-insights');
            insightsContainer.innerHTML = '';
            
            if (data.assets === 0 && data.liabilities === 0) {
                insightsContainer.innerHTML = `
                    <div class="settlement-payment-row" style="border-left: 3px solid var(--text-muted);">
                        <div>📖 <strong>Empty Ledger Sheet</strong>: Go to <strong>Ledger & Accounts</strong> to create an account and log transactions!</div>
                    </div>`;
                return;
            }

            if (data.liabilities > data.assets) {
                insightsContainer.innerHTML += `
                    <div class="settlement-payment-row" style="border-left: 3px solid var(--neon-orange);">
                        <div>⚠️ <strong>Debt Alert</strong>: Total liabilities exceed assets. Consider paying down high-interest borrowed debts.</div>
                    </div>`;
            } else {
                insightsContainer.innerHTML += `
                    <div class="settlement-payment-row" style="border-left: 3px solid var(--neon-green);">
                        <div>📈 <strong>Solvent balance</strong>: Assets exceed liabilities by <strong>${formatCurrency(data.assets - data.liabilities)}</strong>.</div>
                    </div>`;
            }

            const projectedSpend = data.burn_rate * (data.days_elapsed + data.days_left);
            insightsContainer.innerHTML += `
                <div class="settlement-payment-row" style="border-left: 3px solid var(--neon-cyan);">
                    <div>📊 <strong>Daily average projection</strong>: Burning ${formatCurrency(data.burn_rate)}/day will result in month-end spend of <strong>${formatCurrency(projectedSpend)}</strong>.</div>
                </div>`;

            // Savings and months cover
            fetch('/api/savings')
                .then(res => res.json())
                .then(goals => {
                    const totalSaved = goals.reduce((sum, g) => sum + g.saved_amount, 0);
                    const monthlySpend = data.burn_rate * 30;
                    const monthsCover = monthlySpend > 0 ? (totalSaved / monthlySpend) : 999;
                    
                    let coverClass = 'var(--neon-green)';
                    let coverEmoji = '🛡️';
                    if (monthsCover < 3) {
                        coverClass = 'var(--neon-orange)';
                        coverEmoji = '⚠️';
                    } else if (monthsCover < 6) {
                        coverClass = 'var(--neon-cyan)';
                    }
                    
                    if (totalSaved > 0) {
                        insightsContainer.innerHTML += `
                            <div class="settlement-payment-row" style="border-left: 3px solid ${coverClass};">
                                <div>${coverEmoji} <strong>Emergency Fund Tracker</strong>: Total savings cover <strong>${monthsCover.toFixed(1)} months</strong> of monthly spending.</div>
                            </div>`;
                    }
                });
        });

    // Cash flow trends line chart
    fetch('/api/stats/cashflow-trends')
        .then(res => res.json())
        .then(data => {
            plotDashboardChart(data.labels, data.income, data.expense);
        });
}

function plotDashboardChart(labels, incomeData, expenseData) {
    if (state.flowChart) state.flowChart.destroy();
    
    // Check if charts have any values, else render empty canvas
    const hasData = incomeData.some(x => x > 0) || expenseData.some(x => x > 0);
    if (!hasData) {
        const ctx = document.getElementById('dashFlowChart').getContext('2d');
        ctx.clearRect(0, 0, 100, 100);
        return;
    }
    
    const ctx = document.getElementById('dashFlowChart').getContext('2d');
    state.flowChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Income (₹)',
                    data: incomeData,
                    borderColor: '#00f5a0',
                    backgroundColor: 'rgba(0, 245, 160, 0.05)',
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Expenses (₹)',
                    data: expenseData,
                    borderColor: '#f857a6',
                    backgroundColor: 'rgba(248, 87, 166, 0.05)',
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { family: 'Outfit' } } }
            },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#94a3b8' } },
                y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#94a3b8' } }
            }
        }
    });
}

// ----------------- 2. LEDGER SCREEN -----------------
function loadLedgerScreen() {
    // Populate form account lists
    fetch('/api/accounts')
        .then(res => res.json())
        .then(accs => {
            state.accounts = accs;
            
            // Fill Quick Transfer selectors
            const fromSelect = document.getElementById('trans-from');
            const toSelect = document.getElementById('trans-to');
            fromSelect.innerHTML = '';
            toSelect.innerHTML = '';
            
            // Fill transaction forms account fields
            const addTxAcc = document.getElementById('add-tx-account');
            const addTxToAcc = document.getElementById('add-tx-to-account');
            addTxAcc.innerHTML = '';
            addTxToAcc.innerHTML = '';
            
            accs.forEach(acc => {
                const opt = `<option value="${acc.id}">${acc.name} (${formatCurrency(acc.balance)})</option>`;
                fromSelect.innerHTML += opt;
                toSelect.innerHTML += opt;
                
                const shortOpt = `<option value="${acc.id}">${acc.name}</option>`;
                addTxAcc.innerHTML += shortOpt;
                addTxToAcc.innerHTML += shortOpt;
            });
            
            // Render Accounts list column
            const container = document.getElementById('accounts-container');
            container.innerHTML = '';
            if (accs.length === 0) {
                container.innerHTML = '<span class="muted-text">No accounts created.</span>';
                return;
            }
            accs.forEach(acc => {
                const typeClass = `card-${acc.type.toLowerCase().replace(' ', '-')}`;
                container.innerHTML += `
                    <div class="account-card ${typeClass}" style="min-height: auto; padding:15px; border-radius:10px; margin-bottom:10px;">
                        <div class="account-header">
                            <span class="account-type" style="font-size:9px; padding:2px 6px;">${acc.type}</span>
                            <h4 style="margin:2px 0;">${acc.name}</h4>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:8px;">
                            <span class="account-balance ${acc.balance >= 0 ? 'cyan-text' : 'magenta-text'}" style="font-size:18px;">
                                ${formatCurrency(acc.balance)}
                            </span>
                            <button class="btn btn-sm btn-text" style="color:var(--neon-orange); font-size:11px;" onclick="handleDeleteAccount(${acc.id}, '${acc.name}')">
                                Delete
                            </button>
                        </div>
                    </div>`;
            });
        });
        
    // Initial query trigger
    runQueryLedger();
}

function handleSearchInstant() {
    runQueryLedger();
}

function runQueryLedger() {
    const search_text = document.getElementById('filter-search').value;
    const type = document.getElementById('filter-type').value;
    
    const filters = {};
    if (search_text) filters.search_text = search_text;
    if (type) filters.type = type;
    
    fetch('/api/transactions/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters })
    })
    .then(res => res.json())
    .then(data => {
        const tbody = document.getElementById('ledger-transactions');
        tbody.innerHTML = '';
        
        if (data.transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="muted-text" style="text-align:center;">No matching transactions.</td></tr>';
            return;
        }
        
        data.transactions.forEach(tx => {
            const sign = tx.type === 'income' ? '+' : tx.type === 'expense' ? '-' : '';
            const receiptButton = tx.receipt_path ? 
                `<button class="receipt-icon" onclick="viewReceipt('${tx.receipt_path}')">📄</button>` : 
                '-';
            
            let accPath = tx.account_name || 'N/A';
            if (tx.type === 'transfer') {
                accPath = `${tx.account_name} &rarr; ${tx.to_account_name}`;
            }

            tbody.innerHTML += `
                <tr>
                    <td>${formatDateShort(tx.date)}</td>
                    <td><span class="badge badge-${tx.type}">${tx.type.toUpperCase()}</span></td>
                    <td><strong>${tx.category}</strong></td>
                    <td>${accPath}</td>
                    <td class="${tx.type === 'income' ? 'green-text' : tx.type === 'expense' ? 'magenta-text' : 'cyan-text'} font-weight-bold">
                        ${sign}${formatCurrency(tx.amount)}
                    </td>
                    <td class="muted-text">${tx.notes || ''}</td>
                    <td>${receiptButton}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" style="padding: 2px 8px; font-size:10px;" onclick="handleDeleteTransaction(${tx.id})">Delete</button>
                    </td>
                </tr>`;
        });
    });
}

// Consolidated transaction selectors
function setupConsolidatedCategorySelectors() {
    const addTxType = document.getElementById('add-tx-type');
    if (addTxType) {
        addTxType.addEventListener('change', toggleConsolidatedTxFields);
        toggleConsolidatedTxFields();
    }
}

function toggleConsolidatedTxFields() {
    const type = document.getElementById('add-tx-type').value;
    const catGroup = document.getElementById('group-tx-category');
    const toAccGroup = document.getElementById('group-tx-to-account');
    const freqGroup = document.getElementById('group-tx-frequency');
    const dateLabel = document.getElementById('label-tx-date');
    
    // Hide all first
    catGroup.style.display = 'block';
    toAccGroup.style.display = 'none';
    freqGroup.style.display = 'none';
    dateLabel.textContent = "Date";
    
    if (type === 'transfer') {
        catGroup.style.display = 'none';
        toAccGroup.style.display = 'block';
    } else if (type === 'recurring_expense' || type === 'recurring_income') {
        freqGroup.style.display = 'block';
        dateLabel.textContent = "Next Occurrence Date";
        
        // Populate category dropdown
        const activeType = type === 'recurring_income' ? 'income' : 'expense';
        const catSelect = document.getElementById('add-tx-category');
        catSelect.innerHTML = '';
        state.categories[activeType].forEach(c => {
            catSelect.innerHTML += `<option value="${c}">${c}</option>`;
        });
    } else {
        // Standard expense / income
        const catSelect = document.getElementById('add-tx-category');
        catSelect.innerHTML = '';
        state.categories[type].forEach(c => {
            catSelect.innerHTML += `<option value="${c}">${c}</option>`;
        });
    }
}

function submitAddTransaction(e) {
    e.preventDefault();
    const type = document.getElementById('add-tx-type').value;
    const amount = document.getElementById('add-tx-amount').value;
    const date = document.getElementById('add-tx-date').value;
    const account_id = document.getElementById('add-tx-account').value;
    const notes = document.getElementById('add-tx-notes').value;
    const tags = document.getElementById('add-tx-tags').value;
    
    if (type === 'transfer') {
        const to_account_id = document.getElementById('add-tx-to-account').value;
        if (account_id === to_account_id) {
            alert("Source and Destination accounts must be different.");
            return;
        }
        fetch('/api/transactions/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from_account_id: account_id, to_account_id, amount, date })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-transaction');
            loadLedgerScreen();
            loadGlobalStats();
        });
        
    } else if (type === 'recurring_expense' || type === 'recurring_income') {
        const category = document.getElementById('add-tx-category').value;
        const frequency = document.getElementById('add-tx-frequency').value;
        const mappedType = type === 'recurring_income' ? 'income' : 'expense';
        
        fetch('/api/recurring', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: notes || "Recurring schedule", type: mappedType, amount, category, account_id, frequency, next_occurrence: date })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-transaction');
            alert("Recurring transaction scheduled successfully.");
            loadLedgerScreen();
        });
        
    } else {
        // Standard expense / income with upload
        const form = e.target;
        const formData = new FormData();
        formData.append('amount', amount);
        formData.append('type', type);
        formData.append('date', date);
        formData.append('category', document.getElementById('add-tx-category').value);
        formData.append('account_id', account_id);
        formData.append('notes', notes);
        formData.append('tags', tags);
        
        const fileField = document.getElementById('add-tx-receipt');
        if (fileField.files.length > 0) {
            formData.append('receipt', fileField.files[0]);
        }
        
        fetch('/api/transactions', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-transaction');
            form.reset();
            loadLedgerScreen();
            loadGlobalStats();
        });
    }
}

// ----------------- 3. SPLIT GROUPS SCREEN -----------------
function loadSplitScreen() {
    fetch('/api/groups')
        .then(res => res.json())
        .then(gps => {
            const list = document.getElementById('groups-list-container');
            list.innerHTML = '';
            
            if (gps.length === 0) {
                list.innerHTML = '<span class="muted-text" style="padding:10px; font-size:13px;">No split groups.</span>';
                return;
            }
            
            gps.forEach(gp => {
                const activeClass = state.activeGroup && state.activeGroup.id === gp.id ? 'active' : '';
                list.innerHTML += `
                    <div class="group-menu-item ${activeClass}" tabindex="0" onclick="selectGroup(${gp.id})" onkeydown="if(event.key==='Enter'||event.key===' '){selectGroup(${gp.id}); event.preventDefault();}">
                        <h4>${gp.name}</h4>
                        <span>${gp.description || 'Split group'}</span>
                    </div>`;
            });
        });
}

function selectGroup(groupId) {
    fetch(`/api/groups/${groupId}`)
        .then(res => res.json())
        .then(gp => {
            state.activeGroup = gp;
            loadSplitScreen();
            
            // Get running balances and settlements
            fetch(`/api/groups/${groupId}/balances`)
                .then(res => res.json())
                .then(balances => {
                    fetch(`/api/groups/${groupId}/settlements`)
                        .then(res => res.json())
                        .then(payments => {
                            renderGroupDetails(gp, balances, payments);
                        });
                });
        });
}

function renderGroupDetails(gp, balances, payments) {
    const panel = document.getElementById('group-details-panel');
    const memberLabels = gp.members.map(m => `<span class="badge badge-tag">👤 ${m.name}</span>`).join(' ');
    
    // Balance sheets
    let balanceRows = '';
    Object.entries(balances).forEach(([name, bal]) => {
        const balClass = bal > 0.01 ? 'green-text' : bal < -0.01 ? 'magenta-text' : 'muted-text';
        const balSign = bal > 0.01 ? 'gets back' : bal < -0.01 ? 'owes' : 'settled';
        balanceRows += `
            <div class="balance-row">
                <span><strong>${name}</strong></span>
                <span class="${balClass}"><strong>${balSign} ${formatCurrency(Math.abs(bal))}</strong></span>
            </div>`;
    });

    // Settlements rows
    let paymentRows = '';
    if (payments.length === 0) {
        paymentRows = '<div class="empty-state" style="padding:10px; min-height:auto;">All members settled!</div>';
    } else {
        payments.forEach(p => {
            paymentRows += `
                <div class="settlement-payment-row">
                    <strong>${p.from}</strong> &rarr; <strong>${p.to}</strong>
                    <span style="margin-left: auto;"><strong>${formatCurrency(p.amount)}</strong></span>
                </div>`;
        });
    }

    // Bills logs rows
    let expenseRows = '';
    if (gp.expenses.length === 0) {
        expenseRows = '<tr><td colspan="5" class="muted-text" style="text-align:center;">No bills logged.</td></tr>';
    } else {
        gp.expenses.forEach(e => {
            expenseRows += `
                <tr>
                    <td>${formatDateShort(e.date)}</td>
                    <td><strong>{e.description}</strong></td>
                    <td>Paid by ${e.paid_by_member_name}</td>
                    <td class="magenta-text font-weight-bold">${formatCurrency(e.amount)}</td>
                    <td>
                        <span class="badge badge-tag">${e.split_type.toUpperCase()}</span>
                        <button class="btn btn-sm btn-text" style="color:var(--neon-orange); padding:0;" onclick="handleDeleteGroupExpense(${e.id})">Delete</button>
                    </td>
                </tr>`;
        });
    }

    // Cash transfers
    let paymentLogRows = '';
    if (gp.payments.length === 0) {
        paymentLogRows = '<tr><td colspan="4" class="muted-text" style="text-align:center;">No settlement payments logged.</td></tr>';
    } else {
        gp.payments.forEach(p => {
            paymentLogRows += `
                <tr>
                    <td>${formatDateShort(p.date)}</td>
                    <td><strong>${p.from_member_name}</strong> &rarr; <strong>${p.to_member_name}</strong></td>
                    <td class="green-text font-weight-bold">${formatCurrency(p.amount)}</td>
                    <td>
                        <button class="btn btn-sm btn-text" style="color:var(--neon-orange); padding:0;" onclick="handleDeleteGroupPayment(${p.id})">Delete</button>
                    </td>
                </tr>`;
        });
    }

    panel.innerHTML = `
        <div class="group-header-area">
            <div class="group-info">
                <h2>${gp.name}</h2>
                <p class="muted-text">${gp.description || ''}</p>
                <div style="margin-top:8px;">${memberLabels}</div>
            </div>
            <div class="group-actions" style="flex-wrap:wrap;">
                <button class="btn btn-primary btn-sm" onclick="openGroupExpenseModal(${gp.id})">+ Add Shared Bill</button>
                <button class="btn btn-secondary btn-sm" onclick="openGroupPaymentModal(${gp.id})">Record Return Payment</button>
                <button class="btn btn-danger btn-sm" onclick="handleDeleteGroup(${gp.id}, '${gp.name}')">Delete Group</button>
            </div>
        </div>

        <div class="group-dashboard-grid">
            <div class="running-balances-card">
                <h3>Balance Sheet</h3>
                ${balanceRows}
            </div>
            <div class="settlements-card">
                <h3>Optimized Settlements</h3>
                ${paymentRows}
            </div>
        </div>

        <div class="card" style="margin-top: 20px; padding: 15px;">
            <h3>Shared Bills Log</h3>
            <table class="ledger-table" style="margin-top:10px;">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Bill</th>
                        <th>Payer</th>
                        <th>Amount</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>${expenseRows}</tbody>
            </table>
        </div>

        <div class="card" style="margin-top: 20px; padding: 15px;">
            <h3>Settlement Payments Log</h3>
            <table class="ledger-table" style="margin-top:10px;">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Details</th>
                        <th>Amount</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>${paymentLogRows}</tbody>
            </table>
        </div>
    `;
}

// ----------------- 4. PLANNING TARGETS SCREEN -----------------
function loadPlanningScreen() {
    // Populate form accounts drop down lists
    fetch('/api/accounts')
        .then(res => res.json())
        .then(accs => {
            const planAcc = document.getElementById('plan-account');
            planAcc.innerHTML = '';
            accs.forEach(acc => {
                planAcc.innerHTML += `<option value="${acc.id}">${acc.name}</option>`;
            });
            
            // Populate update modal account drop down as well
            const upAcc = document.getElementById('update-val-account');
            upAcc.innerHTML = '';
            accs.forEach(acc => {
                upAcc.innerHTML += `<option value="${acc.id}">${acc.name}</option>`;
            });
        });

    // 1. Budgets
    fetch('/api/budgets')
        .then(res => res.json())
        .then(budgets => {
            const container = document.getElementById('budgets-container');
            container.innerHTML = '';
            if (budgets.length === 0) {
                container.innerHTML = '<span class="muted-text">No category budgets set.</span>';
                return;
            }
            budgets.forEach(b => {
                fetch(`/api/stats/category-spending?category=${b.category}`)
                    .then(res => res.json())
                    .then(data => {
                        const spent = data.spent;
                        const pct = b.amount > 0 ? (spent / b.amount) * 100 : 0;
                        let fillClass = 'normal';
                        if (pct >= 90) fillClass = 'danger';
                        else if (pct >= 70) fillClass = 'warn';
                        
                        container.innerHTML += `
                            <div class="budget-progress-card">
                                <div class="progress-header">
                                    <h4>${b.category}</h4>
                                    <span>${pct.toFixed(0)}%</span>
                                </div>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill ${fillClass}" style="width: ${Math.min(100, pct)}%"></div>
                                </div>
                                <div class="progress-footer">
                                    <span>Spent: ${formatCurrency(spent)} / Limit: ${formatCurrency(b.amount)}</span>
                                    <button class="btn btn-sm btn-text" style="color:var(--neon-orange); font-size:11px;" onclick="handleDeleteBudget(${b.id}, '${b.category}')">Delete</button>
                                </div>
                            </div>`;
                    });
            });
        });

    // 2. Savings goals
    fetch('/api/savings')
        .then(res => res.json())
        .then(goals => {
            const container = document.getElementById('savings-container');
            container.innerHTML = '';
            if (goals.length === 0) {
                container.innerHTML = '<span class="muted-text">No savings goals target set.</span>';
                return;
            }
            goals.forEach(g => {
                const pct = g.target_amount > 0 ? (g.saved_amount / g.target_amount) * 100 : 0;
                container.innerHTML += `
                    <div class="budget-progress-card">
                        <div class="progress-header">
                            <h4>${g.name}</h4>
                            <span class="green-text">${pct.toFixed(0)}%</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill normal" style="width: ${Math.min(100, pct)}%"></div>
                        </div>
                        <div class="progress-footer">
                            <span>Saved: ${formatCurrency(g.saved_amount)} / ${formatCurrency(g.target_amount)}</span>
                            <div style="display:flex; gap:8px;">
                                <button class="btn btn-sm btn-text" style="font-size:11px;" onclick="openUpdateSavingsModal(${g.id}, '${g.name}', ${g.saved_amount})">+ Funds</button>
                                <button class="btn btn-sm btn-text" style="color:var(--neon-orange); font-size:11px;" onclick="handleDeleteSavings(${g.id}, '${g.name}')">Delete</button>
                            </div>
                        </div>
                    </div>`;
            });
        });

    // 3. Subscriptions
    fetch('/api/subscriptions')
        .then(res => res.json())
        .then(subs => {
            const container = document.getElementById('subscriptions-container');
            container.innerHTML = '';
            if (subs.length === 0) {
                container.innerHTML = '<span class="muted-text">No subscriptions logged.</span>';
                return;
            }
            subs.forEach(s => {
                container.innerHTML += `
                    <div class="sub-bill-card">
                        <div class="sub-bill-info">
                            <h4>${s.name}</h4>
                            <p class="muted-text">Source: ${s.account_name} (${s.billing_cycle})</p>
                            <p style="font-size:10px; margin-top:2px;">Due: ${formatDateShort(s.renewal_date)}</p>
                        </div>
                        <div class="sub-bill-price">
                            <span>${formatCurrency(s.amount)}</span>
                            <div style="display:flex; gap:8px; margin-top:4px;">
                                <button class="btn btn-sm btn-text" style="color:var(--neon-green); font-size:11px;" onclick="renewSubscription(${s.id}, '${s.renewal_date}', '${s.billing_cycle}')">Renew</button>
                                <button class="btn btn-sm btn-text" style="color:var(--neon-orange); font-size:11px;" onclick="handleDeleteSubscription(${s.id})">Delete</button>
                            </div>
                        </div>
                    </div>`;
            });
        });

    // 4. Bills
    fetch('/api/bills')
        .then(res => res.json())
        .then(bills => {
            const container = document.getElementById('bills-container');
            container.innerHTML = '';
            if (bills.length === 0) {
                container.innerHTML = '<span class="muted-text">No upcoming bills due.</span>';
                return;
            }
            bills.forEach(b => {
                const isPaid = b.status === 'paid';
                const statusColor = isPaid ? 'green-text' : 'magenta-text';
                const actionBtn = isPaid ? 
                    '<span class="badge badge-income" style="font-size:9px; padding:2px 6px;">PAID</span>' : 
                    `<button class="btn btn-sm btn-primary" style="font-size:10px; padding:3px 6px;" onclick="openPayBillModal(${b.id}, '${b.name}', ${b.amount})">Pay</button>`;
                
                container.innerHTML += `
                    <div class="sub-bill-card" style="border-left: 3px solid ${isPaid ? 'var(--neon-green)' : 'var(--neon-magenta)'}">
                        <div class="sub-bill-info">
                            <h4>${b.name} (${b.type})</h4>
                            <p class="muted-text">Due: ${formatDateShort(b.due_date)}</p>
                        </div>
                        <div class="sub-bill-price">
                            <span>${formatCurrency(b.amount)}</span>
                            <div style="display:flex; gap:8px; margin-top:4px; align-items:center;">
                                ${actionBtn}
                                <button class="btn btn-sm btn-text" style="color:var(--neon-orange); font-size:11px;" onclick="handleDeleteBill(${b.id})">Delete</button>
                            </div>
                        </div>
                    </div>`;
            });
        });
}

// Toggle fields in unified modal forms
function togglePlanningFields() {
    const type = document.getElementById('plan-type').value;
    const catGroup = document.getElementById('group-plan-category');
    const nameGroup = document.getElementById('group-plan-name');
    const savedGroup = document.getElementById('group-plan-saved');
    const dateGroup = document.getElementById('group-plan-date');
    const cycleGroup = document.getElementById('group-plan-cycle');
    const accGroup = document.getElementById('group-plan-account');
    
    const amtLabel = document.getElementById('label-plan-amount');
    const dateLabel = document.getElementById('label-plan-date');
    
    // Hide all optional
    catGroup.style.display = 'none';
    nameGroup.style.display = 'block';
    savedGroup.style.display = 'none';
    dateGroup.style.display = 'none';
    cycleGroup.style.display = 'none';
    accGroup.style.display = 'none';
    
    if (type === 'budget') {
        catGroup.style.display = 'block';
        nameGroup.style.display = 'none';
        amtLabel.textContent = "Monthly Budget Limit (₹)";
    } else if (type === 'savings_goal') {
        savedGroup.style.display = 'block';
        dateGroup.style.display = 'block';
        amtLabel.textContent = "Target Goal Amount (₹)";
        dateLabel.textContent = "Target Due Date";
    } else if (type === 'subscription') {
        dateGroup.style.display = 'block';
        cycleGroup.style.display = 'block';
        accGroup.style.display = 'block';
        amtLabel.textContent = "Billing Cost Amount (₹)";
        dateLabel.textContent = "Renewal Date";
    } else if (type === 'bill') {
        dateGroup.style.display = 'block';
        accGroup.style.display = 'block';
        amtLabel.textContent = "Bill Total Due (₹)";
        dateLabel.textContent = "Due Date";
    }
}

function submitAddPlanningItem(e) {
    e.preventDefault();
    const type = document.getElementById('plan-type').value;
    const amount = document.getElementById('plan-amount').value;
    
    if (type === 'budget') {
        const category = document.getElementById('plan-category').value;
        fetch('/api/budgets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, amount, period: 'monthly' })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-planning-item');
            loadPlanningScreen();
        });
        
    } else if (type === 'savings_goal') {
        const name = document.getElementById('plan-name').value;
        const saved = document.getElementById('plan-saved').value || 0;
        const date = document.getElementById('plan-date').value;
        fetch('/api/savings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, target_amount: amount, saved_amount: saved, target_date: date })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-planning-item');
            loadPlanningScreen();
        });
        
    } else if (type === 'subscription') {
        const name = document.getElementById('plan-name').value;
        const date = document.getElementById('plan-date').value;
        const cycle = document.getElementById('plan-cycle').value;
        const account_id = document.getElementById('plan-account').value;
        fetch('/api/subscriptions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, amount, renewal_date: date, billing_cycle: cycle, account_id })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-planning-item');
            loadPlanningScreen();
        });
        
    } else if (type === 'bill') {
        const name = document.getElementById('plan-name').value;
        const date = document.getElementById('plan-date').value;
        const account_id = document.getElementById('plan-account').value;
        fetch('/api/bills', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, type: 'Other', amount, due_date: date, status: 'unpaid', account_id })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-planning-item');
            loadPlanningScreen();
        });
    }
}

// ----------------- 5. BALANCE SCREEN (Assets & Debts) -----------------
function loadBalanceScreen() {
    // Investments
    fetch('/api/investments')
        .then(res => res.json())
        .then(invests => {
            const tbody = document.getElementById('investments-list');
            tbody.innerHTML = '';
            if (invests.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="muted-text" style="text-align:center;">No asset investments added.</td></tr>';
                return;
            }
            invests.forEach(iv => {
                const profit = iv.current_value - iv.invested_amount;
                const growthClass = profit >= 0 ? 'green-text' : 'magenta-text';
                const sign = profit >= 0 ? '+' : '';
                
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${iv.name}</strong> <span class="muted-text" style="font-size:10px;">(${iv.type})</span></td>
                        <td>${formatCurrency(iv.invested_amount)}</td>
                        <td class="${growthClass} font-weight-bold">${formatCurrency(iv.current_value)}</td>
                        <td class="${growthClass}">${sign}${formatCurrency(profit)}</td>
                        <td>
                            <div style="display:flex; gap:6px;">
                                <button class="btn btn-sm btn-text" onclick="openUpdateInvestmentModal(${iv.id}, '${iv.name}', ${iv.current_value})">Update</button>
                                <button class="btn btn-sm btn-text" style="color:var(--neon-orange);" onclick="handleDeleteInvestment(${iv.id})">Delete</button>
                            </div>
                        </td>
                    </tr>`;
            });
        });

    // Debts
    fetch('/api/debts')
        .then(res => res.json())
        .then(debts => {
            const container = document.getElementById('debt-container');
            container.innerHTML = '';
            if (debts.length === 0) {
                container.innerHTML = '<span class="muted-text">No loan files logged.</span>';
                return;
            }
            debts.forEach(d => {
                const badgeType = d.type === 'borrowed' ? 'borrowed' : 'lent';
                const statusColor = d.type === 'borrowed' ? 'magenta-text' : 'green-text';
                
                container.innerHTML += `
                    <div class="debt-card" style="padding:15px; border-radius:10px; margin-bottom:10px;">
                        <div class="debt-header" style="padding-bottom:8px; margin-bottom:8px;">
                            <span class="debt-type-badge ${badgeType}">${badgeType}</span>
                            <h4>${d.person}</h4>
                        </div>
                        <div class="debt-details" style="gap:4px; font-size:12px;">
                            <div class="debt-row"><span>Principal Owed:</span> <span class="${statusColor}"><strong>${formatCurrency(d.remaining_balance)}</strong></span></div>
                            <div class="debt-row"><span>Interest:</span> <span>${d.interest_rate}% compounding ${d.compounding_period}</span></div>
                            <div class="debt-row"><span>Start Date:</span> <span>${formatDateShort(d.start_date)}</span></div>
                        </div>
                        <div class="debt-actions" style="margin-top:10px; padding-top:8px; gap:8px;">
                            <button class="btn btn-sm btn-primary" style="font-size:11px; padding:4px 8px;" onclick="openRepayDebtModal(${d.id}, '${d.person}', '${d.type}', ${d.remaining_balance})">
                                Repay Balance
                            </button>
                            <button class="btn btn-sm btn-text" style="color:var(--neon-orange); font-size:11px;" onclick="handleDeleteDebt(${d.id})">
                                Delete
                            </button>
                        </div>
                    </div>`;
            });
        });
}

function toggleBalanceFields() {
    const type = document.getElementById('bal-type').value;
    const invGroup = document.getElementById('group-bal-invest-type');
    const curGroup = document.getElementById('group-bal-current');
    const rateGroup = document.getElementById('group-bal-rate');
    const compGroup = document.getElementById('group-bal-compound');
    const emiGroup = document.getElementById('group-bal-emi');
    const dateGroup = document.getElementById('group-bal-date');
    
    const nameLabel = document.getElementById('label-bal-name');
    const priLabel = document.getElementById('label-bal-principal');
    
    // Hide debt fields as default
    invGroup.style.display = 'block';
    curGroup.style.display = 'block';
    rateGroup.style.display = 'none';
    compGroup.style.display = 'none';
    emiGroup.style.display = 'none';
    dateGroup.style.display = 'none';
    nameLabel.textContent = "Asset Name";
    priLabel.textContent = "Principal Invested Amount (₹)";
    
    if (type === 'borrowed' || type === 'lent') {
        invGroup.style.display = 'none';
        curGroup.style.display = 'none';
        rateGroup.style.display = 'block';
        compGroup.style.display = 'block';
        emiGroup.style.display = 'block';
        dateGroup.style.display = 'block';
        nameLabel.textContent = "Person Name";
        priLabel.textContent = "Loan Principal Amount (₹)";
    }
}

function submitAddBalanceItem(e) {
    e.preventDefault();
    const type = document.getElementById('bal-type').value;
    const name = document.getElementById('bal-name').value;
    const principal = document.getElementById('bal-principal').value;
    const notes = document.getElementById('bal-notes').value;
    
    if (type === 'investment') {
        const i_type = document.getElementById('bal-invest-type').value;
        const current = document.getElementById('bal-current').value;
        fetch('/api/investments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, type: i_type, invested_amount: principal, current_value: current, notes })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-balance-item');
            loadBalanceScreen();
            loadDashboard();
        });
        
    } else {
        const rate = document.getElementById('bal-rate').value;
        const compound = document.getElementById('bal-compound').value;
        const emi = document.getElementById('bal-emi').value || 0;
        const date = document.getElementById('bal-date').value;
        
        fetch('/api/debts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type, person: name, amount: principal, interest_rate: rate,
                compounding_period: compound, remaining_balance: principal, emi_amount: emi,
                start_date: date, due_date: '', notes
            })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-add-balance-item');
            loadBalanceScreen();
            loadDashboard();
        });
    }
}

// ----------------- GENERIC VAL DIALOG UPDATES -----------------
function openUpdateSavingsModal(id, name, current) {
    setupGenericModal(id, 'savings', `Add savings targets for "${name}" (₹)`, current);
}

function openUpdateInvestmentModal(id, name, current) {
    setupGenericModal(id, 'investment', `Update Market value of "${name}" (₹)`, current);
}

function openRepayDebtModal(id, person, type, remaining) {
    setupGenericModal(id, `debt_${type}`, `Repay Debt to "${person}" (₹)`, remaining, true);
}

function openPayBillModal(id, name, amount) {
    setupGenericModal(id, 'bill_pay', `Pay Bill "${name}" (₹)`, amount, true);
}

function setupGenericModal(id, mode, title, value, showAccount = false) {
    document.getElementById('update-val-id').value = id;
    document.getElementById('update-val-mode').value = mode;
    document.getElementById('update-val-title').textContent = title;
    document.getElementById('update-val-input').value = value;
    
    const accGroup = document.getElementById('group-update-val-account');
    if (showAccount) {
        accGroup.style.display = 'block';
    } else {
        accGroup.style.display = 'none';
    }
    
    openModal('modal-update-value');
}

function submitGenericUpdate(e) {
    e.preventDefault();
    const id = document.getElementById('update-val-id').value;
    const mode = document.getElementById('update-val-mode').value;
    const val = document.getElementById('update-val-input').value;
    
    if (mode === 'savings') {
        fetch(`/api/savings/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ saved_amount: val })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-update-value');
            loadPlanningScreen();
            loadDashboard();
        });
        
    } else if (mode === 'investment') {
        fetch(`/api/investments/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_value: val })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-update-value');
            loadBalanceScreen();
            loadDashboard();
        });
        
    } else if (mode.startsWith('debt_')) {
        const type = mode.replace('debt_', '');
        const account_id = document.getElementById('update-val-account').value;
        fetch(`/api/debts/${id}/repay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: val, account_id, type })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-update-value');
            loadBalanceScreen();
            loadDashboard();
        });
        
    } else if (mode === 'bill_pay') {
        const account_id = document.getElementById('update-val-account').value;
        fetch(`/api/bills/${id}/pay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ account_id })
        })
        .then(res => res.json())
        .then(() => {
            closeModal('modal-update-value');
            loadPlanningScreen();
            loadDashboard();
        });
    }
}

// Helper deletions/actions
function handleDeleteAccount(id, name) {
    if (confirm(`Delete account "${name}"? It will delete related transactions.`)) {
        fetch(`/api/accounts/${id}`, { method: 'DELETE' }).then(() => loadLedgerScreen());
    }
}

function handleTransfer(e) {
    e.preventDefault();
    const from_id = document.getElementById('trans-from').value;
    const to_id = document.getElementById('trans-to').value;
    const amount = document.getElementById('trans-amount').value;
    
    if (from_id === to_id) {
        alert("Source and Destination accounts must be different.");
        return;
    }
    
    fetch('/api/transactions/transfer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_account_id: from_id, to_account_id: to_id, amount, date: new Date().toISOString().split('T')[0] })
    })
    .then(res => res.json())
    .then(() => {
        document.getElementById('trans-amount').value = '';
        loadLedgerScreen();
    });
}

function handleDeleteTransaction(id) {
    if (confirm("Delete transaction ledger entry?")) {
        fetch(`/api/transactions/${id}`, { method: 'DELETE' }).then(() => loadLedgerScreen());
    }
}

function viewReceipt(path) {
    window.open(`/api/receipts/view?path=${encodeURIComponent(path)}`, '_blank');
}

function submitAddGroup(e) {
    e.preventDefault();
    const name = document.getElementById('add-gp-name').value;
    const desc = document.getElementById('add-gp-desc').value;
    const membersText = document.getElementById('add-gp-members').value;
    const members = membersText.split('\n').map(m => m.trim()).filter(m => m.length > 0);
    
    fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description: desc, members })
    })
    .then(res => res.json())
    .then(data => {
        closeModal('modal-add-group');
        document.getElementById('add-gp-name').value = '';
        document.getElementById('add-gp-desc').value = '';
        document.getElementById('add-gp-members').value = '';
        loadSplitScreen();
        selectGroup(data.group_id);
    });
}

function handleDeleteGroup(id, name) {
    if (confirm(`Delete the split group "${name}"?`)) {
        fetch(`/api/groups/${id}`, { method: 'DELETE' }).then(() => {
            state.activeGroup = null;
            loadSplitScreen();
            document.getElementById('group-details-panel').innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">👥</div>
                    <h3>No Split Group Selected</h3>
                    <p>Select a group from the sidebar, or create a new permanent group for flatmates, trips, or team events.</p>
                </div>`;
        });
    }
}

// Helper functions to populate personal account selectors in split groups modals
function populateGroupExpenseAccountSelector() {
    const select = document.getElementById('gp-exp-personal-account');
    if (!select) return;
    select.innerHTML = '<option value="">-- Do Not Deduct From Ledger --</option>';
    
    const addOptions = (accs) => {
        accs.forEach(acc => {
            select.innerHTML += `<option value="${acc.id}">Deduct from ${acc.name} (Bal: ₹${acc.balance.toFixed(2)})</option>`;
        });
    };
    
    if (state.accounts && state.accounts.length > 0) {
        addOptions(state.accounts);
    } else {
        fetch('/api/accounts')
            .then(res => res.json())
            .then(accs => {
                state.accounts = accs;
                addOptions(accs);
            });
    }
}

function populateGroupPaymentAccountSelector() {
    const select = document.getElementById('gp-pay-personal-account');
    if (!select) return;
    select.innerHTML = '<option value="">-- Do Not Link to Ledger --</option>';
    
    const addOptions = (accs) => {
        accs.forEach(acc => {
            select.innerHTML += `<option value="income_${acc.id}">Received: Add to ${acc.name} (Bal: ₹${acc.balance.toFixed(2)})</option>`;
            select.innerHTML += `<option value="expense_${acc.id}">Paid: Deduct from ${acc.name} (Bal: ₹${acc.balance.toFixed(2)})</option>`;
        });
    };
    
    if (state.accounts && state.accounts.length > 0) {
        addOptions(state.accounts);
    } else {
        fetch('/api/accounts')
            .then(res => res.json())
            .then(accs => {
                state.accounts = accs;
                addOptions(accs);
            });
    }
}

// Split Group Expense details
function openGroupExpenseModal(groupId) {
    document.getElementById('gp-exp-group-id').value = groupId;
    document.getElementById('gp-exp-date').value = new Date().toISOString().split('T')[0];
    
    const payerSelect = document.getElementById('gp-exp-payer');
    payerSelect.innerHTML = '';
    state.activeGroup.members.forEach(m => {
        payerSelect.innerHTML += `<option value="${m.id}">${m.name}</option>`;
    });
    
    populateGroupExpenseAccountSelector();
    changeSplitWizardType();
    openModal('modal-add-group-expense');
}

function changeSplitWizardType() {
    const type = document.getElementById('gp-exp-type').value;
    const container = document.getElementById('split-wizard-options');
    const amount = parseFloat(document.getElementById('gp-exp-amount').value) || 0.0;
    const members = state.activeGroup.members.map(m => m.name);
    
    container.innerHTML = '';
    
    if (type === 'equal') {
        members.forEach(m => {
            container.innerHTML += `
                <div class="wizard-row" style="padding: 4px 0;">
                    <label>${m}</label>
                    <input type="checkbox" checked value="${m}" name="equal-participant" style="width:20px; height:20px;">
                </div>`;
        });
    } else if (type === 'unequal') {
        members.forEach(m => {
            container.innerHTML += `
                <div class="wizard-row">
                    <label>${m}</label>
                    <input type="number" step="0.01" value="0.00" class="unequal-share" data-member="${m}" oninput="verifyUnequalSum()">
                </div>`;
        });
        container.innerHTML += `<div id="unequal-error" class="orange-text" style="font-size:11px; margin-top:8px;">Sum of shares: $0.00 / Target: $${amount.toFixed(2)}</div>`;
    } else if (type === 'percentage') {
        members.forEach(m => {
            container.innerHTML += `
                <div class="wizard-row">
                    <label>${m}</label>
                    <input type="number" step="0.1" value="0" class="percentage-share" data-member="${m}" oninput="verifyPercentageSum()">
                </div>`;
        });
        container.innerHTML += `<div id="percentage-error" class="orange-text" style="font-size:11px; margin-top:8px;">Sum of percentages: 0% / Target: 100%</div>`;
    } else if (type === 'quantity') {
        members.forEach(m => {
            container.innerHTML += `
                <div class="wizard-row">
                    <label>${m}</label>
                    <input type="number" min="0" value="0" class="quantity-share" data-member="${m}">
                </div>`;
        });
    } else if (type === 'item') {
        container.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <h4>Add Itemized Lines</h4>
                <button type="button" class="btn btn-sm btn-secondary" onclick="addWizardItemRow()">+ Add Item Row</button>
            </div>
            <div class="wizard-items-list" id="wizard-items-container"></div>
            <div class="form-row" style="margin-top:15px;">
                <div class="form-group-v" style="flex:1;">
                    <label>Tax ($)</label>
                    <input type="number" id="wizard-item-tax" step="0.01" value="0.00" oninput="verifyItemTotal()">
                </div>
                <div class="form-group-v" style="flex:1;">
                    <label>Tip ($)</label>
                    <input type="number" id="wizard-item-tip" step="0.01" value="0.00" oninput="verifyItemTotal()">
                </div>
            </div>
            <div class="form-group-v">
                <label>Split Tax & Tip</label>
                <select id="wizard-item-tax-split">
                    <option value="proportional" selected>Proportionate</option>
                    <option value="equal">Equal</option>
                </select>
            </div>
            <div id="item-error" class="orange-text" style="font-size:11px; margin-top:8px;">Subtotal + Tax + Tip: $0.00 / Target: $${amount.toFixed(2)}</div>
        `;
        addWizardItemRow();
    }
}

function updateSplitWizardDetails() {
    const type = document.getElementById('gp-exp-type').value;
    if (type === 'unequal') verifyUnequalSum();
    else if (type === 'percentage') verifyPercentageSum();
    else if (type === 'item') verifyItemTotal();
}

function verifyUnequalSum() {
    const target = parseFloat(document.getElementById('gp-exp-amount').value) || 0.0;
    let sum = 0;
    document.querySelectorAll('.unequal-share').forEach(input => {
        sum += parseFloat(input.value) || 0.0;
    });
    const errEl = document.getElementById('unequal-error');
    if (Math.abs(sum - target) > 0.02) {
        errEl.textContent = `Sum: $${sum.toFixed(2)} / Target: $${target.toFixed(2)}`;
        errEl.className = "orange-text";
    } else {
        errEl.textContent = `Sum matches target! ($${sum.toFixed(2)})`;
        errEl.className = "green-text";
    }
}

function verifyPercentageSum() {
    let sum = 0;
    document.querySelectorAll('.percentage-share').forEach(input => {
        sum += parseFloat(input.value) || 0.0;
    });
    const errEl = document.getElementById('percentage-error');
    if (Math.abs(sum - 100) > 0.1) {
        errEl.textContent = `Sum: ${sum.toFixed(1)}% / Target: 100%`;
        errEl.className = "orange-text";
    } else {
        errEl.textContent = `Percentages valid! (100%)`;
        errEl.className = "green-text";
    }
}

function addWizardItemRow() {
    const container = document.getElementById('wizard-items-container');
    const members = state.activeGroup.members.map(m => m.name);
    const rowId = 'item-row-' + Math.random().toString(36).substr(2, 5);
    
    let consumerBadges = '';
    members.forEach(m => {
        consumerBadges += `<span class="consumer-badge selected" onclick="toggleConsumerSelection(this)" data-member="${m}">${m}</span>`;
    });

    const itemRow = document.createElement('div');
    itemRow.className = 'item-wizard-row';
    itemRow.id = rowId;
    itemRow.innerHTML = `
        <div class="item-fields">
            <input type="text" class="wizard-item-name" placeholder="Item name" required style="flex:2; padding:6px;">
            <input type="number" class="wizard-item-price" step="0.01" min="0" placeholder="$0.00" oninput="verifyItemTotal()" required style="flex:1; padding:6px;">
            <button type="button" class="btn btn-sm btn-danger" onclick="document.getElementById('${rowId}').remove(); verifyItemTotal();">X</button>
        </div>
        <div class="item-consumers" style="margin-top:5px;">
            ${consumerBadges}
        </div>
    `;
    container.appendChild(itemRow);
    verifyItemTotal();
}

function toggleConsumerSelection(badge) {
    badge.classList.toggle('selected');
    verifyItemTotal();
}

function verifyItemTotal() {
    const target = parseFloat(document.getElementById('gp-exp-amount').value) || 0.0;
    let subtotal = 0;
    document.querySelectorAll('.wizard-item-price').forEach(input => {
        subtotal += parseFloat(input.value) || 0.0;
    });
    const tax = parseFloat(document.getElementById('wizard-item-tax').value) || 0.0;
    const tip = parseFloat(document.getElementById('wizard-item-tip').value) || 0.0;
    const grandTotal = subtotal + tax + tip;
    const errEl = document.getElementById('item-error');
    if (!errEl) return;
    if (Math.abs(grandTotal - target) > 0.02) {
        errEl.textContent = `Calculated: $${grandTotal.toFixed(2)} / Target: $${target.toFixed(2)}`;
        errEl.className = "orange-text";
    } else {
        errEl.textContent = `Matches target! ($${grandTotal.toFixed(2)})`;
        errEl.className = "green-text";
    }
}

function submitGroupExpense(e) {
    e.preventDefault();
    const groupId = document.getElementById('gp-exp-group-id').value;
    const description = document.getElementById('gp-exp-desc').value;
    const amount = parseFloat(document.getElementById('gp-exp-amount').value);
    const payer_id = document.getElementById('gp-exp-payer').value;
    const date = document.getElementById('gp-exp-date').value;
    const split_type = document.getElementById('gp-exp-type').value;
    const details = {};
    
    if (split_type === 'equal') {
        const participants = [];
        document.querySelectorAll('input[name="equal-participant"]:checked').forEach(c => {
            participants.push(c.value);
        });
        if (participants.length === 0) return;
        details.participants = participants;
    } else if (split_type === 'unequal') {
        const shares = {};
        document.querySelectorAll('.unequal-share').forEach(input => {
            shares[input.getAttribute('data-member')] = parseFloat(input.value) || 0.0;
        });
        details.shares = shares;
    } else if (split_type === 'percentage') {
        const percentages = {};
        document.querySelectorAll('.percentage-share').forEach(input => {
            percentages[input.getAttribute('data-member')] = parseFloat(input.value) || 0.0;
        });
        details.percentages = percentages;
    } else if (split_type === 'quantity') {
        const quantities = {};
        document.querySelectorAll('.quantity-share').forEach(input => {
            quantities[input.getAttribute('data-member')] = parseInt(input.value) || 0;
        });
        details.quantities = quantities;
    } else if (split_type === 'item') {
        const items = [];
        document.querySelectorAll('.item-wizard-row').forEach(row => {
            const name = row.querySelector('.wizard-item-name').value;
            const price = parseFloat(row.querySelector('.wizard-item-price').value) || 0.0;
            const consumers = [];
            row.querySelectorAll('.consumer-badge.selected').forEach(badge => {
                consumers.push(badge.getAttribute('data-member'));
            });
            items.push({ name, price, consumers });
        });
        details.items = items;
        details.tax = parseFloat(document.getElementById('wizard-item-tax').value) || 0.0;
        details.tip = parseFloat(document.getElementById('wizard-item-tip').value) || 0.0;
        details.tax_tip_split = document.getElementById('wizard-item-tax-split').value;
    }
    
    const personalAccVal = document.getElementById('gp-exp-personal-account').value;
    const personal_account_id = personalAccVal ? parseInt(personalAccVal) : null;
    
    fetch(`/api/groups/${groupId}/expenses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, amount, paid_by_member_id: payer_id, date, split_type, details, personal_account_id })
    }).then(() => {
        closeModal('modal-add-group-expense');
        document.getElementById('form-group-expense').reset();
        selectGroup(groupId);
        loadGlobalStats();
        if (window.location.hash === '#ledger') loadLedgerScreen();
    });
}

function handleDeleteGroupExpense(expId) {
    if (confirm("Delete shared bill expense?")) {
        fetch(`/api/groups/expenses/${expId}`, { method: 'DELETE' }).then(() => {
            selectGroup(state.activeGroup.id);
            loadGlobalStats();
            if (window.location.hash === '#ledger') loadLedgerScreen();
        });
    }
}

function openGroupPaymentModal(groupId) {
    document.getElementById('gp-pay-group-id').value = groupId;
    document.getElementById('gp-pay-date').value = new Date().toISOString().split('T')[0];
    
    const fromSelect = document.getElementById('gp-pay-from');
    const toSelect = document.getElementById('gp-pay-to');
    fromSelect.innerHTML = '';
    toSelect.innerHTML = '';
    
    state.activeGroup.members.forEach(m => {
        fromSelect.innerHTML += `<option value="${m.id}">${m.name}</option>`;
        toSelect.innerHTML += `<option value="${m.id}">${m.name}</option>`;
    });
    
    populateGroupPaymentAccountSelector();
    openModal('modal-add-group-payment');
}

function submitGroupPayment(e) {
    e.preventDefault();
    const groupId = document.getElementById('gp-pay-group-id').value;
    const from_member_id = document.getElementById('gp-pay-from').value;
    const to_member_id = document.getElementById('gp-pay-to').value;
    const amount = document.getElementById('gp-pay-amount').value;
    const date = document.getElementById('gp-pay-date').value;
    
    if (from_member_id === to_member_id) {
        alert("Payer and Receiver members must be different.");
        return;
    }
    
    const personalLinkVal = document.getElementById('gp-pay-personal-account').value;
    let personal_account_id = null;
    let personal_action = null;
    if (personalLinkVal) {
        const parts = personalLinkVal.split('_');
        personal_action = parts[0];
        personal_account_id = parseInt(parts[1]);
    }
    
    fetch(`/api/groups/${groupId}/payments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_member_id, to_member_id, amount, date, personal_account_id, personal_action })
    }).then(() => {
        closeModal('modal-add-group-payment');
        selectGroup(groupId);
        loadGlobalStats();
        if (window.location.hash === '#ledger') loadLedgerScreen();
    });
}

function handleDeleteGroupPayment(payId) {
    if (confirm("Delete cash payment log?")) {
        fetch(`/api/groups/payments/${payId}`, { method: 'DELETE' }).then(() => {
            selectGroup(state.activeGroup.id);
            loadGlobalStats();
            if (window.location.hash === '#ledger') loadLedgerScreen();
        });
    }
}

// ----------------- PLANNING HELPER ACTIONS -----------------
function handleDeleteBudget(id, name) {
    if (confirm(`Delete budget for "${name}"?`)) {
        fetch(`/api/budgets/${id}`, { method: 'DELETE' }).then(() => loadPlanningScreen());
    }
}

function handleDeleteSavings(id, name) {
    if (confirm(`Delete goal "${name}"?`)) {
        fetch(`/api/savings/${id}`, { method: 'DELETE' }).then(() => loadPlanningScreen());
    }
}

function renewSubscription(id, current_renewal, billing_cycle) {
    let date = new Date(current_renewal);
    if (billing_cycle === 'monthly') date.setMonth(date.getMonth() + 1);
    else date.setFullYear(date.getFullYear() + 1);
    
    fetch(`/api/subscriptions/${id}/renew`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ renewal_date: date.toISOString().split('T')[0] })
    }).then(() => loadPlanningScreen());
}

function handleDeleteSubscription(id) {
    if (confirm("Remove subscription?")) {
        fetch(`/api/subscriptions/${id}`, { method: 'DELETE' }).then(() => loadPlanningScreen());
    }
}

function handleDeleteBill(id) {
    if (confirm("Delete bill reminder?")) {
        fetch(`/api/bills/${id}`, { method: 'DELETE' }).then(() => loadPlanningScreen());
    }
}

// ----------------- BALANCE SHEET HELPER ACTIONS -----------------
function handleDeleteInvestment(id) {
    if (confirm("Remove investment asset?")) {
        fetch(`/api/investments/${id}`, { method: 'DELETE' }).then(() => {
            loadBalanceScreen();
            loadDashboard();
        });
    }
}

function handleDeleteDebt(id) {
    if (confirm("Delete debt record?")) {
        fetch(`/api/debts/${id}`, { method: 'DELETE' }).then(() => {
            loadBalanceScreen();
            loadDashboard();
        });
    }
}

// ----------------- CALCULATORS -----------------
function runCompoundCalc(e) {
    e.preventDefault();
    const principal = document.getElementById('cc-principal').value;
    const rate = document.getElementById('cc-rate').value;
    const frequency = document.getElementById('cc-frequency').value;
    const years = document.getElementById('cc-years').value;
    
    fetch('/api/calc/compound', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ principal, rate, times_compounded_per_year: frequency, years })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('cc-res-total').textContent = formatCurrency(data.total_amount);
        document.getElementById('cc-res-interest').textContent = formatCurrency(data.interest_earned);
        document.getElementById('compound-results').style.display = 'flex';
    });
}

function runLoanCalc(e) {
    e.preventDefault();
    const principal = document.getElementById('lc-principal').value;
    const rate = document.getElementById('lc-rate').value;
    const months = document.getElementById('lc-months').value;
    
    fetch('/api/calc/loan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ principal, rate, tenure_months: months })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('lc-res-emi').textContent = `${formatCurrency(data.emi)}/mo`;
        document.getElementById('lc-res-total').textContent = formatCurrency(data.total_payment);
        document.getElementById('lc-res-interest').textContent = formatCurrency(data.total_interest);
        document.getElementById('loan-results').style.display = 'flex';
        
        const tbody = document.getElementById('amortization-schedule-rows');
        tbody.innerHTML = '';
        data.schedule.forEach(row => {
            tbody.innerHTML += `
                <tr>
                    <td>Month ${row.month}</td>
                    <td>${formatCurrency(row.emi)}</td>
                    <td class="green-text">${formatCurrency(row.principal_paid)}</td>
                    <td class="magenta-text">${formatCurrency(row.interest_paid)}</td>
                    <td class="muted-text">${formatCurrency(row.remaining_principal)}</td>
                </tr>`;
        });
        document.getElementById('amortization-table-card').style.display = 'block';
    });
}

// ----------------- EXPORT -----------------
function exportData(format) {
    const search_text = document.getElementById('filter-search').value;
    const type = document.getElementById('filter-type').value;
    let url = `/api/transactions/export?format=${format}`;
    if (search_text) url += `&search_text=${encodeURIComponent(search_text)}`;
    if (type) url += `&type=${type}`;
    window.open(url, '_blank');
}

// ----------------- MODAL ACTIONS -----------------
function openModal(id) {
    state.lastActiveElement = document.activeElement;
    document.getElementById('modal-backdrop').style.display = 'block';
    const modal = document.getElementById(id);
    modal.style.display = 'block';
    setTimeout(() => modal.classList.add('active'), 10);
    
    if (id === 'modal-add-transaction') toggleConsolidatedTxFields();
    else if (id === 'modal-add-planning-item') togglePlanningFields();
    else if (id === 'modal-add-balance-item') toggleBalanceFields();

    // Auto-focus first visible input
    setTimeout(() => {
        const focusables = modal.querySelectorAll('input, select, textarea, button');
        const visible = Array.from(focusables).filter(el => {
            return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
        });
        if (visible.length > 0) {
            visible[0].focus();
        }
    }, 220);
}

function closeModal(id) {
    const modal = document.getElementById(id);
    modal.classList.remove('active');
    setTimeout(() => {
        modal.style.display = 'none';
        const activeModals = document.querySelectorAll('.modal.active');
        if (activeModals.length === 0) {
            document.getElementById('modal-backdrop').style.display = 'none';
        }
        if (state.lastActiveElement) {
            state.lastActiveElement.focus();
            state.lastActiveElement = null;
        }
    }, 200);
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('active');
        setTimeout(() => modal.style.display = 'none', 200);
    });
    document.getElementById('modal-backdrop').style.display = 'none';
}

function submitAddAccount(e) {
    e.preventDefault();
    const name = document.getElementById('add-acc-name').value;
    const type = document.getElementById('add-acc-type').value;
    const balance = document.getElementById('add-acc-balance').value;
    
    fetch('/api/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, type, initial_balance: balance })
    }).then(() => {
        closeModal('modal-add-account');
        loadLedgerScreen();
        loadGlobalStats();
    });
}

function formatCurrency(amt) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amt);
}

function formatDateShort(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Global Keyboard Shortcuts (Simple single-character keys when not typing)
document.addEventListener('keydown', (e) => {
    const active = document.activeElement;
    const isTyping = active && (active.tagName === 'INPUT' || active.tagName === 'SELECT' || active.tagName === 'TEXTAREA');
    const isTextareaOrSelect = active && (active.tagName === 'TEXTAREA' || active.tagName === 'SELECT');

    if (e.key === 'Escape') {
        if (isTyping) {
            active.blur(); // Blur exits form insert mode
            e.preventDefault();
        } else {
            closeAllModals();
        }
        return;
    }

    // Allow ArrowUp and ArrowDown to navigate input fields inside forms & modals (except textareas and selects)
    if (isTyping && !isTextareaOrSelect && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
        const activeContainer = active.closest('form') || active.closest('.modal') || active.closest('.card') || document.body;
        const focusables = activeContainer.querySelectorAll('input, select, textarea, button');
        const visible = Array.from(focusables).filter(el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length));
        const idx = visible.indexOf(active);
        
        if (e.key === 'ArrowDown') {
            if (idx !== -1 && idx < visible.length - 1) {
                visible[idx + 1].focus();
                e.preventDefault();
            }
        } else if (e.key === 'ArrowUp') {
            if (idx > 0) {
                visible[idx - 1].focus();
                e.preventDefault();
            }
        }
    }

    // Trap focus inside open active modals to enable full keyboard tab navigation
    if (e.key === 'Tab') {
        const activeModal = document.querySelector('.modal.active');
        if (activeModal) {
            const focusables = activeModal.querySelectorAll('input, select, textarea, button, a, [tabindex="0"]');
            const visible = Array.from(focusables).filter(el => {
                return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
            });
            if (visible.length > 0) {
                const first = visible[0];
                const last = visible[visible.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                    last.focus();
                    e.preventDefault();
                } else if (!e.shiftKey && document.activeElement === last) {
                    first.focus();
                    e.preventDefault();
                }
            }
        }
    }

    // Support single character key shortcuts when NOT actively typing in an input form field
    if (!isTyping && !e.ctrlKey && !e.metaKey && !e.altKey) {
        // Tab screen navigation using ArrowLeft and ArrowRight keys
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
            const tabs = ['dashboard', 'ledger', 'split', 'planning', 'balance'];
            const currentTab = window.location.hash.replace('#', '') || 'dashboard';
            let idx = tabs.indexOf(currentTab);
            if (idx === -1) idx = 0;
            
            if (e.key === 'ArrowRight') {
                const nextIdx = (idx + 1) % tabs.length;
                window.location.hash = `#${tabs[nextIdx]}`;
                e.preventDefault();
            } else if (e.key === 'ArrowLeft') {
                const prevIdx = (idx - 1 + tabs.length) % tabs.length;
                window.location.hash = `#${tabs[prevIdx]}`;
                e.preventDefault();
            }
            return;
        }

        let handled = true;
        switch (e.key.toLowerCase()) {
            case '1':
                window.location.hash = '#dashboard';
                break;
            case '2':
                window.location.hash = '#ledger';
                break;
            case '3':
                window.location.hash = '#split';
                break;
            case '4':
                window.location.hash = '#planning';
                break;
            case '5':
                window.location.hash = '#balance';
                break;
            case 'n':
                openModal('modal-add-transaction');
                break;
            case 'p':
                openModal('modal-add-planning-item');
                break;
            case 'a':
                openModal('modal-add-balance-item');
                break;
            case 'g':
                openModal('modal-add-group');
                break;
            case 'h':
                openModal('modal-keyboard-help');
                break;
            default:
                handled = false;
        }
        if (handled) {
            e.preventDefault();
        }
    }
});

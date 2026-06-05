document.addEventListener('DOMContentLoaded', () => {
    // --- State Management ---
    let currentDevice = null;
    let riskChart = null;
    let scanInterval = null;
    let currentPath   = '/sdcard/';
    let pathHistory   = [];
    let scanMode      = 'quick';   // 'quick' | 'deep'
    let virusScanMode = 'quick';   // 'quick' | 'deep'

    // --- Initialization ---
    initRiskChart();
    checkDeviceStatus();
    setInterval(checkDeviceStatus, 5000); // Check device every 5s
    
    // --- Theme System (persists via localStorage, dark by default) ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    function applyTheme(theme) {
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('droidScanTheme', theme);
        if (themeToggleBtn) {
            themeToggleBtn.innerHTML = theme === 'dark' ? '<i data-lucide="sun"></i>' : '<i data-lucide="moon"></i>';
            lucide.createIcons();
        }
        ['theme-dark-btn','theme-light-btn'].forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            const isActive = (id === 'theme-dark-btn' && theme === 'dark') || (id === 'theme-light-btn' && theme === 'light');
            el.style.background = isActive ? 'var(--accent-primary)' : 'transparent';
            el.style.color = isActive ? '#fff' : 'var(--text-main)';
            el.style.borderColor = isActive ? 'var(--accent-primary)' : 'var(--border-color)';
        });
    }
    window.setTheme = (t) => applyTheme(t);
    applyTheme(localStorage.getItem('droidScanTheme') || 'dark');
    themeToggleBtn?.addEventListener('click', () => {
        applyTheme(document.body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });

    // --- Device Detail Modal ---
    let deviceModalData = {};
    window.toggleDeviceModal = function() {
        const modal = document.getElementById('device-detail-modal');
        if (!modal) return;
        const isOpen = modal.style.display === 'flex';
        modal.style.display = isOpen ? 'none' : 'flex';
        if (!isOpen) {
            const d = deviceModalData;
            document.getElementById('modal-device-name').textContent = d.model || 'No Device';
            document.getElementById('modal-device-sub').textContent  = d.android_version ? `Android ${d.android_version}` : 'Connect a device via USB';
            document.getElementById('modal-serial').textContent = d.device_id || '--';
            const badge = document.getElementById('modal-connected-badge');
            if (badge) badge.style.display = d.connected ? 'inline-flex' : 'none';
            // Battery
            const bat = parseInt(d.battery) || 0;
            document.getElementById('modal-battery').textContent = bat ? `${bat}%` : '--';
            const batBar = document.getElementById('modal-battery-bar');
            if (batBar) { batBar.style.width = `${bat}%`; batBar.style.background = bat<=20?'#ef4444':bat<=50?'#f59e0b':'#10b981'; }
            // Storage
            const sf = parseFloat(d.storage_free)||0, st = parseFloat(d.storage_total)||0;
            document.getElementById('modal-storage').textContent = st ? `${sf} free / ${st} GB total` : '--';
            const storBar = document.getElementById('modal-storage-bar');
            if (storBar && st) storBar.style.width = `${Math.min(Math.round(((st-sf)/st)*100),100)}%`;
            // RAM
            document.getElementById('modal-ram').textContent = (d.ram_str && d.ram_str!=='N/A') ? d.ram_str+' GB' : '--';
            const ramBar = document.getElementById('modal-ram-bar');
            if (ramBar && d.ram_str && d.ram_str!=='N/A') {
                const parts = d.ram_str.split('/');
                if (parts.length===2) { const used=parseFloat(parts[0]), total=parseFloat(parts[1]); if(total>0) ramBar.style.width=`${Math.round((used/total)*100)}%`; }
            }
        }
    };

    // --- Navigation ---
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view-content');
    const viewTitle = document.getElementById('view-title');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetView = item.getAttribute('data-view');

            // UI Toggle
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            views.forEach(v => v.classList.remove('active'));
            document.getElementById(`${targetView}-view`).classList.add('active');

            // Header Update
            viewTitle.textContent = item.textContent.trim();

            // View-specific loading
            if (targetView === 'explorer')  loadFiles(currentPath);
            if (targetView === 'history')   loadHistory();
            if (targetView === 'processes') fetchProcesses();
            if (targetView === 'scanner')   setTimeout(fetchETA, 200);
            if (targetView === 'virusscan') {
                // Fetch ETA for virus scan tab
                const serial = currentDevice?.device_id || 'MOCK';
                fetch(`/api/scan/estimate?serial=${serial}`).then(r => r.json()).then(data => {
                    const quick = data.quick, virus = data.virus;
                    const label = document.getElementById('virus-eta-label');
                    if (label && quick) {
                        const fmtTime = s => s >= 60 ? `${Math.round(s/60)}m ${s%60}s` : `${s}s`;
                        const modeData = virusScanMode === 'deep' ? virus : { count: quick.count, eta_sec: Math.round((quick.count||35)*0.05) };
                        label.textContent = `⏱ Est. ${fmtTime(modeData.eta_sec)} (${modeData.count} apps)`;
                    }
                }).catch(() => {});
            }
        });
    });

    // --- Scanning Logic ---
    const startScanBtn = document.getElementById('start-scan-btn');
    const scanProgressArea = document.getElementById('scan-progress-area');
    const scanProgressFill = document.getElementById('scan-progress-fill');
    const scanPercentText = document.getElementById('scan-percent');
    const scanStatusText = document.getElementById('scan-status-text');

    startScanBtn.addEventListener('click', async () => {
        addLog(`initiating ${scanMode === 'deep' ? 'DEEP (all apps)' : 'QUICK (user apps)'} scan...`, 'info');
        
        try {
            const resp = await fetch('/api/scan/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ serial: currentDevice?.device_id || 'MOCK', scan_mode: scanMode })
            });
            const data = await resp.json();
            
            if (data.status === 'success') {
                startScanBtn.disabled = true;
                startScanBtn.textContent = 'Scan in Progress...';
                scanProgressArea.style.display = 'block';
                pollScanProgress();
            }
        } catch (err) {
            addLog(`Scan initiation failed: ${err.message}`, 'error');
        }
    });

    function pollScanProgress() {
        scanInterval = setInterval(async () => {
            try {
                const resp = await fetch('/api/scan/progress');
                const data = await resp.json();
                
                if (data.status === 'running') {
                    scanProgressFill.style.width = `${data.percent}%`;
                    scanPercentText.textContent = `${data.percent}%`;
                    scanStatusText.textContent = data.current_task;
                } else if (data.status === 'completed') {
                    clearInterval(scanInterval);
                    handleScanComplete(data.results);
                } else if (data.status === 'error') {
                    clearInterval(scanInterval);
                    addLog(data.current_task, 'error');
                    startScanBtn.disabled = false;
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 800);
    }

    function handleScanComplete(results) {
        addLog('Scan completed successfully.', 'system');
        startScanBtn.disabled = false;
        startScanBtn.textContent = 'Restart Deep Scan';
        
        // Update Dashboard Stats with smooth animations
        animateNumber(document.getElementById('total-apps'), 0, results.total_apps, 1500);
        animateNumber(document.getElementById('threats-found'), 0, results.threats_found, 1500);
        animateNumber(document.getElementById('main-score'), 0, results.risk_score, 1500);
        updateRiskChart(results.risk_score);

        // Update Threat List
        const threatList = document.getElementById('recent-threats');
        threatList.innerHTML = '';
        
        const appsWithThreats = results.apps.filter(a => a.threats.length > 0);
        if (appsWithThreats.length === 0) {
            threatList.innerHTML = '<div class="empty-state">✅ No threats detected in latest scan.</div>';
        } else {
            appsWithThreats.forEach(app => {
                app.threats.forEach(t => {
                    const row = document.createElement('div');
                    row.className = 'threat-item';
                    row.innerHTML = `
                        <div class="threat-icon ${t.risk.toLowerCase()}"><i data-lucide="alert-circle"></i></div>
                        <div class="threat-details" style="flex:1;">
                            <strong>${app.package}</strong>
                            <span style="font-size:0.75rem;color:var(--text-muted);margin-left:6px;">${t.type || ''}</span>
                            <p style="margin:4px 0 6px;">${t.description}</p>
                            ${t.solution ? `<div style="background:rgba(79,70,229,0.08);border-left:3px solid var(--accent-primary);padding:8px 12px;border-radius:0 6px 6px 0;font-size:0.78rem;color:var(--text-main);line-height:1.5;">
                                💡 <strong>Fix:</strong> ${t.solution}
                            </div>` : ''}
                        </div>
                        <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end;flex-shrink:0;padding-left:12px;">
                            <span class="threat-risk-badge ${t.risk.toLowerCase()}">${t.risk}</span>
                            ${t.fix_action === 'uninstall' ? `<button onclick="uninstallApp('${app.package}')" style="background:var(--color-danger);color:#fff;border:none;font-size:0.75rem;font-weight:700;padding:4px 10px;border-radius:6px;cursor:pointer;white-space:nowrap;">🗑 Uninstall</button>` : `<button onclick="alert('Go to Settings › Apps › ${app.package.split('.').pop()} › Permissions to revoke dangerous permissions.')" style="background:var(--color-warning,#f59e0b);color:#fff;border:none;font-size:0.75rem;font-weight:700;padding:4px 10px;border-radius:6px;cursor:pointer;white-space:nowrap;">⚙ Fix</button>`}
                        </div>
                    `;
                    threatList.appendChild(row);
                });
            });
            lucide.createIcons();
        }
    }

    // --- File Explorer ---
    async function loadFiles(path) {
        const grid = document.getElementById('file-grid');
        grid.innerHTML = '<div class="loading">Reading storage...</div>';
        
        try {
            const resp = await fetch(`/api/files/list?path=${encodeURIComponent(path)}&serial=${currentDevice?.device_id || 'MOCK'}`);
            const data = await resp.json();
            
            grid.innerHTML = '';
            document.getElementById('current-path').textContent = data.path;
            
            data.files.forEach(file => {
                const item = document.createElement('div');
                item.className = `file-item ${file.type}`;
                if (file.type === 'dir') {
                    item.innerHTML = `
                        <i data-lucide="folder"></i>
                        <span>${file.name}</span>
                    `;
                    item.onclick = () => {
                        pathHistory.push(path);   // save current path so back works
                        currentPath = path + file.name;
                        loadFiles(currentPath);
                    };
                } else {
                    const isApk = file.name.toLowerCase().endsWith('.apk');
                    const ext = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : '';
                    const previewExts = ['jpg','jpeg','png','gif','webp','bmp','txt','log','json','xml','csv','md','py','js','html','css','java','kt','sh','yaml','yml'];
                    const canPreview = previewExts.includes(ext);
                    const isImage = ['jpg','jpeg','png','gif','webp','bmp'].includes(ext);
                    const dlUrl = `/api/files/download?path=${encodeURIComponent(path + file.name)}&serial=${currentDevice?.device_id || 'MOCK'}`;
                    const fullPath = (path + file.name).replace(/'/g, "\\'");
                    item.innerHTML = `
                        <i data-lucide="${isImage ? 'image' : isApk ? 'package' : 'file-text'}"></i>
                        <span>${file.name}</span>
                        <div style="display:flex; gap:6px; margin-top:10px; flex-wrap:wrap; justify-content:center;">
                            <a href="${dlUrl}" download="${file.name}"
                                style="color:#fff; background:var(--accent-primary); text-decoration:none; font-size:0.78rem; font-weight:600; padding:5px 12px; border-radius:6px; display:inline-flex; align-items:center; gap:4px;">
                                ⬇ Download
                            </a>
                            ${canPreview ? `<button onclick="previewFile('${fullPath}', '${file.name.replace(/'/g, "\\'")}')"
                                style="color:var(--accent-primary); background:var(--accent-light,rgba(79,70,229,0.1)); border:1px solid var(--accent-primary); font-size:0.78rem; font-weight:600; padding:5px 12px; border-radius:6px; cursor:pointer;">
                                👁 Preview
                            </button>` : ''}
                            ${isApk ? `<button onclick="installApk('${fullPath}')"
                                style="color:#fff; background:#7c3aed; border:none; font-size:0.78rem; font-weight:600; padding:5px 12px; border-radius:6px; cursor:pointer;">
                                ⚙ Install
                            </button>` : ''}
                        </div>
                    `;
                }
                grid.appendChild(item);
            });
            lucide.createIcons();
        } catch (err) {
            grid.innerHTML = `<div class="error">Failed to load files: ${err.message}</div>`;
        }
    }

    // --- History ---
    async function loadHistory() {
        const list = document.getElementById('history-list');
        list.innerHTML = '<tr><td colspan="5">Loading history...</td></tr>';
        
        try {
            const resp = await fetch(`/api/device/history/${currentDevice?.device_id || 'ADB-MOCK-7788'}`);
            const data = await resp.json();
            
            list.innerHTML = '';
            data.history.forEach(h => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${h[1]}</td>
                    <td>${currentDevice?.model || 'Device'}</td>
                    <td><span class="score-pill">${parseFloat(h[2]).toFixed(1)}</span></td>
                    <td>${h[4]} Threats</td>
                    <td><button class="btn-text" onclick="window.location.href='/api/scan/report/${h[0]}'">⬇ Report</button></td>
                `;
                list.appendChild(row);
            });
        } catch (err) {
            list.innerHTML = '<tr><td colspan="5">History unavailable.</td></tr>';
        }
    }

    async function checkDeviceStatus() {
        try {
            const resp = await fetch('/api/device/status');
            const data = await resp.json();

            const dot = document.querySelector('.status-dot');
            const text = document.querySelector('.status-text');
            const badge = document.getElementById('header-device-name');

            if (data.connected) {
                currentDevice = data;
                deviceModalData = data;   // cache for modal
                dot.classList.add('online');
                dot.classList.remove('error');
                text.textContent = 'Device Connected';
                badge.textContent = data.model;

                // Update enhanced device badge
                document.getElementById('header-device-name').textContent = data.model;
                document.getElementById('header-device-sub').textContent  = `Android ${data.android_version} • ${data.device_id}`;
                const batPill = document.getElementById('header-battery-pill');
                const batVal  = document.getElementById('header-battery-val');
                if (data.battery && data.battery !== 'N/A') {
                    batVal.textContent  = data.battery;
                    const pct = parseInt(data.battery);
                    batPill.style.display = 'block';
                    batPill.style.color   = pct <= 20 ? '#ef4444' : pct <= 50 ? '#f59e0b' : '#10b981';
                    batPill.style.borderColor = pct <= 20 ? 'rgba(239,68,68,0.4)' : pct <= 50 ? 'rgba(245,158,11,0.4)' : 'rgba(16,185,129,0.4)';
                    batPill.style.background  = pct <= 20 ? 'rgba(239,68,68,0.1)' : pct <= 50 ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)';
                } else {
                    batPill.style.display = 'none';
                }
                // Update Vitals
                document.getElementById('vital-battery').textContent = data.battery !== 'N/A' ? data.battery + '%' : 'N/A';
                const sf = data.storage_free, st = data.storage_total;
                document.getElementById('vital-storage').textContent =
                    (sf && sf !== 'N/A' && st && st !== 'N/A') ? `${sf} / ${st} GB` :
                    (sf && sf !== 'N/A') ? `${sf} GB Free` : 'N/A';
                document.getElementById('vital-ram').textContent = data.ram_str !== 'N/A' ? data.ram_str + ' GB' : 'N/A';

                // Hide troubleshoot card if shown
                const card = document.getElementById('no-device-card');
                if (card) card.style.display = 'none';

            } else {
                currentDevice = null;
                dot.classList.remove('online');
                dot.classList.add('error');
                text.textContent = 'No Device';
                document.getElementById('header-device-name').textContent = 'No Device';
                document.getElementById('header-device-sub').textContent  = 'Connect via USB';
                document.getElementById('header-battery-pill').style.display = 'none';

                // Reset Vitals
                document.getElementById('vital-battery').textContent = '--%';
                document.getElementById('vital-storage').textContent = '-- GB Free';
                document.getElementById('vital-ram').textContent = '-- / -- GB';

                // Show troubleshoot card
                showNoDeviceCard(data.error, data.adb_path);
            }
        } catch (err) {
            console.error('Status check failed:', err);
        }
    }

    function showNoDeviceCard(errorMsg, adbPath) {
        let card = document.getElementById('no-device-card');
        if (!card) {
            card = document.createElement('div');
            card.id = 'no-device-card';
            card.style.cssText = `
                position: fixed; bottom: 24px; right: 24px; z-index: 9999;
                background: linear-gradient(135deg, #1e1e2e 0%, #16213e 100%);
                border: 1px solid rgba(239,68,68,0.4);
                border-radius: 16px; padding: 20px 24px; width: 360px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(239,68,68,0.1);
                font-family: 'Inter', sans-serif; color: #e2e8f0;
                animation: slideInUp 0.4s cubic-bezier(0.16,1,0.3,1);
            `;
            document.body.appendChild(card);
        }
        card.style.display = 'block';
        card.innerHTML = `
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
                <span style="width:10px;height:10px;border-radius:50%;background:#ef4444;display:inline-block;animation:pulse 1.5s infinite;"></span>
                <strong style="color:#f87171; font-size:0.95rem;">ADB Connection Issue</strong>
                <button onclick="document.getElementById('no-device-card').style.display='none'"
                    style="margin-left:auto; background:none; border:none; color:#94a3b8; cursor:pointer; font-size:1.2rem; line-height:1;">×</button>
            </div>
            <p style="margin:0 0 12px; font-size:0.82rem; color:#f1a1a1; line-height:1.5;">${errorMsg || 'No device detected.'}</p>
            <div style="font-size:0.78rem; color:#64748b; margin-bottom:10px;">
                <strong style="color:#94a3b8;">ADB Binary:</strong><br>
                <code style="font-size:0.75rem; color:#7dd3fc; background:rgba(125,211,252,0.08); padding:2px 6px; border-radius:4px; display:inline-block; margin-top:4px; word-break:break-all;">${adbPath || 'Not found'}</code>
            </div>
            <hr style="border:none; border-top: 1px solid rgba(255,255,255,0.07); margin:12px 0;">
            <p style="font-size:0.78rem; color:#94a3b8; margin:0 0 8px;"><strong>Quick Fixes:</strong></p>
            <ol style="margin:0; padding-left:18px; font-size:0.78rem; color:#64748b; line-height:1.8;">
                <li>Enable <strong style="color:#e2e8f0;">USB Debugging</strong> in Developer Options</li>
                <li>Set USB mode to <strong style="color:#e2e8f0;">File Transfer (MTP)</strong></li>
                <li>Tap <strong style="color:#e2e8f0;">Allow</strong> on the phone popup</li>
                <li>Try a different <strong style="color:#e2e8f0;">data USB cable</strong></li>
                <li>Open CMD and run: <code style="color:#7dd3fc;">adb devices</code></li>
            </ol>
            <button onclick="fetch('/api/device/status').then(r=>r.json()).then(d=>{ if(d.connected) document.getElementById('no-device-card').style.display='none'; else document.querySelector('.status-text').textContent='Retrying...'; checkDeviceStatus(); })"
                style="margin-top:14px; width:100%; padding:9px; background:linear-gradient(135deg,#4f46e5,#7c3aed); border:none;
                border-radius:8px; color:#fff; font-weight:600; font-size:0.82rem; cursor:pointer;
                transition: opacity 0.2s;" onmouseover="this.style.opacity=0.85" onmouseout="this.style.opacity=1">
                🔄 Retry Connection
            </button>
        `;
    }

    function initRiskChart() {
        const ctx = document.getElementById('risk-gauge').getContext('2d');
        riskChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#ef4444', '#1e293b'],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270,
                    cutout: '85%'
                }]
            },
            options: {
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                maintainAspectRatio: false
            }
        });
    }

    function animateNumber(element, start, end, duration) {
        if (!element) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const easeProgress = progress * (2 - progress); // ease out quad
            element.textContent = Math.floor(easeProgress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                element.textContent = end;
            }
        };
        window.requestAnimationFrame(step);
    }

    function updateRiskChart(score) {
        const color = score > 70 ? '#ef4444' : (score > 30 ? '#f59e0b' : '#10b981');
        
        let currentScore = 0;
        if (riskChart.data.datasets[0].data[0] !== undefined) {
            currentScore = riskChart.data.datasets[0].data[0];
        }
        
        let startTimestamp = null;
        const duration = 1500;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const easeProgress = progress * (2 - progress);
            const currentVal = easeProgress * (score - currentScore) + currentScore;
            
            riskChart.data.datasets[0].data = [currentVal, 100 - currentVal];
            riskChart.data.datasets[0].backgroundColor = [color, '#1e293b'];
            riskChart.update();
            
            if (progress < 1) window.requestAnimationFrame(step);
        };
        window.requestAnimationFrame(step);
        
        const label = document.querySelector('.score-label');
        label.textContent = score > 70 ? 'Insecure' : (score > 30 ? 'Warning' : 'Secure');
        label.style.color = color;
    }

    function addLog(msg, type = 'system') {
        const container = document.getElementById('log-content');
        const entry = document.createElement('div');
        const now = new Date().toLocaleTimeString();
        entry.className = `log-entry ${type}`;
        container.appendChild(entry);
        
        const fullText = `[${now}] ${msg.toUpperCase()}`;
        let i = 0;
        function typeWriter() {
            if (i < fullText.length) {
                entry.textContent += fullText.charAt(i);
                i++;
                container.scrollTop = container.scrollHeight;
                setTimeout(typeWriter, 15 + Math.random() * 20);
            }
        }
        typeWriter();
    }

    // --- Processes Manager ---
    async function fetchProcesses() {
        const list = document.getElementById('processes-list');
        if (!currentDevice) {
            list.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">⚠ No device connected. Connect a device to view processes.</td></tr>';
            return;
        }
        list.innerHTML = '<tr><td colspan="5" style="text-align:center;">Fetching processes...</td></tr>';
        try {
            const resp = await fetch(`/api/device/processes?serial=${currentDevice.device_id}`);
            const data = await resp.json();
            list.innerHTML = '';
            if (data.processes && data.processes.length > 0) {
                data.processes.forEach(p => {
                    const memMb = (parseInt(p.memory) / 1024).toFixed(1);
                    const isSuspicious = p.user === 'root' || parseInt(p.memory) > 200000;
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td style="${isSuspicious ? 'color:var(--color-warning);font-weight:600;' : ''}">${p.user}</td>
                        <td><span style="font-family:monospace;">${p.pid}</span></td>
                        <td><span style="${parseInt(p.memory)>100000 ? 'color:var(--color-danger);font-weight:600;' : ''}">${memMb} MB</span></td>
                        <td style="font-weight:600; word-break:break-all; max-width:250px;">${p.name}</td>
                        <td style="text-align:right; white-space:nowrap;"><button onclick="killProcess('${p.pid}','${p.name.replace(/'/g,"\\'")}')" style="color:#fff;background:var(--color-danger);border:none;font-size:0.75rem;font-weight:700;padding:6px 12px;border-radius:6px;cursor:pointer;white-space:nowrap;box-shadow:0 2px 8px rgba(239,68,68,0.3);">⚡ Kill</button></td>
                    `;
                    list.appendChild(tr);
                });
            } else {
                list.innerHTML = '<tr><td colspan="5" style="text-align:center;">No processes detected.</td></tr>';
            }
        } catch (err) {
            list.innerHTML = '<tr><td colspan="5" style="text-align:center;">Error fetching processes.</td></tr>';
        }
    }

    document.getElementById('refresh-processes-btn')?.addEventListener('click', fetchProcesses);
    document.querySelector('[data-view="processes"]')?.addEventListener('click', () => fetchProcesses());

    // --- Scan History ---
    async function loadHistory() {
        const list = document.getElementById('history-list');
        if (!currentDevice) {
            list.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:28px;color:var(--text-muted);">📡 Connect a device to view scan history.</td></tr>`;
            return;
        }
        list.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted);">Loading history...</td></tr>`;
        try {
            const resp = await fetch(`/api/device/history/${currentDevice.device_id}`);
            const data = await resp.json();
            list.innerHTML = '';
            const rows = data.history || [];
            if (rows.length === 0) {
                list.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:32px;color:var(--text-muted);">📋 No scan history yet. Run a Security Scan to get started.</td></tr>`;
                return;
            }
            rows.forEach(([id, ts, risk, total, threats]) => {
                const riskNum = parseFloat(risk) || 0;
                const riskColor = riskNum > 70 ? '#ef4444' : riskNum > 30 ? '#f59e0b' : '#10b981';
                const riskLabel = riskNum > 70 ? 'HIGH RISK' : riskNum > 30 ? 'MEDIUM' : '✅ SAFE';
                const date = new Date(ts).toLocaleString();
                const tr = document.createElement('tr');
                tr.id = `history-row-${id}`;
                tr.innerHTML = `
                    <td style="font-size:0.85rem;color:var(--text-muted);">${date}</td>
                    <td style="font-weight:600;font-size:0.88rem;">${currentDevice.model}</td>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div style="width:38px;height:38px;border-radius:50%;background:${riskColor}22;border:2px solid ${riskColor};display:flex;align-items:center;justify-content:center;font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:0.85rem;color:${riskColor};">${Math.round(riskNum)}</div>
                            <span style="font-size:0.72rem;font-weight:700;color:${riskColor};background:${riskColor}18;padding:2px 8px;border-radius:20px;">${riskLabel}</span>
                        </div>
                    </td>
                    <td>
                        <span style="font-weight:700;color:${threats>0?'#ef4444':'#10b981'};">${threats}</span>
                        <span style="font-size:0.78rem;color:var(--text-muted);"> threat${threats!==1?'s':''}</span>
                        <span style="color:var(--text-muted);"> / </span>
                        <span style="font-size:0.88rem;font-weight:600;">${total}</span>
                        <span style="font-size:0.78rem;color:var(--text-muted);"> apps</span>
                    </td>
                    <td>
                        <div style="display:flex;gap:6px;">
                            <a href="/api/scan/report/${id}" target="_blank"
                               style="background:var(--accent-primary);color:#fff;text-decoration:none;font-size:0.75rem;font-weight:700;padding:5px 12px;border-radius:6px;white-space:nowrap;">📄 Report</a>
                            <button onclick="deleteHistoryRow(${id})"
                               style="background:rgba(239,68,68,0.12);color:#ef4444;border:1px solid rgba(239,68,68,0.3);font-size:0.75rem;font-weight:700;padding:5px 12px;border-radius:6px;cursor:pointer;white-space:nowrap;">🗑 Delete</button>
                        </div>
                    </td>
                `;
                list.appendChild(tr);
            });
        } catch (err) {
            list.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#ef4444;padding:20px;">Error: ${err.message}</td></tr>`;
        }
    }

    window.deleteHistoryRow = async function(id) {
        if (!confirm('Delete this scan record permanently?')) return;
        try {
            const resp = await fetch(`/api/history/delete/${id}`, { method: 'DELETE' });
            const data = await resp.json();
            if (data.status === 'success') {
                const row = document.getElementById(`history-row-${id}`);
                if (row) { row.style.opacity = '0'; row.style.transition = 'opacity 0.3s'; setTimeout(() => row.remove(), 320); }
                addLog(`Scan #${id} deleted from history.`, 'system');
            } else { addLog(data.message || 'Delete failed.', 'error'); }
        } catch (err) { addLog(`Delete error: ${err.message}`, 'error'); }
    };

    // --- App Uninstall ---
    window.uninstallApp = async function(pkg) {
        if (!currentDevice) { addLog('No device connected.', 'error'); return; }
        if (!confirm(`Uninstall "${pkg}" from the device?`)) return;
        addLog(`Uninstalling ${pkg}...`, 'info');
        try {
            const resp = await fetch('/api/apps/uninstall', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ package: pkg, serial: currentDevice.device_id })
            });
            const data = await resp.json();
            addLog(data.message, data.status === 'success' ? 'system' : 'error');
            alert((data.status === 'success' ? '✅ ' : '❌ ') + data.message);
        } catch (err) { addLog(`Uninstall error: ${err.message}`, 'error'); }
    };

    // --- Kill Process ---
    window.killProcess = async function(pid, name) {
        if (!currentDevice) return;
        if (!confirm(`Force-kill "${name}" (PID ${pid})?`)) return;
        try {
            const resp = await fetch('/api/device/kill', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pid, serial: currentDevice.device_id })
            });
            const data = await resp.json();
            addLog(data.message, 'system');
            fetchProcesses();
        } catch (err) { addLog(`Kill error: ${err.message}`, 'error'); }
    };

    // --- File Explorer Back Button ---
    document.getElementById('explorer-back-btn')?.addEventListener('click', () => {
        if (pathHistory.length > 0) {
            currentPath = pathHistory.pop();
            loadFiles(currentPath);
        }
    });

    // --- Install APK on Device ---
    window.installApk = async function(remotePath) {
        if (!currentDevice) { addLog('No device connected.', 'error'); return; }
        addLog(`Installing ${remotePath} on device...`, 'info');
        try {
            const resp = await fetch('/api/files/install', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: remotePath, serial: currentDevice.device_id })
            });
            const data = await resp.json();
            if (data.status === 'success') {
                addLog(data.message, 'system');
                alert('✅ ' + data.message);
            } else {
                addLog(data.message, 'error');
                alert('❌ ' + data.message);
            }
        } catch (err) {
            addLog(`Install failed: ${err.message}`, 'error');
        }
    };

    // --- File Preview ---
    const previewModal   = document.getElementById('preview-modal');
    const previewContent = document.getElementById('preview-content');
    const previewFname   = document.getElementById('preview-filename');

    document.getElementById('close-preview-btn')?.addEventListener('click', () => {
        previewModal.style.display = 'none';
        previewContent.innerHTML = '';
    });
    previewModal?.addEventListener('click', (e) => {
        if (e.target === previewModal) {
            previewModal.style.display = 'none';
            previewContent.innerHTML = '';
        }
    });

    window.previewFile = async function(remotePath, name) {
        previewFname.textContent = name;
        previewContent.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">Loading preview...</div>';
        previewModal.style.display = 'flex';
        try {
            const serial = currentDevice?.device_id || 'MOCK';
            const resp = await fetch(`/api/files/preview?path=${encodeURIComponent(remotePath)}&serial=${serial}`);
            const data = await resp.json();
            if (data.error) {
                previewContent.innerHTML = `<div style="color:var(--color-danger);padding:20px;">${data.error}</div>`;
            } else if (data.type === 'image') {
                previewContent.innerHTML = `<img src="${data.src}" alt="${name}" style="max-width:100%; max-height:70vh; display:block; margin:0 auto; border-radius:8px;">`;
            } else if (data.type === 'text') {
                previewContent.innerHTML = `<pre style="white-space:pre-wrap; word-break:break-all; font-family:'JetBrains Mono',monospace; font-size:0.82rem; line-height:1.6; color:var(--text-main); margin:0; background:var(--bg-main); padding:16px; border-radius:8px; overflow:auto;">${data.content.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</pre>`;
            }
        } catch (err) {
            previewContent.innerHTML = `<div style="color:var(--color-danger);padding:20px;">Preview failed: ${err.message}</div>`;
        }
    };

    // --- DB Management ---
    document.getElementById('clear-db-btn')?.addEventListener('click', async () => {
        if(confirm("Are you sure you want to permanently delete all scan history?")) {
            try {
                const resp = await fetch('/api/settings/clear_db', { method: 'POST' });
                const res = await resp.json();
                alert(res.message);
                loadHistory();
            } catch (err) {
                alert("Failed to clear database.");
            }
        }
    });

    // --- Scan Mode Toggle (targets scanner-view buttons) ---
    window.setScanMode = function(mode) {
        scanMode = mode;
        const qBtn = document.getElementById('scan-mode-quick');
        const dBtn = document.getElementById('scan-mode-deep');
        if (qBtn && dBtn) {
            const activeStyle   = 'background:var(--accent-primary);color:#fff;border-color:var(--accent-primary);';
            const inactiveStyle = 'background:transparent;color:var(--text-main);border-color:var(--border-color);';
            qBtn.setAttribute('style', qBtn.getAttribute('style').split(';').slice(0,5).join(';') + ';' + (mode==='quick' ? activeStyle : inactiveStyle));
            dBtn.setAttribute('style', dBtn.getAttribute('style').split(';').slice(0,5).join(';') + ';' + (mode==='deep'  ? activeStyle : inactiveStyle));
        }
        fetchETA();
    };

    // --- Virus Scan Mode Toggle ---
    window.setVirusScanMode = function(mode) {
        virusScanMode = mode;
        const qBtn = document.getElementById('vscan-mode-quick');
        const dBtn = document.getElementById('vscan-mode-deep');
        if (qBtn && dBtn) {
            if (mode === 'quick') {
                qBtn.style.background='#ef4444'; qBtn.style.color='#fff'; qBtn.style.borderColor='#ef4444';
                dBtn.style.background='transparent'; dBtn.style.color='var(--text-main)'; dBtn.style.borderColor='var(--border-color)';
            } else {
                dBtn.style.background='#ef4444'; dBtn.style.color='#fff'; dBtn.style.borderColor='#ef4444';
                qBtn.style.background='transparent'; qBtn.style.color='var(--text-main)'; qBtn.style.borderColor='var(--border-color)';
            }
        }
        // Update virus ETA label
        const serial = currentDevice?.device_id || 'MOCK';
        fetch(`/api/scan/estimate?serial=${serial}`).then(r=>r.json()).then(data => {
            const virusData = mode === 'deep' ? data.virus : { count: data.quick?.count, eta_sec: Math.round((data.quick?.count||35)*0.05) };
            const label = document.getElementById('virus-eta-label');
            if (label && virusData) {
                const fmtTime = s => s >= 60 ? `${Math.round(s/60)}m ${s%60}s` : `${s}s`;
                label.textContent = `⏱ Est. ${fmtTime(virusData.eta_sec)} (${virusData.count} apps)`;
            }
        }).catch(()=>{});
    };

    async function fetchETA() {
        const serial = currentDevice?.device_id || 'MOCK';
        try {
            const resp = await fetch(`/api/scan/estimate?serial=${serial}`);
            const data = await resp.json();
            if (data.error) return;
            const modeData = scanMode === 'deep' ? data.deep : data.quick;
            const virusData = data.virus;
            const label = document.getElementById('eta-label');
            if (label) {
                const fmtTime = s => s >= 60 ? `${Math.round(s/60)}m ${s%60}s` : `${s}s`;
                label.textContent = `⏱ Est. ${fmtTime(modeData.eta_sec)} (${modeData.count} apps) | 🦠 Virus: ~${fmtTime(virusData.eta_sec)}`;
            }
        } catch (_) {}
    }

    // Fetch ETA when navigating to scanner tab
    document.querySelector('[data-view="scanner"]')?.addEventListener('click', () => {
        setTimeout(fetchETA, 300);
    });
    // Initial ETA on load
    setTimeout(fetchETA, 2000);

    // --- Virus Scan ---
    document.getElementById('start-virus-btn')?.addEventListener('click', async () => {
        addLog(`Starting ${virusScanMode.toUpperCase()} Virus & Malware scan...`, 'info');
        const virusArea   = document.getElementById('virus-progress-area');
        const virusFill   = document.getElementById('virus-progress-fill');
        const virusPct    = document.getElementById('virus-percent');
        const virusStatus = document.getElementById('virus-status-text');
        const resultsArea = document.getElementById('virus-results-area') || document.getElementById('scan-results-area');

        try {
            const resp = await fetch('/api/virus/start', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ serial: currentDevice?.device_id || 'MOCK', scan_mode: virusScanMode })
            });
            const data = await resp.json();
            if (data.status !== 'success') { addLog(data.message, 'error'); return; }

            virusArea.style.display = 'block';
            if (resultsArea) resultsArea.style.display = 'none';

            const virusInterval = setInterval(async () => {
                const pr = await (await fetch('/api/virus/progress')).json();
                virusFill.style.width   = `${pr.percent}%`;
                virusPct.textContent    = `${pr.percent}%`;
                virusStatus.textContent = pr.current_task;

                // Live Log Update
                const liveLog = document.getElementById('virus-live-log');
                if (liveLog && pr.current_task && pr.current_task !== window._lastLogTask) {
                    window._lastLogTask = pr.current_task;
                    const logLine = document.createElement('div');
                    logLine.innerHTML = `> <span style="color:#64748b;">[${new Date().toLocaleTimeString()}]</span> ${pr.current_task}`;
                    liveLog.prepend(logLine);
                }

                if (pr.status === 'completed') {
                    clearInterval(virusInterval);
                    addLog('Virus scan complete.', 'system');
                    if (resultsArea) showVirusResults(pr.results, resultsArea);
                } else if (pr.status === 'error') {
                    clearInterval(virusInterval);
                    addLog(pr.current_task, 'error');
                }
            }, 600);
        } catch (err) { addLog(`Virus scan failed: ${err.message}`, 'error'); }
    });

    function showVirusResults(results, container) {
        container.style.display = 'block';
        const infected = results.infected || [];
        const cleanCount = results.clean || 0;

        let html = `<div style="padding:20px;background:var(--bg-panel);border-radius:14px;border:1px solid var(--border-color);margin-top:16px;">`;
        html += `<h3 style="font-family:'Plus Jakarta Sans',sans-serif;margin:0 0 16px;display:flex;align-items:center;gap:10px;">`;
        html += infected.length > 0
            ? `<span style="color:#ef4444;">🦠 ${infected.length} Threat${infected.length>1?'s':''} Found</span>`
            : `<span style="color:#10b981;">✅ Device is Clean — No Malware Detected</span>`;
        html += `<span style="font-size:0.78rem;font-weight:400;color:var(--text-muted);margin-left:auto;">${results.total_checked} packages checked | ${cleanCount} clean</span></h3>`;

        if (infected.length > 0) {
            infected.forEach(v => {
                html += `<div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.3);border-left:4px solid #ef4444;border-radius:8px;padding:14px 16px;margin-bottom:12px;display:flex;gap:12px;align-items:flex-start;">`;
                html += `<div style="flex:1;">`;
                html += `<div style="font-weight:700;color:var(--text-main);">${v.package} <span style="font-size:0.72rem;background:#ef4444;color:#fff;padding:2px 8px;border-radius:20px;margin-left:6px;">${v.category}</span></div>`;
                html += `<p style="margin:6px 0;font-size:0.83rem;color:var(--text-muted);">${v.description}</p>`;
                html += `<div style="background:rgba(79,70,229,0.08);border-left:3px solid var(--accent-primary);padding:8px 12px;border-radius:0 6px 6px 0;font-size:0.78rem;line-height:1.5;">💡 <strong>Fix:</strong> ${v.solution}</div>`;
                html += `</div>`;
                if (v.fix_action === 'uninstall') {
                    html += `<button onclick="uninstallApp('${v.package}')" style="background:#ef4444;color:#fff;border:none;padding:8px 14px;border-radius:8px;font-size:0.8rem;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0;">🗑 Uninstall</button>`;
                }
                html += `</div>`;
            });
        }
        html += `</div>`;
        container.innerHTML = html;
    }

    // --- Export Last Report ---
    document.getElementById('export-report-btn')?.addEventListener('click', async () => {
        try {
            const serial = currentDevice?.device_id || 'ADB-MOCK-7788';
            const resp = await fetch(`/api/device/history/${serial}`);
            const data = await resp.json();
            if (data.history && data.history.length > 0) {
                const lastId = data.history[0][0];
                window.location.href = `/api/scan/report/${lastId}`;
            } else {
                alert('No scan history found. Run a scan first.');
            }
        } catch (err) {
            alert('Could not export report: ' + err.message);
        }
    });

    // --- 3D Hover Tilt Effect ---
    function applyTiltEffect(elements) {
        elements.forEach(el => {
            el.addEventListener('mousemove', (e) => {
                const rect = el.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const rotateX = ((y - centerY) / centerY) * -4; // max 4deg
                const rotateY = ((x - centerX) / centerX) * 4;
                el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
                el.style.transition = 'none';
            });
            el.addEventListener('mouseleave', () => {
                el.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
                el.style.transition = 'transform 0.5s ease';
            });
        });
    }
    applyTiltEffect(document.querySelectorAll('.vital-card, .stat-card'));

});

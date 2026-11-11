/* ==========================================================================
   AI-DRIVEN FORCE - MAIN APP CORE CONTROLLER
   ========================================================================== */

const App = {
    state: {
        cases: [],
        activeCaseId: null,
        activeCaseData: null,
        charts: {},
        pipelineInterval: null
    },

    init() {
        this.bindEvents();
        this.handleRouting();
        this.loadDashboardData();
    },

    bindEvents() {
        // Sidebar click anchors routing
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const targetScreen = item.getAttribute('data-target');
                document.querySelectorAll('.menu-item').forEach(mi => mi.classList.remove('active'));
                item.classList.add('active');
            });
        });

        window.addEventListener('hashchange', () => this.handleRouting());

        // Setup Drag & Drop File Upload listeners
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        
        if (dropZone && fileInput) {
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('active');
            });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('active'));
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('active');
                if (e.dataTransfer.files.length) {
                    fileInput.files = e.dataTransfer.files;
                    this.handleFileSelected(e.dataTransfer.files[0]);
                }
            });
            fileInput.addEventListener('change', () => {
                if (fileInput.files.length) {
                    this.handleFileSelected(fileInput.files[0]);
                }
            });
        }

        // Preview actions
        const clearBtn = document.getElementById('preview-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFileSelection());
        }

        // Process trigger
        const processBtn = document.getElementById('btn-start-process');
        if (processBtn) {
            processBtn.addEventListener('click', () => this.triggerUploadAndPipeline());
        }

        // Case selection in tables
        document.addEventListener('click', (e) => {
            const selectBtn = e.target.closest('.select-case-btn');
            if (selectBtn) {
                const caseId = selectBtn.getAttribute('data-case-id');
                this.selectCase(caseId);
            }
        });

        // Chat send button and quick-query listeners
        const sendChatBtn = document.getElementById('btn-send-chat');
        const chatInput = document.getElementById('chat-query-input');
        if (sendChatBtn && chatInput) {
            sendChatBtn.addEventListener('click', () => this.sendChatMessage());
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendChatMessage();
            });
        }

        document.querySelectorAll('.suggested-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const query = btn.getAttribute('data-query');
                if (chatInput) {
                    chatInput.value = query;
                    this.sendChatMessage();
                }
            });
        });

        // Export PDF Report button
        const exportPdfBtn = document.getElementById('btn-export-pdf');
        if (exportPdfBtn) {
            exportPdfBtn.addEventListener('click', () => this.exportForensicPdf());
        }
    },

    handleRouting() {
        const hash = window.location.hash || '#dashboard';
        const menuItem = document.querySelector(`.menu-item[href="${hash}"]`);
        
        if (menuItem) {
            const screenId = menuItem.getAttribute('data-target');
            
            // Switch views
            document.querySelectorAll('.app-screen').forEach(screen => {
                screen.classList.remove('active');
            });
            const targetScreen = document.getElementById(screenId);
            if (targetScreen) targetScreen.classList.add('active');
            
            // Switch menu item state
            document.querySelectorAll('.menu-item').forEach(mi => mi.classList.remove('active'));
            menuItem.classList.add('active');
        }
    },

    async loadDashboardData() {
        try {
            const stats = await Api.getStats();
            this.state.cases = stats.recent;
            
            // Update counts cards
            document.getElementById('stat-videos').innerText = stats.cards.videos_processed;
            document.getElementById('stat-active').innerText = stats.cards.active_investigations;
            document.getElementById('stat-events').innerText = stats.cards.suspicious_events;
            document.getElementById('stat-high-risk').innerText = stats.cards.high_risk_cases;
            document.getElementById('stat-people').innerText = stats.cards.people_detected;
            document.getElementById('stat-vehicles').innerText = stats.cards.vehicles_logged;
            document.getElementById('stat-weapons').innerText = stats.cards.weapons_detected;
            document.getElementById('stat-time').innerText = `${stats.cards.processing_time}s`;

            // Draw Case Table Rows
            const tableBody = document.getElementById('cases-table-body');
            if (tableBody) {
                if (this.state.cases.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="7" class="loading-td">No active cases registered. Go to 'Upload Evidence' to create one.</td></tr>`;
                } else {
                    tableBody.innerHTML = this.state.cases.map(c => Components.renderCaseRow(c)).join('');
                }
            }

            // Sync cases dropdown filters and forms
            const filterDropdown = document.getElementById('case-select-filter');
            if (filterDropdown) {
                filterDropdown.innerHTML = `<option value="all">All Cases</option>` + 
                    this.state.cases.map(c => `<option value="${c.case_id}">${c.case_id} - ${c.case_name}</option>`).join('');
            }

            // Redraw charts
            this.renderCharts(stats.charts);
            
            // Auto select latest case if none selected
            if (this.state.cases.length > 0 && !this.state.activeCaseId) {
                this.selectCase(this.state.cases[0].case_id, false);
            }
        } catch (err) {
            console.error('Error loading dashboard analytics: ', err);
        }
    },

    renderCharts(chartData) {
        // Destroy existing canvas contexts if already instantiated to prevent chart overlap issues
        if (this.state.charts.evidenceDate) this.state.charts.evidenceDate.destroy();
        if (this.state.charts.riskDist) this.state.charts.riskDist.destroy();
        if (this.state.charts.objectsDet) this.state.charts.objectsDet.destroy();
        if (this.state.charts.dailyInv) this.state.charts.dailyInv.destroy();
        if (this.state.charts.confScores) this.state.charts.confScores.destroy();

        const fontOptions = { family: 'Plus Jakarta Sans', size: 11, color: '#94A3B8' };
        
        // 1. Line Chart: Evidence processing trends
        const ctxLine = document.getElementById('chart-evidence-date');
        if (ctxLine) {
            this.state.charts.evidenceDate = new Chart(ctxLine, {
                type: 'line',
                data: {
                    labels: chartData.evidence_by_date.labels,
                    datasets: [{
                        label: 'Processed Evidence',
                        data: chartData.evidence_by_date.values,
                        borderColor: '#06B6D4',
                        backgroundColor: 'rgba(6, 182, 212, 0.05)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: fontOptions },
                        y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: fontOptions, beginAtZero: true }
                    }
                }
            });
        }

        // 2. Doughnut Chart: Risk Level Distribution
        const ctxDoughnut = document.getElementById('chart-risk-dist');
        if (ctxDoughnut) {
            this.state.charts.riskDist = new Chart(ctxDoughnut, {
                type: 'doughnut',
                data: {
                    labels: chartData.risk_distribution.labels,
                    datasets: [{
                        data: chartData.risk_distribution.values,
                        backgroundColor: ['#10B981', '#F59E0B', '#EF4444', '#7F1D1D'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, color: '#94A3B8', font: { family: 'Plus Jakarta Sans', size: 10 } } }
                    },
                    cutout: '75%'
                }
            });
        }

        // 3. Bar Chart: Objects Logged (Analytics tab)
        const ctxObjects = document.getElementById('chart-objects-detected');
        if (ctxObjects) {
            this.state.charts.objectsDet = new Chart(ctxObjects, {
                type: 'bar',
                data: {
                    labels: chartData.objects_detected.labels,
                    datasets: [{
                        label: 'Assets Detections',
                        data: chartData.objects_detected.values,
                        backgroundColor: ['#3B82F6', '#14B8A6', '#EF4444'],
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: fontOptions },
                        y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: fontOptions, beginAtZero: true }
                    }
                }
            });
        }

        // 4. Bar Chart: Daily Investigations (Analytics tab)
        const ctxDaily = document.getElementById('chart-daily-investigations');
        if (ctxDaily) {
            this.state.charts.dailyInv = new Chart(ctxDaily, {
                type: 'line',
                data: {
                    labels: chartData.daily_investigations.labels,
                    datasets: [{
                        label: 'Cases Audited',
                        data: chartData.daily_investigations.values,
                        borderColor: '#8B5CF6',
                        backgroundColor: 'rgba(139, 92, 246, 0.08)',
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: fontOptions },
                        y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: fontOptions, beginAtZero: true }
                    }
                }
            });
        }

        // 5. Radar Chart: Confidence (Analytics tab)
        const ctxConf = document.getElementById('chart-confidence-scores');
        if (ctxConf) {
            this.state.charts.confScores = new Chart(ctxConf, {
                type: 'bar',
                data: {
                    labels: chartData.confidence_scores.labels,
                    datasets: [{
                        label: 'Score Confidence %',
                        data: chartData.confidence_scores.values,
                        backgroundColor: '#10B981',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: fontOptions },
                        y: { min: 50, max: 100, ticks: fontOptions }
                    }
                }
            });
        }
    },

    selectCase(caseId, navigate = true) {
        this.state.activeCaseId = caseId;
        this.loadCaseData(caseId, navigate);
    },

    async loadCaseData(caseId, navigate = true) {
        try {
            const c = await Api.getCase(caseId);
            this.state.activeCaseData = c;
            
            // Update global profile views
            document.getElementById('analysis-case-id').innerText = `CASE: ${c.case_id} (${c.case_name})`;
            
            // Set video details and source paths
            const videoPlayer = document.getElementById('forensic-video-player');
            const videoSource = document.getElementById('video-source');
            
            if (videoPlayer && videoSource) {
                // If there are uploaded videos, point source towards upload route
                if (c.video_filename) {
                    videoSource.src = `/static/uploads/${c.video_filename}`;
                } else {
                    videoSource.src = '';
                }
                videoPlayer.load();
            }

            // Fill risk metrics gauge
            const riskScore = c.risk_score || 0;
            document.getElementById('analysis-risk-score').innerText = riskScore;
            document.getElementById('analysis-risk-level').innerText = (c.risk_level || 'LOW').toUpperCase();
            
            // Render gauge ring indicator
            const fillBar = document.getElementById('gauge-fill');
            if (fillBar) {
                const angle = (riskScore / 100) * 180;
                fillBar.style.transform = `rotate(${angle}deg)`;
            }

            const riskFactorsList = document.getElementById('analysis-risk-factors');
            if (riskFactorsList) {
                const factors = c.report?.risk_assessment?.factors || ["No critical hazard detections flagged."];
                riskFactorsList.innerHTML = factors.map(f => `<div class="factor-item">${f}</div>`).join('');
            }

            // Fill Speech Transcripts list
            const transContainer = document.getElementById('transcript-container');
            if (transContainer) {
                const trans = c.speech_transcript || [];
                if (trans.length === 0) {
                    transContainer.innerHTML = `<p class="placeholder-text">No speech segments captured for this video.</p>`;
                } else {
                    transContainer.innerHTML = trans.map(line => Components.renderTranscriptLine(line)).join('');
                }
            }

            // Fill Timelines logs (Dashboard side panel & dedicated viewport)
            const timelineContainer = document.getElementById('analysis-timeline-container');
            const fullTimelineContainer = document.getElementById('full-timeline-events-list');
            const timelineEvents = c.timeline || [];
            
            if (timelineContainer) {
                if (timelineEvents.length === 0) {
                    timelineContainer.innerHTML = `<p class="placeholder-text">No timeline evidence chunks cataloged.</p>`;
                } else {
                    timelineContainer.innerHTML = timelineEvents.map(ev => Components.renderTimelineEvent(ev, 'App.jumpVideoTo')).join('');
                }
            }

            if (fullTimelineContainer) {
                document.getElementById('timeline-case-title').innerText = `Case: ${c.case_name} (${c.case_id})`;
                if (timelineEvents.length === 0) {
                    fullTimelineContainer.innerHTML = `<p class="placeholder-text">No timeline evidence chunks cataloged.</p>`;
                } else {
                    fullTimelineContainer.innerHTML = timelineEvents.map(ev => Components.renderFullTimelineCard(ev, 'App.jumpVideoTo')).join('');
                }
            }

            // Render Forensic Report document sheet
            this.compileReportSheet(c);

            // Navigate user screen
            if (navigate) {
                window.location.hash = '#analysis';
            }
        } catch (err) {
            console.error('Failed to load case files: ', err);
        }
    },

    compileReportSheet(c) {
        document.getElementById('rep-case-id').innerText = `CASE ID: ${c.case_id}`;
        
        const stamp = document.getElementById('rep-stamp-level');
        if (stamp) {
            stamp.innerText = `${c.risk_level || 'LOW'} RISK`;
            stamp.style.borderColor = c.risk_level === 'Critical' || c.risk_level === 'High' ? '#EF4444' : c.risk_level === 'Medium' ? '#F59E0B' : '#10B981';
            stamp.style.color = stamp.style.borderColor;
        }

        const rep = c.report || {};
        document.getElementById('rep-summary').innerText = rep.executive_summary || 'Analysis report pending completion.';
        
        // Metadata fields
        const meta = rep.metadata || {};
        document.getElementById('rep-meta-name').innerText = meta.filename || '-';
        document.getElementById('rep-meta-res').innerText = meta.resolution || '-';
        document.getElementById('rep-meta-dur').innerText = meta.duration_seconds ? `${meta.duration_seconds}s` : '-';
        document.getElementById('rep-meta-fps').innerText = meta.fps || '-';

        // Count aggregates
        document.getElementById('rep-count-people').innerText = c.people_count || 0;
        document.getElementById('rep-count-vehicles').innerText = c.vehicles_count || 0;
        document.getElementById('rep-count-weapons').innerText = c.weapons_count || 0;

        // Signature
        document.getElementById('rep-sig-officer').innerText = c.officer_name || 'Jones';

        // Timeline body table
        const timelineBody = document.getElementById('rep-timeline-body');
        if (timelineBody) {
            const events = rep.timeline || [];
            if (events.length === 0) {
                timelineBody.innerHTML = `<tr><td colspan="4" class="text-center">No catalog timeline found.</td></tr>`;
            } else {
                timelineBody.innerHTML = events.map(ev => `
                    <tr>
                        <td>${ev.timestamp.toFixed(2)}s</td>
                        <td><strong>${ev.event_type}</strong></td>
                        <td>${ev.description}</td>
                        <td style="color: ${ev.risk_level === 'Critical' || ev.risk_level === 'High' ? '#EF4444' : ev.risk_level === 'Medium' ? '#F59E0B' : '#10B981'}; font-weight:700;">${ev.risk_level}</td>
                    </tr>
                `).join('');
            }
        }

        // Recommendations list
        const recList = document.getElementById('rep-recommendations');
        if (recList) {
            const recs = rep.recommendations || [];
            recList.innerHTML = recs.map(r => `<li>${r}</li>`).join('');
        }
    },

    jumpVideoTo(seconds) {
        const video = document.getElementById('forensic-video-player');
        if (video) {
            video.currentTime = parseFloat(seconds);
            video.play();
            
            // Highlight frame alert trigger
            const alertsLayer = document.getElementById('video-alerts-layer');
            if (alertsLayer) {
                alertsLayer.innerHTML = `<div class="viewport-critical-alert"><i class="fa-solid fa-expand"></i> FORENSIC LOG ANCHOR TARGET AT ${seconds.toFixed(1)}s</div>`;
                alertsLayer.classList.add('pulse');
                setTimeout(() => alertsLayer.classList.remove('pulse'), 1800);
            }
        }
    },

    handleFileSelected(file) {
        document.getElementById('drop-zone').classList.add('hidden');
        const preview = document.getElementById('file-preview');
        preview.classList.remove('hidden');

        document.getElementById('preview-filename').innerText = file.name;
        document.getElementById('preview-filesize').innerText = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
        
        // Simulating estimated scanning times (e.g. 5 seconds setup + 0.1s/MB)
        const estSec = Math.round(5 + (file.size / (1024 * 1024)) * 0.4);
        document.getElementById('preview-est-time').innerText = `~${estSec} seconds remaining`;
    },

    clearFileSelection() {
        document.getElementById('file-preview').classList.add('hidden');
        document.getElementById('drop-zone').classList.remove('hidden');
        document.getElementById('file-input').value = '';
    },

    async triggerUploadAndPipeline() {
        const caseName = document.getElementById('input-case-name').value;
        const officerName = document.getElementById('input-officer').value;
        const desc = document.getElementById('input-desc').value;
        
        const fileInput = document.getElementById('file-input');
        
        if (!caseName || !officerName || !fileInput.files.length) {
            alert('Please specify case reference details and select a video file.');
            return;
        }

        const file = fileInput.files[0];
        
        // Open Processing Overlay Screen
        const processingView = document.getElementById('processing-view');
        processingView.classList.remove('hidden');

        // Draw initial workflow nodes listing
        const stagesList = [
            "Upload", "Frame Extraction", "Speech Recognition", "OCR", 
            "Object Detection", "Face Detection", "Scene Analysis", 
            "Metadata Extraction", "Databricks Processing", "Embedding Generation", 
            "Vector Database", "LangGraph Workflow", "Evidence Report", "Completed"
        ];
        
        const stagesContainer = document.getElementById('pipeline-stages');
        stagesContainer.innerHTML = stagesList.map(st => Components.renderPipelineStage(st, 'Upload', false)).join('');

        try {
            // 1. Create case file record
            const newCase = await Api.createCase(caseName, officerName, desc);
            
            // 2. Post file via AJAX chunked upload
            document.getElementById('processing-status-label').innerText = 'Uploading raw video binaries...';
            const uploadRes = await Api.uploadVideo(newCase.case_id, file, (progress) => {
                document.getElementById('processing-status-label').innerText = `Uploading evidence file (${progress}% completed)...`;
            });
            
            // 3. Initiate active polling loop to track LangGraph node transitions
            this.state.pipelineInterval = setInterval(() => {
                this.pollPipelineStatus(newCase.case_id);
            }, 1000);
            
        } catch (err) {
            console.error('Pipeline setup failed: ', err);
            document.getElementById('processing-status-label').innerText = `Execution halted: ${err.message}`;
            alert(`Pipeline trigger failed: ${err.message}`);
            processingView.classList.add('hidden');
        }
    },

    async pollPipelineStatus(caseId) {
        try {
            const c = await Api.getCase(caseId);
            const currentStage = c.current_stage || 'Upload';
            
            document.getElementById('processing-status-label').innerText = `Active Stage: ${currentStage}...`;
            
            // Redraw workflow nodes list with progress levels
            const stagesList = [
                "Upload", "Frame Extraction", "Speech Recognition", "OCR", 
                "Object Detection", "Face Detection", "Scene Analysis", 
                "Metadata Extraction", "Databricks Processing", "Embedding Generation", 
                "Vector Database", "LangGraph Workflow", "Evidence Report", "Completed"
            ];
            
            const stagesContainer = document.getElementById('pipeline-stages');
            stagesContainer.innerHTML = stagesList.map(st => Components.renderPipelineStage(st, currentStage, c.status === 'Failed')).join('');

            // Stop condition
            if (c.status === 'Completed' || c.status === 'Failed') {
                clearInterval(this.state.pipelineInterval);
                setTimeout(() => {
                    // Close overlay and reload stats
                    document.getElementById('processing-view').classList.add('hidden');
                    this.clearFileSelection();
                    this.loadDashboardData();
                    this.selectCase(caseId);
                }, 1500);
            }
        } catch (err) {
            console.error('Polling error: ', err);
        }
    },

    async sendChatMessage() {
        const input = document.getElementById('chat-query-input');
        const query = input.value.trim();
        if (!query) return;

        const caseId = this.state.activeCaseId;
        if (!caseId) {
            alert('Please select or upload a case before querying the AI assistant.');
            return;
        }

        // Draw User Chat bubble
        const chatContainer = document.getElementById('chat-messages-container');
        chatContainer.innerHTML += Components.renderChatMessage('user', query);
        input.value = '';
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Draw temporary loading system bubble
        const loadBubbleId = `load-${Date.now()}`;
        chatContainer.innerHTML += `
            <div class="message system-msg" id="${loadBubbleId}">
                <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-bubble"><i class="fa-solid fa-circle-notch fa-spin"></i> Indexing retrieval logs...</div>
            </div>
        `;
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const res = await Api.sendChatMessage(caseId, query);
            
            // Remove loading bubble and append actual answer
            document.getElementById(loadBubbleId).remove();
            chatContainer.innerHTML += Components.renderChatMessage('bot', res.answer);
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // Render retrieved references source panel
            const citationContainer = document.getElementById('citations-container');
            const docs = res.retrieved_evidence || [];
            
            if (citationContainer) {
                if (docs.length === 0) {
                    citationContainer.innerHTML = `<p class="placeholder-text font-size:10px;">No exact matching chunks retrieved.</p>`;
                } else {
                    citationContainer.innerHTML = docs.map(c => Components.renderCitation(c)).join('');
                }
            }
        } catch (err) {
            document.getElementById(loadBubbleId).remove();
            chatContainer.innerHTML += Components.renderChatMessage('bot', `Assistant Error: Failed to fetch reply (${err.message}).`);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    },

    exportForensicPdf() {
        const caseId = this.state.activeCaseId;
        if (!caseId) {
            alert('Select an active case to export.');
            return;
        }
        
        const url = Api.getReportDownloadUrl(caseId);
        // Direct browser file download hook
        window.open(url, '_blank');
    }
};

// Initialize App on DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => App.init());
window.App = App;

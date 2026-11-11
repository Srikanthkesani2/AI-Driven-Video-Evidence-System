/* ==========================================================================
   AI-DRIVEN FORCE - REUSABLE VIEW COMPONENTS
   ========================================================================== */

const Components = {
    renderCaseRow(c) {
        const dateStr = new Date(c.created_at).toLocaleDateString(undefined, {
            month: 'short', day: 'numeric', year: 'numeric'
        });
        
        const riskClass = (c.risk_level || 'Low').toLowerCase();
        const statusClass = (c.status || 'Pending').toLowerCase();
        
        return `
            <tr data-case-id="${c.case_id}">
                <td><strong>${c.case_id}</strong></td>
                <td>${c.case_name}</td>
                <td>${dateStr}</td>
                <td><span class="badge-risk ${riskClass}">${c.risk_level || 'Low'}</span></td>
                <td>
                    <span class="badge-status ${statusClass}">
                        <i class="fa-solid ${c.status === 'Completed' ? 'fa-circle-check' : c.status === 'Processing' ? 'fa-spinner fa-spin' : c.status === 'Failed' ? 'fa-circle-xmark' : 'fa-circle'}"></i>
                        ${c.status}
                    </span>
                </td>
                <td>${c.officer_name}</td>
                <td>
                    <button class="btn btn-secondary btn-sm select-case-btn" data-case-id="${c.case_id}">
                        <i class="fa-solid fa-folder-open"></i> Open
                    </button>
                </td>
            </tr>
        `;
    },

    renderPipelineStage(stage, currentActiveStage, isFailed) {
        const stagesList = [
            "Upload", "Frame Extraction", "Speech Recognition", "OCR", 
            "Object Detection", "Face Detection", "Scene Analysis", 
            "Metadata Extraction", "Databricks Processing", "Embedding Generation", 
            "Vector Database", "LangGraph Workflow", "Evidence Report", "Completed"
        ];
        
        const targetIdx = stagesList.indexOf(stage);
        const activeIdx = stagesList.indexOf(currentActiveStage);
        
        let status = 'pending';
        if (isFailed && targetIdx >= activeIdx) {
            status = 'pending'; // left uncompleted
        } else if (targetIdx < activeIdx || currentActiveStage === 'Completed') {
            status = 'completed';
        } else if (targetIdx === activeIdx) {
            status = 'running';
        }
        
        return `
            <div class="stage-item ${status}">
                <div class="stage-bullet"></div>
                <span class="stage-name">${stage}</span>
            </div>
        `;
    },

    renderTimelineEvent(ev, onClickCallbackName) {
        const riskClass = (ev.risk_level || 'Low').toLowerCase();
        return `
            <div class="timeline-item" onclick="${onClickCallbackName}(${ev.timestamp})">
                <span class="time-badge">${ev.timestamp.toFixed(1)}s</span>
                <div class="timeline-info">
                    <span class="timeline-title">${ev.event_type}</span>
                    <span class="timeline-desc">${ev.description}</span>
                </div>
            </div>
        `;
    },

    renderFullTimelineCard(ev, onClickCallbackName) {
        const riskClass = (ev.risk_level || 'Low').toLowerCase();
        const icon = ev.event_type.toLowerCase().includes('weapon') || ev.event_type.toLowerCase().includes('hazard')
            ? 'fa-gun' 
            : ev.event_type.toLowerCase().includes('vehicle') 
            ? 'fa-car' 
            : ev.event_type.toLowerCase().includes('subject') 
            ? 'fa-user' 
            : 'fa-shield-halved';
            
        return `
            <div class="timeline-item full-timeline-card" onclick="${onClickCallbackName}(${ev.timestamp})" style="padding: 16px;">
                <span class="time-badge" style="font-size: 12px; padding: 4px 8px;">${ev.timestamp.toFixed(1)}s</span>
                <div class="timeline-info" style="margin-left: 10px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <i class="fa-solid ${icon}" style="color: var(--primary);"></i>
                        <span class="timeline-title" style="font-size: 14px; font-weight:700;">${ev.event_type}</span>
                        <span class="badge-risk ${riskClass}" style="margin-left:auto;">${ev.risk_level}</span>
                    </div>
                    <span class="timeline-desc" style="font-size: 12px; margin-top: 6px; color: var(--text-primary);">${ev.description}</span>
                    <span style="font-size: 10px; color: var(--text-muted); margin-top: 4px;"><i class="fa-solid fa-circle-check"></i> Confidence: ${(ev.confidence * 100).toFixed(0)}%</span>
                </div>
            </div>
        `;
    },

    renderTranscriptLine(line) {
        return `
            <div class="transcript-line">
                <div class="trans-meta">
                    <span>${line.speaker}</span>
                    <span>${line.start_time.toFixed(1)}s - ${line.end_time.toFixed(1)}s</span>
                </div>
                <div class="trans-text">"${line.text}"</div>
            </div>
        `;
    },

    renderChatMessage(role, text) {
        const isBot = role === 'bot';
        const avatarIcon = isBot ? 'fa-robot' : 'fa-user-tie';
        const cssClass = isBot ? 'system-msg' : 'user-msg';
        
        // Parse custom timestamp badges [12.5s] into clickable badges
        let formattedText = text;
        const timestampRegex = /\[(\d+(?:\.\d+)?)s\]/g;
        formattedText = formattedText.replace(timestampRegex, (match, sec) => {
            return `<span class="citation-badge" onclick="App.jumpVideoTo(${sec})"><i class="fa-solid fa-play"></i> ${sec}s</span>`;
        });
        
        return `
            <div class="message ${cssClass}">
                <div class="msg-avatar"><i class="fa-solid ${avatarIcon}"></i></div>
                <div class="msg-bubble">${formattedText}</div>
            </div>
        `;
    },

    renderCitation(c) {
        const meta = c.metadata || {};
        const type = meta.type || 'Evidence';
        const time = meta.timestamp || meta.start_time || 0.0;
        
        const icon = type === 'speech' ? 'fa-comment' : type === 'ocr' ? 'fa-font' : 'fa-eye';
        
        return `
            <div class="citation-card" onclick="App.jumpVideoTo(${time})">
                <div class="citation-meta">
                    <span><i class="fa-solid ${icon}"></i> ${type.toUpperCase()}</span>
                    <span>${time.toFixed(1)}s</span>
                </div>
                <div class="citation-text" style="color: var(--text-secondary); margin-top: 4px;">${c.content}</div>
            </div>
        `;
    }
};

window.Components = Components;

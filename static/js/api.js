/* ==========================================================================
   AI-DRIVEN FORCE - API REQUEST LAYER
   ========================================================================== */

const API_BASE = '/api';

const Api = {
    async getCases() {
        const response = await fetch(`${API_BASE}/cases`);
        if (!response.ok) throw new Error('Failed to retrieve cases list.');
        return await response.json();
    },

    async getCase(caseId) {
        const response = await fetch(`${API_BASE}/cases/${caseId}`);
        if (!response.ok) throw new Error(`Failed to retrieve case details for ${caseId}`);
        return await response.json();
    },

    async getStats() {
        const response = await fetch(`${API_BASE}/cases/stats`);
        if (!response.ok) throw new Error('Failed to retrieve system statistics.');
        return await response.json();
    },

    async createCase(caseName, officerName, description) {
        const response = await fetch(`${API_BASE}/cases`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ case_name: caseName, officer_name: officerName, description })
        });
        if (!response.ok) throw new Error('Failed to create new case.');
        return await response.json();
    },

    async uploadVideo(caseId, file, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);
            
            xhr.open('POST', `${API_BASE}/videos/upload?case_id=${caseId}`, true);
            
            // Track upload progression
            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable && onProgress) {
                    const percentage = Math.round((e.loaded / e.total) * 100);
                    onProgress(percentage);
                }
            };
            
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const res = JSON.parse(xhr.responseText);
                        resolve(res);
                    } catch (err) {
                        reject(new Error('Invalid upload response format.'));
                    }
                } else {
                    reject(new Error(xhr.responseText || 'Upload failed.'));
                }
            };
            
            xhr.onerror = () => reject(new Error('Network connection error during file upload.'));
            xhr.send(formData);
        });
    },

    async sendChatMessage(caseId, query) {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ case_id: caseId, query })
        });
        if (!response.ok) throw new Error('Failed to retrieve chat response.');
        return await response.json();
    },

    getReportDownloadUrl(caseId) {
        return `${API_BASE}/reports/download/${caseId}`;
    }
};

window.Api = Api;

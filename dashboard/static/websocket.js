class DashboardWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.connect();
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Dashboard WebSocket connected');
            this.reconnectAttempts = 0;
            this.updateStatus('Connected', 'green');
        };
        
        this.ws.onmessage = (event) => {
            const agentEvent = JSON.parse(event.data);
            this.handleAgentEvent(agentEvent);
        };
        
        this.ws.onclose = () => {
            console.log('Dashboard WebSocket disconnected');
            this.updateStatus('Disconnected', 'red');
            this.attemptReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('Error', 'red');
        };
    }
    
    handleAgentEvent(event) {
        const container = document.getElementById('events-container');
        const eventElement = document.createElement('div');
        eventElement.className = 'p-3 bg-gray-50 rounded border-l-4 border-blue-500';
        eventElement.innerHTML = `
            <div class="text-sm text-gray-600">${new Date(event.timestamp).toLocaleTimeString()}</div>
            <div class="font-medium">${event.type}</div>
            <div class="text-sm text-gray-700">${JSON.stringify(event.data, null, 2)}</div>
        `;
        
        container.insertBefore(eventElement, container.firstChild);
        
        // Keep only last 50 events
        while (container.children.length > 50) {
            container.removeChild(container.lastChild);
        }
    }
    
    updateStatus(status, color) {
        const statusPanel = document.getElementById('status-panel');
        statusPanel.textContent = `● ${status}`;
        statusPanel.className = `text-${color}-600`;
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
        }
    }
}

// Initialize WebSocket when page loads
document.addEventListener('DOMContentLoaded', () => {
    new DashboardWebSocket();
}); 
class SatelliteListUI {
    constructor(satelliteManager, viewer, options = {}) {
        this.satelliteManager = satelliteManager;
        this.viewer = viewer;
        this.options = options;
        this.containerId = options.containerId || 'satelliteListContainer';
        this.selectedIndex = -1;
        this.filterCategory = 'all';
        this.searchText = '';
        
        this.init();
    }
    
    init() {
        this.createContainer();
        this.update();
    }
    
    createContainer() {
        let container = document.getElementById(this.containerId);
        
        if (!container) {
            container = document.createElement('div');
            container.id = this.containerId;
            container.className = 'satellite-list-sidebar';
            
            document.body.appendChild(container);
        }
        
        this.container = container;
        this.render();
    }
    
    render() {
        const satellites = this.getFilteredSatellites();
        
        this.container.innerHTML = `
            <div class="sidebar-header">
                <h3>卫星列表</h3>
                <div class="sidebar-stats">
                    总数: ${this.satelliteManager.getAllSatellites().length} | 显示: ${satellites.length}
                </div>
            </div>
            
            <div class="sidebar-controls">
                <div class="search-box">
                    <input type="text" id="satelliteSearch" placeholder="搜索卫星..." 
                           value="${this.searchText}">
                </div>
                <div class="filter-box">
                    <select id="categoryFilter">
                        <option value="all" ${this.filterCategory === 'all' ? 'selected' : ''}>全部类型</option>
                        ${this.renderCategoryOptions()}
                    </select>
                </div>
                <div class="action-box">
                    <button class="action-btn" onclick="this.satelliteListUI.showAll()">显示全部</button>
                    <button class="action-btn" onclick="this.satelliteListUI.hideAll()">隐藏全部</button>
                </div>
            </div>
            
            <div class="satellite-list-items" id="satelliteItems">
                ${this.renderSatelliteItems(satellites)}
            </div>
            
            <div class="sidebar-info">
                <div class="category-legend">
                    ${this.renderCategoryLegend()}
                </div>
            </div>
        `;
        
        this.bindEvents();
        window.satelliteListUI = this;
    }
    
    renderCategoryOptions() {
        const categories = this.getCategories();
        return categories.map(cat => 
            `<option value="${cat}" ${this.filterCategory === cat ? 'selected' : ''}>${cat}</option>`
        ).join('');
    }
    
    renderSatelliteItems(satellites) {
        if (satellites.length === 0) {
            return `<div class="no-results">没有匹配的卫星</div>`;
        }
        
        return satellites.map((satellite, i) => {
            const index = this.satelliteManager.getAllSatellites().indexOf(satellite);
            const isSelected = index === this.selectedIndex;
            const isVisible = satellite.entity ? satellite.entity.show : true;
            const category = satellite.category || '其他';
            const elements = satellite.getOrbitalElements();
            
            return `
                <div class="satellite-item ${isSelected ? 'active' : ''}" 
                     data-index="${index}">
                    <div class="satellite-header" onclick="window.satelliteListUI.toggleExpand(${index})">
                        <div class="satellite-info">
                            <div class="satellite-color" 
                                 style="background-color: ${satellite.color.toCssColorString()};"></div>
                            <div class="satellite-name">${satellite.name}</div>
                        </div>
                        <div class="satellite-controls">
                            <button class="ctrl-btn ${isVisible ? 'active' : ''}" 
                                    title="显示/隐藏"
                                    onclick="event.stopPropagation(); window.satelliteListUI.toggleVisibility(${index})">
                                ${isVisible ? '👁' : '👁‍🗨'}
                            </button>
                            <button class="ctrl-btn" title="聚焦"
                                    onclick="event.stopPropagation(); window.satelliteListUI.focusOnSatellite(${index})">
                                🎯
                            </button>
                        </div>
                    </div>
                    
                    <div class="satellite-details ${isSelected ? 'expanded' : ''}">
                        <div class="detail-row">
                            <span class="label">类型:</span>
                            <span class="value">${category}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">半长轴:</span>
                            <span class="value">${(elements.semiMajorAxis).toFixed(2)} km</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">倾角:</span>
                            <span class="value">${elements.inclination.toFixed(2)}°</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">周期:</span>
                            <span class="value">${(elements.period / 60).toFixed(2)} min</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    renderCategoryLegend() {
        const categories = [
            { name: '空间站', color: '#FF0000' },
            { name: '通信卫星', color: '#00FFFF' },
            { name: '气象卫星', color: '#FFFF00' },
            { name: '导航卫星', color: '#00FF00' },
            { name: '遥感卫星', color: '#FF00FF' },
            { name: '其他', color: '#FFFFFF' }
        ];
        
        return categories.map(cat => `
            <div class="legend-item">
                <div class="legend-color" style="background-color: ${cat.color};"></div>
                <span>${cat.name}</span>
            </div>
        `).join('');
    }
    
    bindEvents() {
        const searchInput = document.getElementById('satelliteSearch');
        const categorySelect = document.getElementById('categoryFilter');
        
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchText = e.target.value;
                this.update();
            });
        }
        
        if (categorySelect) {
            categorySelect.addEventListener('change', (e) => {
                this.filterCategory = e.target.value;
                this.update();
            });
        }
    }
    
    getCategories() {
        const cats = new Set();
        this.satelliteManager.getAllSatellites().forEach(sat => {
            if (sat.category) cats.add(sat.category);
        });
        return Array.from(cats);
    }
    
    getFilteredSatellites() {
        let satellites = this.satelliteManager.getAllSatellites();
        
        if (this.filterCategory !== 'all') {
            satellites = satellites.filter(sat => sat.category === this.filterCategory);
        }
        
        if (this.searchText && this.searchText.trim()) {
            const search = this.searchText.toLowerCase();
            satellites = satellites.filter(sat => 
                sat.name.toLowerCase().includes(search) ||
                (sat.category && sat.category.toLowerCase().includes(search))
            );
        }
        
        return satellites;
    }
    
    toggleExpand(index) {
        if (this.selectedIndex === index) {
            this.selectedIndex = -1;
        } else {
            this.selectedIndex = index;
            
            if (this.options.onSelect) {
                const satellite = this.satelliteManager.getAllSatellites()[index];
                this.options.onSelect(satellite, index);
            }
        }
        this.update();
    }
    
    focusOnSatellite(index) {
        const satellite = this.satelliteManager.getAllSatellites()[index];
        if (!satellite) return;
        
        this.selectedIndex = index;
        this.update();
        
        if (this.options.onSelect) {
            this.options.onSelect(satellite, index);
        }
    }
    
    toggleVisibility(index) {
        const satellite = this.satelliteManager.getAllSatellites()[index];
        if (!satellite || !satellite.entity) return;
        
        const newVisible = !satellite.entity.show;
        
        if (this.options.onToggleVisibility) {
            this.options.onToggleVisibility(satellite, newVisible);
        } else {
            satellite.entity.show = newVisible;
        }
        
        this.update();
    }
    
    showAll() {
        const satellites = this.satelliteManager.getAllSatellites();
        satellites.forEach(sat => {
            if (sat.entity) sat.entity.show = true;
            if (this.options.onToggleVisibility) {
                this.options.onToggleVisibility(sat, true);
            }
        });
        this.update();
    }
    
    hideAll() {
        const satellites = this.satelliteManager.getAllSatellites();
        satellites.forEach(sat => {
            if (sat.entity) sat.entity.show = false;
            if (this.options.onToggleVisibility) {
                this.options.onToggleVisibility(sat, false);
            }
        });
        this.update();
    }
    
    update() {
        const itemsContainer = document.getElementById('satelliteItems');
        const statsContainer = document.querySelector('.sidebar-stats');
        
        const satellites = this.getFilteredSatellites();
        
        if (itemsContainer) {
            itemsContainer.innerHTML = this.renderSatelliteItems(satellites);
        }
        
        if (statsContainer) {
            statsContainer.textContent = `总数: ${this.satelliteManager.getAllSatellites().length} | 显示: ${satellites.length}`;
        }
    }
    
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

const satelliteListStyles = `
    .satellite-list-sidebar {
        position: absolute;
        top: 20px;
        right: 20px;
        width: 320px;
        max-height: calc(100vh - 40px);
        background: rgba(0, 0, 0, 0.85);
        color: white;
        border-radius: 8px;
        font-family: Arial, sans-serif;
        z-index: 100;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .sidebar-header {
        padding: 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(0, 0, 0, 0.3);
    }
    
    .sidebar-header h3 {
        margin: 0 0 8px 0;
        font-size: 16px;
        color: #4db8ff;
    }
    
    .sidebar-stats {
        font-size: 11px;
        color: #aaa;
    }
    
    .sidebar-controls {
        padding: 10px 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(0, 0, 0, 0.2);
    }
    
    .search-box {
        margin-bottom: 8px;
    }
    
    .search-box input {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        font-size: 12px;
        box-sizing: border-box;
    }
    
    .search-box input::placeholder {
        color: #888;
    }
    
    .search-box input:focus {
        outline: none;
        border-color: #4db8ff;
    }
    
    .filter-box {
        margin-bottom: 8px;
    }
    
    .filter-box select {
        width: 100%;
        padding: 6px 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        font-size: 12px;
        cursor: pointer;
    }
    
    .filter-box select option {
        background: #333;
        color: white;
    }
    
    .action-box {
        display: flex;
        gap: 8px;
    }
    
    .action-btn {
        flex: 1;
        padding: 6px;
        border: none;
        border-radius: 4px;
        background: rgba(77, 184, 255, 0.3);
        color: white;
        font-size: 11px;
        cursor: pointer;
        transition: background 0.2s;
    }
    
    .action-btn:hover {
        background: rgba(77, 184, 255, 0.5);
    }
    
    .satellite-list-items {
        flex: 1;
        overflow-y: auto;
        padding: 5px;
    }
    
    .satellite-list-items::-webkit-scrollbar {
        width: 6px;
    }
    
    .satellite-list-items::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
    }
    
    .satellite-list-items::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 3px;
    }
    
    .satellite-item {
        margin: 4px 0;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 6px;
        overflow: hidden;
        transition: background 0.2s;
    }
    
    .satellite-item:hover {
        background: rgba(255, 255, 255, 0.1);
    }
    
    .satellite-item.active {
        background: rgba(77, 184, 255, 0.15);
        border-left: 3px solid #4db8ff;
    }
    
    .satellite-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 12px;
        cursor: pointer;
    }
    
    .satellite-info {
        display: flex;
        align-items: center;
        gap: 10px;
        flex: 1;
        min-width: 0;
    }
    
    .satellite-color {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        flex-shrink: 0;
        box-shadow: 0 0 8px currentColor;
    }
    
    .satellite-name {
        font-size: 13px;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .satellite-controls {
        display: flex;
        gap: 4px;
        margin-left: 8px;
    }
    
    .ctrl-btn {
        width: 26px;
        height: 26px;
        border: none;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        cursor: pointer;
        font-size: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
    }
    
    .ctrl-btn:hover {
        background: rgba(255, 255, 255, 0.2);
    }
    
    .ctrl-btn.active {
        background: rgba(77, 184, 255, 0.4);
    }
    
    .satellite-details {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease-out;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .satellite-details.expanded {
        max-height: 200px;
    }
    
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 15px;
        font-size: 11px;
    }
    
    .detail-row .label {
        color: #888;
    }
    
    .detail-row .value {
        color: #4db8ff;
        font-weight: 500;
    }
    
    .no-results {
        text-align: center;
        padding: 40px 20px;
        color: #888;
        font-size: 13px;
    }
    
    .sidebar-info {
        padding: 10px 15px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(0, 0, 0, 0.2);
    }
    
    .category-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 10px;
        color: #aaa;
    }
    
    .legend-color {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
`;

(function injectStyles() {
    const styleId = 'satellite-list-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = satelliteListStyles;
        document.head.appendChild(style);
    }
})();

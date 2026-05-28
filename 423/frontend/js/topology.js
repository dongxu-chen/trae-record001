const API_BASE = "/api";

class TopologyGraph {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.width = this.container.clientWidth;
        this.height = this.container.clientHeight;
        this.svg = null;
        this.simulation = null;
        this.tooltip = null;
        this.currentData = null;
        this.selectedNode = null;
        this.collapsedGroups = new Set();
        this.groupMembers = new Map();
        this.animationPath = null;
        this.isAnimating = false;
        this.animationTimeout = null;
        this.layerColors = {
            0: "#81c784",
            1: "#4fc3f7",
            2: "#ffb74d",
            3: "#ba68c8",
            4: "#f06292",
            5: "#4db6ac"
        };
        this.groupColors = {
            "database": "#ba68c8",
            "cache": "#4db6ac",
            "message-queue": "#f06292",
            "storage": "#ffb74d",
            "gateway": "#81c784",
            "service": "#4fc3f7",
            "infrastructure": "#90a4ae"
        };
        this.edgeTypeColors = {
            "call": "#4fc3f7",
            "produce": "#ffb74d",
            "consume": "#4db6ac",
            "sync": "#4fc3f7",
            "async": "#ffb74d"
        };
        this.init();
    }

    init() {
        this.svg = d3.select(this.container)
            .append("svg")
            .attr("viewBox", [0, 0, this.width, this.height]);

        const defs = this.svg.append("defs");

        defs.append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "-0 -5 10 10")
            .attr("refX", 30)
            .attr("refY", 0)
            .attr("orient", "auto")
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .append("path")
            .attr("d", "M 0,-5 L 10,0 L 0,5")
            .attr("fill", "#8b949e");

        defs.append("marker")
            .attr("id", "arrowhead-group")
            .attr("viewBox", "-0 -5 10 10")
            .attr("refX", 45)
            .attr("refY", 0)
            .attr("orient", "auto")
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .append("path")
            .attr("d", "M 0,-5 L 10,0 L 0,5")
            .attr("fill", "#8b949e");

        defs.append("marker")
            .attr("id", "arrowhead-produce")
            .attr("viewBox", "-0 -5 10 10")
            .attr("refX", 30)
            .attr("refY", 0)
            .attr("orient", "auto")
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .append("path")
            .attr("d", "M 0,-5 L 10,0 L 0,5")
            .attr("fill", "#ffb74d");

        defs.append("marker")
            .attr("id", "arrowhead-consume")
            .attr("viewBox", "-0 -5 10 10")
            .attr("refX", 30)
            .attr("refY", 0)
            .attr("orient", "auto")
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .append("path")
            .attr("d", "M 0,-5 L 10,0 L 0,5")
            .attr("fill", "#4db6ac");

        defs.append("marker")
            .attr("id", "arrowhead-animate")
            .attr("viewBox", "-0 -5 10 10")
            .attr("refX", 8)
            .attr("refY", 0)
            .attr("orient", "auto")
            .attr("markerWidth", 8)
            .attr("markerHeight", 8)
            .append("path")
            .attr("d", "M 0,-5 L 10,0 L 0,5")
            .attr("fill", "#ffeb3b");

        this.g = this.svg.append("g").attr("class", "main-layer");
        this.animationLayer = this.svg.append("g").attr("class", "animation-layer");

        this.tooltip = d3.select("body")
            .append("div")
            .attr("class", "tooltip")
            .style("opacity", 0);

        this.zoom = d3.zoom()
            .scaleExtent([0.3, 3])
            .on("zoom", (event) => {
                this.g.attr("transform", event.transform);
                this.animationLayer.attr("transform", event.transform);
            });

        this.svg.call(this.zoom);

        window.addEventListener("resize", () => this.handleResize());
    }

    handleResize() {
        this.width = this.container.clientWidth;
        this.height = this.container.clientHeight;
        this.svg.attr("viewBox", [0, 0, this.width, this.height]);
        if (this.currentData) {
            this.update(this.currentData);
        }
    }

    classifyServiceType(name, service_type) {
        if (service_type) return service_type;
        const lower = name.toLowerCase();
        if (lower.includes("db") || lower.includes("database") || lower.includes("mysql") ||
            lower.includes("postgres") || lower.includes("mongo") || lower.includes("redis")) {
            if (lower.includes("redis") || lower.includes("cache")) return "cache";
            return "database";
        }
        if (lower.includes("cache") || lower.includes("redis") || lower.includes("memcached")) return "cache";
        if (lower.includes("queue") || lower.includes("kafka") || lower.includes("rabbit") ||
            lower.includes("mq") || lower.includes("nsq")) return "message-queue";
        if (lower.includes("gateway") || lower.includes("proxy") || lower.includes("nginx")) return "gateway";
        if (lower.includes("storage") || lower.includes("s3") || lower.includes("oss")) return "storage";
        return "service";
    }

    computeGrouping(nodes, edges) {
        const typeMap = new Map();
        nodes.forEach(n => {
            const type = this.classifyServiceType(n.name, n.service_type);
            n.actual_type = type;
            if (!typeMap.has(type)) typeMap.set(type, []);
            typeMap.get(type).push(n);
        });

        const typeEdges = new Map();
        edges.forEach(e => {
            const srcType = this.classifyServiceType(
                e.source,
                nodes.find(n => n.name === e.source)?.service_type
            );
            const tgtType = this.classifyServiceType(
                e.target,
                nodes.find(n => n.name === e.target)?.service_type
            );
            if (srcType !== tgtType) {
                const key = `${srcType}->${tgtType}`;
                if (!typeEdges.has(key)) {
                    typeEdges.set(key, {
                        source: srcType,
                        target: tgtType,
                        call_count: 0,
                        error_count: 0,
                        total_latency: 0,
                        member_edges: []
                    });
                }
                const agg = typeEdges.get(key);
                agg.call_count += e.call_count || 0;
                agg.error_count += e.error_count || 0;
                agg.total_latency += e.total_latency || 0;
                agg.member_edges.push(e);
            }
        });

        const groupedNodes = [];
        const typeTotals = new Map();

        typeMap.forEach((members, type) => {
            const totals = members.reduce((acc, m) => ({
                call_count: acc.call_count + (m.call_count || 0),
                error_count: acc.error_count + (m.error_count || 0)
            }), { call_count: 0, error_count: 0 });

            typeTotals.set(type, totals);

            groupedNodes.push({
                name: `__group_${type}`,
                display_name: this.getGroupDisplayName(type),
                is_group: true,
                group_type: type,
                members: members.map(m => m.name),
                member_count: members.length,
                call_count: totals.call_count,
                error_count: totals.error_count,
                layer: Math.min(...members.map(m => m.layer || 0)),
                hub: members.some(m => m.hub)
            });

            this.groupMembers.set(`__group_${type}`, members);
        });

        const groupedEdges = [];
        typeEdges.forEach((agg, key) => {
            groupedEdges.push({
                source: `__group_${agg.source}`,
                target: `__group_${agg.target}`,
                source_type: agg.source,
                target_type: agg.target,
                call_count: agg.call_count,
                error_count: agg.error_count,
                total_latency: agg.total_latency,
                error_rate: agg.call_count > 0 ? agg.error_count / agg.call_count : 0,
                avg_latency: agg.call_count > 0 ? agg.total_latency / agg.call_count : 0,
                member_count: agg.member_edges.length
            });
        });

        return { groupedNodes, groupedEdges, typeMap, typeTotals };
    }

    getGroupDisplayName(type) {
        const names = {
            "database": "数据库组",
            "cache": "缓存组",
            "message-queue": "消息队列组",
            "storage": "存储组",
            "gateway": "网关组",
            "service": "服务组",
            "infrastructure": "基础设施组"
        };
        return names[type] || `${type}组`;
    }

    getGroupIcon(type) {
        const icons = {
            "database": "🗄️",
            "cache": "⚡",
            "message-queue": "📨",
            "storage": "💾",
            "gateway": "🚪",
            "service": "⚙️",
            "infrastructure": "🏗️"
        };
        return icons[type] || "📦";
    }

    getEdgeColor(d) {
        if (d.is_group) return "#8b949e";
        if (d.type === "produce") return "#ffb74d";
        if (d.type === "consume") return "#4db6ac";
        if (d.call_type === "async") return "#ffb74d";
        const errorRate = d.error_rate || 0;
        if (errorRate > 0.1) return "#f44336";
        if (errorRate > 0.05) return "#ff9800";
        return "#4fc3f7";
    }

    getEdgeDashArray(d) {
        if (d.is_group) return "6,3";
        if (d.type === "produce" || d.type === "consume") return "4,4";
        if (d.call_type === "async") return "4,4";
        return "none";
    }

    getEdgeMarker(d) {
        if (d.is_group) return "url(#arrowhead-group)";
        if (d.type === "produce") return "url(#arrowhead-produce)";
        if (d.type === "consume") return "url(#arrowhead-consume)";
        return "url(#arrowhead)";
    }

    update(data, layersInfo = null) {
        this.currentData = data;
        const { nodes, edges } = this.processData(data, layersInfo);
        const { groupedNodes, groupedEdges, typeMap } = this.computeGrouping(nodes, edges);

        this.g.selectAll("*").remove();
        this.animationLayer.selectAll("*").remove();

        if (nodes.length === 0) {
            this.g.append("text")
                .attr("x", this.width / 2)
                .attr("y", this.height / 2)
                .attr("text-anchor", "middle")
                .attr("fill", "#8b949e")
                .attr("font-size", "16px")
                .text("暂无拓扑数据，请导入Trace");
            return;
        }

        const hasCollapsed = this.collapsedGroups.size > 0;
        let displayNodes = hasCollapsed ? groupedNodes : nodes;
        let displayEdges = hasCollapsed ? groupedEdges : edges;

        const nodeMap = new Map();
        displayNodes.forEach(n => nodeMap.set(n.name, n));

        const link = this.g.append("g")
            .attr("class", "links")
            .selectAll("path")
            .data(displayEdges)
            .enter()
            .append("path")
            .attr("class", "link")
            .attr("data-edge-id", d => d.id || `${d.source}->${d.target}`)
            .attr("stroke", d => this.getEdgeColor(d))
            .attr("stroke-width", d => Math.max(1.5, Math.log2((d.call_count || 1) + 1) * (d.is_group ? 2 : 1)))
            .attr("stroke-dasharray", d => this.getEdgeDashArray(d))
            .attr("marker-end", d => this.getEdgeMarker(d))
            .attr("fill", "none")
            .on("mouseover", (event, d) => this.showEdgeTooltip(event, d))
            .on("mouseout", () => this.hideTooltip());

        const linkLabel = this.g.append("g")
            .attr("class", "link-labels")
            .selectAll("text")
            .data(displayEdges.filter(e => (e.call_count || 0) > 0))
            .enter()
            .append("text")
            .attr("class", "link-label")
            .attr("fill", "#8b949e")
            .attr("font-size", "10px")
            .attr("text-anchor", "middle")
            .text(d => {
                if (d.is_group) return `${d.member_count}条依赖, ${d.call_count}次`;
                const typeLabel = d.type === "produce" ? "生产" :
                                  d.type === "consume" ? "消费" : "";
                const asyncLabel = d.call_type === "async" ? "异步" : "";
                const label = typeLabel || asyncLabel;
                return label ? `${label} · ${d.call_count}次` : `${d.call_count}次`;
            });

        const node = this.g.append("g")
            .attr("class", "nodes")
            .selectAll("g")
            .data(displayNodes)
            .enter()
            .append("g")
            .attr("class", d => d.type === "message_queue" ? "node mq-node" : "node")
            .call(this.drag());

        node.filter(d => d.is_group)
            .append("rect")
            .attr("x", d => -this.getGroupRadius(d) - 5)
            .attr("y", d => -this.getGroupRadius(d) - 5)
            .attr("width", d => (this.getGroupRadius(d) + 5) * 2)
            .attr("height", d => (this.getGroupRadius(d) + 5) * 2)
            .attr("rx", 12)
            .attr("fill", d => this.getGroupColor(d))
            .attr("fill-opacity", 0.15)
            .attr("stroke", d => this.getGroupColor(d))
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "8,4");

        node.filter(d => d.type === "message_queue")
            .append("rect")
            .attr("x", d => -22)
            .attr("y", d => -22)
            .attr("width", 44)
            .attr("height", 44)
            .attr("rx", 8)
            .attr("fill", "#f06292")
            .attr("stroke", "#f06292")
            .attr("stroke-width", 2)
            .attr("fill-opacity", 0.3);

        node.filter(d => d.type === "message_queue")
            .append("text")
            .attr("dy", "0.35em")
            .attr("text-anchor", "middle")
            .attr("font-size", "16px")
            .text("📨");

        node.filter(d => d.type === "message_queue")
            .append("text")
            .attr("dy", 48)
            .attr("text-anchor", "middle")
            .attr("fill", "#c9d1d9")
            .attr("font-size", "10px")
            .text(d => d.name);

        node.filter(d => d.type === "message_queue")
            .append("text")
            .attr("dy", 62)
            .attr("text-anchor", "middle")
            .attr("fill", "#8b949e")
            .attr("font-size", "9px")
            .text(d => `生产:${d.produce_count} | 消费:${d.consume_count}`);

        node.filter(d => d.type !== "message_queue" || d.is_group)
            .append("circle")
            .attr("r", d => d.is_group
                ? this.getGroupRadius(d)
                : Math.max(14, Math.min(30, Math.log2((d.call_count || 1) + 1) * 5)))
            .attr("fill", d => d.is_group
                ? this.getGroupColor(d)
                : this.getNodeColor(d, layersInfo))
            .attr("stroke", d => d.is_group
                ? this.getGroupColor(d)
                : this.getNodeStroke(d))
            .attr("stroke-width", d => d.is_group ? 2 : (d.hub ? 3 : 2))
            .attr("fill-opacity", d => d.is_group ? 0.6 : 1);

        node.filter(d => d.is_group && d.group_type !== "message_queue")
            .append("text")
            .attr("dy", "0.35em")
            .attr("text-anchor", "middle")
            .attr("font-size", "18px")
            .text(d => this.getGroupIcon(d.group_type));

        node.filter(d => d.type !== "message_queue")
            .append("text")
            .attr("dy", d => {
                if (d.is_group) return this.getGroupRadius(d) + 20;
                return Math.max(14, Math.min(30, Math.log2((d.call_count || 1) + 1) * 5)) + 16;
            })
            .attr("text-anchor", "middle")
            .text(d => d.is_group ? d.display_name : d.name)
            .attr("fill", "#c9d1d9")
            .attr("font-size", d => d.is_group ? "12px" : "11px")
            .attr("font-weight", d => d.is_group ? "600" : "400");

        node.filter(d => d.is_group)
            .append("text")
            .attr("dy", d => this.getGroupRadius(d) + 34)
            .attr("text-anchor", "middle")
            .attr("fill", "#8b949e")
            .attr("font-size", "10px")
            .text(d => `${d.member_count} 个服务 · ${d.call_count}次调用`);

        node.filter(d => d.is_group)
            .append("text")
            .attr("y", d => -this.getGroupRadius(d) - 12)
            .attr("text-anchor", "middle")
            .attr("fill", "#58a6ff")
            .attr("font-size", "10px")
            .attr("cursor", "pointer")
            .text("点击展开")
            .on("click", (event, d) => {
                event.stopPropagation();
                this.toggleGroup(d);
            });

        node.filter(d => !d.is_group && this.isGroupedMember(d.name))
            .append("text")
            .attr("y", d => {
                const r = Math.max(14, Math.min(30, Math.log2((d.call_count || 1) + 1) * 5));
                return -r - 12;
            })
            .attr("text-anchor", "middle")
            .attr("fill", "#58a6ff")
            .attr("font-size", "9px")
            .attr("cursor", "pointer")
            .text("点击折叠到组")
            .on("click", (event, d) => {
                event.stopPropagation();
                this.collapseMember(d);
            });

        node.on("mouseover", (event, d) => this.showNodeTooltip(event, d))
            .on("mouseout", () => this.hideTooltip())
            .on("click", (event, d) => {
                if (d.is_group) {
                    this.toggleGroup(d);
                } else {
                    this.selectNode(d);
                }
            });

        this.simulation = d3.forceSimulation(displayNodes)
            .force("link", d3.forceLink(displayEdges).id(d => d.name).distance(d => d.is_group ? 160 : 100).strength(0.7))
            .force("charge", d3.forceManyBody().strength(d => d.is_group ? -500 : -300))
            .force("center", d3.forceCenter(this.width / 2, this.height / 2))
            .force("collision", d3.forceCollide().radius(d => {
                if (d.is_group) return this.getGroupRadius(d) + 20;
                return Math.max(20, Math.log2((d.call_count || 1) + 1) * 5) + 10;
            }))
            .force("x", d3.forceX(d => {
                if (d.is_group) {
                    const typeOrder = { "gateway": 0.1, "service": 0.4, "database": 0.75, "cache": 0.85, "message-queue": 0.6, "storage": 0.9 };
                    return (typeOrder[d.group_type] || 0.5) * this.width;
                }
                return this.width / 2;
            }).strength(0.08))
            .force("y", d3.forceY(this.height / 2).strength(0.05))
            .on("tick", () => {
                link.attr("d", d => this.linkPath(d));
                linkLabel
                    .attr("x", d => (d.source.x + d.target.x) / 2)
                    .attr("y", d => (d.source.y + d.target.y) / 2);
                node.attr("transform", d => `translate(${d.x},${d.y})`);
            });
    }

    getGroupRadius(d) {
        return Math.max(25, Math.min(45, 15 + Math.sqrt(d.member_count || 1) * 8));
    }

    getGroupColor(d) {
        return this.groupColors[d.group_type] || "#90a4ae";
    }

    isGroupedMember(serviceName) {
        for (const [groupName, members] of this.groupMembers) {
            if (members.some(m => m.name === serviceName)) return true;
        }
        return false;
    }

    toggleGroup(groupNode) {
        this.collapsedGroups.delete(groupNode.name);
        this.update(this.currentData);
    }

    collapseMember(node) {
        const type = this.classifyServiceType(node.name, node.service_type);
        const groupName = `__group_${type}`;
        this.collapsedGroups.add(groupName);
        this.update(this.currentData);
    }

    collapseAllGroups() {
        const types = new Set();
        this.currentData.nodes.forEach(n => {
            types.add(this.classifyServiceType(n.name, n.service_type));
        });
        types.forEach(t => this.collapsedGroups.add(`__group_${t}`));
        this.update(this.currentData);
    }

    expandAllGroups() {
        this.collapsedGroups.clear();
        this.update(this.currentData);
    }

    processData(data, layersInfo) {
        const nodeMap = new Map();
        data.nodes.forEach(n => {
            nodeMap.set(n.name, {
                ...n,
                layer: layersInfo && layersInfo.layers ? layersInfo.layers[n.name] : 1,
                hub: false,
                call_count: n.call_count || 0,
                error_count: n.error_count || 0
            });
        });

        const edges = data.edges.map(e => ({
            ...e,
            source: e.source,
            target: e.target,
            call_count: e.call_count || 0,
            error_count: e.error_count || 0,
            error_rate: e.error_rate || 0,
            avg_latency: e.avg_latency || 0,
            max_latency: e.max_latency || 0,
            min_latency: e.min_latency || 0
        }));

        edges.forEach(e => {
            if (nodeMap.has(e.source) && e.type === "call") {
                nodeMap.get(e.source).hub = true;
            }
        });

        return {
            nodes: Array.from(nodeMap.values()),
            edges: edges
        };
    }

    getNodeColor(node, layersInfo) {
        if (node.error_count && node.call_count > 0) {
            const errorRate = node.error_count / node.call_count;
            if (errorRate > 0.05) return "#f85149";
            if (errorRate > 0.01) return "#ff9800";
        }
        if (layersInfo && layersInfo.layers && layersInfo.layers[node.name] !== undefined) {
            return this.layerColors[layersInfo.layers[node.name]] || "#4fc3f7";
        }
        return "#4fc3f7";
    }

    getNodeStroke(node) {
        if (node.hub) return "#58a6ff";
        return "#30363d";
    }

    linkPath(d) {
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy);
        return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
    }

    showNodeTooltip(event, d) {
        const errorRate = (d.call_count || 0) > 0 ? ((d.error_count || 0) / (d.call_count || 0) * 100).toFixed(2) : 0;

        if (d.is_group) {
            const memberNames = d.members.join(", ");
            this.tooltip
                .style("opacity", 1)
                .html(`
                    <div class="tooltip-title">${this.getGroupIcon(d.group_type)} ${d.display_name}</div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">类型:</span>
                        <span>${d.group_type}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">成员数:</span>
                        <span>${d.member_count} 个服务</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">成员:</span>
                        <span style="font-size:11px;max-width:200px;">${memberNames}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">总调用:</span>
                        <span>${d.call_count}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">总错误:</span>
                        <span>${d.error_count}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">错误率:</span>
                        <span>${errorRate}%</span>
                    </div>
                    <div style="margin-top:8px;font-size:11px;color:#58a6ff;">点击展开查看详情</div>
                `)
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 10) + "px");
        } else {
            this.tooltip
                .style("opacity", 1)
                .html(`
                    <div class="tooltip-title">${d.name}</div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">类型:</span>
                        <span>${d.actual_type || d.service_type || 'unknown'}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">层级:</span>
                        <span>L${d.layer || 0}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">调用次数:</span>
                        <span>${d.call_count || 0}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">错误次数:</span>
                        <span>${d.error_count || 0}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">错误率:</span>
                        <span>${errorRate}%</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">枢纽节点:</span>
                        <span>${d.hub ? "是" : "否"}</span>
                    </div>
                `)
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 10) + "px");
        }
    }

    showEdgeTooltip(event, d) {
        const content = d.is_group
            ? `
                <div class="tooltip-title">${d.source_type}组 → ${d.target_type}组</div>
                <div class="tooltip-row">
                    <span class="tooltip-label">聚合依赖:</span>
                    <span>${d.member_count} 条</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">总调用次数:</span>
                    <span>${d.call_count}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">总错误次数:</span>
                    <span>${d.error_count}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">错误率:</span>
                    <span>${(d.error_rate * 100).toFixed(2)}%</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">平均延迟:</span>
                    <span>${d.avg_latency.toFixed(0)}μs</span>
                </div>
            `
            : `
                <div class="tooltip-title">${d.source} → ${d.target}</div>
                <div class="tooltip-row">
                    <span class="tooltip-label">调用次数:</span>
                    <span>${d.call_count}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">错误次数:</span>
                    <span>${d.error_count}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">错误率:</span>
                    <span>${(d.error_rate * 100).toFixed(2)}%</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">平均延迟:</span>
                    <span>${d.avg_latency.toFixed(0)}μs</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">最大延迟:</span>
                    <span>${d.max_latency.toFixed(0)}μs</span>
                </div>
            `;

        this.tooltip
            .style("opacity", 1)
            .html(content)
            .style("left", (event.pageX + 15) + "px")
            .style("top", (event.pageY - 10) + "px");
    }

    hideTooltip() {
        this.tooltip.style("opacity", 0);
    }

    selectNode(node) {
        if (this.selectedNode && this.selectedNode.name === node.name) {
            this.selectedNode = null;
        } else {
            this.selectedNode = node;
        }
        if (typeof this.onSelectNode === "function") {
            this.onSelectNode(this.selectedNode);
        }
    }

    drag() {
        const that = this;
        function dragstarted(event, d) {
            if (!event.active) that.simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (!event.active) that.simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }

    highlightNode(serviceName) {
        this.g.selectAll(".node circle")
            .attr("opacity", d => d.name === serviceName ? 1 : 0.3);

        this.g.selectAll(".link")
            .attr("opacity", d =>
                d.source.name === serviceName || d.target.name === serviceName ? 1 : 0.1
            );
    }

    resetHighlight() {
        this.g.selectAll(".node circle").attr("opacity", 1);
        this.g.selectAll(".link").attr("opacity", 0.6);
    }

    stopAnimation() {
        this.isAnimating = false;
        if (this.animationTimeout) {
            clearTimeout(this.animationTimeout);
            this.animationTimeout = null;
        }
        this.animationLayer.selectAll("*").remove();
    }

    async animatePath(nodeNames, speed = 1500) {
        if (nodeNames.length < 2) return;

        this.stopAnimation();
        this.isAnimating = true;

        const nodeMap = new Map();
        this.g.selectAll(".node").each(function(d) {
            nodeMap.set(d.name, d);
        });

        const edgeMap = new Map();
        this.g.selectAll(".link").each(function(d) {
            const key = `${d.source.name}->${d.target.name}`;
            edgeMap.set(key, {
                element: this,
                path: d3.select(this).attr("d")
            });
        });

        this.animationLayer.selectAll("*").remove();

        for (let i = 0; i < nodeNames.length - 1; i++) {
            if (!this.isAnimating) break;

            const sourceName = nodeNames[i];
            const targetName = nodeNames[i + 1];
            const source = nodeMap.get(sourceName);
            const target = nodeMap.get(targetName);

            if (!source || !target) continue;

            const edgeKey = `${sourceName}->${targetName}`;
            const edgeData = edgeMap.get(edgeKey);

            if (edgeData) {
                d3.select(edgeData.element)
                    .attr("stroke", "#ffeb3b")
                    .attr("stroke-width", 4)
                    .attr("opacity", 1);
            }

            const pulseNode = this.animationLayer.append("circle")
                .attr("r", 8)
                .attr("fill", "#ffeb3b")
                .attr("opacity", 0.8)
                .attr("filter", "drop-shadow(0 0 8px #ffeb3b)");

            const pulseLabel = this.animationLayer.append("text")
                .attr("fill", "#ffeb3b")
                .attr("font-size", "10px")
                .attr("font-weight", "bold")
                .attr("text-anchor", "middle")
                .attr("dy", -14);

            const duration = speed;
            const startTime = performance.now();

            const animateStep = (now) => {
                if (!this.isAnimating) return;

                const elapsed = now - startTime;
                const t = Math.min(elapsed / duration, 1);

                const x = source.x + (target.x - source.x) * t;
                const y = source.y + (target.y - source.y) * t;

                pulseNode
                    .attr("cx", x)
                    .attr("cy", y);

                pulseLabel
                    .attr("x", x)
                    .attr("y", y)
                    .text(`${i + 1}/${nodeNames.length - 1}`);

                if (t < 1) {
                    requestAnimationFrame(animateStep);
                } else {
                    pulseNode.remove();
                    pulseLabel.remove();
                    if (edgeData) {
                        d3.select(edgeData.element)
                            .attr("stroke", d => this.getEdgeColor(d))
                            .attr("stroke-width", d => Math.max(1.5, Math.log2((d.call_count || 1) + 1) * (d.is_group ? 2 : 1)))
                            .attr("opacity", 0.6);
                    }
                }
            };

            requestAnimationFrame(animateStep);

            await new Promise(resolve => {
                this.animationTimeout = setTimeout(resolve, duration + 200);
            });
        }

        this.isAnimating = false;
    }

    async animateFromSource(sourceName, targetName = null, maxPaths = 3) {
        try {
            const url = targetName
                ? `${API_BASE}/request/paths?source=${encodeURIComponent(sourceName)}&target=${encodeURIComponent(targetName)}&max_paths=${maxPaths}`
                : `${API_BASE}/request/paths?source=${encodeURIComponent(sourceName)}&max_paths=${maxPaths}`;

            const response = await fetch(url);
            const data = await response.json();

            if (!data.paths || data.paths.length === 0) {
                alert("未找到请求路径");
                return;
            }

            for (let i = 0; i < data.paths.length; i++) {
                if (!this.isAnimating && i > 0) break;
                await this.animatePath(data.paths[i].nodes, 1200);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        } catch (e) {
            console.error("Failed to load request paths:", e);
        }
    }

    async animateCriticalPaths() {
        try {
            const response = await fetch(`${API_BASE}/topology/critical-paths`);
            const data = await response.json();

            if (!data || data.length === 0) {
                alert("未找到关键路径");
                return;
            }

            for (let i = 0; i < Math.min(data.length, 3); i++) {
                if (!this.isAnimating && i > 0) break;
                const path = data[i];
                const nodeNames = path.nodes.map(n => n.name);
                await this.animatePath(nodeNames, 1200);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        } catch (e) {
            console.error("Failed to load critical paths:", e);
        }
    }
}

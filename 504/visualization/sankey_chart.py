from pyecharts import options as opts
from pyecharts.charts import Sankey
from typing import Dict, List


class SankeyChart:
    @staticmethod
    def create_sankey(sankey_data: Dict, 
                      title: str = "用户行为路径桑基图",
                      width: str = "100%",
                      height: str = "600px") -> Sankey:
        nodes = sankey_data.get('nodes', [])
        links = sankey_data.get('links', [])

        if not nodes or not links:
            return Sankey()

        colors = [
            "#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
            "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc", "#48b4bd"
        ]

        for i, node in enumerate(nodes):
            if 'itemStyle' not in node:
                node['itemStyle'] = {'color': colors[i % len(colors)]}

        sankey = (
            Sankey(init_opts=opts.InitOpts(width=width, height=height))
            .add(
                series_name="",
                nodes=nodes,
                links=links,
                pos_left="10%",
                pos_right="10%",
                node_width=20,
                node_gap=12,
                node_align="justify",
                layout_iterations=0,
                orient="horizontal",
                is_draggable=True,
                label_opts=opts.LabelOpts(
                    position="right",
                    font_size=12,
                    color="#333"
                ),
                line_style_opts=opts.LineStyleOpts(
                    color="gradient",
                    curve=0.5,
                    opacity=0.6
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="item",
                    formatter="{b}: {c}"
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title=title,
                    pos_left="center",
                    title_textstyle_opts=opts.TextStyleOpts(font_size=18)
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="item",
                    trigger_on="mousemove"
                )
            )
        )

        return sankey

    @staticmethod
    def create_advanced_sankey(sankey_data: Dict,
                         title: str = "用户行为路径桑基图",
                         width: str = "100%",
                         height: str = "600px") -> Sankey:
        nodes = sankey_data.get('nodes', [])
        links = sankey_data.get('links', [])

        if not nodes or not links:
            return Sankey()

        sankey_nodes = []
        for node in nodes:
            display_name = node['name']
            if node.get('is_aggregate'):
                display_name = f"[{display_name}]"
            
            sankey_nodes.append({
                'name': display_name,
                'itemStyle': node.get('itemStyle', {})
            })

        sankey_links = []
        for link in links:
            sankey_links.append({
                'source': link['source'],
                'target': link['target'],
                'value': link['value'],
                'lineStyle': link.get('lineStyle', {'opacity': 0.5})
            })

        sankey = (
            Sankey(init_opts=opts.InitOpts(width=width, height=height))
            .add(
                series_name="",
                nodes=sankey_nodes,
                links=sankey_links,
                pos_left="10%",
                pos_right="15%",
                node_width=20,
                node_gap=12,
                node_align="justify",
                layout_iterations=0,
                orient="horizontal",
                is_draggable=True,
                label_opts=opts.LabelOpts(
                    position="right",
                    font_size=12,
                    color="#333",
                    formatter="{b}"
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="item",
                    formatter="{b}: {c}"
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title=title,
                    pos_left="center",
                    title_textstyle_opts=opts.TextStyleOpts(font_size=18)
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="item",
                    trigger_on="mousemove"
                )
            )
        )

        return sankey

    @staticmethod
    def create_grouped_sankey(sankey_data_list: List[Dict],
                                group_names: List[str],
                                title: str = "分组路径对比") -> Sankey:
        all_nodes = []
        all_links = []
        node_offset = 0

        colors = ["#5470c6", "#ee6666", "#91cc75", "#fac858"]

        for idx, (sankey_data, group_name) in enumerate(zip(sankey_data_list, group_names)):
            nodes = sankey_data.get('nodes', [])
            links = sankey_data.get('links', [])

            group_color = colors[idx % len(colors)]
            for node in nodes:
                new_node = node.copy()
                new_node['name'] = f"{group_name}: {node['name']}"
                new_node['itemStyle'] = {'color': group_color}
                all_nodes.append(new_node)

            node_mapping = {i: i + node_offset for i in range(len(nodes))}
            for link in links:
                new_link = link.copy()
                source_idx = link['source']
                target_idx = link['target']
                if isinstance(source_idx, int) and isinstance(target_idx, int):
                    new_link['source'] = node_mapping.get(source_idx, source_idx)
                    new_link['target'] = node_mapping.get(target_idx, target_idx)
                else:
                    new_link['source'] = f"{group_name}: {source_idx}"
                    new_link['target'] = f"{group_name}: {target_idx}"
                new_link['lineStyle'] = {'color': group_color, 'opacity': 0.4}
                all_links.append(new_link)

            node_offset += len(nodes)

        sankey = (
            Sankey(init_opts=opts.InitOpts(width="100%", height="700px"))
            .add(
                series_name="",
                nodes=all_nodes,
                links=all_links,
                pos_left="5%",
                pos_right="20%",
                node_width=15,
                node_gap=10,
                label_opts=opts.LabelOpts(font_size=10)
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, pos_left="center")
            )
        )

        return sankey

from pyecharts import options as opts
from pyecharts.charts import Bar, Line, Pie, HeatMap, Table
from pyecharts.commons.utils import JsCode
import pandas as pd
from typing import List, Dict


class PathCharts:
    @staticmethod
    def create_top_paths_bar(paths_df: pd.DataFrame,
                             title: str = "Top 路径分布",
                             top_n: int = 10) -> Bar:
        if paths_df.empty:
            return Bar()

        df = paths_df.head(top_n).sort_values('count', ascending=True)

        bar = (
            Bar(init_opts=opts.InitOpts(width="100%", height="500px"))
            .add_xaxis(df['path'].tolist())
            .add_yaxis(
                "会话数",
                df['count'].tolist(),
                itemstyle_opts=opts.ItemStyleOpts(
                    color=JsCode(
                        "function(params) { "
                        "var colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#48b4bd'];"
                        "return colors[params.dataIndex % colors.length];"
                        "}"
                    )
                )
            )
            .reversal_axis()
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, pos_left="center"),
                xaxis_opts=opts.AxisOpts(name="会话数"),
                yaxis_opts=opts.AxisOpts(
                    name="路径",
                    axislabel_opts=opts.LabelOpts(font_size=10, interval=0)
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="shadow"
                )
            )
            .set_series_opts(
                label_opts=opts.LabelOpts(position="right", formatter="{c}")
            )
        )

        return bar

    @staticmethod
    def create_dropoff_bar(dropoff_df: pd.DataFrame,
                            title: str = "各节点流失率") -> Bar:
        if dropoff_df.empty:
            return Bar()

        df = dropoff_df.sort_values('dropoff_rate', ascending=True)

        bar = (
            Bar(init_opts=opts.InitOpts(width="100%", height="500px"))
            .add_xaxis(df['event'].tolist())
            .add_yaxis(
                "流失率(%)",
                df['dropoff_rate'].tolist(),
                itemstyle_opts=opts.ItemStyleOpts(color="#ee6666")
            )
            .reversal_axis()
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, pos_left="center"),
                xaxis_opts=opts.AxisOpts(name="流失率(%)", max_=100),
                yaxis_opts=opts.AxisOpts(name="事件节点"),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    formatter="{b}: {c}%"
                )
            )
            .set_series_opts(label_opts=opts.LabelOpts(position="right", formatter="{c}%"))
        )

        return bar

    @staticmethod
    def create_churn_pie(churn_data: Dict,
                          title: str = "用户流失分布") -> Pie:
        if not churn_data:
            return Pie()

        pie_data = [
            {"value": churn_data.get('churned_users', 0), "name": "流失用户"},
            {"value": churn_data.get('total_users', 0) - churn_data.get('churned_users', 0), "name": "活跃用户"}
        ]

        pie = (
            Pie(init_opts=opts.InitOpts(width="100%", height="400px"))
            .add(
                series_name="",
                data_pair=[(item['name'], item['value']) for item in pie_data],
                radius=["40%", "70%"],
                label_opts=opts.LabelOpts(
                    formatter="{b}: {c}人 ({d}%)"
                )
            )
            .set_colors(["#ee6666", "#91cc75"])
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, pos_left="center"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="left", pos_top="middle")
            )
        )

        return pie

    @staticmethod
    def create_retention_heatmap(retention_df: pd.DataFrame,
                                  title: str = "用户留存热力图") -> HeatMap:
        if retention_df.empty:
            return HeatMap()

        pivot_df = retention_df.pivot(
            index='cohort_date',
            columns='period_number',
            values='retention_rate'
        ).fillna(0)

        cohorts = [str(d)[:10] for d in pivot_df.index.tolist()]
        periods = [f"P{int(p)}" for p in pivot_df.columns.tolist()]

        heatmap_data = []
        for i, cohort in enumerate(cohorts):
            for j, period in enumerate(periods):
                value = pivot_df.iloc[i, j] if j < len(pivot_df.columns) else 0
                heatmap_data.append([j, i, round(value, 1)])

        heatmap = (
            HeatMap(init_opts=opts.InitOpts(width="100%", height="600px"))
            .add_xaxis(periods)
            .add_yaxis(
                series_name="留存率(%)",
                yaxis_data=cohorts,
                value=heatmap_data,
                label_opts=opts.LabelOpts(
                    is_show=True,
                    color="#fff",
                    font_size=10,
                    formatter="{c}%"
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, pos_left="center"),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    split_area_opts=opts.SplitAreaOpts(is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1))
                ),
                yaxis_opts=opts.AxisOpts(
                    type_="category",
                    split_area_opts=opts.SplitAreaOpts(is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1))
                ),
                visualmap_opts=opts.VisualMapOpts(
                    min_=0,
                    max_=100,
                    range_color=["#5470c6", "#91cc75", "#fac858", "#ee6666"],
                    pos_left="right",
                    pos_top="middle",
                    calculable=True,
                    formatter="{value}%"
                ),
                tooltip_opts=opts.TooltipOpts(
                    formatter="第{b}期<br/>留存率: {c}%"
                )
            )
        )

        return heatmap

    @staticmethod
    def create_comparison_bar(comparison_df: pd.DataFrame,
                               title: str = "分组对比") -> Bar:
        if comparison_df.empty:
            return Bar()

        bar = (
            Bar(init_opts=opts.InitOpts(width="100%", height="500px"))
            .add_xaxis(comparison_df['step'].tolist())
            .add_yaxis("A组", comparison_df['users_a'].tolist(), color="#5470c6")
            .add_yaxis("B组", comparison_df['users_b'].tolist(), color="#ee6666")
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, pos_left="center"),
                xaxis_opts=opts.AxisOpts(name="步骤"),
                yaxis_opts=opts.AxisOpts(name="用户数"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                legend_opts=opts.LegendOpts(pos_top="bottom")
            )
        )

        return bar

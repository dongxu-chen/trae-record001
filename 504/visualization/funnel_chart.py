from pyecharts import options as opts
from pyecharts.charts import Funnel
import pandas as pd


class FunnelChart:
    @staticmethod
    def create_funnel(funnel_df: pd.DataFrame,
                      title: str = "转化漏斗") -> Funnel:
        if funnel_df.empty:
            return Funnel()

        funnel_data = [
            (row['step'], row['users'])
            for _, row in funnel_df.iterrows()
        ]

        funnel = (
            Funnel(init_opts=opts.InitOpts(width="100%", height="500px"))
            .add(
                series_name="用户数",
                data_pair=funnel_data,
                gap=2,
                tooltip_opts=opts.TooltipOpts(
                    trigger="item",
                    formatter="{b}: {c}人 ({d}%)"
                ),
                label_opts=opts.LabelOpts(
                    position="inside",
                    formatter="{b}\n{c}人",
                    font_size=12
                ),
                itemstyle_opts=opts.ItemStyleOpts(
                    border_color="#fff",
                    border_width=1
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title=title,
                    pos_left="center"
                ),
                legend_opts=opts.LegendOpts(
                    pos_top="bottom"
                )
            )
        )

        return funnel

    @staticmethod
    def create_funnel_with_conversion(funnel_df: pd.DataFrame,
                                       title: str = "转化漏斗（含转化率）") -> Funnel:
        if funnel_df.empty:
            return Funnel()

        funnel_data = []
        for _, row in funnel_df.iterrows():
            funnel_data.append({
                'value': row['users'],
                'name': f"{row['step']}\n转化率: {row['conversion_from_previous']}%"
            })

        funnel = (
            Funnel(init_opts=opts.InitOpts(width="100%", height="500px"))
            .add(
                series_name="",
                data_pair=[(item['name'], item['value']) for item in funnel_data],
                gap=5,
                label_opts=opts.LabelOpts(
                    position="inside",
                    formatter="{b}\n{c}人",
                    font_size=11
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, pos_left="center"),
                legend_opts=opts.LegendOpts(pos_top="bottom")
            )
        )

        return funnel

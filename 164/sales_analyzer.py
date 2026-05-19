import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from collections import defaultdict
from itertools import combinations

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def setup_logger():
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f'sales_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


class SalesAnalyzer:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = None
        self.raw_df = None
        self.logger = setup_logger()
        self.logger.info("=" * 60)
        self.logger.info("电商销量数据分析系统启动")
        self.logger.info("=" * 60)
        
        self.load_data()
        self.clean_data()

    def load_data(self):
        self.logger.info(f"开始加载数据文件: {self.csv_path}")
        
        try:
            self.raw_df = pd.read_csv(self.csv_path, encoding='utf-8')
            self.logger.info(f"原始数据加载成功，共 {len(self.raw_df)} 条记录")
        except Exception as e:
            self.logger.error(f"数据加载失败: {str(e)}")
            raise
        
        self.df = self.raw_df.copy()

    def clean_data(self):
        self.logger.info("开始数据清洗...")
        initial_count = len(self.df)
        
        self.logger.info(f"原始数据行数: {initial_count}")
        
        null_counts = self.df.isnull().sum()
        if null_counts.sum() > 0:
            self.logger.warning("发现空值:")
            for col, count in null_counts[null_counts > 0].items():
                self.logger.warning(f"  - {col}: {count} 个空值")
            
            self.df = self.df.dropna(subset=['订单ID', '订单日期', '用户ID', '商品ID', '总价'])
            self.logger.info(f"已删除关键字段为空的记录，剩余 {len(self.df)} 条")
        else:
            self.logger.info("未发现空值")
        
        duplicate_count = self.df.duplicated(subset=['订单ID']).sum()
        if duplicate_count > 0:
            self.logger.warning(f"发现 {duplicate_count} 条重复订单记录")
            self.df = self.df.drop_duplicates(subset=['订单ID'], keep='first')
            self.logger.info(f"已删除重复订单，剩余 {len(self.df)} 条")
        else:
            self.logger.info("未发现重复订单记录")
        
        self._parse_dates()
        
        numeric_columns = ['单价', '数量', '总价']
        for col in numeric_columns:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            
        invalid_numeric = self.df[numeric_columns].isnull().sum().sum()
        if invalid_numeric > 0:
            self.logger.warning(f"发现 {invalid_numeric} 条数值字段异常记录")
            self.df = self.df.dropna(subset=numeric_columns)
            self.logger.info(f"已删除数值异常记录，剩余 {len(self.df)} 条")
        
        negative_values = (self.df[['单价', '数量', '总价']] < 0).sum().sum()
        if negative_values > 0:
            self.logger.warning(f"发现 {negative_values} 条负数值记录")
            for col in ['单价', '数量', '总价']:
                self.df = self.df[self.df[col] >= 0]
            self.logger.info(f"已删除负数值记录，剩余 {len(self.df)} 条")
        
        final_count = len(self.df)
        removed_count = initial_count - final_count
        self.logger.info(f"数据清洗完成，共删除 {removed_count} 条异常记录，保留 {final_count} 条有效记录")
        
        self.df['年份'] = self.df['订单日期'].dt.year
        self.df['月份'] = self.df['订单日期'].dt.to_period('M')
        
        self.logger.info(f"数据时间范围: {self.df['订单日期'].min().date()} 至 {self.df['订单日期'].max().date()}")

    def _parse_dates(self):
        self.logger.info("开始统一解析日期格式...")
        
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y%m%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
        ]
        
        parsed_dates = pd.Series([np.nan] * len(self.df), index=self.df.index)
        
        for date_format in date_formats:
            mask = parsed_dates.isnull()
            if mask.sum() == 0:
                break
            
            try:
                temp_dates = pd.to_datetime(
                    self.df.loc[mask, '订单日期'], 
                    format=date_format, 
                    errors='coerce'
                )
                parsed_dates.loc[mask] = temp_dates
                parsed_count = temp_dates.notnull().sum()
                if parsed_count > 0:
                    self.logger.info(f"使用格式 {date_format} 成功解析 {parsed_count} 条日期")
            except Exception as e:
                self.logger.debug(f"格式 {date_format} 解析失败: {str(e)}")
        
        parsed_count = parsed_dates.notnull().sum()
        failed_count = parsed_dates.isnull().sum()
        
        if failed_count > 0:
            self.logger.warning(f"日期解析失败 {failed_count} 条，尝试通用解析...")
            parsed_dates = pd.to_datetime(self.df['订单日期'], errors='coerce')
            final_failed = parsed_dates.isnull().sum()
            self.logger.info(f"通用解析后仍有 {final_failed} 条日期无法解析")
        else:
            self.logger.info(f"所有日期成功解析，共 {parsed_count} 条")
        
        self.df['订单日期'] = parsed_dates
        self.df = self.df.dropna(subset=['订单日期'])
        self.logger.info(f"日期解析完成，有效日期记录 {len(self.df)} 条")

    def calculate_monthly_sales(self):
        self.logger.info("开始计算月销售额...")
        
        monthly_sales = self.df.groupby('月份')['总价'].agg(['sum', 'count']).reset_index()
        monthly_sales.columns = ['月份', '销售额', '订单数']
        monthly_sales['月份'] = monthly_sales['月份'].astype(str)
        monthly_sales['环比增长率'] = monthly_sales['销售额'].pct_change() * 100
        
        self.logger.info("\n【月销售额统计】")
        self.logger.info("-" * 40)
        for _, row in monthly_sales.iterrows():
            growth_str = f"({row['环比增长率']:.1f}%)" if not pd.isna(row['环比增长率']) else ""
            self.logger.info(f"{row['月份']}: 销售额 {row['销售额']:,}元, 订单数 {row['订单数']}单 {growth_str}")
        
        self.monthly_sales = monthly_sales
        self.logger.info("月销售额计算完成")
        return monthly_sales

    def calculate_top10_products(self):
        self.logger.info("开始计算Top10热销商品...")
        
        product_sales = self.df.groupby(['商品ID', '商品名称', '商品类别']).agg({
            '总价': 'sum',
            '数量': 'sum',
            '订单ID': 'count'
        }).reset_index()
        product_sales.columns = ['商品ID', '商品名称', '商品类别', '总销售额', '总销量', '订单数']
        top10 = product_sales.sort_values('总销售额', ascending=False).head(10)
        
        self.logger.info("\n【Top10 热销商品】")
        self.logger.info("-" * 40)
        for i, (_, row) in enumerate(top10.iterrows(), 1):
            self.logger.info(f"{i}. {row['商品名称']} ({row['商品类别']})")
            self.logger.info(f"   销售额: {row['总销售额']:,}元, 销量: {row['总销量']}件, 订单数: {row['订单数']}单")
        
        self.top10_products = top10
        self.logger.info("Top10热销商品计算完成")
        return top10

    def calculate_repurchase_rate(self):
        self.logger.info("开始计算复购率...")
        
        self.df_sorted = self.df.sort_values('订单日期')
        
        user_order_counts = self.df.groupby('用户ID')['订单ID'].nunique()
        total_users = len(user_order_counts)
        
        repeat_users = user_order_counts[user_order_counts >= 2]
        repeat_user_count = len(repeat_users)
        
        if total_users > 0:
            repurchase_rate = (repeat_user_count / total_users) * 100
        else:
            repurchase_rate = 0.0
        
        self.logger.info("\n【复购率分析】")
        self.logger.info("-" * 40)
        self.logger.info(f"总用户数: {total_users}人")
        self.logger.info(f"复购用户数: {repeat_user_count}人")
        self.logger.info(f"整体复购率: {repurchase_rate:.1f}%")
        
        user_details = []
        for user_id in repeat_users.index:
            user_orders = self.df_sorted[self.df_sorted['用户ID'] == user_id]
            order_dates = user_orders['订单日期'].sort_values()
            
            first_order_date = order_dates.iloc[0]
            last_order_date = order_dates.iloc[-1]
            order_count = len(user_orders)
            total_amount = user_orders['总价'].sum()
            
            if order_count >= 2:
                intervals = []
                for i in range(1, len(order_dates)):
                    interval = (order_dates.iloc[i] - order_dates.iloc[i-1]).days
                    intervals.append(interval)
                avg_interval = np.mean(intervals) if intervals else 0
            else:
                avg_interval = 0
            
            user_details.append({
                '用户ID': user_id,
                '订单数': order_count,
                '首次购买日期': first_order_date.date(),
                '最近购买日期': last_order_date.date(),
                '平均复购间隔(天)': round(avg_interval, 1),
                '总消费金额': total_amount
            })
        
        if user_details:
            self.logger.info("\n复购用户详情:")
            for detail in sorted(user_details, key=lambda x: x['订单数'], reverse=True):
                self.logger.info(f"  {detail['用户ID']}: {detail['订单数']}单, 消费 {detail['总消费金额']:,}元, "
                              f"平均间隔 {detail['平均复购间隔(天)']}天")
        
        self.repurchase_data = {
            'total_users': total_users,
            'repeat_users': repeat_user_count,
            'repurchase_rate': repurchase_rate,
            'details': user_details
        }
        
        self.logger.info("复购率计算完成")
        return self.repurchase_data

    def calculate_churn_warning(self, days_threshold=60):
        self.logger.info(f"开始流失预警分析 (阈值: {days_threshold}天)...")
        
        latest_date = self.df['订单日期'].max()
        cutoff_date = latest_date - timedelta(days=days_threshold)
        
        user_last_purchase = self.df.groupby('用户ID')['订单日期'].max().reset_index()
        user_last_purchase.columns = ['用户ID', '最后购买日期']
        
        churn_users = user_last_purchase[user_last_purchase['最后购买日期'] < cutoff_date]
        
        self.logger.info("\n【流失预警分析】")
        self.logger.info("-" * 40)
        self.logger.info(f"统计基准日期: {latest_date.date()}")
        self.logger.info(f"流失阈值: {days_threshold}天未购买")
        self.logger.info(f"潜在流失用户数: {len(churn_users)}人")
        
        churn_details = []
        if len(churn_users) > 0:
            for _, row in churn_users.iterrows():
                user_orders = self.df[self.df['用户ID'] == row['用户ID']]
                days_since = (latest_date - row['最后购买日期']).days
                total_spent = user_orders['总价'].sum()
                order_count = len(user_orders)
                
                if days_since > 90:
                    warning_level = "高风险"
                elif days_since > 60:
                    warning_level = "中风险"
                else:
                    warning_level = "低风险"
                
                churn_details.append({
                    '用户ID': row['用户ID'],
                    '最后购买日期': row['最后购买日期'].date(),
                    '未购买天数': days_since,
                    '历史总消费': total_spent,
                    '历史订单数': order_count,
                    '风险等级': warning_level
                })
            
            self.logger.info("\n潜在流失用户详情:")
            for detail in sorted(churn_details, key=lambda x: x['未购买天数'], reverse=True):
                self.logger.info(f"  [{detail['风险等级']}] {detail['用户ID']}: "
                              f"{detail['未购买天数']}天未购买, "
                              f"历史消费 {detail['历史总消费']:,}元, "
                              f"订单数 {detail['历史订单数']}单")
        
        self.churn_data = {
            'threshold_days': days_threshold,
            'churn_user_count': len(churn_users),
            'details': churn_details
        }
        
        self.logger.info("流失预警分析完成")
        return self.churn_data

    def calculate_association_rules(self, min_support=0.01, min_confidence=0.3, min_lift=1.0):
        self.logger.info("开始商品关联规则分析...")
        
        order_products = self.df.groupby('订单ID')['商品名称'].apply(list).reset_index()
        order_products.columns = ['订单ID', '商品列表']
        
        total_orders = len(order_products)
        
        if total_orders < 2:
            self.logger.warning("订单数量不足，无法进行关联规则分析")
            self.association_rules = []
            return []
        
        def calculate_support(itemsets, transactions):
            item_counts = defaultdict(int)
            for transaction in transactions:
                transaction_set = set(transaction)
                for itemset in itemsets:
                    if set(itemset).issubset(transaction_set):
                        item_counts[itemset] += 1
            return {itemset: count / total_orders for itemset, count in item_counts.items()}
        
        transactions = order_products['商品列表'].tolist()
        
        single_items = set()
        for trans in transactions:
            for item in trans:
                single_items.add(item)
        single_items = [(item,) for item in single_items]
        
        support_1 = calculate_support(single_items, transactions)
        frequent_1 = {itemset: supp for itemset, supp in support_1.items() if supp >= min_support}
        
        rules = []
        k = 2
        current_frequent = frequent_1
        
        while current_frequent and k <= 5:
            items = list(current_frequent.keys())
            candidates = []
            
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    item1 = set(items[i])
                    item2 = set(items[j])
                    union = item1.union(item2)
                    if len(union) == k:
                        candidates.append(tuple(sorted(union)))
            
            candidates = list(set(candidates))
            
            if not candidates:
                break
            
            support_k = calculate_support(candidates, transactions)
            frequent_k = {itemset: supp for itemset, supp in support_k.items() if supp >= min_support}
            
            for itemset in frequent_k:
                for i in range(1, len(itemset)):
                    for antecedent in combinations(itemset, i):
                        antecedent = tuple(sorted(antecedent))
                        consequent = tuple(sorted(set(itemset) - set(antecedent)))
                        
                        if len(consequent) == 0:
                            continue
                        
                        supp_itemset = frequent_k[itemset]
                        
                        if len(antecedent) == 1:
                            supp_antecedent = support_1.get(antecedent, 0)
                        else:
                            supp_antecedent = current_frequent.get(antecedent, 0)
                        
                        if supp_antecedent > 0:
                            confidence = supp_itemset / supp_antecedent
                        else:
                            confidence = 0
                        
                        if len(consequent) == 1:
                            supp_consequent = support_1.get(consequent, 0)
                        else:
                            supp_consequent = current_frequent.get(consequent, 0)
                        
                        if supp_consequent > 0:
                            lift = confidence / supp_consequent
                        else:
                            lift = 0
                        
                        if confidence >= min_confidence and lift >= min_lift:
                            rules.append({
                                '前件': antecedent,
                                '后件': consequent,
                                '支持度': round(supp_itemset, 4),
                                '置信度': round(confidence, 4),
                                '提升度': round(lift, 4)
                            })
            
            current_frequent = frequent_k
            k += 1
        
        rules_sorted = sorted(rules, key=lambda x: x['提升度'], reverse=True)
        
        self.logger.info("\n【商品关联规则分析】")
        self.logger.info("-" * 40)
        self.logger.info(f"总订单数: {total_orders}")
        self.logger.info(f"发现关联规则: {len(rules_sorted)}条")
        
        if rules_sorted:
            self.logger.info("\nTop 10 关联规则 (按提升度排序):")
            for i, rule in enumerate(rules_sorted[:10], 1):
                ante = " + ".join(rule['前件'])
                cons = " + ".join(rule['后件'])
                self.logger.info(f"{i}. {ante} -> {cons}")
                self.logger.info(f"   支持度: {rule['支持度']:.1%}, 置信度: {rule['置信度']:.1%}, 提升度: {rule['提升度']:.2f}")
        else:
            self.logger.info("未发现满足条件的关联规则")
        
        self.association_rules = rules_sorted
        self.logger.info("关联规则分析完成")
        return rules_sorted

    def calculate_rfm(self):
        self.logger.info("开始用户RFM分群分析...")
        
        latest_date = self.df['订单日期'].max()
        
        rfm = self.df.groupby('用户ID').agg({
            '订单日期': lambda x: (latest_date - x.max()).days,
            '订单ID': 'nunique',
            '总价': 'sum'
        }).reset_index()
        
        rfm.columns = ['用户ID', 'R_最近购买天数', 'F_购买频率', 'M_消费金额']
        
        rfm['R_评分'] = pd.qcut(rfm['R_最近购买天数'], q=5, labels=[5, 4, 3, 2, 1], duplicates='drop').astype(int)
        rfm['F_评分'] = pd.qcut(rfm['F_购买频率'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
        rfm['M_评分'] = pd.qcut(rfm['M_消费金额'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
        
        rfm['RFM_总分'] = rfm['R_评分'] + rfm['F_评分'] + rfm['M_评分']
        
        def classify_user(row):
            r, f, m = row['R_评分'], row['F_评分'], row['M_评分']
            total = row['RFM_总分']
            
            if r >= 4 and f >= 4 and m >= 4:
                return '重要价值用户'
            elif r >= 4 and f <= 2 and m >= 4:
                return '重要发展用户'
            elif r <= 2 and f >= 4 and m >= 4:
                return '重要挽留用户'
            elif r <= 2 and f <= 2 and m >= 4:
                return '重要流失用户'
            elif r >= 4 and f >= 4 and m <= 2:
                return '一般价值用户'
            elif r >= 4 and f <= 2 and m <= 2:
                return '新用户'
            elif r <= 2 and f >= 4 and m <= 2:
                return '一般挽留用户'
            else:
                return '一般用户'
        
        rfm['用户分群'] = rfm.apply(classify_user, axis=1)
        
        group_stats = rfm.groupby('用户分群').agg({
            '用户ID': 'count',
            'R_最近购买天数': 'mean',
            'F_购买频率': 'mean',
            'M_消费金额': 'mean'
        }).round(2).reset_index()
        group_stats.columns = ['用户分群', '用户数量', '平均最近购买天数', '平均购买频率', '平均消费金额']
        group_stats = group_stats.sort_values('用户数量', ascending=False)
        
        self.logger.info("\n【用户RFM分群分析】")
        self.logger.info("-" * 40)
        self.logger.info(f"总用户数: {len(rfm)}人")
        self.logger.info(f"RFM平均得分: R={rfm['R_评分'].mean():.1f}, F={rfm['F_评分'].mean():.1f}, M={rfm['M_评分'].mean():.1f}")
        
        self.logger.info("\n用户分群统计:")
        for _, row in group_stats.iterrows():
            self.logger.info(f"  {row['用户分群']}: {row['用户数量']}人 (占比 {row['用户数量']/len(rfm)*100:.1f}%)")
            self.logger.info(f"    平均消费: {row['平均消费金额']:,}元, 平均购买: {row['平均购买频率']}次")
        
        self.logger.info("\n各分群Top用户示例:")
        for group in group_stats['用户分群'].head(3):
            group_users = rfm[rfm['用户分群'] == group].sort_values('M_消费金额', ascending=False).head(3)
            self.logger.info(f"\n  [{group}]")
            for _, user in group_users.iterrows():
                self.logger.info(f"    {user['用户ID']}: 消费 {user['M_消费金额']:,}元, 购买{user['F_购买频率']}次")
        
        self.rfm_data = {
            'rfm': rfm,
            'group_stats': group_stats
        }
        
        self.logger.info("RFM分群分析完成")
        return self.rfm_data

    def predict_sales(self, forecast_months=3):
        self.logger.info(f"开始销售额预测分析 (预测{forecast_months}个月)...")
        
        if not SKLEARN_AVAILABLE:
            self.logger.warning("scikit-learn未安装，跳过线性回归预测")
            self.prediction_data = None
            return None
        
        monthly_sales = self.df.groupby('月份')['总价'].agg(['sum', 'count']).reset_index()
        monthly_sales.columns = ['月份', '销售额', '订单数']
        monthly_sales['月份序号'] = range(1, len(monthly_sales) + 1)
        monthly_sales['月份_str'] = monthly_sales['月份'].astype(str)
        
        if len(monthly_sales) < 3:
            self.logger.warning("历史数据不足3个月，无法进行可靠预测")
            self.prediction_data = None
            return None
        
        X = monthly_sales['月份序号'].values.reshape(-1, 1)
        y_sales = monthly_sales['销售额'].values
        y_orders = monthly_sales['订单数'].values
        
        model_sales = LinearRegression()
        model_orders = LinearRegression()
        
        model_sales.fit(X, y_sales)
        model_orders.fit(X, y_orders)
        
        r2_sales = model_sales.score(X, y_sales)
        r2_orders = model_orders.score(X, y_orders)
        
        future_months = range(len(monthly_sales) + 1, len(monthly_sales) + 1 + forecast_months)
        X_future = np.array(future_months).reshape(-1, 1)
        
        pred_sales = model_sales.predict(X_future)
        pred_orders = model_orders.predict(X_future)
        
        last_month = monthly_sales['月份'].iloc[-1]
        future_month_labels = []
        current_month = last_month
        for _ in range(forecast_months):
            current_month = current_month + 1
            future_month_labels.append(str(current_month))
        
        predictions = []
        for i, (month, sales, orders) in enumerate(zip(future_month_labels, pred_sales, pred_orders)):
            predictions.append({
                '预测月份': month,
                '预测销售额': round(sales, 2),
                '预测订单数': round(orders),
                '同比增长': f"+{((sales - y_sales[-1]) / y_sales[-1] * 100):.1f}%" if sales > y_sales[-1] else f"{((sales - y_sales[-1]) / y_sales[-1] * 100):.1f}%"
            })
        
        self.logger.info("\n【销售额预测分析 (线性回归)】")
        self.logger.info("-" * 40)
        self.logger.info(f"历史数据月份: {len(monthly_sales)}个月")
        self.logger.info(f"销售额拟合R²: {r2_sales:.4f}")
        self.logger.info(f"订单数拟合R²: {r2_orders:.4f}")
        
        if r2_sales < 0.3:
            self.logger.warning("销售额趋势拟合度较低，预测结果仅供参考")
        
        self.logger.info(f"\n未来{forecast_months}个月预测:")
        for pred in predictions:
            self.logger.info(f"  {pred['预测月份']}: 销售额 {pred['预测销售额']:,}元, 订单数 {pred['预测订单数']}单 ({pred['同比增长']})")
        
        self.logger.info(f"\n增长趋势分析:")
        trend_sales = model_sales.coef_[0]
        if trend_sales > 0:
            self.logger.info(f"  销售额呈上升趋势，月均增长约 {trend_sales:,.0f}元")
        else:
            self.logger.info(f"  销售额呈下降趋势，月均减少约 {abs(trend_sales):,.0f}元")
        
        self.prediction_data = {
            'historical': monthly_sales,
            'predictions': predictions,
            'model_sales_coef': model_sales.coef_[0],
            'model_sales_intercept': model_sales.intercept_,
            'r2_sales': r2_sales,
            'r2_orders': r2_orders
        }
        
        self.logger.info("销售额预测分析完成")
        return self.prediction_data

    def generate_report(self, output_path='sales_report.txt'):
        self.logger.info("\n" + "=" * 60)
        self.logger.info("生成分析报告...")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("电商销量数据分析报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"有效数据记录数: {len(self.df)}条\n")
            f.write(f"时间范围: {self.df['订单日期'].min().date()} 至 {self.df['订单日期'].max().date()}\n\n")
            
            f.write("\n" + "-" * 60 + "\n")
            f.write("一、月销售额统计\n")
            f.write("-" * 60 + "\n")
            for _, row in self.monthly_sales.iterrows():
                growth = f" ({row['环比增长率']:.1f}%)" if not pd.isna(row['环比增长率']) else ""
                f.write(f"{row['月份']}: 销售额 {row['销售额']:,}元, 订单数 {row['订单数']}单{growth}\n")
            
            f.write("\n" + "-" * 60 + "\n")
            f.write("二、Top10 热销商品\n")
            f.write("-" * 60 + "\n")
            for i, (_, row) in enumerate(self.top10_products.iterrows(), 1):
                f.write(f"{i}. {row['商品名称']} ({row['商品类别']}) - 销售额: {row['总销售额']:,}元, 销量: {row['总销量']}件\n")
            
            f.write("\n" + "-" * 60 + "\n")
            f.write("三、复购率分析\n")
            f.write("-" * 60 + "\n")
            f.write(f"整体复购率: {self.repurchase_data['repurchase_rate']:.1f}%\n")
            f.write(f"总用户数: {self.repurchase_data['total_users']}人\n")
            f.write(f"复购用户数: {self.repurchase_data['repeat_users']}人\n")
            if self.repurchase_data['details']:
                f.write("\n复购用户列表:\n")
                for detail in self.repurchase_data['details']:
                    f.write(f"  - {detail['用户ID']}: {detail['订单数']}单, 消费 {detail['总消费金额']:,}元\n")
            
            f.write("\n" + "-" * 60 + "\n")
            f.write("四、流失预警分析\n")
            f.write("-" * 60 + "\n")
            f.write(f"流失阈值: {self.churn_data['threshold_days']}天\n")
            f.write(f"潜在流失用户数: {self.churn_data['churn_user_count']}人\n")
            if self.churn_data['details']:
                f.write("\n潜在流失用户列表:\n")
                for detail in self.churn_data['details']:
                    f.write(f"  - [{detail['风险等级']}] {detail['用户ID']}: {detail['未购买天数']}天未购买, 消费 {detail['历史总消费']:,}元\n")
            
            f.write("\n" + "-" * 60 + "\n")
            f.write("五、商品关联规则分析\n")
            f.write("-" * 60 + "\n")
            if self.association_rules:
                f.write(f"发现关联规则: {len(self.association_rules)}条\n")
                f.write("\nTop 10 关联规则:\n")
                for i, rule in enumerate(self.association_rules[:10], 1):
                    ante = " + ".join(rule['前件'])
                    cons = " + ".join(rule['后件'])
                    f.write(f"{i}. {ante} -> {cons}\n")
                    f.write(f"   支持度: {rule['支持度']:.1%}, 置信度: {rule['置信度']:.1%}, 提升度: {rule['提升度']:.2f}\n")
            else:
                f.write("未发现满足条件的关联规则\n")
            
            f.write("\n" + "-" * 60 + "\n")
            f.write("六、用户RFM分群分析\n")
            f.write("-" * 60 + "\n")
            if hasattr(self, 'rfm_data') and self.rfm_data:
                f.write(f"总用户数: {len(self.rfm_data['rfm'])}人\n")
                f.write("\n用户分群统计:\n")
                for _, row in self.rfm_data['group_stats'].iterrows():
                    f.write(f"  {row['用户分群']}: {row['用户数量']}人 (占比 {row['用户数量']/len(self.rfm_data['rfm'])*100:.1f}%)\n")
            else:
                f.write("RFM分群分析未执行\n")
            
            f.write("\n" + "-" * 60 + "\n")
            f.write("七、销售额预测分析\n")
            f.write("-" * 60 + "\n")
            if hasattr(self, 'prediction_data') and self.prediction_data:
                f.write(f"销售额拟合R²: {self.prediction_data['r2_sales']:.4f}\n")
                f.write("\n未来月份预测:\n")
                for pred in self.prediction_data['predictions']:
                    f.write(f"  {pred['预测月份']}: 销售额 {pred['预测销售额']:,}元, 订单数 {pred['预测订单数']}单 ({pred['同比增长']})\n")
            else:
                f.write("销售额预测分析未执行或数据不足\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("数据清洗日志:\n")
            f.write("=" * 60 + "\n")
            f.write(f"原始数据量: {len(self.raw_df)}条\n")
            f.write(f"清洗后数据量: {len(self.df)}条\n")
            f.write(f"删除异常记录: {len(self.raw_df) - len(self.df)}条\n")
        
        self.logger.info(f"报告已保存至: {output_path}")
        self.logger.info("日志文件已保存至 logs/ 目录")

    def run_full_analysis(self):
        self.logger.info("\n" + "=" * 60)
        self.logger.info("开始执行完整数据分析流程")
        self.logger.info("=" * 60 + "\n")
        
        self.calculate_monthly_sales()
        self.calculate_top10_products()
        self.calculate_repurchase_rate()
        self.calculate_churn_warning()
        self.calculate_association_rules()
        self.calculate_rfm()
        self.predict_sales()
        self.generate_report()
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("数据分析流程全部完成！")
        self.logger.info("=" * 60)


if __name__ == "__main__":
    try:
        analyzer = SalesAnalyzer('sales_data.csv')
        analyzer.run_full_analysis()
    except Exception as e:
        logging.error(f"程序执行出错: {str(e)}", exc_info=True)
        raise

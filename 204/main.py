from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import Optional
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import json
import os

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib

from database import get_db, engine, Base
from models import Order, Subscription

Base.metadata.create_all(bind=engine)

app = FastAPI(title="销售数据可视化仪表板")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

scheduler = BackgroundScheduler()

def get_smtp_config():
    return {
        'host': os.getenv('SMTP_HOST', 'smtp.qq.com'),
        'port': int(os.getenv('SMTP_PORT', '465')),
        'user': os.getenv('SMTP_USER', ''),
        'password': os.getenv('SMTP_PASSWORD', ''),
        'from': os.getenv('SMTP_FROM', '')
    }

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

def parse_date(date_str: Optional[str]) -> Optional[datetime.date]:
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()

@app.get("/api/summary")
def get_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    start = parse_date(start_date)
    end = parse_date(end_date)
    cat = category if category and category != "全部" else None
    
    filters = []
    if start:
        filters.append(Order.order_date >= start)
    if end:
        filters.append(Order.order_date <= end)
    if cat:
        filters.append(Order.category == cat)
    
    result = db.query(
        func.sum(Order.total_amount).label("total_sales"),
        func.count(Order.id).label("total_orders"),
        func.count(func.distinct(Order.customer_id)).label("unique_customers")
    )
    
    if filters:
        result = result.filter(and_(*filters))
    
    result = result.first()
    
    total_sales = result.total_sales or 0
    total_orders = result.total_orders or 0
    unique_customers = result.unique_customers or 0
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    daily_growth_rate = 0
    period_growth_rate = 0
    today_sales = 0
    yesterday_sales = 0
    
    if start and end:
        period_days = (end - start).days + 1
        prev_start = start - timedelta(days=period_days)
        prev_end = start - timedelta(days=1)
        
        prev_filters = [
            Order.order_date >= prev_start,
            Order.order_date <= prev_end
        ]
        if cat:
            prev_filters.append(Order.category == cat)
        
        prev_result = db.query(
            func.sum(Order.total_amount).label("prev_sales")
        ).filter(and_(*prev_filters)).first()
        
        prev_sales = prev_result.prev_sales or 0
        if prev_sales > 0:
            period_growth_rate = ((total_sales - prev_sales) / prev_sales) * 100
        elif total_sales > 0:
            period_growth_rate = 100
    
    latest_date = db.query(func.max(Order.order_date)).scalar()
    if latest_date:
        yesterday = latest_date - timedelta(days=1)
        
        today_filters = [Order.order_date == latest_date]
        if cat:
            today_filters.append(Order.category == cat)
        
        today_result = db.query(
            func.sum(Order.total_amount).label("sales")
        ).filter(and_(*today_filters)).first()
        today_sales = today_result.sales or 0
        
        yesterday_filters = [Order.order_date == yesterday]
        if cat:
            yesterday_filters.append(Order.category == cat)
        
        yesterday_result = db.query(
            func.sum(Order.total_amount).label("sales")
        ).filter(and_(*yesterday_filters)).first()
        yesterday_sales = yesterday_result.sales or 0
        
        if yesterday_sales > 0:
            daily_growth_rate = ((today_sales - yesterday_sales) / yesterday_sales) * 100
        elif today_sales > 0:
            daily_growth_rate = 100
    
    return {
        "total_sales": round(total_sales, 2),
        "total_orders": total_orders,
        "avg_order_value": round(avg_order_value, 2),
        "unique_customers": unique_customers,
        "daily_growth_rate": round(daily_growth_rate, 2),
        "period_growth_rate": round(period_growth_rate, 2),
        "today_sales": round(today_sales, 2),
        "yesterday_sales": round(yesterday_sales, 2)
    }

@app.get("/api/daily-sales")
def get_daily_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    start = parse_date(start_date)
    end = parse_date(end_date)
    cat = category if category and category != "全部" else None
    
    filters = []
    if start:
        filters.append(Order.order_date >= start)
    if end:
        filters.append(Order.order_date <= end)
    if cat:
        filters.append(Order.category == cat)
    
    query = db.query(
        Order.order_date,
        func.sum(Order.total_amount).label("sales"),
        func.count(Order.id).label("orders")
    )
    
    if filters:
        query = query.filter(and_(*filters))
    
    results = query.group_by(Order.order_date).order_by(Order.order_date).all()
    
    return {
        "dates": [str(r.order_date) for r in results],
        "sales": [round(r.sales, 2) for r in results],
        "orders": [r.orders for r in results]
    }

@app.get("/api/category-sales")
def get_category_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    start = parse_date(start_date)
    end = parse_date(end_date)
    cat = category if category and category != "全部" else None
    
    filters = []
    if start:
        filters.append(Order.order_date >= start)
    if end:
        filters.append(Order.order_date <= end)
    if cat:
        filters.append(Order.category == cat)
    
    query = db.query(
        Order.category,
        func.sum(Order.total_amount).label("sales"),
        func.count(Order.id).label("orders")
    )
    
    if filters:
        query = query.filter(and_(*filters))
    
    results = query.group_by(Order.category).order_by(func.sum(Order.total_amount).desc()).all()
    
    return {
        "categories": [r.category for r in results],
        "sales": [round(r.sales, 2) for r in results],
        "orders": [r.orders for r in results]
    }

@app.get("/api/region-sales")
def get_region_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    start = parse_date(start_date)
    end = parse_date(end_date)
    cat = category if category and category != "全部" else None
    
    filters = []
    if start:
        filters.append(Order.order_date >= start)
    if end:
        filters.append(Order.order_date <= end)
    if cat:
        filters.append(Order.category == cat)
    
    query = db.query(
        Order.region,
        func.sum(Order.total_amount).label("sales"),
        func.count(Order.id).label("orders")
    )
    
    if filters:
        query = query.filter(and_(*filters))
    
    results = query.group_by(Order.region).order_by(func.sum(Order.total_amount).desc()).all()
    
    return {
        "regions": [r.region for r in results],
        "sales": [round(r.sales, 2) for r in results],
        "orders": [r.orders for r in results]
    }

@app.get("/api/yearly-comparison")
def get_yearly_comparison(
    year: Optional[int] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if year is None:
        year = datetime.now().year
    
    cat = category if category and category != "全部" else None
    
    current_year_data = db.query(
        extract('month', Order.order_date).label('month'),
        func.sum(Order.total_amount).label('sales'),
        func.count(Order.id).label('orders')
    ).filter(
        extract('year', Order.order_date) == year
    )
    
    if cat:
        current_year_data = current_year_data.filter(Order.category == cat)
    
    current_year_data = current_year_data.group_by(
        extract('month', Order.order_date)
    ).order_by('month').all()
    
    last_year_data = db.query(
        extract('month', Order.order_date).label('month'),
        func.sum(Order.total_amount).label('sales'),
        func.count(Order.id).label('orders')
    ).filter(
        extract('year', Order.order_date) == year - 1
    )
    
    if cat:
        last_year_data = last_year_data.filter(Order.category == cat)
    
    last_year_data = last_year_data.group_by(
        extract('month', Order.order_date)
    ).order_by('month').all()
    
    current_dict = {int(r.month): {'sales': r.sales, 'orders': r.orders} for r in current_year_data}
    last_dict = {int(r.month): {'sales': r.sales, 'orders': r.orders} for r in last_year_data}
    
    months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    current_sales = []
    last_sales = []
    growth_rates = []
    
    for month in range(1, 13):
        curr = current_dict.get(month, {'sales': 0, 'orders': 0})
        last = last_dict.get(month, {'sales': 0, 'orders': 0})
        
        curr_sales = curr['sales'] or 0
        last_sales_val = last['sales'] or 0
        
        current_sales.append(round(curr_sales, 2))
        last_sales.append(round(last_sales_val, 2))
        
        if last_sales_val > 0:
            growth = ((curr_sales - last_sales_val) / last_sales_val) * 100
        elif curr_sales > 0:
            growth = 100
        else:
            growth = 0
        growth_rates.append(round(growth, 2))
    
    return {
        "year": year,
        "months": months,
        "current_year_sales": current_sales,
        "last_year_sales": last_sales,
        "growth_rates": growth_rates
    }

@app.get("/api/all-data")
def get_all_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    start = parse_date(start_date)
    end = parse_date(end_date)
    cat = category if category and category != "全部" else None
    
    filters = []
    if start:
        filters.append(Order.order_date >= start)
    if end:
        filters.append(Order.order_date <= end)
    if cat:
        filters.append(Order.category == cat)
    
    filter_condition = and_(*filters) if filters else True
    
    summary = db.query(
        func.sum(Order.total_amount).label("total_sales"),
        func.count(Order.id).label("total_orders"),
        func.count(func.distinct(Order.customer_id)).label("unique_customers")
    ).filter(filter_condition).first()
    
    total_sales = summary.total_sales or 0
    total_orders = summary.total_orders or 0
    unique_customers = summary.unique_customers or 0
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    period_growth_rate = 0
    if start and end:
        period_days = (end - start).days + 1
        prev_start = start - timedelta(days=period_days)
        prev_end = start - timedelta(days=1)
        
        prev_filters = [
            Order.order_date >= prev_start,
            Order.order_date <= prev_end
        ]
        if cat:
            prev_filters.append(Order.category == cat)
        
        prev_sales = db.query(
            func.sum(Order.total_amount).label("prev_sales")
        ).filter(and_(*prev_filters)).scalar() or 0
        
        if prev_sales > 0:
            period_growth_rate = ((total_sales - prev_sales) / prev_sales) * 100
        elif total_sales > 0:
            period_growth_rate = 100
    
    daily_growth_rate = 0
    latest_date = db.query(func.max(Order.order_date)).scalar()
    if latest_date:
        yesterday = latest_date - timedelta(days=1)
        
        today_filters = [Order.order_date == latest_date]
        if cat:
            today_filters.append(Order.category == cat)
        today_sales = db.query(func.sum(Order.total_amount)).filter(and_(*today_filters)).scalar() or 0
        
        yesterday_filters = [Order.order_date == yesterday]
        if cat:
            yesterday_filters.append(Order.category == cat)
        yesterday_sales = db.query(func.sum(Order.total_amount)).filter(and_(*yesterday_filters)).scalar() or 0
        
        if yesterday_sales > 0:
            daily_growth_rate = ((today_sales - yesterday_sales) / yesterday_sales) * 100
        elif today_sales > 0:
            daily_growth_rate = 100
    
    daily_results = db.query(
        Order.order_date,
        func.sum(Order.total_amount).label("sales"),
        func.count(Order.id).label("orders")
    ).filter(filter_condition).group_by(Order.order_date).order_by(Order.order_date).all()
    
    category_filters = []
    if start:
        category_filters.append(Order.order_date >= start)
    if end:
        category_filters.append(Order.order_date <= end)
    category_condition = and_(*category_filters) if category_filters else True
    
    category_results = db.query(
        Order.category,
        func.sum(Order.total_amount).label("sales"),
        func.count(Order.id).label("orders")
    ).filter(category_condition).group_by(Order.category).order_by(func.sum(Order.total_amount).desc()).all()
    
    region_results = db.query(
        Order.region,
        func.sum(Order.total_amount).label("sales"),
        func.count(Order.id).label("orders")
    ).filter(filter_condition).group_by(Order.region).order_by(func.sum(Order.total_amount).desc()).all()
    
    return {
        "summary": {
            "total_sales": round(total_sales, 2),
            "total_orders": total_orders,
            "avg_order_value": round(avg_order_value, 2),
            "unique_customers": unique_customers,
            "daily_growth_rate": round(daily_growth_rate, 2),
            "period_growth_rate": round(period_growth_rate, 2)
        },
        "daily_sales": {
            "dates": [str(r.order_date) for r in daily_results],
            "sales": [round(r.sales, 2) for r in daily_results],
            "orders": [r.orders for r in daily_results]
        },
        "category_sales": {
            "categories": [r.category for r in category_results],
            "sales": [round(r.sales, 2) for r in category_results],
            "orders": [r.orders for r in category_results]
        },
        "region_sales": {
            "regions": [r.region for r in region_results],
            "sales": [round(r.sales, 2) for r in region_results],
            "orders": [r.orders for r in region_results]
        }
    }

@app.get("/api/export/excel")
def export_excel(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    start = parse_date(start_date)
    end = parse_date(end_date)
    cat = category if category and category != "全部" else None
    
    filters = []
    if start:
        filters.append(Order.order_date >= start)
    if end:
        filters.append(Order.order_date <= end)
    if cat:
        filters.append(Order.category == cat)
    
    query = db.query(
        Order.order_id,
        Order.order_date,
        Order.category,
        Order.region,
        Order.product_name,
        Order.quantity,
        Order.unit_price,
        Order.total_amount,
        Order.customer_id
    )
    
    if filters:
        query = query.filter(and_(*filters))
    
    results = query.all()
    
    df = pd.DataFrame(results, columns=[
        '订单编号', '订单日期', '品类', '区域', '商品名称', '数量', '单价', '总金额', '客户ID'
    ])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='订单明细')
        
        summary_df = pd.DataFrame([{
            '总销售额': df['总金额'].sum(),
            '订单数': len(df),
            '客单价': df['总金额'].mean()
        }])
        summary_df.to_excel(writer, index=False, sheet_name='统计汇总')
    
    output.seek(0)
    
    filename = f"销售数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/export/csv")
def export_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    start = parse_date(start_date)
    end = parse_date(end_date)
    cat = category if category and category != "全部" else None
    
    filters = []
    if start:
        filters.append(Order.order_date >= start)
    if end:
        filters.append(Order.order_date <= end)
    if cat:
        filters.append(Order.category == cat)
    
    query = db.query(
        Order.order_id,
        Order.order_date,
        Order.category,
        Order.region,
        Order.product_name,
        Order.quantity,
        Order.unit_price,
        Order.total_amount,
        Order.customer_id
    )
    
    if filters:
        query = query.filter(and_(*filters))
    
    results = query.all()
    
    df = pd.DataFrame(results, columns=[
        '订单编号', '订单日期', '品类', '区域', '商品名称', '数量', '单价', '总金额', '客户ID'
    ])
    
    output = StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    filename = f"销售数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/subscriptions")
def get_subscriptions(db: Session = Depends(get_db)):
    subscriptions = db.query(Subscription).all()
    return {
        "subscriptions": [
            {
                "id": sub.id,
                "email": sub.email,
                "frequency": sub.frequency,
                "is_active": sub.is_active,
                "filters": sub.filters,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
                "last_sent": sub.last_sent.isoformat() if sub.last_sent else None
            }
            for sub in subscriptions
        ]
    }

@app.post("/api/subscriptions")
def create_subscription(
    email: str,
    frequency: str = Query(..., regex="^(daily|weekly)$"),
    filters: Optional[str] = None,
    db: Session = Depends(get_db)
):
    subscription = Subscription(
        email=email,
        frequency=frequency,
        is_active=True,
        filters=filters or "{}"
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return {"message": "订阅创建成功", "id": subscription.id}

@app.delete("/api/subscriptions/{subscription_id}")
def delete_subscription(subscription_id: int, db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    db.delete(subscription)
    db.commit()
    return {"message": "订阅已删除"}

@app.put("/api/subscriptions/{subscription_id}/toggle")
def toggle_subscription(subscription_id: int, db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    subscription.is_active = not subscription.is_active
    db.commit()
    return {"message": f"订阅已{'激活' if subscription.is_active else '停用'}", "is_active": subscription.is_active}

def send_report_email(email: str, report_data: dict):
    smtp_config = get_smtp_config()
    
    if not smtp_config['user'] or not smtp_config['password']:
        print("邮件配置未设置，跳过发送")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = smtp_config['from']
    msg['To'] = email
    msg['Subject'] = f"销售数据日报 - {datetime.now().strftime('%Y-%m-%d')}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #667eea;">📊 销售数据日报</h2>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
            <tr style="background: #667eea; color: white;">
                <th style="padding: 12px; text-align: left;">指标</th>
                <th style="padding: 12px; text-align: left;">数值</th>
            </tr>
            <tr style="background: #f8f9fa;">
                <td style="padding: 12px; border: 1px solid #ddd;">总销售额</td>
                <td style="padding: 12px; border: 1px solid #ddd;">¥{report_data['total_sales']:,.2f}</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">订单数</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{report_data['total_orders']:,}</td>
            </tr>
            <tr style="background: #f8f9fa;">
                <td style="padding: 12px; border: 1px solid #ddd;">客单价</td>
                <td style="padding: 12px; border: 1px solid #ddd;">¥{report_data['avg_order_value']:,.2f}</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">日环比</td>
                <td style="padding: 12px; border: 1px solid #ddd; color: {'green' if report_data['daily_growth_rate'] >= 0 else 'red'};">
                    {report_data['daily_growth_rate']:+.2f}%
                </td>
            </tr>
        </table>
        
        <p style="color: #666; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        with smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port']) as server:
            server.login(smtp_config['user'], smtp_config['password'])
            server.send_message(msg)
        print(f"邮件已发送至: {email}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

def process_subscriptions():
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        today = datetime.now().date()
        subscriptions = db.query(Subscription).filter(Subscription.is_active == True).all()
        
        for sub in subscriptions:
            should_send = False
            
            if sub.frequency == 'daily':
                should_send = True
            elif sub.frequency == 'weekly':
                should_send = today.weekday() == 0
            
            if should_send:
                latest_date = db.query(func.max(Order.order_date)).scalar()
                if latest_date:
                    start_date = latest_date - timedelta(days=30)
                    
                    result = db.query(
                        func.sum(Order.total_amount).label("total_sales"),
                        func.count(Order.id).label("total_orders")
                    ).filter(Order.order_date >= start_date).first()
                    
                    total_sales = result.total_sales or 0
                    total_orders = result.total_orders or 0
                    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
                    
                    yesterday = latest_date - timedelta(days=1)
                    today_sales = db.query(func.sum(Order.total_amount)).filter(Order.order_date == latest_date).scalar() or 0
                    yesterday_sales = db.query(func.sum(Order.total_amount)).filter(Order.order_date == yesterday).scalar() or 0
                    
                    daily_growth_rate = 0
                    if yesterday_sales > 0:
                        daily_growth_rate = ((today_sales - yesterday_sales) / yesterday_sales) * 100
                    
                    report_data = {
                        'total_sales': total_sales,
                        'total_orders': total_orders,
                        'avg_order_value': avg_order_value,
                        'daily_growth_rate': daily_growth_rate
                    }
                    
                    if send_report_email(sub.email, report_data):
                        sub.last_sent = datetime.now()
                        db.commit()
    
    except Exception as e:
        print(f"处理订阅失败: {e}")
    finally:
        db.close()

@app.get("/api/categories")
def get_categories(db: Session = Depends(get_db)):
    results = db.query(Order.category).distinct().all()
    return {"categories": ["全部"] + [r.category for r in results]}

@app.on_event("startup")
def startup_event():
    scheduler.add_job(process_subscriptions, 'cron', hour=9, minute=0)
    scheduler.start()
    print("定时任务已启动")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("定时任务已关闭")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

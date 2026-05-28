"""
数据模型定义
"""
from datetime import datetime
from loguru import logger

from database.mongo import get_collection


class BaseModel:
    collection_name = ''

    @classmethod
    def get_collection(cls):
        return get_collection(cls.collection_name)

    @classmethod
    def create_indexes(cls):
        raise NotImplementedError


class Product(BaseModel):
    collection_name = 'products'

    @classmethod
    def create_indexes(cls):
        col = cls.get_collection()
        col.create_index([('product_id', 1)], unique=True)
        col.create_index([('source', 1)])
        col.create_index([('category', 1)])
        col.create_index([('brand', 1)])
        col.create_index([('updated_at', -1)])

    @classmethod
    def upsert(cls, product_data):
        col = cls.get_collection()
        product_data['updated_at'] = datetime.utcnow()
        if 'created_at' not in product_data:
            product_data['created_at'] = datetime.utcnow()
        result = col.update_one(
            {'product_id': product_data['product_id']},
            {'$set': product_data, '$setOnInsert': {'created_at': product_data['created_at']}},
            upsert=True,
        )
        return result

    @classmethod
    def get_by_id(cls, product_id):
        return cls.get_collection().find_one({'product_id': product_id})

    @classmethod
    def get_all(cls, source=None, category=None, page=1, page_size=20):
        col = cls.get_collection()
        query = {}
        if source:
            query['source'] = source
        if category:
            query['category'] = category
        skip = (page - 1) * page_size
        cursor = col.find(query).sort('updated_at', -1).skip(skip).limit(page_size)
        total = col.count_documents(query)
        return list(cursor), total


class PriceHistory(BaseModel):
    collection_name = 'price_history'

    @classmethod
    def create_indexes(cls):
        col = cls.get_collection()
        col.create_index([('product_id', 1), ('timestamp', -1)])
        col.create_index([('source', 1)])
        col.create_index([('timestamp', -1)])

    @classmethod
    def insert(cls, price_data):
        price_data['timestamp'] = datetime.utcnow()
        return cls.get_collection().insert_one(price_data)

    @classmethod
    def get_history(cls, product_id, start_date=None, end_date=None):
        query = {'product_id': product_id}
        if start_date:
            query['timestamp'] = query.get('timestamp', {})
            query['timestamp']['$gte'] = start_date
        if end_date:
            query['timestamp'] = query.get('timestamp', {})
            query['timestamp']['$lte'] = end_date
        return list(cls.get_collection().find(query).sort('timestamp', 1))

    @classmethod
    def get_latest(cls, product_id):
        return cls.get_collection().find_one(
            {'product_id': product_id}, sort=[('timestamp', -1)]
        )

    @classmethod
    def get_price_at_date(cls, product_id, target_date, tolerance_hours=12):
        from datetime import timedelta

        tolerance = timedelta(hours=tolerance_hours)
        start_range = target_date - tolerance
        end_range = target_date + tolerance

        col = cls.get_collection()

        exact_match = col.find_one({
            'product_id': product_id,
            'timestamp': {
                '$gte': start_range,
                '$lte': end_range,
            },
        }, sort=[('timestamp', 1)])

        if exact_match:
            return exact_match

        before_match = col.find_one({
            'product_id': product_id,
            'timestamp': {'$lt': start_range},
        }, sort=[('timestamp', -1)])

        after_match = col.find_one({
            'product_id': product_id,
            'timestamp': {'$gt': end_range},
        }, sort=[('timestamp', 1)])

        candidates = []
        if before_match:
            diff = abs((before_match['timestamp'] - target_date).total_seconds())
            candidates.append((diff, before_match))
        if after_match:
            diff = abs((after_match['timestamp'] - target_date).total_seconds())
            candidates.append((diff, after_match))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        return None


class Alert(BaseModel):
    collection_name = 'alerts'

    @classmethod
    def create_indexes(cls):
        col = cls.get_collection()
        col.create_index([('alert_type', 1)])
        col.create_index([('product_id', 1)])
        col.create_index([('created_at', -1)])
        col.create_index([('status', 1)])

    @classmethod
    def insert(cls, alert_data):
        alert_data['created_at'] = datetime.utcnow()
        alert_data['status'] = alert_data.get('status', 'unread')
        return cls.get_collection().insert_one(alert_data)

    @classmethod
    def get_alerts(cls, alert_type=None, status=None, page=1, page_size=20):
        query = {}
        if alert_type:
            query['alert_type'] = alert_type
        if status:
            query['status'] = status
        skip = (page - 1) * page_size
        cursor = cls.get_collection().find(query).sort('created_at', -1).skip(skip).limit(page_size)
        total = cls.get_collection().count_documents(query)
        return list(cursor), total

    @classmethod
    def mark_as_read(cls, alert_id):
        return cls.get_collection().update_one(
            {'_id': alert_id},
            {'$set': {'status': 'read'}},
        )


class Promotion(BaseModel):
    collection_name = 'promotions'

    @classmethod
    def create_indexes(cls):
        col = cls.get_collection()
        col.create_index([('product_id', 1)])
        col.create_index([('source', 1)])
        col.create_index([('start_date', -1)])
        col.create_index([('active', 1)])

    @classmethod
    def upsert(cls, promo_data):
        promo_data['updated_at'] = datetime.utcnow()
        if 'created_at' not in promo_data:
            promo_data['created_at'] = datetime.utcnow()
        return cls.get_collection().update_one(
            {
                'product_id': promo_data['product_id'],
                'promo_type': promo_data.get('promo_type', ''),
            },
            {'$set': promo_data, '$setOnInsert': {'created_at': promo_data['created_at']}},
            upsert=True,
        )

    @classmethod
    def get_active(cls, source=None):
        query = {'active': True}
        if source:
            query['source'] = source
        return list(cls.get_collection().find(query).sort('start_date', -1))


def init_database():
    Product.create_indexes()
    PriceHistory.create_indexes()
    Alert.create_indexes()
    Promotion.create_indexes()
    PricePrediction.create_indexes()
    CrossPromotion.create_indexes()
    ComplianceCheck.create_indexes()
    logger.info("数据库索引创建完成")


class PricePrediction(BaseModel):
    collection_name = 'price_predictions'

    @classmethod
    def create_indexes(cls):
        col = cls.get_collection()
        col.create_index([('product_id', 1), ('created_at', -1)], unique=True)
        col.create_index([('product_id', 1)])
        col.create_index([('created_at', -1)])
        col.create_index([('alert_level', 1)])

    @classmethod
    def insert(cls, prediction_data):
        prediction_data['created_at'] = datetime.utcnow()
        return cls.get_collection().insert_one(prediction_data)

    @classmethod
    def get_latest(cls, product_id):
        return cls.get_collection().find_one(
            {'product_id': product_id}, sort=[('created_at', -1)]
        )

    @classmethod
    def get_by_alert_level(cls, alert_level, page=1, page_size=20):
        query = {'alert_level': alert_level}
        skip = (page - 1) * page_size
        cursor = cls.get_collection().find(query).sort('created_at', -1).skip(skip).limit(page_size)
        total = cls.get_collection().count_documents(query)
        return list(cursor), total


class CrossPromotion(BaseModel):
    collection_name = 'cross_promotions'

    @classmethod
    def create_indexes(cls):
        col = cls.get_collection()
        col.create_index([('trigger_product', 1), ('promo_type', 1), ('created_at', -1)], unique=True)
        col.create_index([('trigger_product', 1)])
        col.create_index([('promo_type', 1)])
        col.create_index([('created_at', -1)])

    @classmethod
    def insert(cls, promo_data):
        promo_data['created_at'] = datetime.utcnow()
        return cls.get_collection().insert_one(promo_data)

    @classmethod
    def get_by_product(cls, product_id):
        return list(cls.get_collection().find({
            '$or': [
                {'trigger_product': product_id},
                {'related_product_id': product_id},
            ]
        }).sort('created_at', -1))

    @classmethod
    def get_active(cls, page=1, page_size=20):
        skip = (page - 1) * page_size
        cursor = cls.get_collection().find({}).sort('created_at', -1).skip(skip).limit(page_size)
        total = cls.get_collection().count_documents({})
        return list(cursor), total


class ComplianceCheck(BaseModel):
    collection_name = 'compliance_checks'

    @classmethod
    def create_indexes(cls):
        col = cls.get_collection()
        col.create_index([('product_id', 1), ('created_at', -1)], unique=True)
        col.create_index([('product_id', 1)])
        col.create_index([('compliance_level', 1)])
        col.create_index([('created_at', -1)])

    @classmethod
    def insert(cls, check_data):
        check_data['created_at'] = datetime.utcnow()
        return cls.get_collection().insert_one(check_data)

    @classmethod
    def get_latest(cls, product_id):
        return cls.get_collection().find_one(
            {'product_id': product_id}, sort=[('created_at', -1)]
        )

    @classmethod
    def get_by_risk_level(cls, risk_level, page=1, page_size=20):
        query = {'compliance_level': risk_level}
        skip = (page - 1) * page_size
        cursor = cls.get_collection().find(query).sort('created_at', -1).skip(skip).limit(page_size)
        total = cls.get_collection().count_documents(query)
        return list(cursor), total
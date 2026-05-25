import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self):
        self.data: Dict[str, pd.DataFrame] = {}

    def load_sales_data(self, file_path: Union[str, Path]) -> pd.DataFrame:
        logger.info(f"Loading sales data from {file_path}")
        df = pd.read_csv(file_path) if str(file_path).endswith('.csv') else pd.read_excel(file_path)
        df['date'] = pd.to_datetime(df['date'])
        self.data['sales'] = df
        return df

    def load_inventory_data(self, file_path: Union[str, Path]) -> pd.DataFrame:
        logger.info(f"Loading inventory data from {file_path}")
        df = pd.read_csv(file_path) if str(file_path).endswith('.csv') else pd.read_excel(file_path)
        df['date'] = pd.to_datetime(df['date'])
        self.data['inventory'] = df
        return df

    def load_promotion_data(self, file_path: Union[str, Path]) -> pd.DataFrame:
        logger.info(f"Loading promotion data from {file_path}")
        df = pd.read_csv(file_path) if str(file_path).endswith('.csv') else pd.read_excel(file_path)
        df['start_date'] = pd.to_datetime(df['start_date'])
        df['end_date'] = pd.to_datetime(df['end_date'])
        self.data['promotion'] = df
        return df

    def load_supplier_data(self, file_path: Union[str, Path]) -> pd.DataFrame:
        logger.info(f"Loading supplier data from {file_path}")
        df = pd.read_csv(file_path) if str(file_path).endswith('.csv') else pd.read_excel(file_path)
        self.data['supplier'] = df
        return df

    def load_product_data(self, file_path: Union[str, Path]) -> pd.DataFrame:
        logger.info(f"Loading product data from {file_path}")
        df = pd.read_csv(file_path) if str(file_path).endswith('.csv') else pd.read_excel(file_path)
        self.data['product'] = df
        return df

    def load_all(self, data_dir: Union[str, Path]) -> Dict[str, pd.DataFrame]:
        data_path = Path(data_dir)
        files = {
            'sales': 'sales.csv',
            'inventory': 'inventory.csv',
            'promotion': 'promotion.csv',
            'supplier': 'supplier.csv',
            'product': 'product.csv'
        }

        for data_type, filename in files.items():
            file_path = data_path / filename
            if file_path.exists():
                load_method = getattr(self, f'load_{data_type}_data')
                load_method(file_path)
            else:
                logger.warning(f"{data_type} data file not found: {file_path}")

        return self.data

    def get_data(self, data_type: str) -> Optional[pd.DataFrame]:
        return self.data.get(data_type)

    def validate_data(self) -> bool:
        required_columns = {
            'sales': ['date', 'product_id', 'region', 'warehouse', 'quantity'],
            'inventory': ['date', 'product_id', 'warehouse', 'stock_quantity'],
            'promotion': ['product_id', 'start_date', 'end_date', 'promotion_type', 'discount'],
            'supplier': ['product_id', 'supplier_name', 'lead_time_days', 'min_order_qty'],
            'product': ['product_id', 'product_name', 'category', 'launch_date']
        }

        for data_type, columns in required_columns.items():
            if data_type in self.data:
                df = self.data[data_type]
                missing_cols = [col for col in columns if col not in df.columns]
                if missing_cols:
                    logger.error(f"Missing columns in {data_type} data: {missing_cols}")
                    return False

        logger.info("Data validation passed")
        return True

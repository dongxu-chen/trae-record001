import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Union
import logging
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

try:
    import tableauserverclient as TSC
    TABLEAU_AVAILABLE = True
except ImportError:
    TABLEAU_AVAILABLE = False

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TableauIntegration:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or Config().config
        self.tableau_config = self.config.get('tableau', {})

        self.server_url = self.tableau_config.get('server_url', '')
        self.site_id = self.tableau_config.get('site_id', '')
        self.project_name = self.tableau_config.get('project_name', 'Supply Chain Forecasting')
        self.datasource_name = self.tableau_config.get('datasource_name', 'Demand Forecast')

        self.server = None
        self.auth = None
        self.connected = False

        if not TABLEAU_AVAILABLE:
            logger.warning("Tableau Server Client not installed. Running in offline mode.")

    def connect(self, username: str = None, password: str = None,
                token_name: str = None, token_value: str = None) -> bool:
        if not TABLEAU_AVAILABLE:
            logger.warning("Tableau Server Client not available. Cannot connect.")
            return False

        try:
            if token_name and token_value:
                self.auth = TSC.PersonalAccessTokenAuth(token_name, token_value, self.site_id)
            elif username and password:
                self.auth = TSC.TableauAuth(username, password, self.site_id)
            else:
                logger.error("No authentication credentials provided")
                return False

            self.server = TSC.Server(self.server_url, use_server_version=True)
            self.server.auth.sign_in(self.auth)
            self.connected = True
            logger.info("Successfully connected to Tableau Server")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Tableau Server: {e}")
            return False

    def disconnect(self):
        if self.connected and self.server:
            try:
                self.server.auth.sign_out()
                self.connected = False
                logger.info("Disconnected from Tableau Server")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")

    def prepare_forecast_data(self, forecast_df: pd.DataFrame,
                               actual_df: pd.DataFrame = None) -> pd.DataFrame:
        logger.info("Preparing forecast data for Tableau...")

        tableau_df = forecast_df.copy()
        tableau_df['date'] = pd.to_datetime(tableau_df['date'])

        if 'product_id' not in tableau_df.columns:
            tableau_df['product_id'] = 'ALL'
        if 'region' not in tableau_df.columns:
            tableau_df['region'] = 'ALL'
        if 'warehouse' not in tableau_df.columns:
            tableau_df['warehouse'] = 'ALL'
        if 'level' not in tableau_df.columns:
            tableau_df['level'] = 'product'

        tableau_df['forecast'] = tableau_df['forecast'].round(2)
        tableau_df['forecast_lower'] = tableau_df.get('forecast_lower', tableau_df['forecast'] * 0.8).round(2)
        tableau_df['forecast_upper'] = tableau_df.get('forecast_upper', tableau_df['forecast'] * 1.2).round(2)

        if 'prophet_forecast' in tableau_df.columns:
            tableau_df['prophet_forecast'] = tableau_df['prophet_forecast'].round(2)
        if 'lgbm_forecast' in tableau_df.columns:
            tableau_df['lgbm_forecast'] = tableau_df['lgbm_forecast'].round(2)

        tableau_df['forecast_period'] = 'Forecast'
        tableau_df['forecast_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')

        if actual_df is not None:
            actual = actual_df.copy()
            actual['date'] = pd.to_datetime(actual['date'])
            actual = actual.groupby(['date', 'product_id', 'region', 'warehouse'])['quantity'].sum().reset_index()
            actual.rename(columns={'quantity': 'actual'}, inplace=True)
            actual['forecast'] = np.nan
            actual['forecast_lower'] = np.nan
            actual['forecast_upper'] = np.nan
            actual['forecast_period'] = 'Actual'
            actual['level'] = 'actual'

            tableau_df = pd.concat([tableau_df, actual], ignore_index=True)

        tableau_df['year'] = tableau_df['date'].dt.year
        tableau_df['month'] = tableau_df['date'].dt.month
        tableau_df['quarter'] = tableau_df['date'].dt.quarter
        tableau_df['week'] = tableau_df['date'].dt.isocalendar().week

        return tableau_df

    def prepare_inventory_data(self, inventory_df: pd.DataFrame,
                                safety_stock_df: pd.DataFrame,
                                replenishment_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Preparing inventory data for Tableau...")

        inv_df = inventory_df.copy()
        inv_df['date'] = pd.to_datetime(inv_df['date'])

        if safety_stock_df is not None and len(safety_stock_df) > 0:
            ss_df = safety_stock_df.copy()
            inv_df = inv_df.merge(
                ss_df[['product_id', 'warehouse', 'safety_stock_recommended',
                       'reorder_point', 'service_level']],
                on=['product_id', 'warehouse'],
                how='left'
            )

        if replenishment_df is not None and len(replenishment_df) > 0:
            rep_df = replenishment_df.copy()
            rep_df['date'] = pd.to_datetime(rep_df['date'])
            inv_df = inv_df.merge(
                rep_df[['date', 'product_id', 'warehouse', 'projected_stock',
                        'order_quantity', 'stock_status']],
                on=['date', 'product_id', 'warehouse'],
                how='left'
            )

        inv_df['stock_vs_safety'] = inv_df.get('stock_quantity', 0) - inv_df.get('safety_stock_recommended', 0)
        inv_df['stock_coverage_days'] = np.where(
            inv_df.get('projected_stock', 0) > 0,
            inv_df['projected_stock'] / inv_df.get('forecast_demand', 1),
            0
        )

        return inv_df

    def prepare_ramp_up_data(self, ramp_df: pd.DataFrame,
                              historical_ramps: Dict = None) -> pd.DataFrame:
        logger.info("Preparing ramp-up data for Tableau...")

        ramp = ramp_df.copy()
        ramp['date'] = pd.to_datetime(ramp['date'])
        ramp['data_type'] = 'Forecast'

        all_data = [ramp]

        if historical_ramps:
            for product_id, ramp_data in historical_ramps.items():
                if isinstance(ramp_data, dict) and 'daily' in ramp_data:
                    hist = ramp_data['daily'].copy()
                    hist['product_id'] = product_id
                    hist['data_type'] = 'Historical'
                    all_data.append(hist)

        combined = pd.concat(all_data, ignore_index=True)
        return combined

    def save_to_csv(self, df: pd.DataFrame, filename: str,
                     output_dir: str = './output') -> Path:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filepath = output_path / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"Saved data to {filepath}")
        return filepath

    def publish_datasource(self, df: pd.DataFrame,
                           datasource_name: str = None,
                           project_name: str = None) -> Optional[str]:
        if not self.connected or not TABLEAU_AVAILABLE:
            logger.warning("Not connected to Tableau Server. Cannot publish datasource.")
            return None

        datasource_name = datasource_name or self.datasource_name
        project_name = project_name or self.project_name

        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                df.to_csv(f, index=False, encoding='utf-8-sig')
                temp_file = f.name

            all_projects, _ = self.server.projects.get()
            target_project = None
            for project in all_projects:
                if project.name == project_name:
                    target_project = project
                    break

            if target_project is None:
                logger.error(f"Project '{project_name}' not found on Tableau Server")
                return None

            new_datasource = TSC.DatasourceItem(project_id=target_project.id, name=datasource_name)

            publish_mode = TSC.Server.PublishMode.Overwrite
            self.server.datasources.publish(
                new_datasource,
                temp_file,
                publish_mode,
                as_job=False
            )

            logger.info(f"Successfully published datasource: {datasource_name}")
            return datasource_name

        except Exception as e:
            logger.error(f"Failed to publish datasource: {e}")
            return None

    def publish_dashboard(self, workbook_path: str,
                          project_name: str = None) -> Optional[str]:
        if not self.connected or not TABLEAU_AVAILABLE:
            logger.warning("Not connected to Tableau Server. Cannot publish workbook.")
            return None

        project_name = project_name or self.project_name

        try:
            all_projects, _ = self.server.projects.get()
            target_project = None
            for project in all_projects:
                if project.name == project_name:
                    target_project = project
                    break

            if target_project is None:
                logger.error(f"Project '{project_name}' not found on Tableau Server")
                return None

            new_workbook = TSC.WorkbookItem(project_id=target_project.id)

            publish_mode = TSC.Server.PublishMode.Overwrite
            workbook = self.server.workbooks.publish(
                new_workbook,
                workbook_path,
                publish_mode,
                as_job=False
            )

            logger.info(f"Successfully published workbook: {workbook.name}")
            return workbook.name

        except Exception as e:
            logger.error(f"Failed to publish workbook: {e}")
            return None

    def refresh_extract(self, datasource_name: str = None) -> bool:
        if not self.connected or not TABLEAU_AVAILABLE:
            logger.warning("Not connected to Tableau Server. Cannot refresh extract.")
            return False

        datasource_name = datasource_name or self.datasource_name

        try:
            all_datasources, _ = self.server.datasources.get()
            target_ds = None
            for ds in all_datasources:
                if ds.name == datasource_name:
                    target_ds = ds
                    break

            if target_ds is None:
                logger.error(f"Datasource '{datasource_name}' not found")
                return False

            job = self.server.datasources.refresh(target_ds)
            logger.info(f"Started extract refresh job: {job.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh extract: {e}")
            return False

    def get_dashboard_url(self, workbook_name: str, view_name: str = None) -> Optional[str]:
        if not self.connected or not TABLEAU_AVAILABLE:
            return None

        try:
            all_workbooks, _ = self.server.workbooks.get()
            target_wb = None
            for wb in all_workbooks:
                if wb.name == workbook_name:
                    target_wb = wb
                    break

            if target_wb is None:
                return None

            if view_name:
                self.server.workbooks.populate_views(target_wb)
                for view in target_wb.views:
                    if view.name == view_name:
                        return f"{self.server_url}/#/views/{target_wb.id}/{view.id}"

            return f"{self.server_url}/#/workbooks/{target_wb.id}"

        except Exception as e:
            logger.error(f"Failed to get dashboard URL: {e}")
            return None

    def create_tableau_hyper(self, df: pd.DataFrame, output_path: str) -> bool:
        try:
            from tableauhyperapi import HyperProcess, Connection, TableDefinition, \
                SqlType, Inserter, CreateMode, TableName

            schema = []
            for col in df.columns:
                dtype = df[col].dtype
                if 'int' in str(dtype):
                    sql_type = SqlType.big_int()
                elif 'float' in str(dtype):
                    sql_type = SqlType.double()
                elif 'datetime' in str(dtype):
                    sql_type = SqlType.timestamp()
                else:
                    sql_type = SqlType.text()

                schema.append(TableDefinition.Column(col, sql_type))

            table = TableDefinition(TableName('Extract', 'ForecastData'), schema)

            with HyperProcess() as hyper:
                with Connection(hyper.endpoint, output_path, CreateMode.CreateAndReplace) as conn:
                    conn.catalog.create_table(table)

                    with Inserter(conn, table) as inserter:
                        rows = []
                        for _, row in df.iterrows():
                            row_data = []
                            for col in df.columns:
                                val = row[col]
                                if pd.isna(val):
                                    row_data.append(None)
                                elif 'datetime' in str(df[col].dtype):
                                    row_data.append(val.to_pydatetime())
                                else:
                                    row_data.append(val)
                            rows.append(row_data)

                        inserter.add_rows(rows)

            logger.info(f"Created Tableau Hyper file: {output_path}")
            return True

        except ImportError:
            logger.warning("Tableau Hyper API not installed. Cannot create Hyper file.")
            return False
        except Exception as e:
            logger.error(f"Failed to create Hyper file: {e}")
            return False

    def export_all_for_tableau(self,
                                forecast_df: pd.DataFrame,
                                inventory_df: pd.DataFrame = None,
                                safety_stock_df: pd.DataFrame = None,
                                replenishment_df: pd.DataFrame = None,
                                ramp_df: pd.DataFrame = None,
                                output_dir: str = './output',
                                publish: bool = False) -> Dict[str, Path]:
        output_files = {}

        logger.info("Exporting all data for Tableau...")

        tableau_forecast = self.prepare_forecast_data(forecast_df)
        output_files['forecast'] = self.save_to_csv(tableau_forecast, 'demand_forecast.csv', output_dir)

        if inventory_df is not None:
            tableau_inventory = self.prepare_inventory_data(
                inventory_df, safety_stock_df, replenishment_df
            )
            output_files['inventory'] = self.save_to_csv(
                tableau_inventory, 'inventory_analysis.csv', output_dir
            )

        if ramp_df is not None:
            tableau_ramp = self.prepare_ramp_up_data(ramp_df)
            output_files['ramp_up'] = self.save_to_csv(tableau_ramp, 'ramp_up_analysis.csv', output_dir)

        if publish and self.connected:
            for name, filepath in output_files.items():
                df = pd.read_csv(filepath)
                self.publish_datasource(df, datasource_name=f"Demand_Forecast_{name.capitalize()}")

        return output_files

    def generate_tableau_tds(self, datasource_name: str,
                              csv_path: str, output_path: str) -> bool:
        tds_content = f'''<?xml version='1.0' encoding='utf-8'?>
<datasource formatted-name='{datasource_name}' version='10.5'>
  <connection class='textscan'>
    <named-connections>
      <named-connection name='{datasource_name}' caption='{datasource_name}'>
        <connection class='textscan' filename='{csv_path}' delim=',' text-qualifier='&quot;' />
      </named-connection>
    </named-connections>
    <relation name='{datasource_name}' type='text'>
      <connection-name>{datasource_name}</connection-name>
    </relation>
  </connection>
</datasource>'''

        try:
            with open(output_path, 'w') as f:
                f.write(tds_content)
            logger.info(f"Created Tableau TDS file: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create TDS file: {e}")
            return False

import json
import os
import pandas as pd
import psycopg
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """Data loader for VN30F1M futures from PostgreSQL database"""

    def __init__(self, config_path=None, cache_dir="data_cache"):
        if config_path is None:
            possible_paths = [
                'config/database.json',
                '../config/database.json',
                '../../config/database.json',
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break

        if config_path is None or not os.path.exists(config_path):
            raise FileNotFoundError(f"Database configuration file not found")

        self.config_path = config_path
        self.db_config = self._load_config()

        if cache_dir is None:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            self.cache_dir = os.path.join(project_root, 'data_cache')
        else:
            self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.tick_cache_dir = os.path.join(self.cache_dir, "tick_data")
        self.contract_cache_dir = os.path.join(self.cache_dir, "contract_data")
        self.ohlcv_cache_dir = os.path.join(self.cache_dir, "ohlcv_data")

        os.makedirs(self.tick_cache_dir, exist_ok=True)
        os.makedirs(self.contract_cache_dir, exist_ok=True)
        os.makedirs(self.ohlcv_cache_dir, exist_ok=True)

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading database config: {e}")
            raise

    def get_connection(self):
        try:
            return psycopg.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                dbname=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

    def get_active_contract_data(self, start_date, end_date):
        """Get VN30F1M active contract data from database"""
        cache_path = os.path.join(self.contract_cache_dir, f"{start_date}_{end_date}_VN30F1M.pkl")

        # Check cache first
        if os.path.exists(cache_path):
            logger.info(f"Loading cached data from {cache_path}")
            return pd.read_pickle(cache_path)

        query = """
            SELECT m.datetime, m.tickersymbol, m.price, v.quantity
            FROM quote.matched m
            JOIN quote.futurecontractcode f ON m.tickersymbol = f.tickersymbol AND DATE(m.datetime) = f.datetime
            LEFT JOIN quote.total v ON m.tickersymbol = v.tickersymbol AND m.datetime = v.datetime
            WHERE m.datetime BETWEEN %s AND %s
            AND f.futurecode = 'VN30F1M'
            ORDER BY m.datetime
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (start_date, end_date))
                    results = cur.fetchall()

                    if not results:
                        logger.warning(f"No active contract data found for the specified period")
                        return pd.DataFrame()

                    df = pd.DataFrame(results, columns=['datetime', 'tickersymbol', 'price', 'quantity'])
                    df['datetime'] = pd.to_datetime(df['datetime'])

                    logger.info(f"Retrieved {len(df)} active contract data points")

                    # Save to cache
                    df.to_pickle(cache_path)

                    return df
        except Exception as e:
            logger.error(f"Error retrieving active contract data: {e}")
            raise

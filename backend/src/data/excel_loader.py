"""
Excel Dataset Loader for Casablanca Traffic Data.

Loads and processes all sheets from the Excel file:
- Table 0: Coordinates (110 points)
- Table 1: Population data
- Table 2: Transit (Tram/Bus stations)
- Table 3: Road types
- Table 4: Land use variables
- Tables 5-11: Traffic data (Monday-Sunday)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class CasablancaDataLoader:
    """Loads and processes the Casablanca traffic dataset."""
    
    # Sheet name mappings
    SHEET_NAMES = {
        'coordinates': 'Table 0. Coordinates',
        'population': 'Table 1. Population size in eac',
        'transit': 'Table 2. Number of Tram and Bus',
        'roads': 'Table 3. Type of roads',
        'land_use': 'Table 4. Land use variables ',
        'monday': 'Table 5. Monday',
        'tuesday': 'Table 6. Tuesday',
        'wednesday': 'Table 7. Wednesday',
        'thursday': 'Table. 8 Thursday',
        'friday': 'Table. 9 Friday',
        'saturday': 'Table. 10 Saturday',
        'sunday': 'Table. 11 Sunday',
    }
    
    # Day of week mapping
    DAY_MAPPING = {
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
        'saturday': 5,
        'sunday': 6,
    }
    
    def __init__(self, excel_path: str):
        """Initialize with path to Excel file."""
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        self.xl = pd.ExcelFile(self.excel_path)
        self._coordinates: Optional[pd.DataFrame] = None
        self._zone_features: Optional[pd.DataFrame] = None
        self._traffic_data: Optional[pd.DataFrame] = None
        
    def load_coordinates(self) -> pd.DataFrame:
        """Load 110 geographic points with coordinates."""
        if self._coordinates is not None:
            return self._coordinates
        
        df = pd.read_excel(self.xl, sheet_name=self.SHEET_NAMES['coordinates'], header=None)
        
        # Find header row (row 11 contains headers)
        # Data starts at row 12
        coords = []
        current_commune = None
        current_zip = None
        
        for i in range(12, len(df)):
            row = df.iloc[i]
            
            # Update commune/zip if present
            if pd.notna(row[1]):
                current_commune = row[1]
            if pd.notna(row[2]):
                current_zip = row[2]
            
            # Extract point data
            if pd.notna(row[3]):  # Index column
                coords.append({
                    'point_idx': int(row[3]),
                    'commune': current_commune,
                    'zip_code': current_zip,
                    'latitude': float(row[4]),
                    'longitude': float(row[5]),
                })
        
        self._coordinates = pd.DataFrame(coords)
        logger.info(f"Loaded {len(self._coordinates)} coordinate points")
        return self._coordinates
    
    def load_zone_features(self) -> pd.DataFrame:
        """Load zone/commune-level features (population, transit, roads, land use)."""
        if self._zone_features is not None:
            return self._zone_features
        
        # Load population data
        df_pop = pd.read_excel(self.xl, sheet_name=self.SHEET_NAMES['population'], header=None)
        pop_data = []
        for i in range(10, 30):  # Data rows
            row = df_pop.iloc[i]
            if pd.notna(row[1]) and row[1] != 'Commune':
                pop_data.append({
                    'commune': row[1],
                    'zip_code': row[2],
                    'population': float(row[3]) if pd.notna(row[3]) else 0,
                    'households': float(row[4]) if pd.notna(row[4]) else 0,
                    'density': float(row[5]) if pd.notna(row[5]) else 0,
                })
        df_population = pd.DataFrame(pop_data)
        
        # Load transit data
        df_trans = pd.read_excel(self.xl, sheet_name=self.SHEET_NAMES['transit'], header=None)
        transit_data = []
        for i in range(10, 30):
            row = df_trans.iloc[i]
            if pd.notna(row[1]) and row[1] != 'Commune':
                transit_data.append({
                    'commune': row[1],
                    'tram_stations': int(row[3]) if pd.notna(row[3]) else 0,
                    'bus_stations': int(row[4]) if pd.notna(row[4]) else 0,
                })
        df_transit = pd.DataFrame(transit_data)
        
        # Load road types
        df_roads = pd.read_excel(self.xl, sheet_name=self.SHEET_NAMES['roads'], header=None)
        roads_data = []
        for i in range(10, 30):
            row = df_roads.iloc[i]
            if pd.notna(row[1]) and row[1] != 'Commune':
                roads_data.append({
                    'commune': row[1],
                    'primary_roads': int(row[3]) if pd.notna(row[3]) else 0,
                    'secondary_roads': int(row[4]) if pd.notna(row[4]) else 0,
                    'highways': int(row[5]) if pd.notna(row[5]) else 0,
                })
        df_roads_df = pd.DataFrame(roads_data)
        
        # Load land use
        df_land = pd.read_excel(self.xl, sheet_name=self.SHEET_NAMES['land_use'], header=None)
        land_data = []
        for i in range(10, 30):
            row = df_land.iloc[i]
            if pd.notna(row[1]) and row[1] != 'Commune':
                region_area = float(row[3]) if pd.notna(row[3]) else 1
                land_data.append({
                    'commune': row[1],
                    'region_area': region_area,
                    'parking_area': float(row[4]) if pd.notna(row[4]) else 0,
                    'industrial_pct': (float(row[5]) / region_area * 100) if pd.notna(row[5]) and region_area > 0 else 0,
                    'parks_pct': (float(row[6]) / region_area * 100) if pd.notna(row[6]) and region_area > 0 else 0,
                    'residential_pct': (float(row[7]) / region_area * 100) if pd.notna(row[7]) and region_area > 0 else 0,
                    'university_pct': (float(row[8]) / region_area * 100) if pd.notna(row[8]) and region_area > 0 else 0,
                    'commercial_buildings': int(row[9]) if pd.notna(row[9]) else 0,
                })
        df_land_df = pd.DataFrame(land_data)
        
        # Merge all zone features
        self._zone_features = df_population.merge(df_transit, on='commune', how='left')
        self._zone_features = self._zone_features.merge(df_roads_df, on='commune', how='left')
        self._zone_features = self._zone_features.merge(df_land_df, on='commune', how='left')
        
        # Fill NaN with 0
        self._zone_features = self._zone_features.fillna(0)
        
        logger.info(f"Loaded zone features for {len(self._zone_features)} communes")
        return self._zone_features
    
    def load_traffic_day(self, day: str) -> pd.DataFrame:
        """Load traffic data for a specific day of week."""
        if day not in self.SHEET_NAMES:
            raise ValueError(f"Invalid day: {day}")
        
        df = pd.read_excel(self.xl, sheet_name=self.SHEET_NAMES[day], header=None)
        
        traffic_records = []
        
        # Find first data row (where col 3 is a numeric origin index)
        start_row = 10
        for i in range(8, min(20, len(df))):
            val = df.iloc[i, 3]
            if pd.notna(val) and isinstance(val, (int, float)) and not isinstance(val, bool):
                start_row = i
                break
        
        for i in range(start_row, len(df)):
            row = df.iloc[i]
            
            # Skip if no origin index or not numeric
            if pd.isna(row[3]):
                continue
            
            # Skip header rows (string values)
            if isinstance(row[3], str):
                continue
            
            origin_idx = int(row[3])
            dest_idx = int(row[7]) if pd.notna(row[7]) else None
            
            if dest_idx is None:
                continue
            
            # Extract distance
            distance_km = float(row[11]) if pd.notna(row[11]) else 0
            
            # Extract travel times for each hour (cols 12-35)
            for hour in range(24):
                travel_time_col = 12 + hour
                tti_col = 36 + hour
                
                travel_time = float(row[travel_time_col]) if pd.notna(row[travel_time_col]) else None
                tti = float(row[tti_col]) if pd.notna(row[tti_col]) else None
                
                if travel_time is not None and tti is not None:
                    traffic_records.append({
                        'day_of_week': self.DAY_MAPPING[day],
                        'hour': hour,
                        'origin_idx': origin_idx,
                        'destination_idx': dest_idx,
                        'distance_km': distance_km,
                        'travel_time_min': travel_time,
                        'tti': tti,  # Travel Time Index (congestion indicator)
                    })
        
        return pd.DataFrame(traffic_records)
    
    def load_all_traffic(self) -> pd.DataFrame:
        """Load traffic data for all days of the week."""
        if self._traffic_data is not None:
            return self._traffic_data
        
        all_days = []
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            logger.info(f"Loading traffic data for {day}...")
            day_df = self.load_traffic_day(day)
            all_days.append(day_df)
        
        self._traffic_data = pd.concat(all_days, ignore_index=True)
        logger.info(f"Loaded {len(self._traffic_data)} total traffic records")
        return self._traffic_data
    
    def get_point_commune(self, point_idx: int) -> Optional[str]:
        """Get the commune for a given point index."""
        coords = self.load_coordinates()
        match = coords[coords['point_idx'] == point_idx]
        if len(match) > 0:
            return match.iloc[0]['commune']
        return None
    
    def build_training_dataset(self) -> pd.DataFrame:
        """
        Build complete training dataset with all features.
        
        Returns DataFrame with columns:
        - Temporal: day_of_week, hour, is_weekend, is_rush_hour
        - OD pair: origin_idx, destination_idx, distance_km
        - Origin zone: origin_population, origin_density, origin_tram, origin_bus, etc.
        - Destination zone: dest_population, dest_density, dest_tram, dest_bus, etc.
        - Target: tti (Travel Time Index)
        """
        # Load all data
        coords = self.load_coordinates()
        zones = self.load_zone_features()
        traffic = self.load_all_traffic()
        
        # Create point-to-commune mapping
        point_commune = dict(zip(coords['point_idx'], coords['commune']))
        
        # Add commune info to traffic data
        traffic['origin_commune'] = traffic['origin_idx'].map(point_commune)
        traffic['dest_commune'] = traffic['destination_idx'].map(point_commune)
        
        # Add temporal features
        traffic['is_weekend'] = (traffic['day_of_week'] >= 5).astype(int)
        traffic['is_rush_hour'] = traffic['hour'].apply(
            lambda h: 1 if (7 <= h <= 9) or (17 <= h <= 19) else 0
        )
        
        # Merge origin zone features
        origin_zones = zones.copy()
        origin_zones.columns = ['commune'] + [f'origin_{c}' for c in zones.columns if c != 'commune']
        traffic = traffic.merge(origin_zones, left_on='origin_commune', right_on='commune', how='left')
        traffic.drop(columns=['commune'], inplace=True, errors='ignore')
        
        # Merge destination zone features
        dest_zones = zones.copy()
        dest_zones.columns = ['commune'] + [f'dest_{c}' for c in zones.columns if c != 'commune']
        traffic = traffic.merge(dest_zones, left_on='dest_commune', right_on='commune', how='left')
        traffic.drop(columns=['commune'], inplace=True, errors='ignore')
        
        # Fill any remaining NaN
        traffic = traffic.fillna(0)
        
        # Convert TTI to congestion level (1-10 scale)
        # TTI of 1.0 = free flow, TTI of 2.0+ = heavy congestion
        traffic['congestion_level'] = np.clip((traffic['tti'] - 1) * 10, 1, 10)
        
        # Calculate average speed from distance and travel time
        traffic['average_speed'] = np.where(
            traffic['travel_time_min'] > 0,
            traffic['distance_km'] / (traffic['travel_time_min'] / 60),
            30  # Default speed
        )
        traffic['average_speed'] = np.clip(traffic['average_speed'], 5, 120)
        
        logger.info(f"Built training dataset with {len(traffic)} records and {len(traffic.columns)} features")
        return traffic
    
    def get_feature_columns(self) -> Dict[str, list]:
        """Get categorized feature column names."""
        return {
            'temporal': ['day_of_week', 'hour', 'is_weekend', 'is_rush_hour'],
            'od_pair': ['origin_idx', 'destination_idx', 'distance_km'],
            'origin_zone': [
                'origin_population', 'origin_households', 'origin_density',
                'origin_tram_stations', 'origin_bus_stations',
                'origin_primary_roads', 'origin_secondary_roads', 'origin_highways',
                'origin_industrial_pct', 'origin_parks_pct', 'origin_residential_pct',
                'origin_university_pct', 'origin_commercial_buildings'
            ],
            'dest_zone': [
                'dest_population', 'dest_households', 'dest_density',
                'dest_tram_stations', 'dest_bus_stations',
                'dest_primary_roads', 'dest_secondary_roads', 'dest_highways',
                'dest_industrial_pct', 'dest_parks_pct', 'dest_residential_pct',
                'dest_university_pct', 'dest_commercial_buildings'
            ],
            'target': ['tti', 'congestion_level', 'average_speed', 'travel_time_min']
        }


# Convenience function
def load_casablanca_data(excel_path: str) -> CasablancaDataLoader:
    """Load Casablanca traffic dataset."""
    return CasablancaDataLoader(excel_path)

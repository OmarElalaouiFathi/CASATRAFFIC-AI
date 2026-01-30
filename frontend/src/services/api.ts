import axios from 'axios';
import type { TrafficData, TrafficPrediction, RouteOption, DashboardMetrics, TrafficTrend } from '../types';

const apiClient = axios.create({baseURL: import.meta.env.VITE_API_BASE_URL || 'https://backend-production-e652.up.railway.app', headers: {'Content-Type': 'application/json'}});

export const trafficApi = {
  getCurrentTraffic: async () => (await apiClient.get<{data: TrafficData[]; count: number; timestamp: string}>('/api/traffic/current')).data,
  getRoadSegments: async () => (await apiClient.get<{segments: any[]; count: number}>('/api/traffic/segments')).data,
  getTrafficHistory: async (roadSegmentId: string, hours: number = 24) => (await apiClient.get<{data: TrafficData[]; count: number}>(`/api/traffic/history/${roadSegmentId}?hours=${hours}`)).data,
};

export const predictionApi = {
  predict: async (request: {road_segment_id: string; time_horizon?: number}) => (await apiClient.post<TrafficPrediction>('/api/prediction/predict', {road_segment_id: request.road_segment_id, time_horizon: request.time_horizon || 30})).data,
  getAccuracy: async () => (await apiClient.get<{overall_accuracy: number; mae: number; rmse: number; r_squared: number; last_updated: string} | null>('/api/prediction/accuracy')).data,
  getAllPredictions: async (timeHorizon: number = 30) => (await apiClient.get<{predictions: any[]; model_type: string; timestamp: string}>(`/api/prediction/segments?time_horizon=${timeHorizon}`)).data,
  getModelInfo: async () => (await apiClient.get<{is_loaded: boolean; model_type: string; features: any; zones_cached: number}>('/api/prediction/model-info')).data,
  getZones: async () => (await apiClient.get<{count: number; zones: any[]}>('/api/prediction/zones')).data,
};

export const routeApi = {
  suggestRoutes: async (request: {origin_lat: number; origin_lng: number; destination_lat: number; destination_lng: number; avoid_congestion?: boolean}) => (await apiClient.post<{routes: RouteOption[]; recommended_route_id: string} | null>('/api/routes/suggest', request)).data,
};

export const analyticsApi = {
  getDashboard: async () => (await apiClient.get<{metrics: DashboardMetrics; source: string}>('/api/analytics/dashboard')).data,
  getTrends: async (hours: number = 24) => (await apiClient.get<{trends: TrafficTrend[]; period_hours: number; count: number}>(`/api/analytics/trends?hours=${hours}`)).data,
};

export default apiClient;

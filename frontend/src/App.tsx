import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { 
  Search,
  ArrowUpDown,
  Navigation,
  MapPin,
  StopCircle,
  TrendingUp,
  TrendingDown,
  Clock,
  Zap,
  Activity
} from 'lucide-react';
import TrafficMap from './components/TrafficMap';
import { trafficApi } from './services/api';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

type TabType = 'traffic' | 'predictions';
type SortType = 'congestion-high' | 'congestion-low' | 'speed-high' | 'speed-low' | 'name';

// Traffic segment card component matching reference exactly
function TrafficCard({ 
  segment, 
  isSelected,
  onClick,
  prediction,
  isLightMode
}: { 
  segment: {
    road_segment_id: string;
    road_name: string;
    congestion_level: number;
    average_speed: number;
    latitude: number;
    longitude: number;
    traffic_source?: string;
  };
  isSelected: boolean;
  onClick: () => void;
  prediction?: {
    predicted_congestion: number;
    current_congestion?: number;
    predicted_tti?: number;
    confidence: number;
    trend: 'up' | 'down' | 'stable';
  };
  isLightMode: boolean;
}) {
  const getStatusInfo = (congestion: number) => {
    if (congestion >= 7) return { label: 'Heavy Traffic', color: 'text-[#e85d5d]', bgColor: 'bg-[#e85d5d]' };
    if (congestion >= 4) return { label: 'Moderate', color: 'text-[#d4a84b]', bgColor: 'bg-[#d4a84b]' };
    return { label: 'Light Traffic', color: 'text-[#5a9a6e]', bgColor: 'bg-[#5a9a6e]' };
  };

  const status = getStatusInfo(segment.congestion_level);
  const segmentId = segment.road_segment_id.slice(-4).toUpperCase();

  return (
    <div 
      onClick={onClick}
      className={`cursor-pointer border-b last:border-b-0 ${isLightMode ? 'border-gray-200' : 'border-[#191919]'}`}
    >
      <div className={`px-4 py-3 transition-colors duration-150 ${
        isSelected 
          ? isLightMode ? 'bg-orange-100 border-l-3 border-l-[#F65715]' : 'bg-[#191919] border-l-3 border-l-[#F65715]' 
          : isLightMode ? 'hover:bg-gray-50 border-l-3 border-l-transparent' : 'hover:bg-[#141414] border-l-3 border-l-transparent'
      }`}>
        {/* Header row */}
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs tracking-wider font-medium ${isLightMode ? 'bg-gray-100 text-gray-600' : 'bg-[#191919] text-[#9ca3af]'}`}>
              {segmentId}
            </span>
            <div className={`w-2 h-2 rounded-full ${status.bgColor}`}></div>
          </div>
          <div className="flex items-center gap-1">
            <span className={`text-base font-medium ${isLightMode ? 'text-gray-700' : 'text-[#9ca3af]'}`}>{segment.average_speed}</span>
            <span className={`text-xs ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>km/h</span>
          </div>
        </div>

        {/* Road name */}
        <div className="flex items-center gap-2 mb-1.5">
          <Navigation className="w-4 h-4 text-[#F65715] -rotate-45" />
          <span className={`font-medium text-base truncate leading-tight ${isLightMode ? 'text-gray-800' : 'text-white'}`}>{segment.road_name.split(' - ')[0]}</span>
        </div>

        {/* Location */}
        <div className="flex items-center gap-2 text-sm mb-2">
          <MapPin className={`w-3 h-3 ${isLightMode ? 'text-gray-400' : 'text-[#6b7280]'}`} />
          <span className={`leading-tight ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>{segment.road_name.split(' - ')[1] || 'Casablanca'}</span>
        </div>

        {/* Stats row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`font-medium text-xs ${status.color}`}>{status.label}</span>
            <span className={isLightMode ? 'text-gray-300' : 'text-[#4a5057]'}>•</span>
            <span className={`text-xs ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>{segment.congestion_level}/10</span>
          </div>
          
          {/* AI Prediction indicator */}
          {prediction && !isSelected && (
            <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded border ${isLightMode ? 'bg-gray-100 border-gray-200' : 'bg-[#191919] border-[#252525]'}`}>
              {prediction.trend === 'up' ? (
                <TrendingUp className="w-3 h-3 text-[#e85d5d]" />
              ) : prediction.trend === 'down' ? (
                <TrendingDown className="w-3 h-3 text-[#5a9a6e]" />
              ) : (
                <div className={`w-3 h-0.5 ${isLightMode ? 'bg-gray-400' : 'bg-[#6b7280]'}`}></div>
              )}
              <span className={`text-xs ${isLightMode ? 'text-gray-500' : 'text-[#9ca3af]'}`}>
                {prediction.predicted_congestion?.toFixed?.(1) || prediction.predicted_congestion}/10 in 30m
              </span>
            </div>
          )}
        </div>

        {/* Expanded AI Prediction Card when selected */}
        {isSelected && prediction && (
          <div className={`mt-3 pt-3 border-t ${isLightMode ? 'border-gray-200' : 'border-[#252525]'}`}>
            <div className={`rounded-lg p-3 border ${isLightMode ? 'bg-white border-gray-200' : 'bg-[#0D0D0D] border-[#252525]'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4 text-[#F65715]" />
                <span className={`text-xs font-semibold uppercase tracking-wide ${isLightMode ? 'text-gray-700' : 'text-[#9ca3af]'}`}>
                  AI PREDICTION
                </span>
                <span className={`ml-auto text-xs px-1.5 py-0.5 rounded ${isLightMode ? 'bg-bg-orange-50 text-[#F65715]' : 'bg-[#F65715]/50 text-[#F65715]'}`}>
                  Live
                </span>
              </div>
              
              <div className="grid grid-cols-3 gap-2 mb-2">
                <div>
                  <div className={`text-xs ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>Now</div>
                  <div className={`text-lg font-bold ${isLightMode ? 'text-gray-800' : 'text-white'}`}>
                    {(prediction.current_congestion || segment.congestion_level || 0).toFixed?.(1) || prediction.current_congestion || segment.congestion_level}
                  </div>
                </div>
                <div className="flex items-center justify-center">
                  {prediction.trend === 'up' ? (
                    <TrendingUp className="w-5 h-5 text-[#e85d5d]" />
                  ) : prediction.trend === 'down' ? (
                    <TrendingDown className="w-5 h-5 text-[#5a9a6e]" />
                  ) : (
                    <div className={`w-5 h-0.5 ${isLightMode ? 'bg-gray-400' : 'bg-[#6b7280]'}`}></div>
                  )}
                </div>
                <div className="text-right">
                  <div className={`text-xs ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>In 30min</div>
                  <div className={`text-lg font-bold ${
                    prediction.predicted_congestion >= 7 ? 'text-[#e85d5d]' : 
                    prediction.predicted_congestion >= 4 ? 'text-[#d4a84b]' : 'text-[#5a9a6e]'
                  }`}>
                    {prediction.predicted_congestion?.toFixed?.(1) || prediction.predicted_congestion}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center justify-between text-xs">
                <span className={isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}>
                  TTI: <span className={isLightMode ? 'text-gray-700' : 'text-white'}>{prediction.predicted_tti?.toFixed?.(2) || '—'}</span>
                </span>
                <span className={isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}>
                  Confidence: <span className="text-[#F65715]">{((prediction.confidence || 0.85) * 100).toFixed(0)}%</span>
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// AI Predictions Panel Component with real API data
function AIPredictionsPanel({ segments, isLightMode }: { segments: any[]; isLightMode: boolean }) {
  // Fetch real predictions from API
  const { data: predictionsData } = useQuery({
    queryKey: ['predictions', 'all'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8000/api/prediction/segments?time_horizon=30');
      if (!response.ok) return null;
      return response.json();
    },
    refetchInterval: 60000, // Refresh every minute
    retry: 1,
  });

  // Fetch model info
  const { data: modelInfo } = useQuery({
    queryKey: ['model', 'info'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8000/api/prediction/model-info');
      if (!response.ok) return null;
      return response.json();
    },
    retry: 1,
  });

  // Merge predictions with segment data
  const predictions = useMemo(() => {
    const apiPredictions = predictionsData?.predictions || [];
    
    if (apiPredictions.length > 0) {
      // Use real predictions
      return apiPredictions.slice(0, 10).map((pred: any) => {
        const segment = segments.find(s => s.road_segment_id === pred.road_segment_id);
        return {
          ...pred,
          road_name: segment?.road_name || `Segment ${pred.road_segment_id}`,
        };
      });
    }
    
    // Fallback to demo predictions
    return segments.slice(0, 10).map(s => ({
      road_segment_id: s.road_segment_id,
      road_name: s.road_name,
      current_congestion: s.congestion_level,
      predicted_congestion: Math.min(10, Math.max(1, s.congestion_level + (Math.random() > 0.5 ? 0.5 : -0.5))),
      confidence: 0.65 + Math.random() * 0.2,
      trend: s.congestion_level > 6 ? 'up' : s.congestion_level < 4 ? 'down' : 'stable',
      method: 'demo'
    }));
  }, [predictionsData, segments]);

  const isModelLoaded = modelInfo?.is_loaded ?? false;
  const modelType = modelInfo?.model_type || 'Heuristic';
  const zonesCached = modelInfo?.zones_cached || 0;

  return (
    <div className="p-4">
      {/* AI Model Status */}
      <div className={`rounded-lg p-4 mb-4 border ${isLightMode ? 'bg-gray-100 border-gray-200' : 'bg-[#191919] border-[#252525]'}`}>
        <div className="mb-3">
          <h3 className={`text-base font-semibold leading-tight ${isLightMode ? 'text-gray-800' : 'text-white'}`}>
            {isModelLoaded ? 'LSTM PREDICTION' : modelType}
          </h3>
          <p className={`text-xs ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>
            {isModelLoaded ? 'Real-time Traffic Forecasting' : 'Traffic Prediction Engine'}
          </p>
        </div>
        
        <div className="grid grid-cols-3 gap-2">
          <div className={`rounded-lg p-3 ${isLightMode ? 'bg-white' : 'bg-[#0D0D0D]'}`}>
            <div className={`text-xs mb-0.5 ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>Status</div>
            <div className={`text-sm font-bold ${isModelLoaded ? 'text-[#5a9a6e]' : 'text-[#d4a84b]'}`}>
              {isModelLoaded ? 'Live' : 'Demo'}
            </div>
          </div>
          <div className={`rounded-lg p-3 ${isLightMode ? 'bg-white' : 'bg-[#0D0D0D]'}`}>
            <div className={`text-xs mb-0.5 ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>Coordinates</div>
            <div className={`text-xl font-bold ${isLightMode ? 'text-gray-800' : 'text-white'}`}>{zonesCached || '—'}</div>
          </div>
          <div className={`rounded-lg p-3 ${isLightMode ? 'bg-white' : 'bg-[#0D0D0D]'}`}>
            <div className={`text-xs mb-0.5 ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>Horizon</div>
            <div className="text-sm font-bold text-[#F65715]">Next 30min</div>
          </div>
        </div>
      </div>

      {/* Predictions List */}
      <h3 className={`text-sm font-semibold mb-3 flex items-center gap-1.5 ${isLightMode ? 'text-gray-800' : 'text-white'}`}>
        <Zap className="w-4 h-4 text-[#F65715]" />
        {isModelLoaded ? 'Live Predictions' : 'Predictions (Demo)'}
      </h3>
      
      <div className="space-y-2">
        {predictions.map((pred: any, i: number) => (
          <div key={i} className={`rounded-lg p-3 border ${isLightMode ? 'bg-gray-100 border-gray-200' : 'bg-[#191919] border-[#252525]'}`}>
            <div className="flex items-center justify-between mb-1">
              <span className={`font-medium text-sm truncate flex-1 leading-tight ${isLightMode ? 'text-gray-800' : 'text-white'}`}>
                {pred.road_name?.split(' - ')[0] || 'Unknown Road'}
              </span>
              <div className="flex items-center gap-1">
                {pred.trend === 'up' ? (
                  <TrendingUp className="w-4 h-4 text-[#e85d5d]" />
                ) : pred.trend === 'down' ? (
                  <TrendingDown className="w-4 h-4 text-[#5a9a6e]" />
                ) : (
                  <div className={`w-4 h-0.5 ${isLightMode ? 'bg-gray-400' : 'bg-[#6b7280]'}`}></div>
                )}
              </div>
            </div>
            
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className={isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}>Now: <span className={isLightMode ? 'text-gray-800' : 'text-white'}>{(pred.current_congestion || pred.congestion_level || 5).toFixed(1)}</span></span>
                <span className={isLightMode ? 'text-gray-300' : 'text-[#4a5057]'}>→</span>
                <span className={isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}>30m: <span className={
                  pred.predicted_congestion > (pred.current_congestion || pred.congestion_level || 5) 
                    ? 'text-[#e85d5d]' 
                    : 'text-[#5a9a6e]'
                }>{pred.predicted_congestion?.toFixed(1) || '—'}</span></span>
              </div>
              <span className={isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}>{Math.round((pred.confidence || 0.7) * 100)}%</span>
            </div>
          </div>
        ))}
      </div>
      
      {/* Model Info */}
      <div className={`mt-4 p-3 rounded-lg border ${isLightMode ? 'bg-white border-gray-200' : 'bg-[#0D0D0D] border-[#191919]'}`}>
        <h4 className={`text-xs font-medium mb-1 ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>
          {isModelLoaded ? 'Enhanced LSTM Architecture' : 'Model Info'}
        </h4>
        <p className={`text-[10px] leading-relaxed ${isLightMode ? 'text-gray-400' : 'text-[#4a5057]'}`}>
          {isModelLoaded ? (
            <>
              BiLSTM(64) → BatchNorm → LSTM(32) → Dense(128) → Dense(1)
              <br/>Features: temporal, zone (pop/transit/land use), OD embeddings
            </>
          ) : (
            <>
              Heuristic predictions based on time patterns.
              <br/>Train model with: POST /api/prediction/train
            </>
          )}
        </p>
      </div>
    </div>
  );
}

function AppContent() {
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('traffic');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLightMode, setIsLightMode] = useState(false);
  const [sortBy, setSortBy] = useState<SortType>('congestion-high');
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  
  // Resizable panel state
  const [panelWidth, setPanelWidth] = useState(300);
  const [panelTop, setPanelTop] = useState(96); // 96px = top-24 equivalent
  const [isResizingX, setIsResizingX] = useState(false);
  const [isResizingY, setIsResizingY] = useState(false);
  const panelRef = useRef<HTMLElement>(null);
  
  const MIN_PANEL_WIDTH = 250;
  const MAX_PANEL_WIDTH = 600;
  const MIN_PANEL_TOP = 50;
  const MAX_PANEL_TOP = 400;
  
  // Handle horizontal resize (width)
  const handleMouseDownX = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingX(true);
  }, []);
  
  // Handle vertical resize (top)
  const handleMouseDownY = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingY(true);
  }, []);
  
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingX) {
        const newWidth = e.clientX - 6; // 6px offset for the panel margin
        if (newWidth >= MIN_PANEL_WIDTH && newWidth <= MAX_PANEL_WIDTH) {
          setPanelWidth(newWidth);
        }
      }
      if (isResizingY) {
        const newTop = e.clientY;
        if (newTop >= MIN_PANEL_TOP && newTop <= MAX_PANEL_TOP) {
          setPanelTop(newTop);
        }
      }
    };
    
    const handleMouseUp = () => {
      setIsResizingX(false);
      setIsResizingY(false);
    };
    
    if (isResizingX || isResizingY) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = isResizingX ? 'ew-resize' : 'ns-resize';
      document.body.style.userSelect = 'none';
    }
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizingX, isResizingY]);

  const { data: trafficData, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['traffic', 'current'],
    queryFn: trafficApi.getCurrentTraffic,
    refetchInterval: 30000,
  });

  // Fetch predictions for all segments
  const { data: predictionsData } = useQuery({
    queryKey: ['predictions', 'all'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8000/api/prediction/segments?time_horizon=30');
      if (!response.ok) return null;
      return response.json();
    },
    refetchInterval: 60000,
    retry: 1,
  });

  // Create a map of predictions by segment ID
  const predictionsMap = useMemo(() => {
    const map: Record<string, any> = {};
    if (predictionsData?.predictions) {
      predictionsData.predictions.forEach((pred: any) => {
        map[pred.road_segment_id] = pred;
      });
    }
    return map;
  }, [predictionsData]);

  // Update last updated time when data changes
  useMemo(() => {
    if (dataUpdatedAt) {
      setLastUpdated(new Date(dataUpdatedAt));
    }
  }, [dataUpdatedAt]);

  const segments = trafficData?.data || [];
  
  // Filter and sort segments
  const filteredSegments = useMemo(() => {
    let result = segments.filter(s => 
      s.road_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.road_segment_id.toLowerCase().includes(searchQuery.toLowerCase())
    );
    
    // Sort based on selected option
    switch (sortBy) {
      case 'congestion-high':
        result = [...result].sort((a, b) => b.congestion_level - a.congestion_level);
        break;
      case 'congestion-low':
        result = [...result].sort((a, b) => a.congestion_level - b.congestion_level);
        break;
      case 'speed-high':
        result = [...result].sort((a, b) => b.average_speed - a.average_speed);
        break;
      case 'speed-low':
        result = [...result].sort((a, b) => a.average_speed - b.average_speed);
        break;
      case 'name':
        result = [...result].sort((a, b) => a.road_name.localeCompare(b.road_name));
        break;
    }
    
    return result;
  }, [segments, searchQuery, sortBy]);

  // Format time ago
  const getTimeAgo = () => {
    const seconds = Math.floor((new Date().getTime() - lastUpdated.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    return `${Math.floor(minutes / 60)}h ago`;
  };

  const tabs = [
    { id: 'traffic', label: 'Traffic', icon: Activity },
    { id: 'predictions', label: 'AI Predictions', icon: Zap },
  ];

  const sortOptions = [
    { id: 'congestion-high', label: 'Congestion (High → Low)' },
    { id: 'congestion-low', label: 'Congestion (Low → High)' },
    { id: 'speed-high', label: 'Speed (Fast → Slow)' },
    { id: 'speed-low', label: 'Speed (Slow → Fast)' },
    { id: 'name', label: 'Road Name (A → Z)' },
  ];

  return (
    <div className={`relative h-screen w-screen ${isLightMode ? 'bg-[#f5f5f5] text-[#1a1a1a]' : 'bg-[#0D0D0D] text-[#e5e7eb]'} overflow-hidden`}>
      {/* Map Background - Full Screen */}
      <div className="absolute inset-0 z-0">
        <TrafficMap 
          onSegmentSelect={setSelectedSegment}
          selectedSegment={selectedSegment}
          isLightMode={isLightMode}
          onToggleMode={() => setIsLightMode(!isLightMode)}
        />
      </div>

      {/* Main Panel - Resizable */}
      <aside 
        ref={panelRef}
        style={{ width: `${panelWidth}px`, top: `${panelTop}px` }}
        className={`absolute left-1.5 bottom-1 rounded-2xl z-40 flex flex-col transition-colors duration-300 ${isLightMode ? 'bg-white/95 backdrop-blur-sm' : 'bg-[#0D0D0D]'}`}
      >
        {/* Top Resize Handle */}
        <div
          onMouseDown={handleMouseDownY}
          className={`absolute top-0 left-0 right-0 h-2 cursor-ns-resize z-50 flex justify-center items-center group hover:bg-[#F65715]/20 transition-colors rounded-t-2xl ${isResizingY ? 'bg-[#F65715]/30' : ''}`}
        >
          <div className={`w-8 h-1 rounded-full transition-colors ${isResizingY ? 'bg-[#F65715]' : isLightMode ? 'bg-gray-300 group-hover:bg-[#F65715]/70' : 'bg-[#333] group-hover:bg-[#F65715]/70'}`}></div>
        </div>
        
        {/* Right Resize Handle */}
        <div
          onMouseDown={handleMouseDownX}
          className={`absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize z-50 flex items-center justify-center group hover:bg-[#F65715]/20 transition-colors rounded-r-2xl ${isResizingX ? 'bg-[#F65715]/30' : ''}`}
        >
          <div className={`w-1 h-8 rounded-full transition-colors ${isResizingX ? 'bg-[#F65715]' : isLightMode ? 'bg-gray-300 group-hover:bg-[#F65715]/70' : 'bg-[#333] group-hover:bg-[#F65715]/70'}`}></div>
        </div>
        {/* Header */}
        <div className={`px-5 pt-4 pb-3 border-b ${isLightMode ? 'border-gray-200' : 'border-[#191919]'}`}>
          {/* App Title */}
          <div className="flex items-center gap-1 mb-3">
        <h1 className={`text-2xl font-medium tracking-tight ${isLightMode ? 'text-gray-700' : 'text-white/75'}`}>CASA</h1>
        <h1 className={`text-2xl font-medium tracking-tight ${isLightMode ? 'text-gray-700' : 'text-white/75'}`}>TRAFFIC</h1>
        <span className="px-1 py-0.5 text-md font-medium text-[#F65715]">AI</span>
          </div>
          
          {/* Live Traffic Indicator - subtle like reference */}
          <div className="flex items-center justify-between mb-3 opacity-50">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-[#F65715] rounded-full"></div>
          <span className={`text-xs uppercase tracking-wider ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>Live Traffic</span>
        </div>
        <div className={`flex items-center gap-1.5 ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>
          <Clock className="w-3 h-3" /> 
          <span className="text-xs">{getTimeAgo()}</span>
        </div>
          </div>
          
          {/* Tabs */}
          <div className="flex gap-1.5 mb-3">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id as TabType)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium uppercase transition-all duration-200 ${
            activeTab === tab.id
              ? isLightMode ? 'bg-orange-100 text-[#F65715]' : 'bg-[#34180C] text-[#F65715]'
              : isLightMode ? 'text-gray-500 hover:text-gray-800 hover:bg-gray-100' : 'text-[#6b7280] hover:text-white hover:bg-[#191919]'
          }`}
            >
          <Icon className="w-4 h-4" />
          {tab.label}
            </button>
          );
        })}
          </div>

          {/* Search and Sort - only for traffic tab */}
          {activeTab === 'traffic' && (
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isLightMode ? 'text-gray-400' : 'text-[#6b7280]'}`} />
            <input
          type="text"
          placeholder="Search roads..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={`w-full rounded-lg pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:border-[#F65715]/50 transition-colors ${
            isLightMode 
              ? 'bg-gray-100 border border-gray-200 text-gray-800 placeholder:text-gray-400'
              : 'bg-[#191919] border border-[#252525] text-white placeholder:text-[#6b7280]'
          }`}
            />
          </div>
          
          {/* Sort Dropdown */}
          <div className="relative">
            <button 
          onClick={() => setShowSortMenu(!showSortMenu)}
          className={`flex items-center gap-2 px-3 py-2.5 rounded-lg transition-colors ${
            isLightMode
              ? 'bg-gray-100 border border-gray-200 text-gray-500 hover:text-gray-800 hover:border-[#F65715]/50'
              : 'bg-[#191919] border border-[#252525] text-[#6b7280] hover:text-white hover:border-[#F65715]/50'
          }`}
            >
          <ArrowUpDown className="w-4 h-4" />
            </button>
            
            {showSortMenu && (
          <div className={`absolute right-0 top-full mt-1 w-56 rounded-lg shadow-xl z-50 overflow-hidden ${
            isLightMode ? 'bg-white border border-gray-200' : 'bg-[#191919] border border-[#252525]'
          }`}>
            {sortOptions.map((option) => (
              <button
            key={option.id}
            onClick={() => {
              setSortBy(option.id as SortType);
              setShowSortMenu(false);
            }}
            className={`w-full px-3 py-2 text-left text-sm transition-colors ${
              sortBy === option.id 
                ? 'bg-[#34180C] text-[#F65715]' 
                : isLightMode ? 'text-gray-600 hover:bg-gray-100' : 'text-[#9ca3af] hover:bg-[#252525]'
            }`}
              >
            {option.label}
              </button>
            ))}
          </div>
            )}
          </div>
        </div>
          )}
        </div>

        {/* Scrollable List */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'traffic' ? (
        isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-3 border-[#d97706]/30 border-t-[#d97706] rounded-full animate-spin"></div>
          </div>
        ) : filteredSegments.length === 0 ? (
          <div className={`text-center py-20 ${isLightMode ? 'text-gray-500' : 'text-[#7a8289]'}`}>
            <StopCircle className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p className="text-xl">No roads found</p>
          </div>
        ) : (
          filteredSegments.map((segment) => (
            <TrafficCard
          key={segment.road_segment_id}
          segment={segment}
          isSelected={selectedSegment === segment.road_segment_id}
          onClick={() => setSelectedSegment(
            selectedSegment === segment.road_segment_id ? null : segment.road_segment_id
          )}
          prediction={predictionsMap[segment.road_segment_id]}
          isLightMode={isLightMode}
            />
          ))
        )
          ) : (
        <AIPredictionsPanel segments={segments} isLightMode={isLightMode} />
          )}
        </div>

        {/* Footer Stats */}
        <div className={`px-4 py-2.5 rounded-b-3xl ${isLightMode ? 'bg-white/95' : 'bg-[#0D0D0D]'}`}>
          <div className="flex items-center justify-between text-xs font-medium">
        <span className="text-[#F65715] uppercase">
          {filteredSegments.length} roads monitored
        </span>
        <div className={`flex items-center gap-1.5 ${isLightMode ? 'text-gray-500' : 'text-[#6b7280]'}`}>
          <Clock className="w-3 h-3" />
          <span>Auto-refresh 30s</span>
        </div>
          </div>
        </div>
      </aside>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;

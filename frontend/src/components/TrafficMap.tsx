/**
 * TrafficMap component - Interactive map with Waze-like traffic visualization
 * Uses Mapbox navigation style for real road shapes
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useQuery } from '@tanstack/react-query';
import { trafficApi } from '../services/api';

interface TrafficMapProps {
  onSegmentSelect: (segmentId: string | null) => void;
  selectedSegment: string | null;
  isLightMode: boolean;
  onToggleMode: () => void;
}

const MAPBOX_STYLES = {
  dark: 'mapbox://styles/mapbox/navigation-night-v1',
  light: 'mapbox://styles/mapbox/navigation-day-v1',
} as const;

function TrafficMap({ onSegmentSelect, selectedSegment, isLightMode, onToggleMode }: TrafficMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const activePopup = useRef<mapboxgl.Popup | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const layersAdded = useRef(false);

  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN;
  const hasValidToken = mapboxToken && mapboxToken !== 'your_mapbox_access_token_here';

  if (hasValidToken) {
    mapboxgl.accessToken = mapboxToken;
  }

  const { data: trafficData, isLoading } = useQuery({
    queryKey: ['traffic', 'current'],
    queryFn: trafficApi.getCurrentTraffic,
    refetchInterval: 30000,
  });

  // Fetch predictions for map popup
  const { data: predictionsData } = useQuery({
    queryKey: ['predictions', 'all'],
    queryFn: async () => {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'https://backend-production-e652.up.railway.app'}/api/prediction/segments?time_horizon=30`);
      if (!response.ok) return null;
      return response.json();
    },
    refetchInterval: 60000,
    retry: 1,
  });

  // Add traffic visualization layers
  const addTrafficLayers = useCallback(() => {
    if (!map.current || !trafficData?.data || layersAdded.current) return;

    const pointFeatures = trafficData.data.map((point) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [point.longitude, point.latitude],
      },
      properties: {
        congestion: point.congestion_level,
        road_name: point.road_name,
        segment_id: point.road_segment_id,
        speed: point.average_speed,
      },
    }));

    const pointGeojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: pointFeatures,
    };

    // Remove old layers/sources if they exist
    if (map.current.getLayer('traffic-points')) map.current.removeLayer('traffic-points');
    if (map.current.getLayer('traffic-points-glow')) map.current.removeLayer('traffic-points-glow');
    if (map.current.getSource('traffic')) map.current.removeSource('traffic');

    // Add source
    map.current.addSource('traffic', { type: 'geojson', data: pointGeojson });

    // Glow layer for selected point
    map.current.addLayer({
      id: 'traffic-points-glow',
      type: 'circle',
      source: 'traffic',
      paint: {
        'circle-radius': 20,
        'circle-color': '#F65715',
        'circle-blur': 1,
        'circle-opacity': [
          'case',
          ['==', ['get', 'segment_id'], selectedSegment || ''],
          0.6,
          0
        ],
      },
    });

    // Traffic points layer - Waze-like markers
    map.current.addLayer({
      id: 'traffic-points',
      type: 'circle',
      source: 'traffic',
      paint: {
        'circle-radius': [
          'interpolate', ['linear'], ['zoom'],
          10, 6,
          14, 10,
          18, 14
        ],
        'circle-color': [
          'interpolate', ['linear'], ['get', 'congestion'],
          0, '#00E676',
          3, '#69F0AE',
          5, '#FFD600',
          7, '#FF6D00',
          9, '#FF1744',
          10, '#D50000',
        ],
        'circle-opacity': 0.95,
        'circle-stroke-width': [
          'case',
          ['==', ['get', 'segment_id'], selectedSegment || ''],
          4,
          2
        ],
        'circle-stroke-color': [
          'case',
          ['==', ['get', 'segment_id'], selectedSegment || ''],
          '#F65715',
          isLightMode ? '#ffffff' : '#0D0D0D'
        ],
      },
    });

    // Click handler
    map.current.on('click', 'traffic-points', (e) => {
      if (e.features?.[0]) {
        const segmentId = e.features[0].properties?.segment_id;
        onSegmentSelect(segmentId === selectedSegment ? null : segmentId);
      }
    });

    // Cursor handlers
    map.current.on('mouseenter', 'traffic-points', () => {
      if (map.current) map.current.getCanvas().style.cursor = 'pointer';
    });
    map.current.on('mouseleave', 'traffic-points', () => {
      if (map.current) map.current.getCanvas().style.cursor = '';
    });

    layersAdded.current = true;
  }, [trafficData, selectedSegment, onSegmentSelect, isLightMode]);

  // Update point data without recreating layers
  const updateTrafficData = useCallback(() => {
    if (!map.current || !trafficData?.data) return;

    const pointFeatures = trafficData.data.map((point) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [point.longitude, point.latitude],
      },
      properties: {
        congestion: point.congestion_level,
        road_name: point.road_name,
        segment_id: point.road_segment_id,
        speed: point.average_speed,
      },
    }));

    const pointGeojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: pointFeatures,
    };

    const source = map.current.getSource('traffic') as mapboxgl.GeoJSONSource;
    if (source) {
      source.setData(pointGeojson);
    }
  }, [trafficData]);

  // Toggle map style - controlled by parent
  const handleToggleStyle = useCallback(() => {
    if (!map.current) return;
    
    const newMode = !isLightMode;
    const center = map.current.getCenter();
    const zoom = map.current.getZoom();
    const pitch = map.current.getPitch();
    const bearing = map.current.getBearing();
    
    // Reset layers flag so they get re-added after style change
    layersAdded.current = false;
    
    map.current.setStyle(newMode ? MAPBOX_STYLES.light : MAPBOX_STYLES.dark);
    
    map.current.once('style.load', () => {
      if (!map.current) return;
      
      // Restore view
      map.current.setCenter(center);
      map.current.setZoom(zoom);
      map.current.setPitch(pitch);
      map.current.setBearing(bearing);
      
      // Re-add traffic layers
      setTimeout(() => {
        addTrafficLayers();
        
        // Hide logo
        const logos = document.querySelectorAll('.mapboxgl-ctrl-logo');
        logos.forEach(el => (el as HTMLElement).style.display = 'none');
      }, 100);
    });
    
    // Notify parent
    onToggleMode();
  }, [isLightMode, addTrafficLayers, onToggleMode]);

  // Fly to selected segment
  const flyToSegment = useCallback((segmentId: string) => {
    if (!map.current || !trafficData?.data) return;
    
    const segment = trafficData.data.find(s => s.road_segment_id === segmentId);
    if (!segment) return;

    // Get prediction for this segment
    const prediction = predictionsData?.predictions?.find((p: any) => p.road_segment_id === segmentId);

    if (activePopup.current) activePopup.current.remove();

    map.current.flyTo({
      center: [segment.longitude, segment.latitude],
      zoom: 16,
      pitch: 60,
      bearing: -15,
      duration: 2000,
      essential: true,
      easing: (t) => 1 - Math.pow(1 - t, 3),
    });

    setTimeout(() => {
      if (!map.current) return;
      
      const congestionColor = segment.congestion_level >= 7 ? '#FF1744' : 
                              segment.congestion_level >= 4 ? '#FFD600' : '#00E676';
      const statusText = segment.congestion_level >= 7 ? 'Heavy Traffic' : 
                         segment.congestion_level >= 4 ? 'Moderate' : 'Light Traffic';
      
      // Prediction colors
      const predColor = prediction ? (
        prediction.predicted_congestion >= 7 ? '#FF1744' : 
        prediction.predicted_congestion >= 4 ? '#FFD600' : '#00E676'
      ) : '#6b7280';
      
      const trendArrow = prediction?.trend === 'up' ? '↑' : prediction?.trend === 'down' ? '↓' : '→';
      const trendColor = prediction?.trend === 'up' ? '#FF1744' : prediction?.trend === 'down' ? '#00E676' : '#6b7280';
      
      activePopup.current = new mapboxgl.Popup({ 
        className: 'traffic-popup',
        closeButton: true,
        closeOnClick: false,
        offset: 25,
        maxWidth: '320px'
      })
        .setLngLat([segment.longitude, segment.latitude])
        .setHTML(`
          <div style="padding: 16px; font-family: 'DIN Pro', Inter, system-ui, sans-serif; background: ${isLightMode ? '#ffffff' : '#0D0D0D'}; border-radius: 12px; border: 1px solid ${isLightMode ? '#e5e7eb' : '#323232'};">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
              <div style="width: 12px; height: 12px; border-radius: 50%; background: ${congestionColor}; box-shadow: 0 0 8px ${congestionColor};"></div>
              <span style="font-size: 11px; color: ${isLightMode ? '#6b7280' : '#9ca3af'}; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600;">${statusText}</span>
            </div>
            <h3 style="font-weight: 600; margin: 0 0 12px 0; color: ${isLightMode ? '#111' : '#fff'}; font-size: 16px;">${segment.road_name || 'Unknown Road'}</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: ${prediction ? '12px' : '0'};">
              <div style="background: ${isLightMode ? '#f5f5f5' : '#191919'}; padding: 12px; border-radius: 10px;">
                <div style="font-size: 10px; color: #6b7280; margin-bottom: 4px; text-transform: uppercase;">Congestion</div>
                <div style="font-size: 24px; font-weight: 700; color: ${congestionColor};">${segment.congestion_level}/10</div>
              </div>
              <div style="background: ${isLightMode ? '#f5f5f5' : '#191919'}; padding: 12px; border-radius: 10px;">
                <div style="font-size: 10px; color: #6b7280; margin-bottom: 4px; text-transform: uppercase;">Speed</div>
                <div style="font-size: 24px; font-weight: 700; color: ${isLightMode ? '#111' : '#fff'};">${segment.average_speed}<span style="font-size: 12px; color: #6b7280;"> km/h</span></div>
              </div>
            </div>
            ${prediction ? `
            <div style="background: ${isLightMode ? '#fff7ed' : '#1a1a1a'}; padding: 10px 12px; border-radius: 10px; border: 1px solid ${isLightMode ? '#fed7aa' : '#F65715'}33; display: flex; align-items: center; gap: 12px;">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F65715" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
              <div style="flex: 1;">
                <div style="font-size: 9px; color: #6b7280; text-transform: uppercase;">In 30min</div>
                <div style="font-size: 18px; font-weight: 700; color: ${predColor};">${prediction.predicted_congestion?.toFixed?.(1) || prediction.predicted_congestion}/10</div>
              </div>
              <div style="font-size: 18px; color: ${trendColor}; font-weight: bold;">${trendArrow}</div>
              <div style="text-align: right;">
                <div style="font-size: 9px; color: #6b7280;">Confidence</div>
                <div style="font-size: 13px; font-weight: 600; color: #F65715;">${((prediction.confidence || 0.85) * 100).toFixed(0)}%</div>
              </div>
            </div>
            </div>
            ` : ''}
          </div>
        `)
        .addTo(map.current);
    }, 1500);
  }, [trafficData, predictionsData, isLightMode]);

  // Handle segment selection
  useEffect(() => {
    if (selectedSegment && mapLoaded) {
      flyToSegment(selectedSegment);
    } else if (!selectedSegment && map.current) {
      if (activePopup.current) activePopup.current.remove();
      map.current.flyTo({
        center: [-7.6187, 33.5928],
        zoom: 12,
        pitch: 0,
        bearing: 0,
        duration: 1500,
        easing: (t) => 1 - Math.pow(1 - t, 3),
      });
    }
  }, [selectedSegment, mapLoaded, flyToSegment]);

  // Initialize map
  useEffect(() => {
    if (map.current || !mapContainer.current) return;

    if (!hasValidToken) {
      setMapError('Mapbox token not configured');
      return;
    }

    try {
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: MAPBOX_STYLES.dark,
        center: [-7.6187, 33.5928],
        zoom: 12,
        attributionControl: false,
        logoPosition: 'bottom-left',
      });

      map.current.on('load', () => {
        setMapLoaded(true);
        setMapError(null);
        
        // Hide logo
        const logos = document.querySelectorAll('.mapboxgl-ctrl-logo');
        logos.forEach(el => (el as HTMLElement).style.display = 'none');
        
        // Add traffic layers after map loads
        if (trafficData?.data) {
          addTrafficLayers();
        }
      });

      map.current.on('error', (e) => {
        console.error('Map error:', e);
        setMapError(e.error?.message || 'Map failed to load');
      });

      map.current.addControl(new mapboxgl.NavigationControl(), 'bottom-right');
      map.current.addControl(new mapboxgl.ScaleControl({ maxWidth: 100 }), 'bottom-left');

      const resizeObserver = new ResizeObserver(() => map.current?.resize());
      if (mapContainer.current) {
        resizeObserver.observe(mapContainer.current);
      }

      return () => {
        resizeObserver.disconnect();
        map.current?.remove();
        map.current = null;
      };
    } catch (err) {
      console.error('Failed to initialize map:', err);
      setMapError('Failed to initialize map');
    }
  }, [hasValidToken]);

  // Add layers when traffic data loads
  useEffect(() => {
    if (!map.current || !mapLoaded || !trafficData?.data) return;
    
    if (!layersAdded.current) {
      addTrafficLayers();
    } else {
      updateTrafficData();
    }
  }, [mapLoaded, trafficData, addTrafficLayers, updateTrafficData]);

  // Sync map style when isLightMode prop changes from parent
  const prevLightMode = useRef(isLightMode);
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (prevLightMode.current !== isLightMode) {
      prevLightMode.current = isLightMode;
      
      const center = map.current.getCenter();
      const zoom = map.current.getZoom();
      const pitch = map.current.getPitch();
      const bearing = map.current.getBearing();
      
      layersAdded.current = false;
      map.current.setStyle(isLightMode ? MAPBOX_STYLES.light : MAPBOX_STYLES.dark);
      
      map.current.once('style.load', () => {
        if (!map.current) return;
        map.current.setCenter(center);
        map.current.setZoom(zoom);
        map.current.setPitch(pitch);
        map.current.setBearing(bearing);
        
        setTimeout(() => {
          addTrafficLayers();
          const logos = document.querySelectorAll('.mapboxgl-ctrl-logo');
          logos.forEach(el => (el as HTMLElement).style.display = 'none');
        }, 100);
      });
    }
  }, [isLightMode, mapLoaded, addTrafficLayers]);

  // Update selection highlighting
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    if (map.current.getLayer('traffic-points')) {
      map.current.setPaintProperty('traffic-points', 'circle-stroke-width', [
        'case', ['==', ['get', 'segment_id'], selectedSegment || ''], 4, 2
      ]);
      map.current.setPaintProperty('traffic-points', 'circle-stroke-color', [
        'case', ['==', ['get', 'segment_id'], selectedSegment || ''], '#F65715', isLightMode ? '#ffffff' : '#0D0D0D'
      ]);
    }

    if (map.current.getLayer('traffic-points-glow')) {
      map.current.setPaintProperty('traffic-points-glow', 'circle-opacity', [
        'case', ['==', ['get', 'segment_id'], selectedSegment || ''], 0.6, 0
      ]);
    }
  }, [selectedSegment, mapLoaded, isLightMode]);

  return (
    <div className="relative w-full h-full bg-[#050608]">
      <style>{`
        .mapboxgl-ctrl-logo { display: none !important; }
        .mapboxgl-ctrl-attrib { display: none !important; }
        .mapboxgl-popup-content { 
          background: transparent !important; 
          padding: 0 !important; 
          box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
          border-radius: 12px !important;
        }
        .mapboxgl-popup-tip { display: none !important; }
        .mapboxgl-popup-close-button { 
          color: ${isLightMode ? '#666' : '#999'} !important; 
          font-size: 20px !important;
          padding: 8px !important;
          right: 4px !important;
          top: 4px !important;
        }
      `}</style>
      
      <div ref={mapContainer} className="absolute inset-0" style={{ width: '100%', height: '100%' }} />
      
      {/* Dark/Light Overlay - 75% tint to match app aesthetic */}
      <div 
        className={`absolute inset-0 pointer-events-none transition-colors duration-500 ${
          isLightMode 
            ? 'bg-[#f5f5f5]/25' 
            : 'bg-[#0D0D0D]/35'
        }`} 
      />
      
      {/* Error State */}
      {mapError && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm z-50">
          <div className="bg-slate-800 border border-red-500/30 rounded-2xl p-8 max-w-md text-center shadow-2xl">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Map Error</h3>
            <p className="text-slate-400 mb-4">{mapError}</p>
            {!hasValidToken && (
              <div className="bg-slate-900 rounded-lg p-4 text-left">
                <p className="text-sm text-slate-300 mb-2">Add your Mapbox token to:</p>
                <code className="text-xs text-green-400 block bg-black/50 p-2 rounded">
                  frontend/.env<br/>
                  VITE_MAPBOX_TOKEN=pk.xxx
                </code>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading State */}
      {!mapLoaded && !mapError && hasValidToken && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0d0f12] z-40">
          <div className="flex flex-col items-center gap-4">
            <div className="w-14 h-14 border-4 border-[#F65715]/30 border-t-[#F65715] rounded-full animate-spin"></div>
            <p className="text-[#9ca3af] text-xl">Loading map...</p>
          </div>
        </div>
      )}

      {/* Loading Traffic Data */}
      {isLoading && mapLoaded && (
        <div className={`absolute top-6 right-6 px-4 py-2 rounded-lg text-sm font-medium border z-10 flex items-center gap-2 ${
          isLightMode ? 'bg-white/90 text-gray-700 border-gray-200' : 'bg-[#0D0D0D]/90 text-white border-[#323232]'
        }`}>
          <div className="w-2 h-2 bg-[#F65715] rounded-full animate-pulse"></div>
          Updating...
        </div>
      )}

      {/* Google Live Indicator + Light/Dark Toggle */}
      {!isLoading && mapLoaded && trafficData && (
        <div className="absolute top-6 right-6 z-10 flex flex-col gap-2">
          {/* Google LIVE */}
          <div className={`backdrop-blur-sm px-4 py-2 rounded-lg border ${
            isLightMode ? 'bg-white/90 border-gray-200' : 'bg-[#0D0D0D]/90 border-[#323232]'
          }`}>
            <div className="flex items-center gap-2">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#4285f4">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34a853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#fbbc04"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#ea4335"/>
              </svg>
              <span className={`text-sm font-medium ${isLightMode ? 'text-gray-400' : 'text-white/50'}`}>LIVE</span>
            </div>
          </div>
          
          {/* Minimal Light/Dark Toggle */}
          <button
            onClick={handleToggleStyle}
            className={`backdrop-blur-sm px-4 py-2 rounded-lg border transition-all duration-200 flex items-center justify-center gap-2 ${
              isLightMode 
                ? 'bg-white/90 border-gray-200 text-gray-500 hover:text-gray-700' 
                : 'bg-[#0D0D0D]/90 border-[#323232] text-white/50 hover:text-white'
            }`}
            title={isLightMode ? 'Dark Mode' : 'Light Mode'}
          >
            {isLightMode ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            )}
            <span className="text-xs font-medium">{isLightMode ? 'Dark' : 'Light'}</span>
          </button>
        </div>
      )}

      {/* Legend */}
      <div className={`absolute bottom-8 right-8 z-20 backdrop-blur-sm border p-6 rounded-2xl shadow-lg ${
        isLightMode ? 'bg-white/95 border-gray-200' : 'bg-[#0D0D0D] border-[#323232]'
      }`}>
        <h3 className={`text-sm uppercase tracking-widest font-semibold mb-4 ${
          isLightMode ? 'text-gray-500' : 'text-[#7a8289]'
        }`}>Traffic Status</h3>
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-4">
            <div className="w-3 h-3 rounded-full bg-[#00E676] shadow-[0_0_8px_#00E676]"></div>
            <span className={`text-sm font-medium ${isLightMode ? 'text-gray-600' : 'text-[#c4c9cf]'}`}>Light</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-3 h-3 rounded-full bg-[#FFD600] shadow-[0_0_8px_#FFD600]"></div>
            <span className={`text-sm font-medium ${isLightMode ? 'text-gray-600' : 'text-[#c4c9cf]'}`}>Moderate</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-3 h-3 rounded-full bg-[#FF1744] shadow-[0_0_8px_#FF1744]"></div>
            <span className={`text-sm font-medium ${isLightMode ? 'text-gray-600' : 'text-[#c4c9cf]'}`}>Heavy</span>
          </div>
        </div>
        {selectedSegment && (
          <div className={`mt-4 pt-4 border-t ${isLightMode ? 'border-gray-200' : 'border-[#323232]'}`}>
            <button 
              onClick={() => onSegmentSelect(null)}
              className="text-sm text-[#F65715] hover:text-[#ff7d46] transition-colors flex items-center gap-2 font-medium"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Clear Selection
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default TrafficMap;

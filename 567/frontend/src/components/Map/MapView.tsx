import { useRef, useEffect, useCallback, useState, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, Circle, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { Photo, Track, PhotoCluster } from '@/types';
import { useStore } from '@/store/useStore';
import { getPhotoEffectiveGPS } from '@/utils/export';
import { getAllTracksBounds } from '@/utils/gpx';
import { clusterPhotos, getPhotosSortedByTime } from '@/utils/cluster';
import { getDisplayGPS } from '@/utils/privacy';

const TILE_LAYERS = [
  { name: 'OpenStreetMap', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: '&copy; OpenStreetMap' },
  { name: 'Satellite', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attribution: 'Tiles &copy; Esri' },
];

function createPhotoMarkerIcon(selected: boolean, isAnimating: boolean = false): L.DivIcon {
  const color = selected ? '#ff6b35' : '#00d4ff';
  const size = selected ? 32 : isAnimating ? 30 : 24;
  const animClass = isAnimating ? 'animate-pulse' : '';
  
  return L.divIcon({
    className: 'custom-marker',
    html: `<div class="${animClass}" style="width: ${size}px; height: ${size}px; background: ${color}; border: 3px solid white; border-radius: 50%; box-shadow: 0 2px 8px rgba(0,0,0,0.3); position: relative;">
      <div style="position: absolute; bottom: -6px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 6px solid white;"></div>
    </div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function createClusterIcon(cluster: PhotoCluster): L.DivIcon {
  const count = cluster.photos.length;
  const size = Math.min(60, Math.max(30, 20 + count * 3));
  
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="width: ${size}px; height: ${size}px; background: ${cluster.color}cc; border: 3px solid white; border-radius: 50%; box-shadow: 0 2px 12px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; position: relative;">
      <span style="color: white; font-size: ${Math.min(16, 10 + count)}px; font-weight: 700;">${count}</span>
      <div style="position: absolute; bottom: -6px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 6px solid white;"></div>
    </div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function MapEvents() {
  const { selectedPhotoId, selectPhoto, setManualGps } = useStore();
  const map = useMap();
  useMapEvents({
    click: (e) => {
      if (selectedPhotoId) {
        setManualGps(selectedPhotoId, { lat: e.latlng.lat, lng: e.latlng.lng });
      }
    },
  });
  return null;
}

function MapController({ tracks, photos }: { tracks: Track[]; photos: Photo[] }) {
  const map = useMap();
  const boundsRef = useRef<string | null>(null);
  useEffect(() => {
    const trackBounds = getAllTracksBounds(tracks);
    const photoGpsPoints = photos.map(p => getPhotoEffectiveGPS(p)).filter((g): g is NonNullable<typeof g> => !!g);
    let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity;
    if (trackBounds) {
      minLat = Math.min(minLat, trackBounds[0][0]); maxLat = Math.max(maxLat, trackBounds[1][0]);
      minLng = Math.min(minLng, trackBounds[0][1]); maxLng = Math.max(maxLng, trackBounds[1][1]);
    }
    photoGpsPoints.forEach(p => { minLat = Math.min(minLat, p.lat); maxLat = Math.max(maxLat, p.lat); minLng = Math.min(minLng, p.lng); maxLng = Math.max(maxLng, p.lng); });
    if (minLat !== Infinity) {
      const boundsKey = `${minLat}-${maxLat}-${minLng}-${maxLng}`;
      if (boundsKey !== boundsRef.current) { boundsRef.current = boundsKey; map.fitBounds([[minLat, minLng], [maxLat, maxLng]], { padding: [50, 50] }); }
    }
  }, [tracks, photos, map]);
  return null;
}

function AnimationPlayer() {
  const { photos, animation, setAnimation, selectPhoto, privacy } = useStore();
  const map = useMap();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  const sortedPhotos = useMemo(() => getPhotosSortedByTime(photos), [photos]);
  
  useEffect(() => {
    if (animation.isPlaying && sortedPhotos.length > 0) {
      const interval = Math.max(100, 1000 / animation.speed);
      timerRef.current = setTimeout(() => {
        const nextIndex = animation.currentIndex + 1;
        if (nextIndex >= sortedPhotos.length) {
          if (animation.loop) {
            setAnimation({ currentIndex: 0 });
          } else {
            setAnimation({ isPlaying: false, currentIndex: sortedPhotos.length - 1 });
          }
        } else {
          setAnimation({ currentIndex: nextIndex });
        }
      }, interval);
    }
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [animation.isPlaying, animation.currentIndex, animation.speed, animation.loop, sortedPhotos.length, setAnimation]);
  
  useEffect(() => {
    if (animation.isPlaying && sortedPhotos.length > 0 && animation.currentIndex < sortedPhotos.length) {
      const photo = sortedPhotos[animation.currentIndex];
      const gps = getDisplayGPS(photo, privacy);
      if (gps) {
        map.flyTo([gps.lat, gps.lng], map.getZoom(), { duration: 0.3 });
        selectPhoto(photo.id);
      }
    }
  }, [animation.currentIndex, animation.isPlaying, sortedPhotos, map, selectPhoto, privacy]);
  
  return null;
}

export default function MapView() {
  const { photos, tracks, selectedPhotoId, selectPhoto, animation, privacy, showClusters, clusterDistance } = useStore();
  
  const clusters = useMemo(() => {
    if (!showClusters) return [];
    return clusterPhotos(photos, clusterDistance);
  }, [photos, showClusters, clusterDistance]);
  
  const sortedPhotos = useMemo(() => getPhotosSortedByTime(photos), [photos]);
  const animatingPhotoId = animation.isPlaying && animation.currentIndex < sortedPhotos.length
    ? sortedPhotos[animation.currentIndex].id : null;
  
  const trailPhotos = useMemo(() => {
    if (!animation.isPlaying || !animation.showTrail) return [];
    const start = Math.max(0, animation.currentIndex - animation.trailLength);
    return sortedPhotos.slice(start, animation.currentIndex + 1);
  }, [animation.isPlaying, animation.showTrail, animation.currentIndex, animation.trailLength, sortedPhotos]);

  const getPhotoPosition = useCallback((photo: Photo) => {
    const gps = getDisplayGPS(photo, privacy);
    return gps ? [gps.lat, gps.lng] as [number, number] : null;
  }, [privacy]);

  const trackColors = ['#00d4ff', '#ff6b35', '#7c3aed', '#22c55e', '#f59e0b'];
  const [tileIndex, setTileIndex] = useState(0);

  return (
    <MapContainer center={[39.9042, 116.4074]} zoom={10} style={{ width: '100%', height: '100%' }}>
      <TileLayer url={TILE_LAYERS[tileIndex].url} attribution={TILE_LAYERS[tileIndex].attribution} />
      
      <MapEvents />
      <MapController tracks={tracks} photos={photos} />
      <AnimationPlayer />
      
      <div className="leaflet-top leaflet-right" style={{ zIndex: 1000 }}>
        <div className="leaflet-control">
          <button
            onClick={() => setTileIndex(i => (i + 1) % TILE_LAYERS.length)}
            className="bg-white shadow-md rounded-lg px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 m-2"
          >
            {TILE_LAYERS[tileIndex].name}
          </button>
        </div>
      </div>
      
      {tracks.map((track, index) => (
        <Polyline
          key={track.id}
          positions={track.points.map(p => [p.lat, p.lng] as [number, number])}
          color={trackColors[index % trackColors.length]}
          weight={3}
          opacity={0.8}
        />
      ))}
      
      {animation.isPlaying && animation.showTrail && trailPhotos.length > 1 && (
        <Polyline
          positions={trailPhotos.map(p => getPhotoPosition(p)).filter(Boolean) as [number, number][]}
          color="#ff6b35"
          weight={3}
          opacity={0.6}
          dashArray="8, 8"
        />
      )}
      
      {showClusters ? (
        clusters.map(cluster => (
          <div key={cluster.id}>
            <Circle
              center={[cluster.center.lat, cluster.center.lng]}
              radius={cluster.radius || 10}
              pathOptions={{ color: cluster.color, fillColor: cluster.color, fillOpacity: 0.15, weight: 2 }}
            />
            <Marker
              position={[cluster.center.lat, cluster.center.lng]}
              icon={createClusterIcon(cluster)}
            >
              <Popup>
                <div className="min-w-[160px]">
                  <p className="text-sm font-semibold mb-2">{cluster.photos.length} 张照片</p>
                  <div className="grid grid-cols-3 gap-1 max-h-[200px] overflow-y-auto">
                    {cluster.photos.slice(0, 12).map(photo => (
                      <img key={photo.id} src={photo.thumbnail} alt={photo.name} className="w-12 h-12 object-cover rounded" />
                    ))}
                  </div>
                  {cluster.photos.length > 12 && (
                    <p className="text-xs text-gray-500 mt-1">还有 {cluster.photos.length - 12} 张...</p>
                  )}
                </div>
              </Popup>
            </Marker>
          </div>
        ))
      ) : (
        photos.map(photo => {
          const position = getPhotoPosition(photo);
          if (!position) return null;
          return (
            <Marker
              key={photo.id}
              position={position}
              icon={createPhotoMarkerIcon(photo.id === selectedPhotoId, photo.id === animatingPhotoId)}
              eventHandlers={{ click: () => selectPhoto(photo.id) }}
            >
              <Popup>
                <div className="text-center min-w-[120px]">
                  <img src={photo.thumbnail} alt={photo.name} className="w-full max-h-[100px] object-cover rounded mb-2" />
                  <p className="text-xs font-medium truncate">{photo.name}</p>
                  {photo.exifData.dateTimeOriginal && (
                    <p className="text-xs text-gray-500">{photo.exifData.dateTimeOriginal.toLocaleString()}</p>
                  )}
                  {privacy.enabled && privacy.applyToDisplay && (
                    <p className="text-xs text-orange-500 mt-1">🔒 位置已模糊化</p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })
      )}
    </MapContainer>
  );
}

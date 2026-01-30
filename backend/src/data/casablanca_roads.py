"""Casablanca road network data with major roads and intersections for traffic monitoring."""

CASABLANCA_ROADS = [
{"id": "boulevard_mohamed_v", "name": "Boulevard Mohamed V", "start_lat": 33.5928, "start_lng": -7.6187, "end_lat": 33.5731, "end_lng": -7.5898, "importance": "high"},
{"id": "boulevard_zerktouni", "name": "Boulevard Zerktouni", "start_lat": 33.5881, "start_lng": -7.6117, "end_lat": 33.5781, "end_lng": -7.6247, "importance": "high"},
{"id": "avenue_hassan_ii", "name": "Avenue Hassan II", "start_lat": 33.5928, "start_lng": -7.6187, "end_lat": 33.5981, "end_lng": -7.6387, "importance": "high"},
{"id": "boulevard_moulay_youssef", "name": "Boulevard Moulay Youssef", "start_lat": 33.5831, "start_lng": -7.6017, "end_lat": 33.5731, "end_lng": -7.5917, "importance": "high"},
{"id": "avenue_des_far", "name": "Avenue des FAR", "start_lat": 33.5881, "start_lng": -7.6317, "end_lat": 33.5781, "end_lng": -7.6117, "importance": "high"},
{"id": "boulevard_anfa", "name": "Boulevard d'Anfa", "start_lat": 33.5931, "start_lng": -7.6387, "end_lat": 33.5731, "end_lng": -7.6587, "importance": "high"},
{"id": "corniche_ain_diab", "name": "Corniche Ain Diab", "start_lat": 33.5731, "start_lng": -7.6687, "end_lat": 33.5531, "end_lng": -7.6887, "importance": "medium"},
{"id": "boulevard_brahim_roudani", "name": "Boulevard Brahim Roudani", "start_lat": 33.6031, "start_lng": -7.6217, "end_lat": 33.5831, "end_lng": -7.6017, "importance": "medium"},
{"id": "avenue_mers_sultan", "name": "Avenue Mers Sultan", "start_lat": 33.5881, "start_lng": -7.6117, "end_lat": 33.5781, "end_lng": -7.6317, "importance": "medium"},
{"id": "boulevard_rachidi", "name": "Boulevard Rachidi", "start_lat": 33.5981, "start_lng": -7.6087, "end_lat": 33.5881, "end_lng": -7.5987, "importance": "medium"},
{"id": "route_el_jadida", "name": "Route d'El Jadida", "start_lat": 33.5631, "start_lng": -7.6387, "end_lat": 33.5431, "end_lng": -7.6587, "importance": "medium"},
{"id": "autoroute_rabat", "name": "Autoroute de Rabat (A3)", "start_lat": 33.6131, "start_lng": -7.6087, "end_lat": 33.6531, "end_lng": -7.5787, "importance": "high"},
{"id": "boulevard_bir_anzarane", "name": "Boulevard Bir Anzarane", "start_lat": 33.5731, "start_lng": -7.5787, "end_lat": 33.5531, "end_lng": -7.5587, "importance": "medium"},
{"id": "avenue_2_mars", "name": "Avenue 2 Mars", "start_lat": 33.5931, "start_lng": -7.6187, "end_lat": 33.5831, "end_lng": -7.6087, "importance": "medium"},
{"id": "boulevard_abdelmoumen", "name": "Boulevard Abdelmoumen", "start_lat": 33.5781, "start_lng": -7.6387, "end_lat": 33.5681, "end_lng": -7.6487, "importance": "high"},
]

KEY_INTERSECTIONS = [
{"id": "place_nations_unies", "name": "Place des Nations Unies", "lat": 33.5928, "lng": -7.6187, "importance": "high"},
{"id": "place_mohammed_v", "name": "Place Mohammed V", "lat": 33.5881, "lng": -7.6117, "importance": "high"},
{"id": "maarif", "name": "Maarif", "lat": 33.5831, "lng": -7.6317, "importance": "high"},
{"id": "gauthier", "name": "Gauthier", "lat": 33.5781, "lng": -7.6217, "importance": "medium"},
]


def generate_monitoring_points():
    """Generate monitoring points along each road segment."""
    monitoring_points = []
    
    for road in CASABLANCA_ROADS:
        for i in range(5):
            ratio = i / 4.0
            lat = road["start_lat"] + (road["end_lat"] - road["start_lat"]) * ratio
            lng = road["start_lng"] + (road["end_lng"] - road["start_lng"]) * ratio
            
            monitoring_points.append({
                "road_segment_id": f"{road['id']}_point_{i+1}", "road_name": road["name"], "latitude": lat, "longitude": lng, "point_index": i + 1, "importance": road["importance"]
            })
    
    return monitoring_points


__all__ = ["CASABLANCA_ROADS", "KEY_INTERSECTIONS", "generate_monitoring_points"]

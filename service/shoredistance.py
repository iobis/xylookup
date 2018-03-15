import math, json, gc, os
import numpy as np
from scipy.spatial import cKDTree
import service.config as config

_coastlines, _coastpoints, _tree = None, None, None


def _init():
    v = '5'  # '50' for lower resolution
    global _coastlines, _coastpoints, _tree
    _coastpoints, _coastlines = _load_coastlines(os.path.join(config.datadir, "shoredistance/coastlines"+v+".jsonlines"))
    _tree = _build_kdtree(_coastpoints)


def _load_coastlines(path):
    with open(path) as f:
        coastlines = [0]
        points = []
        try:
            pointsoffset = 0
            for fid, line in enumerate(f):
                featuredict = json.loads(line)
                coordinates = featuredict["coordinates"]
                if len(coordinates) == 1:
                    print(fid, len(featuredict["coordinates"]), "Should be more than 1 xy pair in a LineString")
                p = np.array([tuple(xy) for xy in coordinates])
                points.append(p)
                pointsoffset += len(p)
                coastlines.append(pointsoffset)
                if fid > 1 and fid % 100000 == 0:
                    gc.collect()
        except:
            print(fid)
        gc.collect()
        return np.concatenate(points), np.array(coastlines)


def _np_to_cartesian(p):
    # convert lat lon to cartesian coordinates
    lat,lon = np.radians(p[:, 1]), np.radians(p[:, 0])
    points = np.zeros((len(p), 3))
    points[:, 0] = np.cos(lat) * np.cos(lon) # x
    points[:, 1] = np.cos(lat) * np.sin(lon) # y
    points[:, 2] = np.sin(lat)               # z
    return points


def _np_gc_distance(p, points):
    """ http://www.movable-type.co.uk/scripts/latlong.html """
    dLon = np.radians(points[:, 0] - p[0])  # * 0.0174532925
    lat1 = np.radians(p[1])
    lat2 = np.radians(points[:,1])
    return np.arccos(np.sin(lat1) * np.sin(lat2) + np.cos(lat1) * np.cos(lat2) * np.cos(dLon))


def _build_kdtree(coastpoints):
    points = _np_to_cartesian(coastpoints)
    tree = cKDTree(points)
    return tree


def _gc_distance(A, B):
    """ http://www.movable-type.co.uk/scripts/latlong.html """
    dLon = math.radians(B[0]-A[0])  # * 0.0174532925
    if abs(dLon) < 1.7453e-10 and abs(math.radians(B[1]-A[1])) < 1.7453e-10:
        return 0
    lat1 = math.radians(A[1])
    lat2 = math.radians(B[1])
    return math.acos(math.sin(lat1)*math.sin(lat2) + math.cos(lat1)*math.cos(lat2) * math.cos(dLon))


def _gc_distancetoline(p, A, B):
    """ http://www.movable-type.co.uk/scripts/latlong.html """
    xd = B[0] - A[0]
    yd = B[1] - A[1]
    r = ((p[0]- A[0])*(xd) + (p[1]- A[1])*yd)/(xd*xd + yd*yd)
    if 0 < r < 1:
        pointOnLine = (A[0] + r * xd, A[1] + r * yd)
        return _gc_distance(p, pointOnLine)
    else:
        return float("Inf") # minimum distance to p, A and p, B has already been calculated


def _getcoastlinedistance(positions, tree, coastpoints, coastlines):
    radius = 6371000
    positions = np.array(positions)
    _, indexes = tree.query(_np_to_cartesian(positions), k=5, eps=0.00001, p=2)
    mindistances = np.zeros(len(positions))
    for i, p in enumerate(positions):
        distances = _np_gc_distance(p, coastpoints[indexes[i,]])
        mindistance = distances[0]
        if mindistance < (5000.0 / radius):  # less than 5 km
            maxresultindex = np.searchsorted(distances, distances[0] + (250.0 / radius), side="left")
            for resultsindex in range(maxresultindex):
                point_index = indexes[i,resultsindex]
                coastline_index = np.searchsorted(coastlines, point_index, side="right")
                minpointindex_coastline = coastlines[coastline_index-1]
                maxpointindex_coastline = coastlines[coastline_index] - 1
                d1, d2 = None, None # d1 line to the left, d2 line to the right
                if point_index > minpointindex_coastline:
                    d1 = _gc_distancetoline(p, coastpoints[point_index - 1], coastpoints[point_index])
                if point_index < maxpointindex_coastline:
                    d2 = _gc_distancetoline(p, coastpoints[point_index], coastpoints[point_index + 1])
                if (not d1 or not d2) and np.array_equal(coastpoints[minpointindex_coastline], coastpoints[maxpointindex_coastline]): # polygon coastline
                    if not d1:
                        d1 = _gc_distancetoline(p, coastpoints[maxpointindex_coastline], coastpoints[maxpointindex_coastline-1]) # laatste segment
                    if not d2:
                        d2 = _gc_distancetoline(p, coastpoints[minpointindex_coastline], coastpoints[minpointindex_coastline+1]) # eerste segment
                if d1 and d1 < mindistance:
                    mindistance = d1
                if d2 and d2 < mindistance:
                    mindistance = d2
        mindistances[i] = mindistance

    return mindistances * radius


def _on_land(cur, pointstable, npoints):
    cur.execute("""
    SELECT pts.id
      FROM {0} pts
 LEFT JOIN water_polygons0_00005 all_water ON ST_DWithin(all_water.geom, pts.geom, 0)
     WHERE all_water.geom IS NULL
    """.format(pointstable))
    ids_onland = cur.fetchall()
    ids_onland = [id[0] for id in ids_onland]  # tuple to element
    onland = np.ones(npoints)
    onland[ids_onland] = -1
    return onland


def get_shoredistance(cur, points, pointstable):
    distances = np.zeros(len(points))
    chunksize = 1000
    chunks = [points[i:i + chunksize] for i in range(0, len(points), chunksize)]
    for i, chunk in enumerate(chunks):
        distances[i*chunksize:((i+1)*chunksize)] = _getcoastlinedistance(chunk, _tree, _coastpoints, _coastlines)
    onland = _on_land(cur, pointstable, len(points))
    return np.round(distances * onland)


_init()  # Initialize the _tree, _coatlines and _coast_points data structures (slow but necessary)


if __name__ == "__main__":
    def _get_test_points():
        import psycopg2
        conn = psycopg2.connect("dbname=xylookup user=postgres port=5432 password=postgres")
        cur = conn.cursor()
        cur.execute("SELECT x, y FROM test_points_100000")
        points = cur.fetchall()
        return [tuple(point) for point in points]
    tp = _get_test_points()
    print("Ready for landdistance :-)")

    #http: // localhost:8000 / lookup?x = 2.922825, 2.918780, 0 & y = 51.236716, 51.237912, 0 & shoredistance = 1 & grids = 0 & areas = 0
    tp = [[2.922825,51.236716], [2.918780,51.237912]]
    def landdistance():
        positions = tp
        chunksize = 1000
        chunks = [positions[i:i + chunksize] for i in range(0, len(positions), chunksize)]
        for i, chunk in enumerate(chunks):
            try:
                _getcoastlinedistance(chunk, _tree, _coastpoints, _coastlines)
            except:
                print("error " + str(i))

    import cProfile
    cProfile.runctx('landdistance()', globals(), locals())
    # print_timing(landdistance)()

    # _test_getlanddistance3('50')


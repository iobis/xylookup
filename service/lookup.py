import simplejson as json
import msgpack
import falcon
import psycopg2
import uuid
import numpy as np
import sys
if sys.version_info[0] == 2:
    from StringIO import StringIO
else:
    from io import StringIO
import service.areas as areas
import service.rasters as rasters
import service.shoredistance as shoredistance
import service.config as config

conn = psycopg2.connect(config.connstring)


def points_to_file(points):
    txt = "\n".join(["{}\tSRID=4326;POINT({} {})'".format(idx, xy[0], xy[1]) for idx, xy in enumerate(points)])
    return StringIO(txt)


def load_points(cur, points, geog=False):
    tmptable = "tmp" + str(uuid.uuid4()).replace("-", "")
    cur.execute("""CREATE TABLE {0}(id INTEGER);
       SELECT AddGeometryColumn('{0}', 'geom', 4326, 'POINT', 2);
       CREATE INDEX {0}_geom_gist ON {0} USING gist(geom);""".format(tmptable))
    f = points_to_file(points)
    cur.copy_from(f, tmptable, columns = ('id', 'geom'))
    if geog:
        cur.execute("""ALTER TABLE {0} ADD COLUMN geog geography;
            UPDATE {0} SET geog = geom::geography;
            CREATE INDEX {0}_geog_gist ON {0} USING gist(geog);""".format(tmptable))
    return tmptable


def get_param_as_bool_with_default(req, paramname, default=False):
    v = req.get_param_as_bool(paramname, blank_as_true=default)
    if v is None:
        v = default
    return v


def get_param_as_int_with_default(req, paramname, required=False, min=None, max=None, default= 0):
    v = req.get_param_as_int(paramname, required=required, min=min, max=max)
    if v is None:
        v = default
    return v


def lookup(req):
    # points should be a nested array of x,y coordinates
    if req.method == "POST":
        try:
            raw_data = req.stream.read()
        except Exception as ex:
            raise falcon.HTTPError(falcon.HTTP_400, 'Error reading data from POST', str(ex))

        if req.content_type and req.content_type.lower() == falcon.MEDIA_MSGPACK:
            try:
                data = msgpack.unpackb(raw_data, use_list=False, raw=False)
            except Exception:
                raise falcon.HTTPError(falcon.HTTP_400, 'Invalid msgpack', 'Could not decode the request body. The msgpack was incorrect.')
        else:
            try:
                data = json.loads(raw_data)
            except ValueError:
                raise falcon.HTTPError(falcon.HTTP_400, 'Invalid JSON', 'Could not decode the request body. The ''JSON was incorrect.')
        if not data or type(data) is not dict or len(data) == 0:
            raise falcon.HTTPInvalidParam('Request POST data should be a JSON object/Python dictionary/R list', 'POST body')
        points = data.get("points", None)
        if not points or len(points) == 0:
            raise falcon.HTTPInvalidParam('No points provided', 'points')
        pareas = data.get('areas', True)
        pgrids = data.get('grids', True)
        pshoredistance = data.get('shoredistance', True)
        pareasdistancewithin = data.get('areasdistancewithin', 0) # distance to search for areas
    else:
        x = req.get_param_as_list('x')
        y = req.get_param_as_list('y')
        pareas = get_param_as_bool_with_default(req, 'areas', default=True)
        pgrids = get_param_as_bool_with_default(req, 'grids', default=True)
        pshoredistance = get_param_as_bool_with_default(req, 'shoredistance', default=True)
        pareasdistancewithin = get_param_as_int_with_default(req, 'areasdistancewithin', min=0, default=0)
        if not x or not y or len(x) == 0 or len(y) == 0:
            raise falcon.HTTPInvalidParam('Missing parameters x and/or y', 'x/y')
        elif len(x) != len(y):
            raise falcon.HTTPInvalidParam('Length of x parameter is different from length of y', 'x/y')
        points = list(zip(x, y))

    points = np.array(points)
    try:
        points = points.astype(float)
    except ValueError:
        raise falcon.HTTPInvalidParam('Coordinates not numeric', 'x/y points')

    if not all([-180 <= p[0] <= 180 and -90 <= p[1] <= 90 for p in points]):
        raise falcon.HTTPInvalidParam('Invalid coordinates (xmin: -180, ymin: -90, xmax: 180, ymax: 90)', 'x/y points')
    try:
        with conn.cursor() as cur:
            pointstable = load_points(cur, points, geog=(pareas and pareasdistancewithin > 0))
            if pareas:
                areavals = areas.get_areas(cur, points, pointstable, pareasdistancewithin)
            if pgrids:
                rastervals = rasters.get_values(points)
            if pshoredistance:
                shoredists = shoredistance.get_shoredistance(cur, points, pointstable)
        results = [{} for _ in range(len(points))]
        for idx, result in enumerate(results):
            if pareas:
                result['areas'] = areavals[idx]
            if pgrids:
                result['grids'] = rastervals[idx]
            if pshoredistance:
                result['shoredistance'] = shoredists[idx]
    except Exception as ex:
        print(ex)
        raise falcon.HTTPError(falcon.HTTP_400, 'Error looking up data for provided points', str(ex))
    finally:
        conn.rollback()
    return results

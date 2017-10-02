import json
import msgpack
import falcon
import psycopg2
import uuid
import areas
import rasters
import shoredistance
import config
import numpy as np
from StringIO import StringIO

conn = psycopg2.connect(config.connstring)


# TODO Add support for datetime
def points_to_file(points):
    txt = "\n".join(["{}\tSRID=4326;POINT({} {})'".format(idx, xy[0], xy[1]) for idx, xy in enumerate(points)])
    return StringIO(txt)


def load_points(cur, points):
    tmptable = "tmp" + str(uuid.uuid4()).replace("-", "")
    cur.execute("""CREATE TABLE {0}(id INTEGER);
       SELECT AddGeometryColumn('{0}', 'geom', 4326, 'POINT', 2);
       CREATE INDEX {0}_geom_gist ON {0} USING gist(geom);""".format(tmptable))
    f = points_to_file(points)
    cur.copy_from(f, tmptable, columns = ('id', 'geom'))
    return tmptable


def get_param_as_bool_with_default(req, paramname, default=False):
    v = req.get_param_as_bool(paramname, blank_as_true=default)
    if v is None:
        v = default
    return v


def lookup(req):
    # points should be a nested array of x,y coordinates
    if req.method == "POST":
        try:
            raw_data = req.stream.read()
        except Exception as ex:
            raise falcon.HTTPError(falcon.HTTP_400, 'Error reading data from POST', ex.message)

        if req.content_type and req.content_type.lower() == falcon.MEDIA_MSGPACK:
            try:
                data = msgpack.unpackb(raw_data, use_list=False)
            except ValueError:
                raise falcon.HTTPError(falcon.HTTP_400, 'Invalid msgpack', 'Could not decode the request body. The ''msgpack was incorrect.')
        else:
            try:
                data = json.loads(raw_data, encoding='utf-8')
            except ValueError:
                raise falcon.HTTPError(falcon.HTTP_400, 'Invalid JSON', 'Could not decode the request body. The ''JSON was incorrect.')
        if not data or len(data) == 0 or type(data) is not dict:
            raise falcon.HTTPInvalidParam('Request POST data should be a JSON object/Python dictionary/R list', 'POST body')
        points = data.get("points", None)
        if not points or len(points) == 0:
            raise falcon.HTTPInvalidParam('No points provided', 'points')
        pareas = data.get('areas', True)
        pgrids = data.get('grids', True)
        pshoredistance = data.get('shoredistance', True)
    else:
        x = req.get_param_as_list('x')
        y = req.get_param_as_list('y')
        pareas = get_param_as_bool_with_default(req, 'areas', default=True)
        pgrids = get_param_as_bool_with_default(req, 'grids', default=True)
        pshoredistance = get_param_as_bool_with_default(req, 'shoredistance', default=True)
        if not x or not y or len(x) == 0 or len(y) == 0:
            raise falcon.HTTPInvalidParam('Missing parameters x and/or y', 'x/y')
        elif len(x) != len(y):
            raise falcon.HTTPInvalidParam('Length of x parameter is different from length of y', 'x/y')
        points = zip(x, y)

    points = np.array(points)
    try:
        points = points.astype(float)
    except ValueError:
        raise falcon.HTTPInvalidParam('Coordinates not numeric', 'x/y points')

    if not all([-180 <= p[0] <= 180 and -90 <= p[1] <= 90 for p in points]):
        raise falcon.HTTPInvalidParam('Invalid coordinates (xmin: -180, ymin: -90, xmax: 180, ymax: 90)', 'x/y points')
    try:
        with conn.cursor() as cur:
            pointstable = load_points(cur, points)
            if pareas:
                areavals = areas.get_areas(cur, points, pointstable)
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
        raise falcon.HTTPError(falcon.HTTP_400, 'Error looking up data for provided points', ex.message)
    finally:
        conn.rollback()
    return results

import json
import msgpack
import falcon
import psycopg2
import uuid
import areas
import rasters
import shoredistance
from StringIO import StringIO

conn = psycopg2.connect("dbname=xylookup user=postgres port=5432 password=postgres")


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


def lookup(req):
    # points should be a nested array of x,y coordinates
    doc = req.context.get('doc', None)
    if doc:
        if req.get_param('format') == 'msgpack':
            points = msgpack.unpackb(doc, use_list=False)
        else:
            points = json.loads(doc)
    else:
        x = req.get_param_as_list('x')
        y = req.get_param_as_list('y')
        if len(x) != len(y):
            raise falcon.HTTPInvalidParam("Length of x parameter is different from length of y", "x/y")
        points = zip(x, y)
    if not points or len(points) == 0:
        raise falcon.HTTPInvalidParam("No coordinates provided")
    if not all([-180 <= p[0] <= 180 and -90 <= p[1] <= 90 for p in points]):
        raise falcon.HTTPInvalidParam("x,y values outside of the the world (xmin: -180, ymin: -90, xmax: 180, ymax: 90")
    try:
        with conn.cursor() as cur:
            pointstable = load_points(cur, points)
            results = areas.get_areas(cur, points, pointstable)
            rastervals = rasters.get_values(points)
            shoredists = shoredistance.get_shoredistance(cur, points, pointstable)
        for idx, result in results:
            result.extend(rastervals[idx])
            result.append(shoredists[idx])
    finally:
        conn.rollback()
    return results

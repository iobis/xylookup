from __future__ import division
import math
import os
import json
import numpy as np
from datetime import datetime
import config
# INPUT: set of x,y coordinates (+time?, +depth?)
# DATA: set of rasters with metadata (id, extent, time?, depth?) grouped in categories with a hierarchy e.g. first emodnet then gebco bathymetry)
# OUTPUT: for each point the matched raster category, raster id and the value


class Raster:
    def __init__(self, rasterdir, metadata):  # id, category, path, dtype, shape, minx, miny, maxx, maxy, startdate=None, enddate=None, mindepth=None, maxdepth=None
        self.id = metadata['id']
        self.category = metadata['category']
        ncol, nrow =  tuple(metadata['shape'])
        self.nrow = nrow
        self.ncol = ncol
        path = os.path.join(rasterdir, self.id + '.mmf')
        self.data = np.memmap(path, dtype=metadata['dtype'], mode='r', shape=(ncol, nrow))
        self.minx, self.miny = metadata['minx']-1e-12, metadata['miny']-1e-12  # 1e-12 to take care of edge cases
        self.maxx, self.maxy = metadata['maxx']+1e-12, metadata['maxy']+1e-12  # 1e-12 to take care of edge cases
        self.xres, self.yres = metadata['xres'], metadata['yres']
        self.startdate, self.enddate = metadata.get('startdate',datetime.min), metadata.get('enddate',datetime.max)
        self.mindepth, self.maxdepth = metadata.get('mindepth',float("-inf")), metadata.get('maxdepth',float("inf"))
        self.hasdate = self.startdate and self.enddate
        self.hasdepth = self.mindepth and self.maxdepth
        self.nodata = metadata['nodata']

    # def contains_date(self, date):
    #     return self.startdate <= date <= self.enddate
    #
    # def contains_depth(self, depth):
    #     return self.mindepth <= depth <= self.maxdepth

    def contains_points(self, x, y): # x, y should be numpy arrays
        return (self.minx < x) & (x < self.maxx) & (self.miny < y) & (y < self.maxy)

    def get_rows_cols(self, x, y):
        rows, cols = np.floor((y-self.maxy) / self.yres), np.floor((x-self.minx) / self.xres)
        return rows.astype(int), cols.astype(int)

    def get_values(self, x, y):
        cells = self.get_rows_cols(x, y)
        values = self.data[cells]
        okdata = values != self.nodata
        return values, okdata

    def __str__(self):
        return str(self.__dict__)


def get_raster_values(points):
    output = [{} for _ in points]
    x, y = np.array(points).T
    id = np.array(range(0, len(x)))
    for category in categories:
        id_remaining, x_remaining, y_remaining = id, x, y
        for raster in rasters:
            if raster.category == category:
                which = raster.contains_points(x_remaining,y_remaining)
                values, okdata = raster.get_values(x_remaining[which], y_remaining[which])
                values = values[okdata]
                id_ok = id_remaining[which][okdata]
                if len(id_ok) > 0:
                    for i, id in enumerate(id_ok):
                        output[id][category] = values[i]

                    id_remaining = np.array(list(set(id_remaining) - set(id_ok)))
                    if len(id_remaining) > 0:
                        x_remaining = x[id_remaining]
                        y_remaining = y[id_remaining]
    return output

# x = {'id':'A1', 'category':'bathymetry', 'path':os.path.join('/Users/samuel/a/tmp/A1.dat'), 'dtype':'int16', 'shape':(7200, 9480), 'minx':0,'maxx':1,'miny':2,'maxy':3}
# s = pickle.dumps(x)
# r = Raster(pickle.loads(s))
rasterdir = os.path.join(config.datadir, 'rasters')
rasters = map(lambda d:Raster(rasterdir, d), json.load(open(os.path.join(rasterdir, 'rasters.metadata'), 'r')))
categories = set(map(lambda r: r.category, rasters))

def get_values(points):
    return [{"TODO SALINITY": 123, "TODO SST": 456} for _ in points]


if __name__ == "__main__":
    def _get_test_points():
        import psycopg2
        conn = psycopg2.connect("dbname=xylookup user=postgres port=5432 password=postgres")
        cur = conn.cursor()
        cur.execute("SELECT x, y FROM test_points_1000000")
        points = cur.fetchall()
        return [tuple(point) for point in points]
    points = _get_test_points()
    print("Ready for rasters :-)")
    import cProfile
    v = get_raster_values(points)
    cProfile.runctx('get_raster_values(points)', globals(), locals())
    
    # TODO BUG get_raster_values([[-17.48, 84.12, ]]) # SHOULD RETURN -3633.2
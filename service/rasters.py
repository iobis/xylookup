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
        ncol, nrow = tuple(metadata['shape'])
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
        self.bandinfo = metadata['bandinfo']
        self.rasterinfo = metadata['rasterinfo']
        self.nodata = float(metadata['nodata'])
        self.add_offset = float(self.bandinfo.get('add_offset',0))
        self.scale_factor = float(self.bandinfo.get('scale_factor',1.0))

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
        r,c = self.get_rows_cols(x, y)
        values = self.data[r,c]
        okdata = (values <= self.nodata-1e-12) | (values >= self.nodata+1e-12)
        return (values*self.scale_factor+self.add_offset), okdata

    def __str__(self):
        return str(self.__dict__)


def get_raster_values(points):
    output = [{} for _ in points]
    x, y = np.array(points).T
    ids = np.array(range(0, len(x)))
    for category in categories:
        ids_remaining, x_remaining, y_remaining = ids, x, y
        for raster in rasters:
            if raster.category == category:
                which = raster.contains_points(x_remaining,y_remaining)
                values, okdata = raster.get_values(x_remaining[which], y_remaining[which])
                values = values[okdata]
                id_ok = ids_remaining[which][okdata]
                if len(id_ok) > 0:
                    for i, id in enumerate(id_ok):
                        output[id][category] = values[i]

                    ids_remaining = np.array(list(set(ids_remaining) - set(id_ok)))
                    if len(ids_remaining) > 0:
                        x_remaining = x[ids_remaining]
                        y_remaining = y[ids_remaining]
    return output

rasterdir = os.path.join(config.datadir, 'rasters')
rasters = map(lambda d:Raster(rasterdir, d), json.load(open(os.path.join(rasterdir, 'rasters.metadata'), 'r')))
rasters.sort(key=lambda r: math.fabs(r.xres))  # smaller xres = higher precision so ranked first in the list of rasters
categories = set(map(lambda r: r.category, rasters))

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
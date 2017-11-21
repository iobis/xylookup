from __future__ import division
import math
import os
import json
import numpy as np
from datetime import datetime
import service.config as config


class Raster:
    def __init__(self, rasterdir, metadata):
        self.id = metadata['id']
        self.category = metadata['category'].lower()
        nrow, ncol = tuple(metadata['shape'])
        self.nrow = nrow
        self.ncol = ncol
        path = os.path.join(rasterdir, self.id + '.mmf')
        self.data = np.memmap(path, dtype=metadata['dtype'], mode='r', shape=(nrow, ncol))
        self.minx, self.miny = metadata['minx']-1e-12, metadata['miny']-1e-12  # 1e-12 to take care of edge cases
        self.maxx, self.maxy = metadata['maxx']+1e-12, metadata['maxy']+1e-12  # 1e-12 to take care of edge cases
        self.xres, self.yres = metadata['xres'], metadata['yres']
        self.startdate, self.enddate = metadata.get('startdate',datetime.min), metadata.get('enddate',datetime.max)
        self.mindepth, self.maxdepth = metadata.get('mindepth',float("-inf")), metadata.get('maxdepth',float("inf"))
        self.hasdate = self.startdate and self.enddate
        self.hasdepth = self.mindepth and self.maxdepth
        self.bandinfo = metadata['bandinfo']
        self.rasterinfo = metadata['rasterinfo']
        nodata = float(metadata['nodata'])
        nodata_delta = abs(nodata * 1e-7)
        self.nodata = nodata-nodata_delta, nodata+nodata_delta
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
        rows[rows == self.nrow] = self.nrow - 1
        cols[cols == self.ncol] = self.ncol - 1
        return rows.astype(int), cols.astype(int)

    def get_values(self, x, y):
        print(self.id)
        r,c = self.get_rows_cols(x, y)
        values = self.data[r,c]
        okdata = (values <= self.nodata[0]) | (values >= self.nodata[1]) # check outside nodata
        return (values*self.scale_factor+self.add_offset), okdata

    def __str__(self):
        return str(self.__dict__)


def get_values(points):
    output = [{} for _ in points]
    x, y = points.T
    ids = np.array(range(len(x)))
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
                        output[id][category] = float(values[i])

                    ids_remaining = np.array(list(set(ids_remaining) - set(id_ok)))
                    if len(ids_remaining) > 0:
                        x_remaining = x[ids_remaining]
                        y_remaining = y[ids_remaining]
                    else:
                        break
    return output


rasterdir = os.path.join(config.datadir, 'rasters')
rasters = [Raster(rasterdir, d) for d in json.load(open(os.path.join(rasterdir, 'rasters.metadata'), 'r'))]
rasters = [r for r in rasters if r.id not in [u'BOEM_east', u'BOEM_west']] # TODO handle rasters with a different projection e.g. BOEM data (+proj=utm +zone=16 +datum=NAD27 +units=us-ft +no_defs +ellps=clrk66 +nadgrids=@conus,@alaska,@ntv2_0.gsb,@ntv1_can.dat)
rasters.sort(key=lambda r: math.fabs(r.xres))  # smaller xres = higher precision so ranked first in the list of rasters
categories = set([r.category for r in rasters])

if __name__ == "__main__":
    pts = np.array([[2.890605926513672, 51.241779327392585], [3, 55], [3, 54.999999],
                    [0, -90], [0, -89.9999999]])
    v = get_values(pts)

    # get_values(np.array([[-49, 51]]))

    def _get_test_points():
        import psycopg2
        conn = psycopg2.connect("dbname=xylookup user=postgres port=5432 password=postgres")
        cur = conn.cursor()
        cur.execute("SELECT x, y FROM test_points_1000000")
        pts = cur.fetchall()
        return [tuple(point) for point in pts]
    pts = _get_test_points()
    print("Ready for rasters :-)")
    import cProfile
    v = get_values(pts)
    cProfile.runctx('get_raster_values(points)', globals(), locals())

import os
import pickle
import numpy as np
import config
# INPUT: set of x,y coordinates (+time?, +depth?)
# DATA: set of rasters with metadata (id, extent, time?, depth?) grouped in categories with a hierarchy e.g. first emodnet then gebco bathymetry)
# OUTPUT: for each point the matched raster category, raster id and the value


class Raster:
    def __init__(self, metadata):  # id, category, path, dtype, shape, minx, miny, maxx, maxy, startdate=None, enddate=None, mindepth=None, maxdepth=None
        self.id = id
        self.category = metadata['category']
        self.data = np.memmap(metadata['path'], dtype=metadata['dtype'], mode='r', shape=metadata['shape'])
        self.extent = (metadata['minx'], metadata['miny'], metadata['maxx'], metadata['maxy'])
        self.startdate, self.enddate = metadata.get('startdate',None), metadata.get('enddate',None)
        self.mindepth, self.maxdepth = metadata.get('mindepth',None), metadata('maxdepth',None)
        self.hasdate = self.startdate and self.enddate
        self.hasdepth = self.mindepth and self.maxdepth

    def contains_point(self, x, y):
        env = self.extent
        return env[0] <= x <= env[2] and env[1] <= y <= env[3]

    def contains_date(self, date):
        return self.startdate <= date <= self.enddate

    def contains_depth(self, depth):
        return self.mindepth <= depth <= self.maxdepth


# x = {'id':'A1', 'category':'bathymetry', 'path':os.path.join('/Users/samuel/a/tmp/A1.dat'), 'dtype':'int16', 'shape':(7200, 9480), 'minx':0,'maxx':1,'miny':2,'maxy':3}
# s = pickle.dumps(x)
# r = Raster(pickle.loads(s))
rasters = pickle.load(os.path.join(config.datadir, 'rasters/rasters_metadata.pickle'))


def get_values(points):
    return [{"TODO SALINITY": 123, "TODO SST": 456} for _ in points]




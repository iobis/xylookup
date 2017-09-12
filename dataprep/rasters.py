import numpy as np
from osgeo import gdal
import os
import glob
import zipfile
import json
import config

tmpdir = os.path.expanduser('~/a/tmp')
emodnet_dir = os.path.expanduser('~/a/data/EMODNET_Bathy')


def get_info(ds):
    minx, xres, xskew, maxy, yskew, yres = ds.GetGeoTransform()
    maxx = minx + xres * ds.RasterXSize
    miny = maxy + yres * ds.RasterYSize
    return {'minx': minx, 'miny': miny, 'maxx': maxx, 'maxy': maxy, 'xres': xres, 'yres': yres}


def create_memmap(path, outdir, outname):
    ds = gdal.Open(path)
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    outpath = os.path.join(outdir, outname+'.mmf')
    fp = np.memmap(outpath, dtype=arr.dtype, mode='w+', shape=arr.shape)
    fp[:] = arr[:]
    del fp  # flush to disk
    metadata = {'id': outname, 'dtype': str(arr.dtype), 'shape': arr.shape}
    metadata.update(get_info(ds))
    return metadata


def emodnet2memmap(overwrite=False):
    # Step 1 unzip all
    for bathyzip in glob.glob(os.path.join(emodnet_dir, "*.zip")):
        with zipfile.ZipFile(bathyzip, 'r') as zipf:
            if overwrite or not os.path.exists(os.path.join(tmpdir, os.path.split(bathyzip)[1].replace('.zip', ''))):
                zipf.extractall(tmpdir)
    # Step 2 create memmap for all netcdf files
    for bathymnt in glob.glob(os.path.join(tmpdir, "*.mnt")):
        outdir = os.path.join(config.datadir, 'rasters')
        outname = 'emodnet_bathy_' + os.path.split(bathymnt)[1].replace('.mnt', '')
        if overwrite or not os.path.exists(os.path.join(outdir, outname + '.mmf')) or not os.path.exists(os.path.join(outdir, outname + '.json')):
            metadata = create_memmap('NETCDF:"' + bathymnt + '":DEPTH', outdir, outname)
            metadata['category'] = 'bathymetry'
            metadata['nodata'] = 32767
            json.dump(metadata, open(os.path.join(outdir, outname+'.json'), 'w'))


def combine_metadata():
    # for all .pickle files combine into one pickle file called raster.metadata
    rastersdir = os.path.join(config.datadir, 'rasters')
    allmeta = [json.load(open(p, 'r')) for p in glob.glob(os.path.join(rastersdir, "*.json"))]
    json.dump(allmeta, open(os.path.join(rastersdir, 'rasters.metadata'), 'w'))

if __name__ == '__main__':
    emodnet2memmap()
    combine_metadata()
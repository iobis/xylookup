import numpy as np
from osgeo import gdal
import os
import glob
import zipfile
import json
import subprocess
import config
# import rpy2.robjects as robjects
# for python 2.7:
# brew install llvm
# ln -s /usr/local/Cellar/llvm/5.5.0/lib/libomp.dylib /user/local/lib/libomp.dylib
# pip install 'rpy2<2.9.0'


tmpdir = os.path.expanduser('~/a/tmp')
outdir = os.path.join(config.datadir, 'rasters')
dataprep_dir = os.path.expanduser('~/Dropbox (IPOfI)/xylookup/dataprep')


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
    metadata = {'id': outname, 'dtype': str(arr.dtype), 'shape': arr.shape, 'nodata': band.GetNoDataValue(),
                'bandinfo': band.GetMetadata_Dict(), 'rasterinfo': ds.GetMetadata_Dict()}
    metadata.update(get_info(ds))
    return metadata


def output_exists(outdir, outname):
    return os.path.exists(os.path.join(outdir, outname + '.mmf')) and os.path.exists(os.path.join(outdir, outname + '.json'))


def emodnet2memmap(overwrite=False):
    emodnet_dir = os.path.join(dataprep_dir, 'EMODNET_Bathy')
    # Step 1 unzip all
    for bathyzip in glob.glob(os.path.join(emodnet_dir, "*.zip")):
        with zipfile.ZipFile(bathyzip, 'r') as zipf:
            if overwrite or not os.path.exists(os.path.join(tmpdir, os.path.split(bathyzip)[1].replace('.zip', ''))):
                zipf.extractall(tmpdir)
    # Step 2 create memmap for all netcdf files
    for bathymnt in glob.glob(os.path.join(tmpdir, "*.mnt")):
        outname = 'emodnet_bathy_' + os.path.split(bathymnt)[1].replace('.mnt', '')
        if overwrite or not output_exists(outdir, outname):
            metadata = create_memmap('NETCDF:"' + bathymnt + '":DEPTH', outdir, outname)
            metadata['category'] = 'bathymetry'
            metadata['bandinfo']['scale_factor'] = -1 * float(metadata['bandinfo'].get('scale_factor', 1))
            metadata['bandinfo']['add_offset'] = -1 * float(metadata['bandinfo'].get('add_offset', 0))
            json.dump(metadata, open(os.path.join(outdir, outname+'.json'), 'w'))


def gebco2memmap(overwrite=False):
    gebco_dir = os.path.join(dataprep_dir, 'GEBCO_2014')
    outname = 'gebco_2014'
    if overwrite or not output_exists(outdir, outname):
        metadata = create_memmap('NETCDF:"' + os.path.join(gebco_dir, 'GEBCO_2014_2D.nc":elevation'), outdir, outname)
        metadata['category'] = 'bathymetry'
        metadata['bandinfo']['missing_value'] = 32767
        metadata['bandinfo']['scale_factor'] = -1 * float(metadata['bandinfo'].get('scale_factor', 1))
        metadata['bandinfo']['add_offset'] = -1 * float(metadata['bandinfo'].get('add_offset', 0))
        json.dump(metadata, open(os.path.join(outdir, outname + '.json'), 'w'))


def gbr100v5_memmap(overwrite=False):
    # gbr100: High-resolution bathymetry model of the Great Barrier Reef and Coral Sea, an output of Project 3DGBR
    # https://www.deepreef.org/bathymetry/65-3dgbr-bathy.html
    gbr_dir = os.path.join(dataprep_dir, 'gbr100')
    outname = 'gbr100'
    if overwrite or not output_exists(outdir, outname):
        metadata = create_memmap('NETCDF:"' + os.path.join(gbr_dir, 'gbr100_02sep_v5.grd":depth'), outdir, outname)
        metadata['category'] = 'bathymetry'
        metadata['bandinfo']['scale_factor'] = -1 * float(metadata['bandinfo'].get('scale_factor', 1))
        metadata['bandinfo']['add_offset'] = -1 * float(metadata['bandinfo'].get('add_offset',0))
        json.dump(metadata, open(os.path.join(outdir, outname + '.json'), 'w'))


def boem2memmap(overwrite=False):
    # BOEM Northern Gulf of Mexico Deepwater Bathymetry Grid from 3D Seismic
    # https://www.boem.gov/Gulf-of-Mexico-Deepwater-Bathymetry/
    boem_dir = os.path.join(dataprep_dir, 'boem')
    for fname, outname in [('BOEMbathyW_m.tif', 'BOEM_west'), ('BOEMbathyE_m.tif', 'BOEM_east')]:
        if overwrite or not output_exists(outdir, outname):
            metadata = create_memmap(os.path.join(boem_dir, fname), outdir, outname)
            metadata['category'] = 'bathymetry'
            metadata['bandinfo']['scale_factor'] = -1 * float(metadata['bandinfo']['scale_factor'])
            metadata['bandinfo']['add_offset'] = -1 * float(metadata['bandinfo']['add_offset'])
            json.dump(metadata, open(os.path.join(outdir, outname + '.json'), 'w'))


def sdmpredictors2memmap(layers, overwrite=False):
    sdmpredictors_dir = os.path.join(dataprep_dir, 'sdmpredictors')
    layercodes = [l for _, codes in layers.items() for l in codes]
    code = """
if(!require(sdmpredictors)){{
    install.packages('sdmpredictors', repos='https://lib.ugent.be/CRAN/')
    library(sdmpredictors)
}}
load_layers(c("{0}"), datadir = "{1}")
""".format('","'.join(layercodes), sdmpredictors_dir)
    rfile = os.path.join(sdmpredictors_dir, 'download_sdmpredictors.R')
    with open(rfile, 'w') as f:
        f.write(code)
    try:
        subprocess.check_call(['Rscript', rfile], universal_newlines=True)
    finally:
        os.remove(rfile)
    for category, layercodes in layers.items():
        for outname in layercodes:
            if overwrite or not output_exists(outdir, outname):
                metadata = create_memmap(os.path.join(sdmpredictors_dir, outname+'_lonlat.tif'), outdir, outname)
                metadata['category'] = category
                json.dump(metadata, open(os.path.join(outdir, outname + '.json'), 'w'))


def combine_metadata():
    # for all json files combine into one pickle file called raster.metadata
    rastersdir = os.path.join(config.datadir, 'rasters')
    allmeta = [json.load(open(p, 'r')) for p in glob.glob(os.path.join(rastersdir, "*.json"))]
    json.dump(allmeta, open(os.path.join(rastersdir, 'rasters.metadata'), 'w'))


if __name__ == '__main__':
    emodnet2memmap()
    gebco2memmap()
    gbr100v5_memmap()
    # boem2memmap() # different projection
    sdmpredictors2memmap(layers={'Temperature (sea surface)': ['BO2_tempmean_ss'], 'Salinity (sea surface)': ['BO2_salinitymean_ss']})
    combine_metadata()
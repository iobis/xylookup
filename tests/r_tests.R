library(raster)
library(sdmpredictors)

setwd("~/a/projects/xylookup/tests")
options(sdmpredictors_datadir="/Users/samuel/a/data/sdmpredictors")

create_test_points <- function(seed = 42) {
  set.seed(seed)
  x <- runif(1000000, -180, 180)
  y <- runif(1000000, -90, 90)
  write.csv(data.frame(x=x, y=y), "r_testfile.csv", row.names = FALSE)
}
# create_test_points()

create_bathymetry_results <- function(points) {
  dir <- "/Users/samuel/Dropbox (IPOfI)/xylookup/dataprep/"
  bathy <- c(#paste0(dir,"boem/BOEMbathyE_m.tif"), 
             #paste0(dir,"boem/BOEMbathyW_m.tif"), 
               paste0(dir, 'gbr100/gbr100_02sep_v5.grd'),
               paste0(dir, 'GEBCO_2014/GEBCO_2014_2D.nc'))
  emodnet_names <- apply(expand.grid(c('A','B','C','D'), 1:4), 1, paste0, collapse='')
  emodnet <- sapply(emodnet_names, function(x) raster:::.rasterFromGDAL(paste0('NETCDF:/Users/samuel/a/tmp/',x,'.mnt:DEPTH'), type='RasterLayer', band=1))
  x <- c(emodnet, sapply(bathy, function(x) {raster(x)}))
  results <- dplyr::bind_cols(lapply(x, function(x) as.vector(extract(x, points))))
  results <- -1 * apply(results, 1, function(v) v[which.min(is.na(v))])
  results
}

create_test_results <- function(points, subset=1:5) {
  points <- points[subset,]
  x <- sdmpredictors::load_layers(c('BO2_tempmean_ss', 'BO2_salinitymean_ss'))
  r <- extract(x, points)
  r <- cbind(r, bathymetry = create_bathymetry_results(points))
  colnames(r) <- c('temperature (sea surface)', 'salinity (sea surface)', 'bathymetry')
  write.csv(cbind(points, r), 'r_testlookup.csv', row.names=FALSE)
}
points <- read.csv("r_testfile.csv")
create_test_results(points, 1:10000)

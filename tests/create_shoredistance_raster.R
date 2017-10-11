library(raster)
library(obistools)
## Shore distance
getOption("sdmpredictors_datadir")
template = raster(sdmpredictors::load_layers("BO_sstmean"), layer=1)
shoredist = raster(matrix(NA, nrow=2160, ncol=4320), template=template)


for (rownr in 1:nrow(shoredist)) {
# for (rownr in 500:550) {
  cells <- cellFromRow(shoredist, rownr)
  xy <- t(sapply(cells, function(cell) xyFromCell(shoredist, cell)))
  colnames(xy) <- c("decimalLongitude", "decimalLatitude")
  options(obistools_xylookup_url="http://localhost:8000/lookup/")
  d <- obistools::lookup_xy(as.data.frame(xy), grids=FALSE)
  shoredist[cells] <- d$shoredistance
}
tifoptions <- c("COMPRESS=DEFLATE", "PREDICTOR=1", "ZLEVEL=6")
writeRaster(shoredist, "~/a/output/shoredistance.tif",
            options = tifoptions, overwrite = T)

# sd <- raster("~/a/projects/zoutput/shoredistance_with_errors.tif")
# plot(crop(sd, extent(-96, -95.5, 40.5, 41)))

sd <- raster("~/a/output/shoredistance.tif")
sd[sd > 5000] <- NA
plot(sd)

sd <- raster("~/a/output/shoredistance.tif")
sd[sd < -5000] <- NA
plot(sd)

sd <- raster("~/a/output/shoredistance.tif")
sd[sd > 10000] <- NA
sd[sd < -10000] <- NA
plot(sd)

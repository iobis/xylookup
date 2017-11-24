# xylookup
Webservice for looking up environmental and societal spatial information based on coordinates.

## API

Get all data for a point as json

http://api.iobis.org/xylookup?x=2.90&y=51.2

Get all data for multiple points as json

http://api.iobis.org/xylookup?x=2.90,2.1&y=51.2,51.1

Filtering the results can be done by excluding the different categories(`areas`, `shoredistance`, `grids`) e.g.
to return results without the distance to the shoreline:

http://api.iobis.org/xylookup?x=2.90&y=51.2&shoredistance=0

Note that msgpack data can also be used for sending/receiving data.

## Dependencies

- PostgreSQL and PostGIS (currently tested on 9.6 and 9.4)
- Python 2.7 with
    - falcon
    - numpy
    - msgpack
    - psycopg2
    - gunicorn (webserver)
    - gdal (for the datapreparation scripts, not for the service itself)
- nginx

## Deployment

- Install postgresql
    - Load the needed areas tables into PostgreSQL
        - Currently only `final_grid5` (see below)
- Install nginx
- Install python
- Copy the source code from the service directory
- Copy the datadir
- Start gunicorn 
    - `gunicorn --reload app:api`
    - Preferably make sure that gunicorn restarts when the service restarts
- Configure nginx so that it proxies all calls to gunicorn
- Update service/config.py, set the datadir, PostgreSQL connection string and if needed the available areas.

## Data pre-processing

### final_grid5

Startign from a the final.shp shapefile, perform the following steps:

    D:\a\prog\PostgreSQL\9.6\bin\shp2pgsql -I -s 4326 final.shp final postgres > final.sql
    psql -d xylookup -U postgres -p 5433 -f final.sql
    
    QGIS => Vector => research tools => Vector grid
    xmin -180.000001 ymin -90.000001
    xmax 180.000001 ymax 90.000001
    
    X: 5,000000030
    Output grid as polygons
    D:/a/projects/iobis/xylookup/vector/data/gridpoly_5.shp
    
    QGIS => Vector => Geoprocessing => Intersect
    final
    gridpoly_5
    D:/a/projects/iobis/xylookup/vector/data/final_grid5.shp
    
    D:\a\prog\PostgreSQL\9.6\bin\shp2pgsql -I -s 4326 final_grid5.shp final_grid5 postgres > final_grid5.sql
    psql -d xylookup -U postgres -p 5433 -f final_grid5.sql

### Shore distance

All data used was downloaded from [Open Street Map](http://openstreetmapdata.com/data/coast).

In order to calculate the shoredistance we need two parts:

1. water polygons in the database which are used to test whether points are on land
    - download [water polygons](http://openstreetmapdata.com/data/water-polygons)
    - simplify
        - `ogr2ogr water_polygons0_00005.shp water_polygons.shp -simplify 0.00005`
    - upload to PostgreSQL
        - `shp2pgsql -s 4326 water_polygons0_00005 public.water_polygons0_00005 > water.sql`
        - `psql -d xylookup -U postgres -p 5433 -f water.sql`
2. coastlines as geojson that are loaded in the python service for calculating the shoredistance
    - download [coastlines](http://openstreetmapdata.com/data/coastlines)
    - import coastline-split-4326 as table coastlines in database xylookup using the QGIS DBManager because the dbf file gives errors with shp2pgsql

Then execute the following sql code in PostgreSQL:
  
    CREATE OR REPLACE FUNCTION simplifyutm(geom geometry, tolerance float, max_segment_length float)
       RETURNS geometry AS
    $BODY$
    DECLARE
         bestUTM integer;
         geomCenter geometry;
         geomUTM geometry;
         geomBack geometry;
    BEGIN
         geomCenter:= ST_centroid(geom);
         bestUTM:= floor((ST_X(geomCenter)+180)/6)+1;
         IF (ST_Y(geomCenter))>0 THEN
            bestUTM:= bestUTM+32600;
         ELSE
            bestUTM:= bestUTM+32700;
         END IF;
         geomUTM:= ST_Transform(geom,bestUTM);
         geomUTM:= ST_SimplifyPreserveTopology(geomUTM, tolerance);
         geomUTM:= ST_Segmentize(geomUTM, max_segment_length);
         geomBack:= ST_Transform(ST_setsrid(geomUTM, bestUTM),4326); -- set_srid as it is sometimes lost for some features ...
         RETURN geomBack;
    END
    $BODY$
       LANGUAGE plpgsql STABLE STRICT;

    SELECT AddGeometryColumn('coastlines', 'geom_simple50', 4326, 'LINESTRING', 2);
    UPDATE coastlines SET geom_simple50 = simplifyutm(geom, 50, 500);
    COPY (SELECT st_asgeojson(geom_simple50) FROM coastlines) TO '<datadir>/coastlines50.jsonlines';

### Rasters

Run dataprep/rasters.py, it prepares both the data and metadata needed. Data is prepared by storing them as uncompressed binary numpy array files which are later on read by using memorymapped files.

Some input source data will have to be downloaded manually such as the EMODnet and GEBCO bathymetry.

## Roadmap

Add support for looking up data based on time and depth.  
Document the api using Swagger.  

import service.config as config


def get_areas(cur, points, pointstable):
    tablecols = config.areas
    results = [{} for _ in range(len(points))]
    for table, columns in tablecols.items():
        cur.execute("""SELECT pts.id, {} FROM {} pts, {} grid 
                        WHERE ST_Intersects(grid.geom, pts.geom) 
                        ORDER BY pts.id""".format(",".join(columns), pointstable, table))
        data = cur.fetchone()
        for idx in range(len(points)):
            results[idx][table] = []
            while data and data[0] == idx:
                d = dict(zip(columns, data[1:]))
                results[idx][table].append(d)
                data = cur.fetchone()
            if len(results[idx][table]) == 0:
                del results[idx][table]
    return results
        
        
        


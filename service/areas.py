
def get_areas(cur, points, pointstable):
    tablecols = {'final_grid5': ['sp_id', 'name', 'country', 'type', 'base']}
    results = [[] for _ in xrange(len(points))]
    for table, columns in tablecols.iteritems():
        cur.execute("""SELECT pts.id, {} FROM {} pts, {} grid 
                        WHERE ST_Intersects(grid.geom, pts.geom) 
                        ORDER BY pts.id""".format(",".join(columns), pointstable, table))
        data = cur.fetchone()
        for idx in range(len(points)):
            while data and data[0] == idx:
                d = dict(zip(columns, data[1:]))
                d['layer'] = table
                results[idx].append(d)
                data = cur.fetchone()
    return results
        
        
        


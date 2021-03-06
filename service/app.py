import falcon
import simplejson as json
import msgpack
import service.lookup as lookup
import service.areas as areas
import traceback

class LookupResource(object):
    @staticmethod
    def _prepare_response(results, req, resp):
        if req.client_accepts_msgpack and req.content_type and req.content_type.lower() == falcon.MEDIA_MSGPACK:
            try:
                resp.data = msgpack.packb(results, use_bin_type=False)
                resp.content_type = falcon.MEDIA_MSGPACK
                resp.status = falcon.HTTP_200
            except Exception as ex:
                print(str(ex))
                raise falcon.HTTPError(falcon.HTTP_400, 'Error creating msgpack response', str(ex))
        else:
            try:
                resp.body = json.dumps(results)
            except Exception as ex:
                print(str(ex))
                raise falcon.HTTPError(falcon.HTTP_400, 'Error creating JSON response', str(ex))

    def on_get(self, req, resp):
	results = lookup.lookup(req)
	self._prepare_response(results, req, resp)

    def on_post(self, req, resp):
        results = lookup.lookup(req)
        self._prepare_response(results, req, resp)


class AreasResource(object):

    def on_get(self, req, resp):
        resp.body = areas.table_sql(req)
        resp.content_type = falcon.MEDIA_TEXT
        resp.status = falcon.HTTP_200
        resp.content_disposition = 'inline; filename = "create_areas.txt"'


def create():
    api = falcon.API()
    api.add_route('/lookup/areas', AreasResource())
    api.add_route('/lookup', LookupResource())
    return api


api = create()

if __name__ == '__main__':
    from wsgiref import simple_server
    httpd = simple_server.make_server('127.0.0.1', 8000, api)
    httpd.serve_forever()

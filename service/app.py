from wsgiref import simple_server

import falcon
import json
import msgpack
import lookup
# VERSION 1: return all data (no filtering)


class LookupResource(object):
    @staticmethod
    def _prepare_response(results, req, resp):
        if req.get_param("format") == "msgpack":
            resp.data = msgpack.packb(results, use_bin_type=True)
            resp.content_type = 'application/msgpack'
            resp.status = falcon.HTTP_200
        else:
            resp.body = json.dumps(results)
    
    def on_get(self, req, resp):
        results = lookup.lookup(req)
        self._prepare_response(results, req, resp)
        
    def on_post(self, req, resp):
        results = lookup.lookup(req)
        self._prepare_response(results, req, resp)


def create():
    api = falcon.API()
    api.add_route('/lookup', LookupResource())
    return api

if __name__ == '__main__':
    api = create()
    httpd = simple_server.make_server('127.0.0.1', 8000, api)
    httpd.serve_forever()

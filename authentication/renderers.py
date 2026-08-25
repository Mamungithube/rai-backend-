import ujson
import time
from rest_framework.renderers import JSONRenderer

class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = 200
        if renderer_context and 'response' in renderer_context:
            status_code = renderer_context['response'].status_code

        success = status_code < 400
        message = "Request successful" if success else "Request failed"

        if data is None:
            data = {}

        if isinstance(data, dict):
            if 'message' in data:
                message = data.pop('message')
            if 'detail' in data:
                if isinstance(data['detail'], str):
                    message = data.pop('detail')
        
        response_data = {
            "success": success,
            "code": status_code,
            "message": message,
            "timestamp": int(time.time()),
        }

        if success:
            if isinstance(data, dict) and 'results' in data and 'count' in data:
                response_data['data'] = data.pop('results')
                response_data['pagination'] = {
                    'count': data.get('count'),
                    'next': data.get('next'),
                    'previous': data.get('previous')
                }
            else:
                response_data['data'] = data
                
            response_data['errors'] = None
        else:
            response_data['data'] = None
            response_data['errors'] = data

        return ujson.dumps(response_data).encode('utf-8')
from django.db import connection


class QueriesCountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        connection.queries.clear()
        queries_time_counter = 0
        response = self.get_response(request)
        query_count = len(connection.queries)
        for query_dict in connection.queries:
            queries_time_counter += float(query_dict["time"])
        print(f"queries: {query_count}, execution time: {queries_time_counter}")
        return response

from rest_framework.pagination import PageNumberPagination

class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination class that allows clients to request large result sets.
    """
    page_size = 200  # Default page size
    page_size_query_param = 'page_size'  # Allow client to set page size via query param
    max_page_size = 20000  # Maximum page size limit

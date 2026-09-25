from rest_framework.pagination import CursorPagination, PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class LargeListCursorPagination(CursorPagination):
    """For append-only, high-volume lists (tracking events, audit log)."""

    page_size = 100
    ordering = "-created_at"

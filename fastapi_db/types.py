from abc import ABC, abstractmethod


class IPage(ABC):
    """分页"""

    def __init__(self, page: int, page_size: int):
        self.set_page(page)
        self.set_page_size(page_size)

    @abstractmethod
    def get_page(self) -> int: ...

    @abstractmethod
    def get_page_size(self) -> int: ...

    @abstractmethod
    def get_page_size_max(self) -> int: ...

    @abstractmethod
    def set_page(self, page: int) -> None: ...

    @abstractmethod
    def set_page_size(self, page_size: int) -> None: ...

    @abstractmethod
    def set_page_size_max(self, page_size_max: int) -> None: ...


class Page(IPage):
    """分页封装"""

    page: int = 1
    page_size: int = 20
    page_size_max: int = 100

    def get_page(self) -> int:
        return self.page

    def get_page_size(self) -> int:
        return self.page_size

    def get_page_size_max(self) -> int:
        return self.page_size_max

    def set_page(self, page: int) -> None:
        self.page = page

    def set_page_size(self, page_size: int) -> None:
        self.page_size = page_size

    def set_page_size_max(self, page_size_max: int) -> None:
        self.page_size_max = page_size_max
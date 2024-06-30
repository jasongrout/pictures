from abc import ABC, abstractmethod

class Display(ABC):

    @abstractmethod
    def sleep(self):
        """Turn off the display."""
        ...

    @abstractmethod
    def wake(self):
        """Turn on the display."""
        ...

    @abstractmethod
    def on(check=False):
        """Return True if the display is on, otherwise False."""
        ...

    @abstractmethod
    def restore(self):
        ...

    @staticmethod
    @abstractmethod
    def active(self):
        ...
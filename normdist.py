# From CPython statistics module

from statistics import StatisticsError
from math import sqrt, exp, tau

class NormalDist:
    "Normal distribution of a random variable"
    # https://en.wikipedia.org/wiki/Normal_distribution
    # https://en.wikipedia.org/wiki/Variance#Properties

    __slots__ = {
        '_mu': 'Arithmetic mean of a normal distribution',
        '_sigma': 'Standard deviation of a normal distribution',
    }

    def __init__(self, mu=0.0, sigma=1.0):
        "NormalDist where mu is the mean and sigma is the standard deviation."
        if sigma < 0.0:
            raise StatisticsError('sigma must be non-negative')
        self._mu = float(mu)
        self._sigma = float(sigma)

    def pdf(self, x):
        "Probability density function.  P(x <= X < x+dx) / dx"
        variance = self._sigma ** 2.0
        if not variance:
            raise StatisticsError('pdf() not defined when sigma is zero')
        return exp((x - self._mu)**2.0 / (-2.0*variance)) / sqrt(tau*variance)

    @property
    def variance(self):
        "Square of the standard deviation."
        return self._sigma ** 2.0

    def __repr__(self):
        return f'{type(self).__name__}(mu={self._mu!r}, sigma={self._sigma!r})'
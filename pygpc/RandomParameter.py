import scipy.special
import scipy.stats
import numpy as np
from BasisFunction import *


class RandomParameter(object):
    """
    RandomParameter class

    Attributes
    ----------
    pdf_type: str
        Distribution type of random variable ('beta', 'norm')

    """
    def __init__(self, pdf_type=None, pdf_shape=None, pdf_limits=None):
        """
        Constructor; Initializes random parameter;
        """

        self.pdf_type = pdf_type
        self.pdf_shape = pdf_shape
        self.pdf_limits = pdf_limits


class Beta(RandomParameter):
    """
    Beta distributed random variable sub-class

    Probability density function:

    .. math
       pdf = \left(\frac{\Gamma(p)\Gamma(q)}{\Gamma(p+q)}(b-a)^{(p+q-1)}\right)^{-1} (x-a)^{(p-1)} (b-x)^{(q-1)}

    Attributes
    ----------
    pdf_shape: list of float [2]
        Shape parameters of beta distributed random variable [p, q]
    pdf_limits: list of float [2]
        Lower and upper bounds of random variable [min, max]
    """
    def __init__(self, pdf_shape, pdf_limits):
        """
        Constructor; Initializes beta distributed random variable

        Parameters
        ----------
        pdf_shape: list of float [2]
            Shape parameters of beta distributed random variable [p, q]
        pdf_limits: list of float [2]
            Lower and upper bounds of random variable [min, max]
        """

        super(Beta, self).__init__(pdf_type='beta', pdf_shape=pdf_shape, pdf_limits=pdf_limits)

    def init_basis_function(self, order):
        """
        Initializes Jacobi BasisFunction of Beta RandomParameter

        Parameters
        ----------
        order: int
            Order of basis function
        """
        return Jacobi({"i": order, "p": self.pdf_shape[0], "q": self.pdf_shape[1]})

    def pdf(self, x):
        """
        Calculate the probability density function of the beta distributed random variable.

        pdf = Beta.pdf(x)

        Parameters
        ----------
        x: np.ndarray
            Values of random variable

        Returns
        -------
        pdf: np.ndarray
            Probability density at values x
        """

        p = self.pdf_shape[0]
        q = self.pdf_shape[1]
        a = self.pdf_limits[0]
        b = self.pdf_limits[1]

        y = np.zeros(x.shape)

        mask = np.logical_and(self.pdf_limits[0] < x, x < self.pdf_limits[1])

        y[mask] = (scipy.special.gamma(p) * scipy.special.gamma(q) / scipy.special.gamma(p + q)
                   * (b - a) ** (p + q - 1)) ** (-1) * (x[mask] - a) ** (p - 1) * (b - x[mask]) ** (q - 1)

        return y

    def pdf_norm(self, x):
        """
        Calculate the probability density function of the normalized beta distributed random variable in interval
        [-1, 1].

        pdf = Beta.pdf_norm(x)

        Parameters
        ----------
        x: np.ndarray
            Values of random variable

        Returns
        -------
        pdf: np.ndarray
            Probability density at values x
        """

        p = self.pdf_shape[0]
        q = self.pdf_shape[1]
        a = -1.0
        b = 1.0

        y = np.zeros(x.shape)

        mask = np.logical_and(self.pdf_limits[0] < x, x < self.pdf_limits[1])

        y[mask] = (scipy.special.gamma(p) * scipy.special.gamma(q) / scipy.special.gamma(p + q)
                   * (b - a) ** (p + q - 1)) ** (-1) * (x[mask] - a) ** (p - 1) * (b - x[mask]) ** (q - 1)

        return y


class Norm(RandomParameter):
    """
    Normal distributed random variable sub-class

    Probability density function

    .. math
       pdf = \frac{1}{\sqrt{2\pi\sigma^2}}\exp{-\frac{(x-\mu)^2}{2\sigma^2}}

    Attributes
    ----------
    pdf_shape: list of float [2]
        Shape parameters of beta distributed random variable [mean, std]
    """
    def __init__(self, pdf_shape):
        """
        Constructor; Initializes beta distributed random variable

        Parameters
        ----------
        pdf_shape: list of float [2]
            Shape parameters of beta distributed random variable [p, q]
        """

        super(Norm, self).__init__(pdf_type='norm', pdf_shape=pdf_shape, pdf_limits=None)

    @staticmethod
    def init_basis_function(order):
        """
        Initializes Hermite BasisFunction of Norm RandomParameter

        Parameters
        ----------
        order: int
            Order of basis function
        """
        return Hermite({"i": order})

    def pdf(self, x):
        """
        Calculate the probability density function of the normal distributed random variable.

        pdf = Norm.pdf(x)

        Parameters
        ----------
        x: np.ndarray
            Values of random variable

        Returns
        -------
        pdf: np.ndarray
            Probability density
        """

        return scipy.stats.norm.pdf(x, loc=self.pdf_shape[0], scale=self.pdf_shape[1])

    @staticmethod
    def pdf_norm(x):
        """
        Calculate the probability density function of the normalized normal distributed random variable
        (zero mean, std 1).

        pdf = Norm.pdf_norm(x)

        Parameters
        ----------
        x: np.ndarray
            Values of random variable

        Returns
        -------
        pdf: np.ndarray
            Probability density
        """

        return scipy.stats.norm.pdf(x, loc=0, scale=1)

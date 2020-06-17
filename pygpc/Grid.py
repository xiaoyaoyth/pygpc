import uuid
import copy
import numpy as np
import scipy.stats
from .io import iprint
from .misc import get_multi_indices
from .misc import get_cartesian_product
from .misc import mutual_coherence
from.Quadrature import *


class Grid(object):
    """
    Grid class

    Parameters
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    weights: ndarray of float [n_grid x dim]
        Weights of the grid (all)
    coords: ndarray of float [n_grid x dim]
        Denormalized coordinates xi
    coords_norm: ndarray of float [n_grid x dim]
        Normalized coordinates xi
    coords_gradient: ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm: ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id: list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    n_grid: int
        Total number of nodes in grid.

    Attributes
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    _weights: ndarray of float [n_grid x dim]
        Weights of the grid (all)
    _coords: ndarray of float [n_grid x dim]
        Denormalized coordinates xi
    _coords_norm: ndarray of float [n_grid x dim]
        Normalized coordinates xi
    _domains: ndarray of float [n_grid]
        Domain IDs of grid points for multi-element gPC
    _coords_gradient: ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    _coords_gradient_norm: ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id: list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    n_grid: int
        Total number of nodes in grid.
    """
    def __init__(self, parameters_random, coords=None, coords_norm=None,
                 coords_gradient=None, coords_gradient_norm=None, coords_id=None, coords_gradient_id=None):
        """
        Constructor; Initialize Grid class
        """
        self._coords = coords                         # Coordinates of gpc model calculation in the system space
        self._coords_norm = coords_norm               # Coordinates of gpc model calculation in the gpc space
        self.coords_id = coords_id                    # Unique IDs of grid points
        self.coords_gradient_id = coords_gradient_id  # Unique IDs of grid gradient points
        self._weights = None                          # Weights for numerical integration
        self.parameters_random = parameters_random    # OrderedDict of RandomParameter instances
        self.dim = len(self.parameters_random)        # Number of random variables
        self._coords_gradient = coords_gradient       # Shifted coordinates for gradient calculation in the system space
        self._coords_gradient_norm = coords_gradient_norm  # Normalized coordinates for gradient calculation

        if coords is not None:
            self.n_grid = self.coords.shape[0]                    # Total number of grid points

        if coords_gradient is not None:
            self.n_grid_gradient = self.coords_gradient.shape[0]  # Total number of grid points for gradient calculation

        if coords_id is None and coords is not None:
            self.coords_id = self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]
            self.n_grid = self._coords.shape[0]

        if coords_gradient_id is None and coords_gradient is not None:
            self.coords_gradient_id = [uuid.uuid4() for _ in range(self.n_grid)]
            self.n_grid_gradient = self._coords_gradient.shape[0]

    @property
    def coords(self):
        return self._coords

    @coords.setter
    def coords(self, value):
        self._coords = value
        self.n_grid = self._coords.shape[0]

        # Generate unique IDs of grid points
        if self.coords_id is None:
            self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]

    @property
    def coords_norm(self):
        return self._coords_norm

    @coords_norm.setter
    def coords_norm(self, value):
        self._coords_norm = value
        self.n_grid = self._coords_norm.shape[0]

        # Generate unique IDs of grid points
        if self.coords_id is None:
            self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]

    @property
    def coords_gradient(self):
        return self._coords_gradient

    @coords_gradient.setter
    def coords_gradient(self, value):
        self._coords_gradient = value
        self.n_grid_gradient = self._coords_gradient.shape[0]

        # Generate unique IDs of grid gradient points
        if self.coords_gradient_id is None:
            self.coords_gradient_id = [uuid.uuid4() for _ in range(self.n_grid_gradient)]

    @property
    def coords_gradient_norm(self):
        return self._coords_gradient_norm

    @coords_gradient_norm.setter
    def coords_gradient_norm(self, value):
        self._coords_gradient_norm = value
        self.n_grid_gradient = self._coords_gradient_norm.shape[0]

        # Generate unique IDs of grid gradient points
        if self.coords_gradient_id is None:
            self.coords_gradient_id = [uuid.uuid4() for _ in range(self.n_grid_gradient)]

    @property
    def weights(self):
        return self._weights

    @weights.setter
    def weights(self, value):
        self._weights = value

    def get_denormalized_coordinates(self, coords_norm):
        """
        Denormalize grid from normalized to original parameter space for simulations.

        coords = Grid.get_denormalized_coordinates(coords_norm)

        Parameters
        ----------
        coords_norm: [N_samples x dim] np.ndarray
            Normalized coordinates xi

        Returns
        -------
        coords: [N_samples x dim] np.ndarray
            Denormalized coordinates xi
        """
        coords = np.zeros(coords_norm.shape)

        for i_p, p in enumerate(self.parameters_random):

            if self.parameters_random[p].pdf_type == "beta":
                coords[:, i_p, ] = (coords_norm[:, i_p, ] + 1) / \
                                   2 * (self.parameters_random[p].pdf_limits[1] -
                                        self.parameters_random[p].pdf_limits[0]) \
                                   + self.parameters_random[p].pdf_limits[0]

            if self.parameters_random[p].pdf_type in ["norm", "normal"]:
                coords[:, i_p, ] = coords_norm[:, i_p, ] * self.parameters_random[p].pdf_shape[1] + \
                                 self.parameters_random[p].pdf_shape[0]

            if self.parameters_random[p].pdf_type in ["gamma"]:
                coords[:, i_p, ] = coords_norm[:, i_p, ] / self.parameters_random[p].pdf_shape[1] + \
                                   self.parameters_random[p].pdf_shape[2]

        return coords

    def get_normalized_coordinates(self, coords):
        """
        Normalize grid from original parameter to normalized space for simulations.

        coords_norm = Grid.get_normalized_coordinates(coords)

        Parameters
        ----------
        coords : [N_samples x dim] np.ndarray
            Denormalized coordinates xi in original parameter space

        Returns
        -------
        coords_norm : [N_samples x dim] np.ndarray
            Normalized coordinates xi
        """
        coords_norm = np.zeros(coords.shape)

        for i_p, p in enumerate(self.parameters_random):

            if self.parameters_random[p].pdf_type == "beta":
                coords_norm[:, i_p] = (coords[:, i_p] - self.parameters_random[p].pdf_limits[0])
                coords_norm[:, i_p] = coords_norm[:, i_p] / \
                                      (self.parameters_random[p].pdf_limits[1] -
                                       self.parameters_random[p].pdf_limits[0]) * \
                                      2.0 - 1

            if self.parameters_random[p].pdf_type in ["norm", "normal"]:
                coords_norm[:, i_p] = (coords[:, i_p] - self.parameters_random[p].pdf_shape[0]) / \
                                      self.parameters_random[p].pdf_shape[1]

            if self.parameters_random[p].pdf_type in ["gamma"]:
                coords_norm[:, i_p] = (coords[:, i_p] - self.parameters_random[p].pdf_shape[2]) * \
                                      self.parameters_random[p].pdf_shape[1]

        return coords_norm

    def create_gradient_grid(self, delta=1e-3):
        """
        Creates new grid points to determine gradient of model function.
        Adds or updates self.coords_gradient, self.coords_gradient_norm and self.coords_gradient_id.

        Parameters
        ----------
        delta : float, optional, default: 1e-3
            Shift of grid-points along axes in normalized parameter space
        """
        # shift of gradient grid in normalized space
        delta = delta * np.eye(self.dim)

        # Create or update the gradient grid [n_grid x dim x dim]
        if self.coords_gradient is not None:
            n_grid_gradient = self.coords_gradient_norm.shape[0]
            self.coords_gradient = np.vstack((self.coords_gradient,
                                              np.zeros((self.n_grid-n_grid_gradient, self.dim, self.dim))))
            self.coords_gradient_norm = np.vstack((self.coords_gradient_norm,
                                                   np.zeros((self.n_grid-n_grid_gradient, self.dim, self.dim))))
        else:
            n_grid_gradient = 0
            self.coords_gradient = np.zeros((self.n_grid, self.dim, self.dim))
            self.coords_gradient_norm = np.zeros((self.n_grid, self.dim, self.dim))

        if n_grid_gradient < self.coords_gradient.shape[0]:
            # shift the grid
            for i_dim in range(self.dim):
                self.coords_gradient_norm[n_grid_gradient:, :, i_dim] = self.coords_norm[n_grid_gradient:, ] - \
                                                                        delta[i_dim, :]

            # determine coordinates in original parameter space
            self.coords_gradient[n_grid_gradient:, :, :] = \
                self.get_denormalized_coordinates(self.coords_gradient_norm[n_grid_gradient:, :, :])

            # total number of grid points
            self.n_grid_gradient = self.coords_gradient.shape[0]*self.coords_gradient.shape[2]

            # Generate unique IDs of grid points [n_grid]
            self.coords_gradient_id = copy.deepcopy(self.coords_id)


class TensorGrid(Grid):
    """
    Generate TensorGrid object instance.

    Parameters
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    options: dict
        Grid options
        - parameters["grid_type"] ... list of str [dim]: type of grid ('jacobi', 'hermite', 'cc', 'fejer2')
        - parameters["n_dim"] ... list of int [dim]: Number of nodes in each dimension
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    knots_dim_list : list of float [dim][n_knots]
        Knots of polynomials in each dimension
    weights_dim_list : list of float [dim][n_knots]
         Weights of polynomials in each dimension
    weights : ndarray of float [n_grid]
        Quadrature weights for each grid point

    Examples
    --------
    >>> import pygpc
    >>> pygpc.TensorGrid(parameters_random, options={"grid_type": ["hermite", "jacobi"], "n_dim": [5, 6]})

    Attributes
    ----------
    grid_type : [N_vars] list of str
        Type of quadrature used to construct tensor grid ('jacobi', 'hermite', 'clenshaw_curtis', 'fejer2')
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    options: dict
        Grid options
        - parameters["grid_type"] ... list of str [dim]: type of grid ('jacobi', 'hermite', 'cc', 'fejer2')
        - parameters["n_dim"] ... list of int [dim]: Number of nodes in each dimension
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    knots_dim_list : list of float [dim][n_knots]
        Knots of polynomials in each dimension
    weights_dim_list : list of float [dim][n_knots]
         Weights of polynomials in each dimension
    weights : ndarray of float [n_grid]
        Quadrature weights for each grid point
    """

    def __init__(self, parameters_random, options, coords=None, coords_norm=None,
                 coords_gradient=None, coords_gradient_norm=None, coords_id=None, coords_gradient_id=None,
                 knots_dim_list=None, weights_dim_list=None, weights=None):
        """
        Constructor; Initializes TensorGrid object instance; Generates grid
        """
        super(TensorGrid, self).__init__(parameters_random,
                                         coords=coords,
                                         coords_norm=coords_norm,
                                         coords_gradient=coords_gradient,
                                         coords_gradient_norm=coords_gradient_norm,
                                         coords_id=coords_id,
                                         coords_gradient_id=coords_gradient_id)
        self.options = options
        self.grid_type = options["grid_type"]
        self.n_dim = options["n_dim"]

        if coords is not None and coords_norm is not None:
            grid_present = True

            self.knots_dim_list = knots_dim_list
            self.weights_dim_list = weights_dim_list
            self.weights = weights

        else:
            grid_present = False

        if not grid_present:

            # get knots and weights of polynomials in each dimension
            self.knots_dim_list = []
            self.weights_dim_list = []

            for i_p, p in enumerate(self.parameters_random):

                # Jacobi polynomials
                if self.grid_type[i_p] == 'jacobi':
                    knots, weights = get_quadrature_jacobi_1d(self.n_dim[i_p],
                                                              self.parameters_random[p].pdf_shape[0] - 1,
                                                              self.parameters_random[p].pdf_shape[1] - 1,)

                # Hermite polynomials
                elif self.grid_type[i_p] == 'hermite':
                    knots, weights = get_quadrature_hermite_1d(self.n_dim[i_p])

                # Clenshaw Curtis
                elif self.grid_type[i_p] in ['clenshaw_curtis' or 'cc']:
                    knots, weights = get_quadrature_clenshaw_curtis_1d(self.n_dim[i_p])

                # Fejer type 2 (Clenshaw Curtis without boundary nodes)
                elif self.grid_type[i_p] == 'fejer2':
                    knots, weights = get_quadrature_fejer2_1d(self.n_dim[i_p])

                # Gauss-Patterson (Nested Legendre rule)
                elif self.grid_type[i_p] == 'patterson':
                    knots, weights = get_quadrature_patterson_1d(self.n_dim[i_p])

                else:
                    knots = []
                    weights = []
                    AttributeError("Specified grid_type {} not implemented!".format(self.grid_type[i_p]))

                self.knots_dim_list.append(knots)
                self.weights_dim_list.append(weights)

            # combine coordinates to full tensor grid (all combinations)
            # self.coords_norm = cartesian(self.knots_dim_list)
            self.coords_norm = get_cartesian_product(self.knots_dim_list)

            # rescale normalized coordinates in case of normal distributions and "fejer2" or "cc" grids
            # +- 0.675 * sigma -> 50%
            # +- 1.645 * sigma -> 90%
            # +- 1.960 * sigma -> 95%
            # +- 2.576 * sigma -> 99%
            # +- 3.000 * sigma -> 99.73%
            for i_p, p in enumerate(self.parameters_random):

                if self.parameters_random[p].pdf_type in ["norm", "normal"] and (not(self.grid_type[i_p] == "hermite")):
                    self.coords_norm[:, i_p] = self.coords_norm[:, i_p] * 1.960

            # determine combined weights of Gauss quadrature
            self.weights = np.prod(get_cartesian_product(self.weights_dim_list), axis=1) / (2.0 ** self.dim)

            # denormalize grid to original parameter space
            self.coords = self.get_denormalized_coordinates(self.coords_norm)

            # Total number of nodes in grid
            self.n_grid = self.coords.shape[0]

            # Generate and append unique IDs of grid points
            self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]


class SparseGrid(Grid):
    """
    SparseGrid object instance.

    Parameters
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    options: dict
        Grid parameters
        - grid_type ([N_vars] list of str) ... Type of quadrature rule used to construct sparse grid
          ('jacobi', 'hermite', 'clenshaw_curtis', 'fejer2', 'patterson')
        - level ([N_vars] list of int) ... Number of levels in each dimension
        - level_max (int) ... Global combined level maximum
        - interaction_order (int) ...Interaction order of parameters and grid, i.e. the grid points are lying
          between this number of dimensions
        - order_sequence_type (str) ... Type of order sequence ('lin', 'exp') common: 'exp'
        - make_grid (boolean, optional, default=True) ... Boolean value to determine if to generate grid
          during initialization
        - verbose (bool, optional, default=True) ... Print output messages into stdout
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    level_sequence: list of int
        Integer sequence of levels
    order_sequence: list of int
        Integer sequence of polynomial order of levels
    weights : ndarray of float [n_grid]
        Quadrature weights for each grid point

    Examples
    --------
    >>> import pygpc
    >>> grid = pygpc.SparseGrid(parameters_random=parameters_random,
    >>>                         options={"grid_type": ["jacobi", "jacobi"],
    >>>                                  "level": [3, 3],
    >>>                                  "level_max": 3,
    >>>                                  "interaction_order": 2,
    >>>                                  "order_sequence_type": "exp"})

    Attributes
    ----------
    grid_type: [N_vars] list of str
        specify type of quadrature used to construct sparse grid ('jacobi', 'hermite', 'cc', 'fejer2')
    level: [N_vars] list of int
        number of levels in each dimension
    level_max: int
        global combined level maximum
    level_sequence: list of int
        list containing the levels
    interaction_order: int
        interaction order of parameters and grid, i.e. the grid points are lying between this number of dimensions
    order_sequence_type: str
        type of order sequence ('lin', 'exp') common: 'exp'
    order_sequence: list of int
        list containing the polynomial order of the levels
    coords : ndarray of float [n_grid_add x dim]
            Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    weights : ndarray of float [n_grid]
            Quadrature weights for each grid point
    verbose: bool
        boolean value to determine if to print out the progress into the standard output
    """

    def __init__(self, parameters_random, options, coords=None, coords_norm=None,
                 coords_gradient=None, coords_gradient_norm=None, coords_id=None, coords_gradient_id=None,
                 level_sequence=None, order_sequence=None, weights=None):
        """
        Constructor; Initializes SparseGrid class; Generates grid
        """
        
        super(SparseGrid, self).__init__(parameters_random,
                                         coords=coords,
                                         coords_norm=coords_norm,
                                         coords_gradient=coords_gradient,
                                         coords_gradient_norm=coords_gradient_norm,
                                         coords_id=coords_id,
                                         coords_gradient_id=coords_gradient_id)

        self.grid_type = options["grid_type"]    # Quadrature rule ('jacobi', 'hermite', 'clenshaw_curtis', 'fejer2')
        self.level = options["level"]            # Number of levels in each dimension [dim x 1]
        self.level_max = options["level_max"]    # Global combined level maximum
        self.interaction_order = options["interaction_order"]        # Interaction order of parameters and grid
        self.order_sequence_type = options["order_sequence_type"]    # Order sequence ('lin', 'exp' (common))
        self.level_sequence = []  # Integer sequence of levels
        self.order_sequence = []  # Integer sequence of polynomial order of levels

        # output while grid generation on/off
        if "verbose" not in options.keys():
            self.verbose = False

        # Generate grid if not specified
        if coords is not None and coords_norm is not None:
            grid_present = True

            self.level_sequence = level_sequence
            self.order_sequence = order_sequence
            self.weights = weights

        else:
            grid_present = False

        # Grid is generated during initialization or coords, coords_norm and weights are added manually
        if not grid_present:
            self.calc_multi_indices()
            self.calc_coords_weights()

            # Determine total number of grid points
            self.n_grid = self.coords.shape[0]

            # Generate unique IDs of grid points
            self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]

    def calc_multi_indices(self):
        """
        Calculate the multi index list needed for the calculation of the SparseGrid.
        """
        for i_p, p in enumerate(self.parameters_random):
            
            if self.grid_type[i_p] == 'fejer2':
                self.level_sequence.append([element for element in range(1, self.level[i_p] + 1)])

            else:
                self.level_sequence.append([element for element in range(self.level[i_p] + 1)])

            if self.order_sequence_type == 'exp':         # order = 2**level + 1

                if self.grid_type[i_p] == 'fejer2':       # start with order = 1 @ level = 1
                    self.order_sequence.append((np.power(2, np.arange(1, self.level[i_p])) - 1).tolist())
                    self.order_sequence[i_p][0] = 1

                elif self.grid_type[i_p] == 'patterson':  # start with order = 1 @ level = 0 [1,3,7,15,31,...]
                    self.order_sequence.append((np.power(2, np.arange(0, self.level[i_p])) + 1).tolist())

                else:                                     # start with order = 1 @ level = 0
                    self.order_sequence.append(
                        (2 ** np.linspace(0, self.level[i_p], self.level[i_p] + 1) + 1).tolist())
                    self.order_sequence[i_p][0] = 1

            elif self.order_sequence_type == 'lin':       # order = level
                if self.grid_type[i_p] == 'fejer2':       # start with level = 1 @ order = 1
                    self.order_sequence.append(np.linspace(1, self.level[i_p] + 1, self.level[i_p] + 1).tolist())

                elif self.grid_type[i_p] == 'patterson':  # start with order = 1 @ level = 0 [1,3,7,15,31,...]
                    iprint("Not possible in case of Gauss-Patterson grid.", tab=0, verbose=self.verbose)

                else:                                       # start with
                    self.order_sequence.append(np.linspace(1, self.level[i_p] + 1, self.level[i_p] + 1).tolist())

    def calc_l_level(self):
        """
        Calculate the l-level needed for the Fejer grid type 2.

        l_level = calc_l_level()

        Returns
        -------
        l_level: np.ndarray
            Multi indices filtered by level capacity and interaction order
        """
        if "fejer2" in self.grid_type:
            if self.dim == 1:
                l_level = np.array([np.linspace(1, self.level_max, self.level_max)]).transpose()
            else:
                l_level = get_multi_indices(self.dim, self.level_max - self.dim)
                l_level = l_level + 1
        else:
            if self.dim == 1:
                l_level = np.array([np.linspace(0, self.level_max, self.level_max + 1)]).transpose()
            else:
                l_level = get_multi_indices(order=[self.level_max] * self.dim,
                                            order_max=self.level_max,
                                            interaction_order=self.dim,
                                            order_max_norm=1.,
                                            interaction_order_current=None)

        # filter out rows exceeding the individual level cap
        for i_p in range(self.dim):
            l_level = l_level[l_level[:, i_p] <= self.level[i_p]]

        # Consider interaction order (filter out multi-indices exceeding it)
        if self.interaction_order < self.dim:
            if any("fejer2" in s for s in self.grid_type):
                l_level = l_level[np.sum(l_level > 1, axis=1) <= self.interaction_order, :]
            else:
                l_level = l_level[np.sum(l_level > 0, axis=1) <= self.interaction_order, :]

        return l_level

    def calc_grid(self):
        """
        Calculate a cubature lookup table for knots and weights.

        dl_k, dl_w = calc_grid()

        Returns
        -------
        dl_k: list of list of float
            Cubature lookup table for knots
        dl_w: list of list of float
            Cubature lookup table for weights
        """
        # make cubature lookup table for knots (dl_k) and weights (dl_w) [max(l) x dim]
        iprint("Generating difference grids...", tab=0, verbose=self.verbose)
        dl_k = [[0 for _ in range(self.dim)] for _ in range(int(np.amax(self.level) + 1))]
        dl_w = [[0 for _ in range(self.dim)] for _ in range(int(np.amax(self.level) + 1))]
        knots_l, weights_l, knots_l_1, weights_l_1 = 0, 0, 0, 0

        for i_p, p in enumerate(self.parameters_random):

            for i_level in self.level_sequence[i_p]:

                # Jacobi polynomials
                if self.grid_type[i_p] == 'jacobi':
                    knots_l, weights_l = get_quadrature_jacobi_1d(self.order_sequence[i_p][i_level],
                                                                  self.parameters_random[p].pdf_shape[0] - 1,
                                                                  self.parameters_random[p].pdf_shape[1] - 1)
                    knots_l_1, weights_l_1 = get_quadrature_jacobi_1d(self.order_sequence[i_p][i_level - 1],
                                                                      self.parameters_random[p].pdf_shape[0] - 1,
                                                                      self.parameters_random[p].pdf_shape[1] - 1)

                # Hermite polynomials
                if self.grid_type[i_p] == 'hermite':
                    knots_l, weights_l = get_quadrature_hermite_1d(
                        self.order_sequence[i_p][i_level])
                    knots_l_1, weights_l_1 = get_quadrature_hermite_1d(
                        self.order_sequence[i_p][i_level - 1])

                # Gauss-Patterson
                if self.grid_type[i_p] == 'patterson':
                    knots_l, weights_l = get_quadrature_patterson_1d(
                        self.order_sequence[i_p][i_level])
                    knots_l_1, weights_l_1 = get_quadrature_patterson_1d(
                        self.order_sequence[i_p][i_level - 1])

                # Clenshaw Curtis
                if self.grid_type[i_p] == 'clenshaw_curtis':
                    knots_l, weights_l = get_quadrature_clenshaw_curtis_1d(
                        self.order_sequence[i_p][i_level])
                    knots_l_1, weights_l_1 = get_quadrature_clenshaw_curtis_1d(
                        self.order_sequence[i_p][i_level - 1])

                # Fejer type 2
                if self.grid_type[i_p] == 'fejer2':
                    knots_l, weights_l = get_quadrature_fejer2_1d(
                        self.order_sequence[i_p][i_level - 1])
                    knots_l_1, weights_l_1 = get_quadrature_fejer2_1d(
                        self.order_sequence[i_p][i_level - 2])

                if (i_level == 0 and not self.grid_type[i_p] == 'fejer2') or \
                   (i_level == 1 and (self.grid_type[i_p] == 'fejer2')):
                    dl_k[i_level][i_p] = knots_l
                    dl_w[i_level][i_p] = weights_l
                else:
                    # noinspection PyTypeChecker
                    dl_k[i_level][i_p] = np.hstack((knots_l, knots_l_1))
                    # noinspection PyTypeChecker
                    dl_w[i_level][i_p] = np.hstack((weights_l, -weights_l_1))

        return dl_k, dl_w

    def calc_tensor_products(self):
        """
        Calculate the tensor products of the knots and the weights.

        dll_k, dll_w = calc_tensor_products()

        Returns
        -------
        dll_k: np.ndarray
            Tensor product of knots
        dll_w: np.ndarray
            Tensor product of weights
        """
        # make list of all tensor products according to multi-index list "l"
        iprint("Generating sub-grids...", tab=0, verbose=self.verbose)
        dl_k, dl_w = self.calc_grid()
        l_level = self.calc_l_level()
        dll_k = []
        dll_w = []

        for i_l_level in range(l_level.shape[0]):

            knots = []
            weights = []

            for i_p in range(self.dim):
                knots.append(np.asarray(dl_k[np.int(l_level[i_l_level, i_p])][i_p], dtype=float))
                weights.append(np.asarray(dl_w[np.int(l_level[i_l_level, i_p])][i_p], dtype=float))

            # tensor product of knots
            dll_k.append(get_cartesian_product(knots))

            # tensor product of weights
            dll_w.append(np.prod(get_cartesian_product(weights), axis=1))

        dll_w = np.hstack(dll_w)
        dll_k = np.vstack(dll_k)

        return dll_k, dll_w

    def calc_coords_weights(self):
        """
        Determine coords and weights of sparse grid by generating, merging and subtracting sub-grids.
        """
        # find similar points in grid and formulate Point list
        dll_k, dll_w = self.calc_tensor_products()
        point_number_list = np.zeros(dll_w.shape[0]) - 1
        point_no = 0
        epsilon_k = 1E-6
        coords_norm = []

        iprint("Merging sub-grids...", tab=0, verbose=self.verbose)

        while any(point_number_list < 0):
            not_found = point_number_list < 0
            dll_k_nf = dll_k[not_found]
            point_temp = np.zeros(dll_k_nf.shape[0]) - 1
            point_temp[np.sum(np.abs(dll_k_nf - dll_k_nf[0]), axis=1) < epsilon_k] = point_no
            point_number_list[not_found] = point_temp
            point_no = point_no + 1
            coords_norm.append(dll_k_nf[0, :])

        coords_norm = np.array(coords_norm)
        point_number_list = np.asarray(point_number_list, dtype=int)

        weights = np.zeros(np.amax(point_number_list) + 1) - 999

        for i_point in range(np.amax(point_number_list) + 1):
            weights[i_point] = np.sum(dll_w[point_number_list == i_point])

        # filter for very small weights
        iprint("Filter grid for very small weights...", tab=0, verbose=self.verbose)
        epsilon_w = 1E-8 / self.dim
        keep_point = np.abs(weights) > epsilon_w
        self.weights = weights[keep_point] / 2 ** self.dim
        coords_norm = coords_norm[keep_point]

        # rescale normalized coordinates in case of normal distributions and "fejer2" or "clenshaw_curtis" grids
        # +- 0.675 * sigma -> 50%
        # +- 1.645 * sigma -> 90%
        # +- 1.960 * sigma -> 95%
        # +- 2.576 * sigma -> 99%
        # +- 3.000 * sigma -> 99.73%
        for i_p, p in enumerate(self.parameters_random):
            if self.parameters_random[p].pdf_type in ["norm", "normal"] and (not(self.grid_type[i_p] == "hermite")):
                coords_norm[:, i_p] = coords_norm[:, i_p] * 1.960

        # denormalize grid to original parameter space
        iprint("Denormalizing grid for computations...", tab=0, verbose=self.verbose)
        self.coords_norm = coords_norm
        self.coords = self.get_denormalized_coordinates(coords_norm)


class RandomGrid(Grid):
    """
    RandomGrid object

    Parameters
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid: int
        Number of random samples in grid
    seed : float, optional, default=None
        Seeding point to replicate random grid
    options : dict, optional, default=None
        RandomGrid options depending on the grid type
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points

    Examples
    --------
    >>> import pygpc
    >>> grid = pygpc.RandomGrid(parameters_random=parameters_random, n_grid=100, seed=1, options=None)

    Attributes
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid: int
        Number of random samples in grid
    seed : float, optional, default=None
        Seeding point to replicate random grid
    options : dict, optional, default=None
        RandomGrid options depending on the grid type
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    """

    def __init__(self, parameters_random, n_grid=None, seed=None, options=None, coords=None, coords_norm=None,
                 coords_gradient=None, coords_gradient_norm=None, coords_id=None, coords_gradient_id=None):
        """
        Constructor; Initializes RandomGrid instance; Generates grid
        """
        super(RandomGrid, self).__init__(parameters_random,
                                         coords=coords,
                                         coords_norm=coords_norm,
                                         coords_gradient=coords_gradient,
                                         coords_gradient_norm=coords_gradient_norm,
                                         coords_id=coords_id,
                                         coords_gradient_id=coords_gradient_id)

        self.n_grid = int(n_grid)
        self.seed = seed
        self.options = options

    def extend_random_grid(self, n_grid_new=None, coords=None, coords_norm=None, seed=None,
                           classifier=None, domain=None, gradient=False, grid=None):
        """
        Add sample points according to input pdfs to grid (old points are kept). Define either the new total number of
        grid points with "n_grid_new" or add grid-points manually by providing "coords" and "coords_norm".

        extend_random_grid(n_grid_new, coords=None, coords_norm=None, seed=None, classifier=None, domain=None):

        Parameters
        ----------
        n_grid_new : float
            Total number of grid points in extended random grid (old points are kept)
            (n_grid_add = n_grid_new - n_grid_old)
        coords : ndarray of float [n_grid_add x dim]
            Grid points to add (model space)
        coords_norm : ndarray of float [n_grid_add x dim]
            Grid points to add (normalized space)
        seed : float, optional, default=None
            Seeding point to replicate random grid
        classifier : Classifier object, optional, default: None
            Classifier
        domain : int, optional, default: None
            Adds grid points only in specified domain (needs Classifier object including a predict() method)
        gradient : bool, optional, default: False
            Add corresponding gradient grid points
        grid : RandomGrid Object, optional, default=None
            Optional initial grid, which gets extended
        """

        def lhs_extend(self, array, n_extend):
            dim = np.shape(array)[1]
            n_old = np.shape(array)[0]
            n_new = n_old + n_extend
            a_new = np.zeros([n_extend, np.shape(array)[1]])
            u = np.random.rand(n_new, np.shape(array)[1])
            # array = np.insert(array, n_old, np.zeros([n_extend ,np.shape(array)[1]]), axis=0)
            for d in range(dim):
                k = 0
                s = 0
                for j in range(n_new - 1):
                    if not float(j / n_new) < float(np.sort(array[:, d])[min((j + s), len(array) - 1)]) < float(
                            (j + 1) / n_new):
                        if float((j + 1) / n_new) <= float(np.sort(array[:, d])[min((j + s), len(array) - 1)]):
                            s = s - 1
                        else:
                            j = j - 1
                            s = s + 1
                        k = k + 1
                        if k is np.shape(a_new)[0] + 1:
                            k = 1
                        a_new[k - 1, d] = float((j + u[j, d]) / n_new)
                np.random.shuffle(a_new[:, d])
            return np.insert(array, n_old, a_new, axis=0)

        if n_grid_new is not None:
            # Number of new grid points
            n_grid_add = int(n_grid_new - self.n_grid)

            if n_grid_add > 0:
                # Generate new grid points
                if classifier is None:
                    if isinstance(self, Random):
                        new_grid = Random(parameters_random=self.parameters_random,
                                          n_grid=n_grid_add,
                                          seed=seed,
                                          options=self.options)

                        # append points to existing grid
                        self.coords = np.vstack([self.coords, new_grid.coords])
                        self.coords_norm = np.vstack([self.coords_norm, new_grid.coords_norm])

                    elif isinstance(self, LHS):
                        # append points to existing grid
                        self.coords = lhs_extend(self.coords_reservoir, n_grid_new)
                        self.coords_norm = np.vstack([self.coords_norm, self.coords_norm_reservoir[self.n_grid:n_grid_new]])

                else:
                    coords = np.zeros((n_grid_add, len(self.parameters_random)))
                    coords_norm = np.zeros((n_grid_add, len(self.parameters_random)))

                    # add grid points one by one because we are looking for samples in the right domain
                    for i in range(n_grid_add):
                        resample = True
                        while resample:
                            if isinstance(self, Random):
                                new_grid = Random(parameters_random=self.parameters_random,
                                                  n_grid=1,
                                                  seed=seed,
                                                  options=self.options)

                                # test if grid point lies in right domain
                                if classifier.predict(new_grid.coords_norm)[0] == domain:
                                    coords[i, :] = new_grid.coords
                                    coords_norm[i, :] = new_grid.coords_norm
                                    resample = False

                            elif isinstance(self, LHS):
                                # check if gridpoint exceeds sampling reservoir
                                # if self.n_grid > max(10000, self.n_grid_lhs * 10)
                                # coords.np.append(pygpc.LSH( seed=seed+1))
                                coords_norm_test = lhs_extend(self.coords_norm_reservoir, 1)
                                # test if next grid point lies in right domain
                                if classifier.predict(coords_norm_test[len(coords_norm_test) - 1]) == domain:
                                    self.coords_norm_reservoir = coords_norm_test
                                    coords[i, :] = self.coords_reservoir[self.n_grid]
                                    coords_norm[i, :] = self.coords_norm_reservoir[self.n_grid]
                                    self.n_grid += 1
                                    resample = False

                                #else:
                                    # delete tested point
                                    # self.coords_norm_reservoir = np.delete(self.coords_norm_reservoir, self.n_grid, 0)
                                    # self.coords_reservoir = np.delete(self.coords_reservoir, self.n_grid, 0)
                                    # self.lhs_reservoir = np.delete(self.lhs_reservoir, self.n_grid, 0)

                    # append points to existing grid
                    self.coords = np.vstack([self.coords, coords])
                    self.coords_norm = np.vstack([self.coords_norm, coords_norm])

        elif coords is not None and coords_norm is not None:
            # Number of new grid points
            n_grid_add = coords.shape[0]

            # check if specified points are lying in right domain
            if classifier is not None:
                if not (classifier.predict(coords_norm) == domain).all():
                    raise AssertionError("Specified coordinates are not lying in right domain!")

            # append points to existing grid
            self.coords = np.vstack([self.coords, coords])
            self.coords_norm = np.vstack([self.coords_norm, coords_norm])

        else:
            raise ValueError("Specify either n_grid_new or coords and coords_norm")

        # Generate and append unique IDs of new grid points
        self.coords_id = self.coords_id + [uuid.uuid4() for _ in range(n_grid_add)]

        self.n_grid = self.coords.shape[0]

        if gradient:
            self.create_gradient_grid()

    def ese_mu_iter(self, dim, n, gpc):

        mu = np.zeros(n)
        for i in range(self.factor):
            design = self.lhs_ese_(dim, n)
            psy = gpc.create_gpc_matrix(b=gpc.basis.b, x=self.coords_norm, gradient=False)
            normalized_psy= psy / np.abs(psy.max(axis=0))
            mu[i] = mutual_coherence(normalized_psy)
            if np.argmin(mu) is i:
                design_best = design
        return design_best

    def ese_mu_greedy(self, dim, n, gpc):
        # self.split = self.options[1]
        n_ese = int(self.split * n)
        n_mu = n - n_ese
        design_ese = self.lhs_ese_(dim, n)
        matrix_ese = gpc.create_gpc_matrix(b=gpc.basis.b, x=self.coords_norm, gradient=False)
        design = design_ese[:n_ese, :]
        idxs = []
        for i in range(n_mu):
            # if (n_mu - i) > 0:
            mu_vals = []
            idx_list = []
            # temp = design_ese[:(n_ese + i), :]
            idx_left = [k for k in range(n_mu) if k not in idxs]
            for j in idx_left:
                a = np.vstack((design, design_ese[j + n_ese]))
                mu_vals.append(mutual_coherence(a))
                idx_list.append(j)
                mu_array = np.array(mu_vals)
            idx_best = idx_list[np.argmin(mu_array)]
            idxs.append(idx_best)
            design = np.vstack((design, design_ese[idx_best + n_ese]))
            # else:
            #     design = np.vstack((design, design_ese[n-1]))
        return design
    def lhs_ese_(self, dim, n, t0=None):
        """
        Create optimized LHS grid using a enhanced stochastic evolutionary algorithm for the PhiP Maximin criterion [1]

        Parameters
        ----------
        dim : int
            Number of random variables
        n : int
            Number of sampling points
        t0 : int, optional, default: None
            Threshold parameter

        Returns
        -------
        design : ndarray of float [n, n_dim]
            LHS grid points

        Notes
        -----
        .. [1] Jin, R., Chen, W., & Sudjianto, A. (2005). An efficient algorithm for constructing optimal
           design of computer experiments. Journal of statistical planning and inference, 134(1), 268-287.
        """

        # Parameters
        P0 = self.lhs_initial(dim, n)
        J = 25
        tol = 1e-3
        p = 10
        outer_loop = min(int(1.5 * dim), 30)
        inner_loop = min(20 * dim, 100)
        fixed_index = []
        if t0 is None:
            t0 = 0.005 * self.PhiP(P0, p=p)

        T = t0
        P_ = P0[:]  # copy of initial design
        P_best = P_[:]
        Phi = self.PhiP(P_best, p=p)
        Phi_best = Phi

        # Outer loop
        for z in range(outer_loop):
            Phi_oldbest = Phi_best
            n_acpt = 0
            n_imp = 0

            # Inner loop
            for i in range(inner_loop):
                modulo = (i + 1) % dim
                l_P = list()
                l_Phi = list()

                # Build J different designs with a single exchanged rows
                # See PhiP_exchange
                for j in range(J):
                    l_P.append(P_.copy())
                    l_Phi.append(self.PhiP_exchange(l_P[j], k=modulo, Phi=Phi, p=p, fixed_index=fixed_index))

                l_Phi = np.asarray(l_Phi)
                k = np.argmin(l_Phi)
                Phi_try = l_Phi[k]

                # Threshold of acceptance
                if Phi_try - Phi <= T * np.random.rand(1)[0]:
                    Phi = Phi_try
                    n_acpt = n_acpt + 1
                    P_ = l_P[k]

                    # Best design retained
                    if Phi < Phi_best:
                        P_best = P_
                        Phi_best = Phi
                        n_imp = n_imp + 1

            p_accpt = float(n_acpt) / inner_loop  # probability of acceptance
            p_imp = float(n_imp) / inner_loop  # probability of improvement

            if Phi_best - Phi_oldbest < tol:
                # flag_imp = 1
                if p_accpt >= 0.1 and p_imp < p_accpt:
                    T = 0.8 * T
                elif p_accpt >= 0.1 and p_imp == p_accpt:
                    pass
                else:
                    T = T / 0.8
            else:
                # flag_imp = 0
                if p_accpt <= 0.1:
                    T = T / 0.7
                else:
                    T = 0.9 * T
        return P_best

    def PhiP(self, x, p=10):
        """
        Calculates the Phi-p criterion of the design x with power p [1].

        Parameters
        ----------
        x : ndarray of float [n x m]
            The design to calculate Phi-p for
        p : int, optional, default: 10
            The power used for the calculation of PhiP

        Returns
        -------
        phip : float
            Phi-p criterion

        Notes
        -----
        .. [1] Morris, M. D., & Mitchell, T. J. (1995). Exploratory designs for computational experiments.
           Journal of statistical planning and inference, 43(3), 381-402.
        """

        phip = ((scipy.spatial.distance.pdist(x) ** (-p)).sum()) ** (1.0 / p)

        return phip

    def PhiP_exchange(self, P, k, Phi, p, fixed_index):
        """
        Performes a row exchange and return the altered design.

        Parameters
        ----------
        P : ndarray of float [m x n]
            The design to perform the exchange on
        k : int
            modulus of the iteration divided by the dimension to pick a row of the design repeating through the
            dimensions of the design
        Phi: float
            the PhiP criterion of the current best Design
        p: int
            The power used for the calculation of PhiP
        fixed_index: list
            an empty list to check if variables are assigned a value

        Returns
        -------
        phip : float
            Phi-p criterion
        """
        # Choose two (different) random rows to perform the exchange
        er = P.shape
        i1 = np.random.randint(P.shape[0])
        while i1 in fixed_index:
            i1 = np.random.randint(P.shape[0])

        i2 = np.random.randint(P.shape[0])
        while i2 == i1 or i2 in fixed_index:
            i2 = np.random.randint(P.shape[0])

        P_ = np.delete(P, [i1, i2], axis=0)

        dist1 = scipy.spatial.distance.cdist([P[i1, :]], P_)
        dist2 = scipy.spatial.distance.cdist([P[i2, :]], P_)
        d1 = np.sqrt(dist1 ** 2 + (P[i2, k] - P_[:, k]) ** 2 - (P[i1, k] - P_[:, k]) ** 2)
        d2 = np.sqrt(dist2 ** 2 - (P[i2, k] - P_[:, k]) ** 2 + (P[i1, k] - P_[:, k]) ** 2)

        res = (Phi ** p + (d1 ** (-p) - dist1 ** (-p) + d2 ** (-p) - dist2 ** (-p)).sum()) ** (1.0 / p)

        P[i1, k], P[i2, k] = P[i2, k], P[i1, k]
        return res

    def lhs_initial(self, dim, n):
        """
        Construct an initial LHS grid

        Parameters
        ----------
        dim : int
            Number of random variables
        n : int
            Number of sampling points

        Returns
        -------
        design : ndarray of float [n, n_dim]
            LHS grid points
        """
        design = np.zeros([n, dim])

        # u = matrix of uniform (0,1) that vary in n subareas
        u = np.random.rand(n, dim)

        for i in range(0, dim):
            for j in range(0, n):
                design[j, i] = j + 1
            np.random.shuffle(design[:, i])

        for i in range(0, dim):
            for j in range(0, n):
                design[j, i] = (design[j, i] - u[j, i]) / n

        return design

class Random(RandomGrid):
    """
    Random grid object

    Parameters
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid : int or float
        Number of random samples in grid
    seed : float, optional, default=None
        Seeding point to replicate random grid
    options : dict, optional, default=None
        RandomGrid options depending on the grid type
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points

    Examples
    --------
    >>> import pygpc
    >>> grid = pygpc.Random(parameters_random=parameters_random, n_grid=100, seed=1)

    Attributes
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid : int or float
        Number of random samples in grid
    seed : float, optional, default=None
        Seeding point to replicate random grid
    options : dict, optional, default=None
        RandomGrid options depending on the grid type
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    """

    def __init__(self, parameters_random, n_grid=None, seed=None, options=None, coords=None, coords_norm=None,
                 coords_gradient=None, coords_gradient_norm=None, coords_id=None, coords_gradient_id=None):
        """
        Constructor; Initializes RandomGrid instance; Generates grid or copies provided content
        """
        super(Random, self).__init__(parameters_random,
                                     n_grid=n_grid,
                                     seed=seed,
                                     options=options,
                                     coords=coords,
                                     coords_norm=coords_norm,
                                     coords_gradient=coords_gradient,
                                     coords_gradient_norm=coords_gradient_norm,
                                     coords_id=coords_id,
                                     coords_gradient_id=coords_gradient_id)

        if coords is not None and coords_norm is not None:
            grid_present = True
        else:
            grid_present = False

        if not grid_present:
            # Seed of random grid (if necessary to reproduce random grid)
            if self.seed is not None:
                np.random.seed(self.seed)

            # Generate random samples for each random input variable [n_grid x dim]
            self.coords_norm = np.zeros([self.n_grid, self.dim])

            # in case of seeding, the random grid is constructed element wise (same grid-points when n_grid differs)
            if self.seed:
                for i_grid in range(self.n_grid):
                    for i_p, p in enumerate(self.parameters_random):

                        if self.parameters_random[p].pdf_type == "beta":
                            self.coords_norm[i_grid, i_p] = np.random.beta(self.parameters_random[p].pdf_shape[0],
                                                                           self.parameters_random[p].pdf_shape[1],
                                                                           1) * 2.0 - 1

                        if self.parameters_random[p].pdf_type in ["norm", "normal"]:

                            resample = True

                            while resample:
                                self.coords_norm[i_grid, i_p] = np.random.normal(loc=0,
                                                                                 scale=1,
                                                                                 size=1)
                                resample = self.coords_norm[i_grid, i_p] < self.parameters_random[p].x_perc_norm[0] or \
                                           self.coords_norm[i_grid, i_p] > self.parameters_random[p].x_perc_norm[1]

                        if self.parameters_random[p].pdf_type in ["gamma"]:

                            resample = True

                            while resample:
                                self.coords_norm[i_grid, i_p] = np.random.gamma(
                                    shape=self.parameters_random[p].pdf_shape[0],
                                    scale=1.0,
                                    size=1)
                                resample = self.coords_norm[i_grid, i_p] > self.parameters_random[p].x_perc_norm

            else:
                for i_p, p in enumerate(self.parameters_random):
                    try:
                        self.parameters_random[p].pdf_type
                    except AttributeError:
                        te = 1
                    if self.parameters_random[p].pdf_type == "beta":
                        self.coords_norm[:, i_p] = (np.random.beta(self.parameters_random[p].pdf_shape[0],
                                                                   self.parameters_random[p].pdf_shape[1],
                                                                   [self.n_grid, 1]) * 2.0 - 1)[:, 0]

                    if self.parameters_random[p].pdf_type in ["norm", "normal"]:
                        resample = True
                        outlier_mask = np.ones(self.n_grid, dtype=bool)
                        j = 0
                        while resample:
                            # print("Iteration: {}".format(j+1))
                            self.coords_norm[outlier_mask, i_p] = (np.random.normal(loc=0,
                                                                                    scale=1,
                                                                                    size=[np.sum(outlier_mask), 1]))[:, 0]

                            outlier_mask = np.logical_or(
                                self.coords_norm[:, i_p] < self.parameters_random[p].x_perc_norm[0],
                                self.coords_norm[:, i_p] > self.parameters_random[p].x_perc_norm[1])

                            resample = outlier_mask.any()

                            j += 1

                    if self.parameters_random[p].pdf_type in ["gamma"]:
                        resample = True
                        outlier_mask = np.ones(self.n_grid, dtype=bool)
                        j = 0
                        while resample:
                            # print("Iteration: {}".format(j + 1))
                            self.coords_norm[outlier_mask, i_p] = (np.random.gamma(
                                shape=self.parameters_random[p].pdf_shape[0],
                                scale=1.0,
                                size=[np.sum(outlier_mask), 1]))[:, 0]

                            outlier_mask = np.array(self.coords_norm[:, i_p] > self.parameters_random[p].x_perc_norm)

                            resample = outlier_mask.any()

                            j += 1

            # Denormalize grid to original parameter space
            self.coords = self.get_denormalized_coordinates(self.coords_norm)

            # Generate unique IDs of grid points
            self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]


class LHS(RandomGrid):
    """
    LHS grid object

    Parameters
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid: int
        Number of random samples to generate
    seed: float
        Seeding point to replicate random grids
    options: dict, optional, default=None
        Grid options:
        - 'corr'            : optimizes design points in their spearman correlation coefficients
        - 'maximin' or 'm'  : optimizes design points in their maximum minimal distance using the Phi-P criterion
        - 'ese'             : uses an enhanced evolutionary algorithm to optimize the Phi-P criterion
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points

    Examples
    --------
    >>> import pygpc
    >>> grid = pygpc.LHS(parameters_random=parameters_random, n_grid=100, seed=1, options=options)

    Attributes
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid : int or float
        Number of random samples in grid
    seed : float, optional, default=None
        Seeding point to replicate random grid
    options: dict, optional, default=None
        Grid options:
        - 'corr'            : optimizes design points in their spearman correlation coefficients
        - 'maximin' or 'm'  : optimizes design points in their maximum minimal distance using the Phi-P criterion
        - 'ese'             : uses an enhanced evolutionary algorithm to optimize the Phi-P criterion
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    """

    def __init__(self, parameters_random, n_grid=None, seed=None, options=None, coords=None, coords_norm=None,
                 coords_gradient=None, coords_gradient_norm=None, coords_id=None, coords_gradient_id=None):
        """
        Constructor; Initializes RandomGrid instance; Generates grid or copies provided content
        """

        self.lhs_reservoir = None
        self.perc_mask = None
        self.coords_reservoir = None
        self.coords_norm_reservoir = None

        super(LHS, self).__init__(parameters_random,
                                  n_grid=n_grid,
                                  seed=seed,
                                  options=options,
                                  coords=coords,
                                  coords_norm=coords_norm,
                                  coords_gradient=coords_gradient,
                                  coords_gradient_norm=coords_gradient_norm,
                                  coords_id=coords_id,
                                  coords_gradient_id=coords_gradient_id)

        if coords is not None and coords_norm is not None:
            grid_present = True
        else:
            grid_present = False

        if not grid_present:
            if self.n_grid > 0:
                self.sample_init(self.n_grid)

    def sample_init(self, n_grid):
        """
        Initialises all parameters for Latin Hypercube Sampling and creates a new design
        if there is at least one sampling point needed

        Parameters
        ----------
        n_grid : ndarray of float [n]
            The number of needed sampes points

        Returns
        -------
        coords : ndarray of float [n_grid_add x dim]
            Grid points to add (model space)
        coords_norm : ndarray of float [n_grid_add x dim]
            Grid points to add (normalized space)
        coords_id : list of UUID objects (version 4) [n_grid]
            Unique IDs of grid points
        """
        if n_grid > 0:
            n_grid_lhs = self.n_grid
            self.coords_reservoir = np.zeros((n_grid_lhs, self.dim))
            self.coords_norm_reservoir = np.zeros((n_grid_lhs, self.dim))
            self.perc_mask = np.zeros((n_grid_lhs, self.dim)).astype(bool)

            if n_grid < 2:
                if self.options is 'ese':
                    self.options = 'maximin'

            # Generate random samples for each random input variable [n_grid x dim]
            self.coords_norm = np.zeros([self.n_grid, self.dim])

            # generate LHS grid in icdf space (seed of random grid (if necessary to reproduce random grid)
            self.lhs_reservoir = self.get_lhs_grid(dim=self.dim, n=n_grid_lhs, crit=self.options, random_state=self.seed)

            # transform sample points from icdf to pdf space
            for i_p, p in enumerate(self.parameters_random):
                self.coords_norm_reservoir[:, i_p] = self.parameters_random[p].icdf(self.lhs_reservoir[:, i_p])
                self.perc_mask[:, i_p] = np.logical_and(
                    self.parameters_random[p].pdf_limits_norm[0] < self.coords_norm_reservoir[:, i_p],
                    self.coords_norm_reservoir[:, i_p] < self.parameters_random[p].pdf_limits_norm[1])

            # get points all satisfying perc constraints
            self.perc_mask = self.perc_mask.all(axis=1)
            self.coords_norm_reservoir = self.coords_norm_reservoir[self.perc_mask, :]

            self.coords_norm = self.coords_norm_reservoir[0:self.n_grid, :]

            # Denormalize grid to original parameter space
            self.coords = self.get_denormalized_coordinates(self.coords_norm)
            self.coords_reservoir = self.get_denormalized_coordinates(self.coords_norm_reservoir)

            # Generate unique IDs of grid points
            self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]

        else:
            pass

    def CL2(self, array):
        """
        Calculate the L2 discrepancy of the design
        The discrepancy is a measure of the difference between the empirical cumulative distribution function
        of an experimental design and the uniform cumulative distribution function [1].

        Parameters
        ----------
        array : ndarray of float [m x n]
            Array with n rows of samples and m columns of variables/dimensions

        Returns
        -------
        cl2d_crit : float
            criterion for centered L2 discrepancy

        Notes
        -----
        .. [1] Hickernell, F. (1998). A generalized discrepancy and quadrature error bound.
           Mathematics of computation, 67(221), 299-322.
        """
        subtract = np.ones([np.shape(array)[0], np.shape(array)[1]])
        array = array - 0.5 * subtract
        prod_array_1 = np.zeros(np.shape(array)[0])
        for n in range(0, np.shape(array)[0]):
            prod_array_1[n] = (np.ones(np.shape(array)[1]) + (1 / 2 * (np.abs(array[n, :]))) - (
                    1 / 2 * ((array[n, :]) ** 2))).prod()
        prod_array_2 = np.zeros([np.shape(array)[0], np.shape(array)[0]])
        for i in range(0, np.shape(array)[0]):
            for j in range(0, np.shape(array)[0]):
                prod_array_2[i, j] = (np.ones(np.shape(array)[1]) + (1 / 2 * (np.abs(array[i, :]))) - (
                        1 / 2 * np.abs(array[j, :]) - 1 / 2 * np.abs(array[i, :] - array[j, :]))).prod()
        cl2d_crit = ((13 / 12) ** 2) - (2 / (np.shape(array)[0]) * prod_array_1.sum()) + (1 / (
                np.shape(array)[0] ** 2) * prod_array_2.sum())
        # centered L2 discrepancy criteria
        return cl2d_crit

    def log_R(self, array):
        """
        Determines the Log(R) Entropy Criterion[1]

        Parameters
        ----------
        array : ndarray of float [m x n]
            Array

        Returns
        -------
        log_R : float
            Log(R) Entropy Criterion
        Notes
        -----
        .. [1] Koehler, J.R., Owen, A.B., 1996. Computer experiments. in: Ghosh, S., Rao, C.R. (Eds.),
           Handbook of Statistics. Elsevier Science, New York, pp.261-308
        """
        # R will be [m x m]
        R = np.corrcoef(array.T)
        for i in range(0, np.shape(array)[1]):
            for j in range(0, np.shape(array)[1]):
                R[i, j] = np.exp((R[i, :] * np.abs(array[i, :] - array[j, :]) ** 2).sum())
        log_R = np.log(np.linalg.norm(R))

        return (log_R)

    def PhiP(self, x, p=10):
        """
        Calculates the Phi-p criterion of the design x with power p [1].

        Parameters
        ----------
        x : ndarray of float [n x m]
            The design to calculate Phi-p for
        p : int, optional, default: 10
            The power used for the calculation of PhiP

        Returns
        -------
        phip : float
            Phi-p criterion

        Notes
        -----
        .. [1] Morris, M. D., & Mitchell, T. J. (1995). Exploratory designs for computational experiments.
           Journal of statistical planning and inference, 43(3), 381-402.
        """

        phip = ((scipy.spatial.distance.pdist(x) ** (-p)).sum()) ** (1.0 / p)

        return phip

    def PhiP_exchange(self, P, k, Phi, p, fixed_index):
        """
        Performes a row exchange and return the altered design.

        Parameters
        ----------
        P : ndarray of float [m x n]
            The design to perform the exchange on
        k : int
            modulus of the iteration divided by the dimension to pick a row of the design repeating through the
            dimensions of the design
        Phi: float
            the PhiP criterion of the current best Design
        p: int
            The power used for the calculation of PhiP
        fixed_index: list
            an empty list to check if variables are assigned a value

        Returns
        -------
        phip : float
            Phi-p criterion
        """
        # Choose two (different) random rows to perform the exchange
        er = P.shape
        i1 = np.random.randint(P.shape[0])
        while i1 in fixed_index:
            i1 = np.random.randint(P.shape[0])

        i2 = np.random.randint(P.shape[0])
        while i2 == i1 or i2 in fixed_index:
            i2 = np.random.randint(P.shape[0])

        P_ = np.delete(P, [i1, i2], axis=0)

        dist1 = scipy.spatial.distance.cdist([P[i1, :]], P_)
        dist2 = scipy.spatial.distance.cdist([P[i2, :]], P_)
        d1 = np.sqrt(dist1 ** 2 + (P[i2, k] - P_[:, k]) ** 2 - (P[i1, k] - P_[:, k]) ** 2)
        d2 = np.sqrt(dist2 ** 2 - (P[i2, k] - P_[:, k]) ** 2 + (P[i1, k] - P_[:, k]) ** 2)

        res = (Phi ** p + (d1 ** (-p) - dist1 ** (-p) + d2 ** (-p) - dist2 ** (-p)).sum()) ** (1.0 / p)

        P[i1, k], P[i2, k] = P[i2, k], P[i1, k]
        return res

    def get_lhs_grid(self, dim, n, crit=None, random_state=None):
        """
        Create samples in an m*n matrix using Latin Hypercube Sampling [1].

        Parameters
        ----------
        dim : int
            Number of random variables
        n : int
            Number of sampling points
        crit : str, optional, default: None (regular LHS)
            Criterion of LHS grid:
            - 'corr' - optimizes design points in their spearman correlation coefficients
            - 'maximin' or 'm' - optimizes design points in their maximum minimal distance using the Phi-P criterion
            - 'ese' -  uses an enhanced evolutionary algorithm to optimize the Phi-P criterion

        Returns
        -------
        design : ndarray of float [n_grid, n_dim]
            LHS grid points

        Notes
        -----
        .. [1] McKay, M. D., Beckman, R. J., & Conover, W. J. (2000). A comparison of three methods for selecting
           values of input variables in the analysis of output from a computer code. Technometrics, 42(1), 55-61.
        """
        if crit is not None:
            if len(crit) is 2:
                self.split = crit[1]
                crit = crit[0]

        if random_state is None:
            random_state = np.random.RandomState()
        elif not isinstance(random_state, np.random.RandomState):
            random_state = np.random.RandomState(random_state)
        if crit is 'corr':
            return self.lhs_corr(dim, n, 100)
        elif crit is 'maximin' or crit is 'm':
            return self.lhs_maximin(dim, n, 100)
        elif crit is 'ese':
            return self.lhs_ese(dim, n)
        elif crit is 'ese_mu':
            return self.ese_mu(dim, n)
        else:
            return self.lhs_initial(dim, n)

    def lhs_initial(self, dim, n):
        """
        Construct an initial LHS grid

        Parameters
        ----------
        dim : int
            Number of random variables
        n : int
            Number of sampling points

        Returns
        -------
        design : ndarray of float [n, n_dim]
            LHS grid points
        """
        design = np.zeros([n, dim])

        # u = matrix of uniform (0,1) that vary in n subareas
        u = np.random.rand(n, dim)

        for i in range(0, dim):
            for j in range(0, n):
                design[j, i] = j + 1
            np.random.shuffle(design[:, i])

        for i in range(0, dim):
            for j in range(0, n):
                design[j, i] = (design[j, i] - u[j, i]) / n

        return design

    def lhs_corr(self, dim, n, iterations):
        """
        Create a correlation optimized LHS grid

        Parameters
        ----------
        dim : int
            Number of random variables
        n : int
            Number of sampling points
        iterations : int
            Number of iterations to optimize

        Returns
        -------
        design : ndarray of float [n, n_dim]
            LHS grid points
        """
        mincorr = np.inf

        # Minimize the components correlation coefficients
        for i in range(iterations):
            # Generate a random LHS
            test = self.lhs_initial(dim, n)
            R = scipy.stats.spearmanr(test)[0]

            if np.max(np.abs(R)) < mincorr:
                mincorr = np.max(np.abs(R))
                design = test.copy()

        return design

    def lhs_maximin(self, dim, n, iterations):
        """
        Create an optimized LHS grid with maximal minimal distance

        Parameters
        ----------
        dim : int
            Number of random variables
        n : int
            Number of sampling points
        iterations : int
            Number of iterations to optimize

        Returns
        -------
        design : ndarray of float [n, n_dim]
            LHS grid points
        """
        phi_best = max(1000, n * 100)

        # Maximize the minimum distance between points
        for i in range(iterations):
            test = self.lhs_initial(dim, n)
            phi = self.PhiP(test)
            if phi_best > phi:
                phi_best = phi
                design = test.copy()

        return design

    def lhs_ese(self, dim, n, t0=None):
        """
        Create optimized LHS grid using a enhanced stochastic evolutionary algorithm for the PhiP Maximin criterion [1]

        Parameters
        ----------
        dim : int
            Number of random variables
        n : int
            Number of sampling points
        t0 : int, optional, default: None
            Threshold parameter

        Returns
        -------
        design : ndarray of float [n, n_dim]
            LHS grid points

        Notes
        -----
        .. [1] Jin, R., Chen, W., & Sudjianto, A. (2005). An efficient algorithm for constructing optimal
           design of computer experiments. Journal of statistical planning and inference, 134(1), 268-287.
        """

        # Parameters
        P0 = self.lhs_initial(dim, n)
        J = 25
        tol = 1e-3
        p = 10
        outer_loop = min(int(1.5 * dim), 30)
        inner_loop = min(20 * dim, 100)
        fixed_index = []
        if t0 is None:
            t0 = 0.005 * self.PhiP(P0, p=p)

        T = t0
        P_ = P0[:]  # copy of initial design
        P_best = P_[:]
        Phi = self.PhiP(P_best, p=p)
        Phi_best = Phi

        # Outer loop
        for z in range(outer_loop):
            Phi_oldbest = Phi_best
            n_acpt = 0
            n_imp = 0

            # Inner loop
            for i in range(inner_loop):
                modulo = (i + 1) % dim
                l_P = list()
                l_Phi = list()

                # Build J different designs with a single exchanged rows
                # See PhiP_exchange
                for j in range(J):
                    l_P.append(P_.copy())
                    l_Phi.append(self.PhiP_exchange(l_P[j], k=modulo, Phi=Phi, p=p, fixed_index=fixed_index))

                l_Phi = np.asarray(l_Phi)
                k = np.argmin(l_Phi)
                Phi_try = l_Phi[k]

                # Threshold of acceptance
                if Phi_try - Phi <= T * np.random.rand(1)[0]:
                    Phi = Phi_try
                    n_acpt = n_acpt + 1
                    P_ = l_P[k]

                    # Best design retained
                    if Phi < Phi_best:
                        P_best = P_
                        Phi_best = Phi
                        n_imp = n_imp + 1

            p_accpt = float(n_acpt) / inner_loop  # probability of acceptance
            p_imp = float(n_imp) / inner_loop  # probability of improvement

            if Phi_best - Phi_oldbest < tol:
                # flag_imp = 1
                if p_accpt >= 0.1 and p_imp < p_accpt:
                    T = 0.8 * T
                elif p_accpt >= 0.1 and p_imp == p_accpt:
                    pass
                else:
                    T = T / 0.8
            else:
                # flag_imp = 0
                if p_accpt <= 0.1:
                    T = T / 0.7
                else:
                    T = 0.9 * T
        return P_best

    # def ese_mu(self, dim, n):
    #     n_ese = int(self.split*n)
    #     n_mu = n - n_ese
    #     if(n_ese < 1):
    #         n_mu = n_mu - 1
    #         design = np.random.rand(1, dim)
    #     elif(n_ese is 1):
    #         design = np.random.rand(1, dim)
    #     else:
    #         design = self.lhs_ese(dim, n_ese)
    #     design_rand = np.random.rand(n_mu, dim)
    #     idxs = []
    #     for i in range(n_mu):
    #         mu_vals = []
    #         idx_list = []
    #         for j in [k for k in range(n_mu) if k not in idxs]:
    #             a = np.vstack((design, design_rand[j]))
    #             mu_vals.append(mutual_coherence(a))
    #             idx_list.append(j)
    #         mu_array = np.array(mu_vals)
    #         idx_best = idx_list[np.argmin(mu_array)]
    #         idxs.append(idx_best)
    #         design = np.vstack((design, design_rand[idx_best]))
    #
    #     return design
class MCMC(RandomGrid):
    """
    LHS grid object

    Parameters
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid: int
        Number of random samples to generate
    seed: float
        Seeding point to replicate random grids
    options: dict, optional, default=None
        Grid options:
        - 'corr'            : optimizes design points in their spearman correlation coefficients
        - 'maximin' or 'm'  : optimizes design points in their maximum minimal distance using the Phi-P criterion
        - 'ese'             : uses an enhanced evolutionary algorithm to optimize the Phi-P criterion
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points

    Examples
    --------
    >>> import pygpc
    >>> grid = pygpc.LHS(parameters_random=parameters_random, n_grid=100, seed=1, options=options)

    Attributes
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid : int or float
        Number of random samples in grid
    seed : float, optional, default=None
        Seeding point to replicate random grid
    options: dict, optional, default=None
        Grid options:
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    """

    def __init__(self, parameters_random, n_grid=None, seed=None, options=None, coords=None, coords_norm=None,
                 coords_gradient=None, coords_gradient_norm=None, coords_id=None, coords_gradient_id=None):
        """
        Constructor; Initializes RandomGrid instance; Generates grid or copies provided content
        """

        self.lhs_reservoir = None
        self.perc_mask = None
        self.coords_reservoir = None
        self.coords_norm_reservoir = None

        super(MCMC, self).__init__(parameters_random,
                                  n_grid=n_grid,
                                  seed=seed,
                                  options=options,
                                  coords=coords,
                                  coords_norm=coords_norm,
                                  coords_gradient=coords_gradient,
                                  coords_gradient_norm=coords_gradient_norm,
                                  coords_id=coords_id,
                                  coords_gradient_id=coords_gradient_id)


        self.coords_reservoir = np.zeros((self.n_grid, self.dim))
        self.coords_norm_reservoir = np.zeros((self.n_grid, self.dim))
        self.perc_mask = np.zeros((self.n_grid, self.dim)).astype(bool)



        # Generate random samples for each random input variable [n_grid x dim]
        self.coords_norm = np.zeros([self.n_grid, self.dim])

        # generate LHS grid in icdf space (seed of random grid (if necessary to reproduce random grid)
        self.lhs_reservoir = self.Metropolis_Hastings()

        # transform sample points from icdf to pdf space
        for i_p, p in enumerate(self.parameters_random):
            self.coords_norm_reservoir[:, i_p] = self.parameters_random[p].icdf(self.lhs_reservoir[:, i_p])
            self.perc_mask[:, i_p] = np.logical_and(
                self.parameters_random[p].pdf_limits_norm[0] < self.coords_norm_reservoir[:, i_p],
                self.coords_norm_reservoir[:, i_p] < self.parameters_random[p].pdf_limits_norm[1])

        # get points all satisfying perc constraints
        self.perc_mask = self.perc_mask.all(axis=1)
        self.coords_norm_reservoir = self.coords_norm_reservoir[self.perc_mask, :]

        self.coords_norm = self.coords_norm_reservoir[0:self.n_grid, :]

        # Denormalize grid to original parameter space
        self.coords = self.get_denormalized_coordinates(self.coords_norm)
        self.coords_reservoir = self.get_denormalized_coordinates(self.coords_norm_reservoir)

        # Generate unique IDs of grid points
        self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]

    def Metropolis_Hastings(self):

        def f(x):
            return 1
        def w(x):
            return 1
        def g(x):
            return 1

        n = max(2 * self.n_grid, 10000)
        # draw n samples from the proposal distribution
        samples = np.random.beta(.5, .5, size=[n, self.dim])

        # Metropolis-Hastings with 10,000 iterations.
        for i in range(n):
            u = np.random.rand(self.dim)
            # 'iterate' over a number of burn in Samples
            for j in range(10):
                x = samples[i, :]
                x_ = np.random.beta(.5, .5, size=self.dim)
                rho = np.zeros(self.dim)

                for k in range(self.dim):
                    rho[k] = np.min((g(x[k]) * f(x_[k]) * (w(x_) ** (-2))/(g(x_[k]) * f(x[k]) * (w(x) ** (-2)))))
                # draw a uniform sample from [0, 1]
                if (u.sum() < rho.sum()):
                    samples[i, :] = x_
                    u = rho
        samples = samples[len(samples)-n: len(samples)]
        return samples

class L1OPT(RandomGrid):
    """
    LHS grid object

    Parameters
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid: int
        Number of random samples to generate
    seed: float
        Seeding point to replicate random grids
    options: dict, optional, default=None
        Grid options:
        - 'corr'            : optimizes design points in their spearman correlation coefficients
        - 'maximin' or 'm'  : optimizes design points in their maximum minimal distance using the Phi-P criterion
        - 'ese'             : uses an enhanced evolutionary algorithm to optimize the Phi-P criterion
    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points

    Examples
    --------
    >>> import pygpc
    >>> grid = pygpc.LHS(parameters_random=parameters_random, n_grid=100, seed=1, options=options)

    Attributes
    ----------
    parameters_random : OrderedDict of RandomParameter instances
        OrderedDict containing the RandomParameter instances the grids are generated for
    n_grid : int or float
        Number of random samples in grid
    seed : float, optional, default=None
        Seeding point to replicate random grid
    options: dict, optional, default=None
        Grid options:

    coords : ndarray of float [n_grid_add x dim]
        Grid points to add (model space)
    coords_norm : ndarray of float [n_grid_add x dim]
        Grid points to add (normalized space)
    coords_gradient : ndarray of float [n_grid x dim x dim]
        Denormalized coordinates xi
    coords_gradient_norm : ndarray of float [n_grid x dim x dim]
        Normalized coordinates xi
    coords_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    coords_gradient_id : list of UUID objects (version 4) [n_grid]
        Unique IDs of grid points
    """

    def __init__(self, parameters_random, n_grid=None, seed=None, options=None, coords=None, coords_norm=None,
                 coords_gradient=None, coords_gradient_norm=None, coords_id=None, coords_gradient_id=None, gpc=None):
        """
        Constructor; Initializes Grid instance; Generates grid or copies provided content
        """

        self.lhs_reservoir = None
        self.perc_mask = None
        self.coords_reservoir = None
        self.coords_norm_reservoir = None

        super(L1OPT, self).__init__(parameters_random,
                                   n_grid=n_grid,
                                   seed=seed,
                                   options=options,
                                   coords=coords,
                                   coords_norm=coords_norm,
                                   coords_gradient=coords_gradient,
                                   coords_gradient_norm=coords_gradient_norm,
                                   coords_id=coords_id,
                                   coords_gradient_id=coords_gradient_id)


        if gpc is not None:

            if self.options is None:
                # self.factor = 10
                self.random_pool = Random(parameters_random, n_grid=10000, seed=None)
                self.coords_norm = self.random_pool.coords_norm[self.get_pool_samples(gpc)[1]]

            elif self.options is 'greedy':
                self.factor = 1000
                self.random_pool = Random(parameters_random, n_grid=self.factor, seed=None)
                self.coords_norm = self.random_pool.coords_norm[self.get_optimal_mu_greedy(gpc)]


            if (len(self.options) > 1 and (self.options[0] is 'ese_iter' or self.options[0] is 'ese_greedy')):
                self.split = self.options[1]
            #TODO: add option for n = 1
            if self.n_grid > 1:
                self.coords_reservoir = np.zeros((self.n_grid, self.dim))
                self.coords_norm_reservoir = np.zeros((self.n_grid, self.dim))
                self.perc_mask = np.zeros((self.n_grid, self.dim)).astype(bool)

                # Generate random samples for each random input variable [n_grid x dim]
                self.coords_norm = np.zeros([self.n_grid, self.dim])

                # generate LHS grid in icdf space (seed of random grid (if necessary to reproduce random grid)
                if self.options is 'ese_iter':
                    self.coords_reservoir = self.ese_mu_greedy(dim=self.dim, n=self.n_grid, gpc=gpc)
                if self.options is 'ese_greedy':
                    self.coords_reservoir = self.ese_mu(dim=self.dim, n=self.n_grid, gpc=gpc)
                # transform sample points from icdf to pdf space
                for i_p, p in enumerate(self.parameters_random):
                    self.coords_norm_reservoir[:, i_p] = self.parameters_random[p].icdf(
                        self.coords_reservoir[:, i_p])
                    self.perc_mask[:, i_p] = np.logical_and(
                        self.parameters_random[p].pdf_limits_norm[0] < self.coords_norm_reservoir[:, i_p],
                        self.coords_norm_reservoir[:, i_p] < self.parameters_random[p].pdf_limits_norm[1])

                # get points all satisfying perc constraints
                self.perc_mask = self.perc_mask.all(axis=1)
                self.coords_norm_reservoir = self.coords_norm_reservoir[self.perc_mask, :]

                self.coords_norm = self.coords_norm_reservoir[0:self.n_grid, :]

                # Denormalize grid to original parameter space
            self.coords = self.get_denormalized_coordinates(self.coords_norm)
            # self.coords_reservoir = self.get_denormalized_coordinates(self.coords_norm_reservoir)

            # Generate unique IDs of grid points
            self.coords_id = [uuid.uuid4() for _ in range(self.n_grid)]

            if self.options is 'iteration':
                self.factor = 1000
                self.coords, self.coords_norm, self.coords_id = self.get_optimal_mu_iteration(gpc, parameters_random)


    def get_optimal_mu_greedy(self, gpc):
        index_list = []
        psy_pool = gpc.create_gpc_matrix(b=gpc.basis.b, x=self.random_pool.coords_norm, gradient=False)
        psy_pool = psy_pool / np.abs(psy_pool).max(axis=0)
        m = self.n_grid
        m_p = int(np.shape(psy_pool)[0])

        # get random row of psy to start
        idx = np.random.randint(m_p)
        index_list.append(idx)
        psy_opt = np.zeros([1, np.shape(psy_pool)[1]])
        psy_opt[0, :] = psy_pool[idx, :]

        for i in range(1, m):
            coh_list = []
            idx_used = []

            for j in [k for k in range(m_p) if k not in index_list]:  # range(0, m_p):

                new_row = psy_pool[j, :]
                psy_temp = np.vstack((psy_opt[:i, :], new_row))

                coh_list.append(mutual_coherence(psy_temp))
                idx_used.append(j)
                # calculate the minimal distance of both criteria from zero and get the index of its row in the pool matrix
                if len(coh_list) > 1:
                    idx_best = np.argmin(coh_list)
                    index_list.append(idx_used[idx_best])
                else:
                    index_list.append(j)
                    idx_best = j

                # add row with best minimal coherence and cross correlation properties to the matrix
                psy_opt = np.vstack((psy_opt[:i, :], psy_pool[idx_best, :]))

        return index_list

    def get_pool_samples(self, gpc):

        def t_averaged_mutual_coherence(array, t=0.2):
            array = np.abs(array)
            mask = array > t

            return np.sum(array[mask]) / np.sum(mask)

        def average_cross_correlation_gram(array):
            n = array.shape[1]
            k = n * (n - 1)
            return (1 / k) * (np.linalg.norm(np.identity(n) - array) ** 2)

        index_list = []

        # create psy pool
        psy_pool = gpc.create_gpc_matrix(b=gpc.basis.b, x=self.random_pool.coords_norm, gradient=False)
        # weight psy pool with the weighting matrix
        normalization_factor = 1 / np.abs(np.linalg.norm(psy_pool))
        psy_pool = psy_pool / np.abs(psy_pool).max(axis=0)

        # m is number of needed samples, m_p number of rows in pool matrix
        m = self.n_grid
        m_p = int(np.shape(psy_pool)[0])

        # get random row of psy to start
        idx = np.random.randint(m_p)
        index_list.append(idx)
        psy_opt = np.zeros([1, np.shape(psy_pool)[1]])
        psy_opt[0, :] = psy_pool[idx, :]

        for i in range(1, m):
            coh1_list = []
            coh_list = []
            corr_list = []
            gram_psy = None
            idx_used = []

            for j in [k for k in range(m_p) if k not in index_list]:  # range(0, m_p):

                new_row = psy_pool[j, :]
                psy_temp = np.vstack((psy_opt[:i, :], new_row))

                # get gram matrix of column normalized psy_temp (update if present)
                if gram_psy is None:
                    gram_psy = np.matmul(psy_temp.T, psy_temp)

                else:
                    gram_psy = gram_psy \
                               + np.matmul(new_row[:, np.newaxis], new_row[np.newaxis, :]) \
                               - np.matmul(prev_row[:, np.newaxis], prev_row[np.newaxis, :])

                prev_row = new_row

                # get a list of the two criteria
                coh_list.append(t_averaged_mutual_coherence(gram_psy))

                corr_list.append(average_cross_correlation_gram(gram_psy))
                # coh1_list.append(pygpc.mutual_coherence(psy_temp))
                idx_used.append(j)
            # calculate the minimal distance of both criteria from zero and get the index of its row in the pool matrix
            if len(coh1_list) > 1:
                coh_component = ((np.asarray(coh_list) - min(coh_list)) / (max(coh_list) - min(coh_list))) ** 2
                corr_component = ((np.asarray(corr_list) - min(corr_list)) / (max(corr_list) - min(corr_list))) ** 2
                dist_list = coh_component + (1 * corr_component)
                idx_best = np.argmin(dist_list)
                index_list.append(idx_used[idx_best])
            else:
                index_list.append(j)
                idx_best = j

            # add row with best minimal coherence and cross correlation properties to the matrix
            psy_opt = np.vstack((psy_opt[:i, :], psy_pool[idx_best, :]))

        return psy_opt, index_list

    def get_optimal_mu_iteration(self, gpc, parameters_random):

        mu = np.zeros(self.factor)
        for i in self.factor:
            sampling_pool = Random(parameters_random, n_grid=self.n_grid, seed=None)
            psy_pool = gpc.create_gpc_matrix(b=gpc.basis.b, x=sampling_pool.coords_norm, gradient=False)
            normalized_pool = psy_pool / np.abs(psy_pool).max(axis=0)
            mu[i] = mutual_coherence(normalized_pool)
            if np.argmin(mu) is i:
                best_pool = sampling_pool
        return best_pool.coords, best_pool.coords_norm, best_pool.coords_id



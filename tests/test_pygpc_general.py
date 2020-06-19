import numpy as np
import unittest
import shutil
import pygpc
import time
import h5py
import sys
import os
from collections import OrderedDict

# disable numpy warnings
import warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

# test options
folder = 'tmp'                  # output folder
plot = False                    # plot and save output
matlab = False                  # test Matlab functionality
save_session_format = ".pkl"    # file format of saved gpc session ".hdf5" (slow) or ".pkl" (fast)

# temporary folder
try:
    os.mkdir(folder)

except FileExistsError:
    pass


class TestPygpcMethods(unittest.TestCase):

    # setup method called before every test-case
    def setUp(self):
        pass

    def run(self, result=None):
        self._result = result
        self._num_expectations = 0
        super(TestPygpcMethods, self).run(result)

    def _fail(self, failure):
        try:
            raise failure
        except failure.__class__:
            self._result.addFailure(self, sys.exc_info())

    def expect_isclose(self, a, b, msg='', atol=None, rtol=None):
        if atol is None:
            atol = 1.e-8
        if rtol is None:
            rtol = 1.e-5

        if not np.isclose(a, b, atol=atol, rtol=rtol).all():
            msg = '({}) Expected {} to be close {}. '.format(self._num_expectations, a, b) + msg
            self._fail(self.failureException(msg))
        self._num_expectations += 1

    def expect_equal(self, a, b, msg=''):
        if a != b:
            msg = '({}) Expected {} to equal {}. '.format(self._num_expectations, a, b) + msg
            self._fail(self.failureException(msg))
        self._num_expectations += 1

    def expect_true(self, a, msg=''):
        if not a:
            self._fail(self.failureException(msg))
        self._num_expectations += 1

    def test_0_Static_gpc_quad(self):
        """
        Algorithm: Static
        Method: Quadrature
        Solver: NumInt
        Grid: TensorGrid
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_0_Static_gpc_quad'
        print(test_name)

        # define model
        model = pygpc.testfunctions.Peaks()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[1.2, 2])
        parameters["x2"] = 1.25
        parameters["x3"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 0.6])
        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "quad"
        options["solver"] = "NumInt"
        options["settings"] = None
        options["order"] = [9, 9]
        options["order_max"] = 9
        options["interaction_order"] = 2
        options["error_type"] = "nrmsd"
        options["n_samples_validation"] = 1e3
        options["n_cpu"] = 0
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["backend"] = "omp"
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # generate grid
        grid = pygpc.TensorGrid(parameters_random=problem.parameters_random,
                                options={"grid_type": ["jacobi", "jacobi"], "n_dim": [9, 9]})

        # define algorithm
        algorithm = pygpc.Static(problem=problem, options=options, grid=grid)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC algorithm
        session, coeffs, results = session.run()

        # read session
        session = pygpc.read_session(fname=session.fn_session, folder=session.fn_session_folder)

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="standard",
                                     n_samples=1e3)

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=[0],
                                    fn_out=options["fn_results"],
                                    folder="gpc_vs_original_plot",
                                    n_cpu=options["n_cpu"])

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      n_cpu=session.n_cpu,
                                      output_idx=[0],
                                      fn_out=options["fn_results"],
                                      folder="gpc_vs_original_mc",
                                      plot=plot)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))
        print("> Checking file consistency...")

        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_1_Static_gpc(self):
        """
        Algorithm: Static
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_1_Static_gpc'
        print(test_name)

        # define model
        model = pygpc.testfunctions.Peaks()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[1.2, 2])
        parameters["x2"] = 1.25
        parameters["x3"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 0.6])
        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "Moore-Penrose"
        options["settings"] = None
        options["order"] = [9, 9]
        options["order_max"] = 9
        options["interaction_order"] = 2
        options["matrix_ratio"] = 20
        options["error_type"] = "nrmsd"
        options["n_samples_validation"] = 1e3
        options["n_cpu"] = 0
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["gradient_enhanced"] = True
        options["gradient_calculation"] = "FD_1st2nd"
        options["gradient_calculation_options"] = {"dx": 0.05, "distance_weight": -2}
        options["backend"] = "omp"
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # generate grid
        n_coeffs = pygpc.get_num_coeffs_sparse(order_dim_max=options["order"],
                                               order_glob_max=options["order_max"],
                                               order_inter_max=options["interaction_order"],
                                               dim=problem.dim)

        grid = pygpc.Random(parameters_random=problem.parameters_random,
                            n_grid=options["matrix_ratio"] * n_coeffs,
                            seed=1)

        # define algorithm
        algorithm = pygpc.Static(problem=problem, options=options, grid=grid)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC algorithm
        session, coeffs, results = session.run()

        # read session
        session = pygpc.read_session(fname=session.fn_session, folder=session.fn_session_folder)

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="standard",
                                     n_samples=1e3)

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=0,
                                    fn_out=options["fn_results"],
                                    folder="gpc_vs_original_plot",
                                    n_cpu=options["n_cpu"])

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      output_idx=0,
                                      n_cpu=session.n_cpu,
                                      fn_out=options["fn_results"],
                                      folder="gpc_vs_original_mc",
                                      plot=plot)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_2_MEStatic_gpc(self):
        """
        Algorithm: MEStatic
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_2_MEStatic_gpc'
        print(test_name)

        # define model
        model = pygpc.testfunctions.SurfaceCoverageSpecies()

        # define problem
        parameters = OrderedDict()
        parameters["rho_0"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 1])
        parameters["beta"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 20])
        parameters["alpha"] = 1.
        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "Moore-Penrose"
        options["settings"] = None
        options["order"] = [9, 9]
        options["order_max"] = 9
        options["interaction_order"] = 2
        options["matrix_ratio"] = 2
        options["n_cpu"] = 0
        options["gradient_enhanced"] = True
        options["gradient_calculation"] = "FD_2nd"
        options["gradient_calculation_options"] = {"dx": 0.05, "distance_weight": -2}
        options["error_type"] = "loocv"
        options["qoi"] = "all"
        options["n_grid_gradient"] = 5
        options["classifier"] = "learning"
        options["classifier_options"] = {"clusterer": "KMeans",
                                         "n_clusters": 2,
                                         "classifier": "MLPClassifier",
                                         "classifier_solver": "lbfgs"}
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # generate grid
        grid = pygpc.Random(parameters_random=problem.parameters_random,
                            n_grid=1000,  # options["matrix_ratio"] * n_coeffs
                            seed=1)

        # define algorithm
        algorithm = pygpc.MEStatic(problem=problem, options=options, grid=grid)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC algorithm
        session, coeffs, results = session.run()

        # read session
        session = pygpc.read_session(fname=session.fn_session, folder=session.fn_session_folder)

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=0,
                                    fn_out=options["fn_results"],
                                    folder="gpc_vs_original_plot",
                                    n_cpu=options["n_cpu"])

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="sampling",
                                     n_samples=1e3)

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      output_idx=0,
                                      n_cpu=options["n_cpu"],
                                      smooth_pdf=False,
                                      fn_out=options["fn_results"],
                                      folder="gpc_vs_original_mc",
                                      plot=plot)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_3_StaticProjection_gpc(self):
        """
        Algorithm: StaticProjection
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_3_StaticProjection_gpc'
        print(test_name)

        # define model
        model = pygpc.testfunctions.GenzOscillatory()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1., 1.], pdf_limits=[0., 1.])
        parameters["x2"] = pygpc.Beta(pdf_shape=[1., 1.], pdf_limits=[0., 1.])
        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "Moore-Penrose"
        options["settings"] = None
        options["order"] = [10]
        options["order_max"] = 10
        options["interaction_order"] = 1
        options["n_cpu"] = 0
        options["error_type"] = "nrmsd"
        options["n_samples_validation"] = 1e3
        options["error_norm"] = "relative"
        options["matrix_ratio"] = 2
        options["qoi"] = 0
        options["n_grid_gradient"] = 10
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["gradient_enhanced"] = True
        options["gradient_calculation"] = "FD_fwd"
        options["gradient_calculation_options"] = {"dx": 0.001, "distance_weight": -2}
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # define algorithm
        algorithm = pygpc.StaticProjection(problem=problem, options=options)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC algorithm
        session, coeffs, results = session.run()

        # read session
        session = pygpc.read_session(fname=session.fn_session, folder=session.fn_session_folder)

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=0,
                                    fn_out=options["fn_results"],
                                    folder="gpc_vs_original_plot",
                                    n_cpu=options["n_cpu"])

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="sampling",
                                     n_samples=1e3)

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      output_idx=0,
                                      n_cpu=options["n_cpu"],
                                      smooth_pdf=False,
                                      fn_out=options["fn_results"],
                                      folder="gpc_vs_original_mc",
                                      plot=plot)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_4_MEStaticProjection_gpc(self):
        """
        Algorithm: MEStaticProjection
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_4_MEStaticProjection_gpc'
        print(test_name)

        # define model
        model = pygpc.testfunctions.DiscontinuousRidgeManufactureDecay()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 1])
        parameters["x2"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 1])
        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "Moore-Penrose"
        options["settings"] = None
        options["order"] = [3, 3]
        options["order_max"] = 3
        options["interaction_order"] = 2
        options["matrix_ratio"] = 2
        options["n_cpu"] = 0
        options["gradient_enhanced"] = True
        options["gradient_calculation"] = "FD_fwd"
        options["gradient_calculation_options"] = {"dx": 0.001, "distance_weight": -2}
        options["n_grid_gradient"] = 5
        options["error_type"] = "nrmsd"
        options["n_samples_validation"] = 1e3
        options["qoi"] = "all"
        options["classifier"] = "learning"
        options["classifier_options"] = {"clusterer": "KMeans",
                                         "n_clusters": 2,
                                         "classifier": "MLPClassifier",
                                         "classifier_solver": "lbfgs"}
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # define algorithm
        algorithm = pygpc.MEStaticProjection(problem=problem, options=options)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC session
        session, coeffs, results = session.run()

        # read session
        session = pygpc.read_session(fname=session.fn_session, folder=session.fn_session_folder)

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=0,
                                    fn_out=options["fn_results"],
                                    folder="gpc_vs_original_plot",
                                    n_cpu=options["n_cpu"])

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="sampling",
                                     n_samples=1e3)

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(5e4),
                                      output_idx=0,
                                      n_cpu=options["n_cpu"],
                                      smooth_pdf=True,
                                      fn_out=options["fn_results"],
                                      folder="gpc_vs_original_mc",
                                      plot=plot)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_5_RegAdaptive_gpc(self):
        """
        Algorithm: RegAdaptive
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_5_RegAdaptive_gpc'
        print(test_name)

        # Model
        model = pygpc.testfunctions.Ishigami()

        # Problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[-np.pi, np.pi])
        parameters["x2"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[-np.pi, np.pi])
        parameters["x3"] = 0.
        parameters["a"] = 7.
        parameters["b"] = 0.1

        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["order_start"] = 5
        options["order_end"] = 20
        options["solver"] = "LarsLasso"
        options["interaction_order"] = 2
        options["order_max_norm"] = 0.7
        options["n_cpu"] = 0
        options["adaptive_sampling"] = True
        options["gradient_enhanced"] = True
        options["gradient_calculation"] = "FD_fwd"
        options["gradient_calculation_options"] = {"dx": 0.001, "distance_weight": -2}
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["eps"] = 0.0075
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # define algorithm
        algorithm = pygpc.RegAdaptive(problem=problem, options=options)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC session
        session, coeffs, results = session.run()

        # read session
        session = pygpc.read_session(fname=session.fn_session, folder=session.fn_session_folder)

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=0,
                                    fn_out=options["fn_results"],
                                    folder="gpc_vs_original_plot",
                                    n_cpu=options["n_cpu"])

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="sampling",
                                     n_samples=1e3)

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      output_idx=0,
                                      n_cpu=options["n_cpu"],
                                      smooth_pdf=True,
                                      fn_out=options["fn_results"],
                                      folder="gpc_vs_original_mc",
                                      plot=plot)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_6_RegAdaptiveProjection_gpc(self):
        """
        Algorithm: RegAdaptiveProjection
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_6_RegAdaptiveProjection_gpc'
        print(test_name)

        # define model
        model = pygpc.testfunctions.GenzOscillatory()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1., 1.], pdf_limits=[0., 1.])
        parameters["x2"] = pygpc.Beta(pdf_shape=[1., 1.], pdf_limits=[0., 1.])
        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["order_start"] = 2
        options["order_end"] = 15
        options["interaction_order"] = 2
        options["solver"] = "Moore-Penrose"
        options["settings"] = None
        options["seed"] = 1
        options["matrix_ratio"] = 2
        options["n_cpu"] = 0
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["adaptive_sampling"] = False
        options["gradient_enhanced"] = True
        options["gradient_calculation"] = "FD_1st"
        options["gradient_calculation_options"] = {"dx": 0.5, "distance_weight": -2}
        options["n_grid_gradient"] = 5
        options["qoi"] = 0
        options["error_type"] = "loocv"
        options["eps"] = 1e-3
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # define algorithm
        algorithm = pygpc.RegAdaptiveProjection(problem=problem, options=options)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC session
        session, coeffs, results = session.run()

        # read session
        session = pygpc.read_session(fname=session.fn_session, folder=session.fn_session_folder)

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=0,
                                    fn_out=options["fn_results"],
                                    folder="gpc_vs_original_plot",
                                    n_cpu=options["n_cpu"])

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="sampling",
                                     n_samples=1e3)

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      output_idx=0,
                                      n_cpu=options["n_cpu"],
                                      smooth_pdf=False,
                                      fn_out=options["fn_results"],
                                      folder="gpc_vs_original_mc",
                                      plot=plot)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_7_MERegAdaptiveProjection_gpc(self):
        """
        Algorithm: MERegAdaptiveProjection
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_7_MERegAdaptiveProjection_gpc'
        print(test_name)

        # define model
        model = pygpc.testfunctions.DiscontinuousRidgeManufactureDecay()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 1])
        parameters["x2"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 1])
        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "LarsLasso"
        options["settings"] = None
        options["order_start"] = 3
        options["order_end"] = 15
        options["interaction_order"] = 2
        options["matrix_ratio"] = 2
        options["n_cpu"] = 0
        options["projection"] = True
        options["adaptive_sampling"] = True
        options["gradient_enhanced"] = True
        options["gradient_calculation"] = "FD_fwd"
        options["gradient_calculation_options"] = {"dx": 0.001, "distance_weight": -2}
        options["error_type"] = "nrmsd"
        options["error_norm"] = "absolute"
        options["n_samples_validations"] = "absolute"
        options["qoi"] = 0
        options["classifier"] = "learning"
        options["classifier_options"] = {"clusterer": "KMeans",
                                         "n_clusters": 2,
                                         "classifier": "MLPClassifier",
                                         "classifier_solver": "lbfgs"}
        options["n_samples_discontinuity"] = 12
        options["eps"] = 0.75
        options["n_grid_init"] = 20
        options["backend"] = "omp"
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # define algorithm
        algorithm = pygpc.MERegAdaptiveProjection(problem=problem, options=options)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC session
        session, coeffs, results = session.run()

        # read session
        session = pygpc.read_session(fname=session.fn_session, folder=session.fn_session_folder)

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      output_idx=[0],
                                      n_cpu=options["n_cpu"],
                                      smooth_pdf=True,
                                      fn_out=options["fn_results"],
                                      folder="gpc_vs_original_mc",
                                      plot=plot)

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=[0, 1],
                                    fn_out=options["fn_results"],
                                    folder="gpc_vs_original_plot",
                                    n_cpu=options["n_cpu"])

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="sampling",
                                     n_samples=1e4)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_8_testfunctions(self):
        """
        Testing testfunctions (multi-threading and inherited parallelization)
        """
        test_name = 'pygpc_test_8_testfunctions'
        print(test_name)

        tests = []
        tests.append(pygpc.Ackley())
        tests.append(pygpc.BukinFunctionNumber6())
        tests.append(pygpc.CrossinTrayFunction())
        tests.append(pygpc.BohachevskyFunction1())
        tests.append(pygpc.PermFunction())
        tests.append(pygpc.SixHumpCamelFunction())
        tests.append(pygpc.RotatedHyperEllipsoid())
        tests.append(pygpc.SumOfDifferentPowersFunction())
        tests.append(pygpc.ZakharovFunction())
        tests.append(pygpc.DropWaveFunction())
        tests.append(pygpc.DixonPriceFunction())
        tests.append(pygpc.RosenbrockFunction())
        tests.append(pygpc.MichalewiczFunction())
        tests.append(pygpc.DeJongFunctionFive())
        tests.append(pygpc.MatyasFunction())
        tests.append(pygpc.GramacyLeeFunction())
        tests.append(pygpc.SchafferFunction4())
        tests.append(pygpc.SphereFunction())
        tests.append(pygpc.McCormickFunction())
        tests.append(pygpc.BoothFunction())
        tests.append(pygpc.Peaks())
        tests.append(pygpc.Franke())
        tests.append(pygpc.Lim2002())
        tests.append(pygpc.Ishigami())
        tests.append(pygpc.ManufactureDecay())
        tests.append(pygpc.GenzContinuous())
        tests.append(pygpc.GenzCornerPeak())
        tests.append(pygpc.GenzOscillatory())
        tests.append(pygpc.GenzProductPeak())
        tests.append(pygpc.Ridge())
        tests.append(pygpc.OakleyOhagan2004())
        tests.append(pygpc.Welch1992())
        tests.append(pygpc.HyperbolicTangent())
        tests.append(pygpc.MovingParticleFrictionForce())
        tests.append(pygpc.SurfaceCoverageSpecies())

        for n_cpu in [4, 0]:
            if n_cpu != 0:
                print("Running testfunctions using multi-threading with {} cores...".format(n_cpu))
            else:
                print("Running testfunctions using inherited function parallelization...")

            com = pygpc.Computation(n_cpu=n_cpu)

            for t in tests:
                grid = pygpc.Random(parameters_random=t.problem.parameters_random,
                                    n_grid=10,
                                    seed=1)

                res = com.run(model=t.problem.model,
                              problem=t.problem,
                              coords=grid.coords,
                              coords_norm=grid.coords_norm,
                              i_iter=None,
                              i_subiter=None,
                              fn_results=None,
                              print_func_time=False)

            com.close()

            print("done!\n")

    def test_9_RandomParameters(self):
        """
        Testing RandomParameters
        """
        global folder, plot
        test_name = 'pygpc_test_9_RandomParameters'
        print(test_name)

        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 1])
        parameters["x2"] = pygpc.Beta(pdf_shape=[5, 5], pdf_limits=[0, 1])
        parameters["x3"] = pygpc.Beta(pdf_shape=[5, 2], pdf_limits=[0, 1])
        parameters["x4"] = pygpc.Beta(pdf_shape=[2, 5], pdf_limits=[0, 1])
        parameters["x5"] = pygpc.Beta(pdf_shape=[0.75, 0.75], pdf_limits=[0, 1])
        parameters["x6"] = pygpc.Norm(pdf_shape=[5, 1])

        if plot:
            import matplotlib.pyplot as plt
            fig = plt.figure()
            ax = parameters["x1"].plot_pdf()
            ax = parameters["x2"].plot_pdf()
            ax = parameters["x3"].plot_pdf()
            ax = parameters["x4"].plot_pdf()
            ax = parameters["x5"].plot_pdf()
            ax = parameters["x6"].plot_pdf()
            ax.legend(["x1", "x2", "x3", "x4", "x5", "x6"])
            ax.savefig(os.path.join(folder, test_name) + ".png")

            print("done!\n")

    def test_10_Grids(self):
        """
        Testing Grids [Random, LHS]
        """
        global folder, plot
        test_name = 'pygpc_test_10_Grids'
        print(test_name)

        test = pygpc.Peaks()

        grids = []
        fn_out = []
        grids.append(pygpc.Random(parameters_random=test.problem.parameters_random,
                                  n_grid=100,
                                  seed=1))
        fn_out.append(test_name + "_Random")
        grids.append(pygpc.TensorGrid(parameters_random=test.problem.parameters_random,
                                      options={"grid_type": ["hermite", "jacobi"], "n_dim": [5, 10]}))
        fn_out.append(test_name + "_TensorGrid_1")
        grids.append(pygpc.TensorGrid(parameters_random=test.problem.parameters_random,
                                      options={"grid_type": ["patterson", "fejer2"], "n_dim": [3, 10]}))
        fn_out.append(test_name + "_TensorGrid_2")
        grids.append(pygpc.SparseGrid(parameters_random=test.problem.parameters_random,
                                      options={"grid_type": ["jacobi", "jacobi"],
                                               "level": [3, 3],
                                               "level_max": 3,
                                               "interaction_order": 2,
                                               "order_sequence_type": "exp"}))
        fn_out.append(test_name + "_SparseGrid")

        if plot:
            for i, g in enumerate(grids):
                pygpc.plot_2d_grid(coords=g.coords_norm, weights=g.weights, fn_plot=os.path.join(folder, fn_out[i]))

        print("done!\n")

    def test_11_Matlab_gpc(self):
        """
        Algorithm: RegAdaptive
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, matlab, save_session_format
        test_name = 'pygpc_test_11_Matlab_gpc'
        print(test_name)

        if matlab:
            import matlab.engine
            from templates.MyModel_matlab import  MyModel_matlab
            # define model
            model = MyModel_matlab(fun_path=os.path.join(pygpc.__path__[0], "testfunctions"))

            # define problem (the parameter names have to be the same as in the model)
            parameters = OrderedDict()
            parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[-np.pi, np.pi])
            parameters["x2"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[-np.pi, np.pi])
            parameters["x3"] = 0.
            parameters["a"] = 7.
            parameters["b"] = 0.1

            problem = pygpc.Problem(model, parameters)

            # gPC options
            options = dict()
            options["order_start"] = 5
            options["order_end"] = 20
            options["solver"] = "LarsLasso"
            options["interaction_order"] = 2
            options["order_max_norm"] = 0.7
            options["n_cpu"] = 0
            options["adaptive_sampling"] = True
            options["gradient_enhanced"] = True
            options["gradient_calculation"] = "FD_fwd"
            options["gradient_calculation_options"] = {"dx": 0.001, "distance_weight": -2}
            options["fn_results"] = os.path.join(folder, test_name)
            options["save_session_format"] = save_session_format
            options["eps"] = 0.0075
            options["matlab_model"] = True
            options["grid"] = pygpc.Random
            options["grid_options"] = None

            # define algorithm
            algorithm = pygpc.RegAdaptive(problem=problem, options=options)

            # Initialize gPC Session
            session = pygpc.Session(algorithm=algorithm)

            # run gPC session
            session, coeffs, results = session.run()

            if plot:
                # Validate gPC vs original model function (2D-surface)
                pygpc.validate_gpc_plot(session=session,
                                        coeffs=coeffs,
                                        random_vars=list(problem.parameters_random.keys()),
                                        n_grid=[51, 51],
                                        output_idx=0,
                                        fn_out=options["fn_results"] + "_val",
                                        n_cpu=options["n_cpu"])

            # Post-process gPC
            pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                         output_idx=None,
                                         calc_sobol=True,
                                         calc_global_sens=True,
                                         calc_pdf=True,
                                         algorithm="sampling",
                                         n_samples=1e3)

            # Validate gPC vs original model function (Monte Carlo)
            nrmsd = pygpc.validate_gpc_mc(session=session,
                                          coeffs=coeffs,
                                          n_samples=int(1e4),
                                          output_idx=0,
                                          n_cpu=options["n_cpu"],
                                          smooth_pdf=True,
                                          fn_out=options["fn_results"] + "_pdf",
                                          plot=plot)

            print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
            # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

            print("> Checking file consistency...")
            files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
            self.expect_true(files_consistent, error_msg)

            print("done!\n")

        else:
            print("Skipping Matlab test...")

    def test_12_random_vars_postprocessing(self):
        """
        Algorithm: Static
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_12_random_vars_postprocessing_sobol'
        print(test_name)

        # define model
        model = pygpc.testfunctions.Peaks()

        # define problem

        parameters = OrderedDict()
        # parameters["x1"] = pygpc.Beta(pdf_shape=[1., 1.], pdf_limits=[1.25, 1.72])
        parameters["x1"] = pygpc.Gamma(pdf_shape=[3., 10., 1.25], p_perc=0.98)
        parameters["x2"] = pygpc.Norm(pdf_shape=[1, 1], p_perc=0.98)
        parameters["x3"] = pygpc.Beta(pdf_shape=[1., 1.], pdf_limits=[0.6, 1.4])
        # parameters["x3"] = pygpc.Norm(pdf_shape=[1., 0.25], p_perc=0.95)
        # parameters["x2"] = 1.

        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "Moore-Penrose"
        options["settings"] = None
        options["order"] = [4, 4, 4]
        options["order_max"] = 4
        options["interaction_order"] = 2
        options["matrix_ratio"] = 2
        options["error_type"] = "loocv"
        options["n_samples_validation"] = 1e3
        options["n_cpu"] = 0
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["gradient_enhanced"] = True
        options["backend"] = "omp"

        # generate grid
        n_coeffs = pygpc.get_num_coeffs_sparse(order_dim_max=options["order"],
                                               order_glob_max=options["order_max"],
                                               order_inter_max=options["interaction_order"],
                                               dim=problem.dim)

        grid = pygpc.Random(parameters_random=problem.parameters_random,
                            n_grid=options["matrix_ratio"] * n_coeffs,
                            seed=1)

        # define algorithm
        algorithm = pygpc.Static(problem=problem, options=options, grid=grid)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC algorithm
        session, coeffs, results = session.run()

        # Determine Sobol indices using standard approach (gPC coefficients)
        sobol_standard, sobol_idx_standard, sobol_idx_bool_standard = session.gpc[0].get_sobol_indices(coeffs=coeffs,
                                                                                                       algorithm="standard")

        sobol_sampling, sobol_idx_sampling, sobol_idx_bool_sampling = session.gpc[0].get_sobol_indices(coeffs=coeffs,
                                                                                                       algorithm="sampling",
                                                                                                       n_samples=3e4)

        # grid = pygpc.Random(parameters_random=session.parameters_random,
        #                     n_grid=int(5e5),
        #                     seed=None)
        #
        # com = pygpc.Computation(n_cpu=0, matlab_model=session.matlab_model)
        # y_orig = com.run(model=session.model,
        #                  problem=session.problem,
        #                  coords=grid.coords,
        #                  coords_norm=grid.coords_norm,
        #                  i_iter=None,
        #                  i_subiter=None,
        #                  fn_results=None,
        #                  print_func_time=False)
        # y_gpc = session.gpc[0].get_approximation(coeffs=coeffs, x=grid.coords_norm)
        #
        # mean_gpc_coeffs = session.gpc[0].get_mean(coeffs=coeffs)
        # mean_gpc_sampling = session.gpc[0].get_mean(samples=y_gpc)
        # mean_orig = np.mean(y_orig, axis=0)
        #
        # std_gpc_coeffs = session.gpc[0].get_std(coeffs=coeffs)
        # std_gpc_sampling = session.gpc[0].get_std(samples=y_gpc)
        # std_orig = np.std(y_orig, axis=0)

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      output_idx=0,
                                      fn_out=options["fn_results"] + "_pdf",
                                      plot=plot,
                                      n_cpu=session.n_cpu)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        for i in range(sobol_standard.shape[0]):
            self.expect_true(np.max(np.abs(sobol_standard[i, :]-sobol_sampling[i, :])) < 0.1,
                             msg="Sobol index: {}".format(str(sobol_idx_sampling[3])))

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=["x2", "x3"],
                                    n_grid=[51, 51],
                                    output_idx=0,
                                    fn_out=options["fn_results"] + "_val",
                                    n_cpu=options["n_cpu"])

        print("done!\n")

    def test_13_clustering_3_domains(self):
        """
        Algorithm: MERegAdaptiveprojection
        Method: Regression
        Solver: Moore-Penrose
        Grid: Random
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_13_clustering_3_domains'
        print(test_name)

        # define model
        model = pygpc.testfunctions.Cluster3Simple()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 1])
        parameters["x2"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 1])
        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "LarsLasso" #"Moore-Penrose"
        options["settings"] = None
        options["order_start"] = 1
        options["order_end"] = 15
        options["interaction_order"] = 2
        options["matrix_ratio"] = 1
        options["projection"] = False
        options["n_cpu"] = 0
        options["gradient_enhanced"] = False
        options["gradient_calculation"] = "FD_fwd"
        options["error_type"] = "loocv"
        options["error_norm"] = "absolute" # "relative"
        options["qoi"] = 0 # "all"
        options["classifier"] = "learning"
        options["classifier_options"] = {"clusterer": "KMeans",
                                         "n_clusters": 3,
                                         "classifier": "MLPClassifier",
                                         "classifier_solver": "lbfgs"}
        options["n_samples_discontinuity"] = 50
        options["adaptive_sampling"] = False
        options["eps"] = 0.01
        options["n_grid_init"] = 50
        options["backend"] = "omp"
        options["fn_results"] = os.path.join(folder, test_name)
        options["save_session_format"] = save_session_format
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        # define algorithm
        algorithm = pygpc.MERegAdaptiveProjection(problem=problem, options=options)

        # Initialize gPC Session
        session = pygpc.Session(algorithm=algorithm)

        # run gPC session
        session, coeffs, results = session.run()

        if plot:
            # Validate gPC vs original model function (2D-surface)
            pygpc.validate_gpc_plot(session=session,
                                    coeffs=coeffs,
                                    random_vars=list(problem.parameters_random.keys()),
                                    n_grid=[51, 51],
                                    output_idx=[0],
                                    fn_out=options["fn_results"] + "_val",
                                    n_cpu=options["n_cpu"])

        # Validate gPC vs original model function (Monte Carlo)
        nrmsd = pygpc.validate_gpc_mc(session=session,
                                      coeffs=coeffs,
                                      n_samples=int(1e4),
                                      output_idx=0,
                                      n_cpu=options["n_cpu"],
                                      smooth_pdf=True,
                                      fn_out=options["fn_results"] + "_pdf",
                                      plot=plot)

        # Post-process gPC
        pygpc.get_sensitivities_hdf5(fn_gpc=options["fn_results"],
                                     output_idx=None,
                                     calc_sobol=True,
                                     calc_global_sens=True,
                                     calc_pdf=True,
                                     algorithm="sampling",
                                     n_samples=1e4)

        print("> Maximum NRMSD (gpc vs original): {:.2}%".format(np.max(nrmsd)))
        # self.expect_true(np.max(nrmsd) < 0.1, 'gPC test failed with NRMSD error = {:1.2f}%'.format(np.max(nrmsd)*100))

        print("> Checking file consistency...")
        files_consistent, error_msg = pygpc.check_file_consistency(options["fn_results"] + ".hdf5")
        self.expect_true(files_consistent, error_msg)

        print("done!\n")

    def test_14_backends(self):
        """
        Test the different backends ["python", "cpu", "omp", "cuda"]
        """

        global folder, gpu
        test_name = 'pygpc_test_14_backends'
        print(test_name)

        backends = ["python", "cpu", "omp", "cuda"]

        # define model
        model = pygpc.testfunctions.Peaks()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[1.2, 2])
        parameters["x2"] = 1.25
        parameters["x3"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 0.6])
        problem = pygpc.Problem(model, parameters)

        # define test grid
        grid = pygpc.Random(parameters_random=problem.parameters_random,
                            n_grid=100,
                            seed=1)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "Moore-Penrose"
        options["settings"] = None
        options["order"] = [9, 9]
        options["order_max"] = 9
        options["interaction_order"] = 2
        options["matrix_ratio"] = 2
        options["error_type"] = "nrmsd"
        options["n_samples_validation"] = 1e3
        options["n_cpu"] = 0
        options["fn_results"] = None
        options["gradient_enhanced"] = True
        options["gradient_calculation"] = "FD_fwd"
        options["gradient_calculation_options"] = {"dx": 0.5, "distance_weight": -2}
        options["grid"] = pygpc.Random
        options["grid_options"] = None

        gpc_matrix = dict()
        gpc_matrix_gradient = dict()
        pce_matrix = dict()

        print("Constructing gPC matrices with different backends:")
        for b in backends:
            try:
                options["backend"] = b

                # setup gPC
                gpc = pygpc.Reg(problem=problem,
                                order=[8, 8],
                                order_max=8,
                                order_max_norm=0.8,
                                interaction_order=2,
                                interaction_order_current=2,
                                options=options,
                                validation=None)

                gpc.grid = grid

                # init gPC matrices
                start = time.time()
                gpc.init_gpc_matrix(gradient_idx=np.arange(grid.coords.shape[0]))
                stop = time.time()

                print(b, "create gpc matrix: ", stop-start)

                # perform polynomial chaos expansion
                coeffs = np.ones([len(gpc.basis.b), 2])
                start = time.time()
                pce = gpc.get_approximation(coeffs, gpc.grid.coords_norm)
                stop = time.time()

                print(b, "polynomial chaos expansion: ", stop-start)

                gpc_matrix[b] = gpc.gpc_matrix
                gpc_matrix_gradient[b] = gpc.gpc_matrix_gradient
                pce_matrix[b] = pce

            except NotImplementedError:
                backends.remove(b)
                warnings.warn("Skipping to test backend: {} (not installed)".format(b))

        for b_ref in backends:
            for b_compare in backends:
                if b_compare != b_ref:
                    self.expect_isclose(gpc_matrix[b_ref], gpc_matrix[b_compare], atol=1e-6,
                                        msg="gpc matrices between "+b_ref+" and "+b_compare+" are not equal")

                    self.expect_isclose(gpc_matrix_gradient[b_ref], gpc_matrix_gradient[b_compare], atol=1e-6,
                                        msg="gpc matrices between "+b_ref+" and "+b_compare+" are not equal")

                    self.expect_isclose(pce_matrix[b_ref], pce_matrix[b_compare], atol=1e-6,
                                        msg="pce matrices between "+b_ref+" and "+b_compare+" are not equal")

        print("done!\n")

    def test_15_save_and_load_session(self):
        """
        Save and load a gPC Session
        """
        global folder, plot, save_session_format
        test_name = 'pygpc_test_15_save_and_load_session'
        print(test_name)

        print("done!\n")

    def test_16_gradient_estimation_methods(self):
        """
        Test gradient estimation methods
        """
        methods_options = dict()
        methods = ["FD_fwd", "FD_1st", "FD_2nd", "FD_1st2nd"]
        methods_options["FD_fwd"] = {"dx": 0.001, "distance_weight": -2}
        methods_options["FD_1st"] = {"dx": 0.1, "distance_weight": -2}
        methods_options["FD_2nd"] = {"dx": 0.1, "distance_weight": -2}
        methods_options["FD_1st2nd"] = {"dx": 0.1, "distance_weight": -2}

        # define model
        model = pygpc.testfunctions.Peaks()

        # define problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[1.2, 2])
        parameters["x2"] = 0.5
        parameters["x3"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[0, 0.6])
        problem = pygpc.Problem(model, parameters)

        # define grid
        n_grid = 1000
        grid = pygpc.Random(parameters_random=problem.parameters_random,
                            n_grid=n_grid,
                            seed=1)

        # create grid points for finite difference approximation
        grid.create_gradient_grid(delta=1e-3)

        # evaluate model function
        com = pygpc.Computation(n_cpu=0, matlab_model=False)

        # [n_grid x n_out]
        res = com.run(model=model,
                      problem=problem,
                      coords=grid.coords,
                      coords_norm=grid.coords_norm,
                      i_iter=None,
                      i_subiter=None,
                      fn_results=None,
                      print_func_time=False)

        grad_res = dict()
        gradient_idx = dict()
        for m in methods:
            # [n_grid x n_out x dim]
            grad_res[m], gradient_idx[m] = pygpc.get_gradient(model=model,
                                                              problem=problem,
                                                              grid=grid,
                                                              results=res,
                                                              com=com,
                                                              method=m,
                                                              gradient_results_present=None,
                                                              gradient_idx_skip=None,
                                                              i_iter=None,
                                                              i_subiter=None,
                                                              print_func_time=False,
                                                              dx=methods_options[m]["dx"],
                                                              distance_weight=methods_options[m]["distance_weight"])

            if m != "FD_fwd":
                nrmsd = pygpc.nrmsd(grad_res[m][:, 0, :], grad_res["FD_fwd"][gradient_idx[m], 0, :])
                self.expect_true((nrmsd < 0.05).all(),
                                 msg="gPC test failed during gradient estimation: {} error too large".format(m))

    def test_17_grids(self):
        """
        Test grids
        """

        global folder, plot
        test_name = 'pygpc_test_17_grids'

        # grids to compare
        grids = [pygpc.Random, pygpc.LHS, pygpc.LHS, pygpc.LHS, pygpc.LHS]
        grids_options = [None, None, "corr", "maximin", "ese"]
        grid_legend = ["Random", "LHS (standard)", "LHS (corr opt)", "LHS (Phi-P opt)", "LHS (ESE)"]
        order = [2, 4, 6]
        repetitions = 2

        err = np.zeros((len(grids), len(order), repetitions))
        n_grid = np.zeros(len(order))

        # Model
        model = pygpc.testfunctions.Ishigami()

        # Problem
        parameters = OrderedDict()
        parameters["x1"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[-np.pi, np.pi])
        parameters["x2"] = pygpc.Beta(pdf_shape=[1, 1], pdf_limits=[-np.pi, np.pi])
        parameters["x3"] = 0.
        parameters["a"] = 7.
        parameters["b"] = 0.1

        problem = pygpc.Problem(model, parameters)

        # gPC options
        options = dict()
        options["method"] = "reg"
        options["solver"] = "Moore-Penrose"
        options["interaction_order"] = problem.dim
        options["order_max_norm"] = 1
        options["n_cpu"] = 0
        options["adaptive_sampling"] = False
        options["gradient_enhanced"] = False
        options["fn_results"] = None
        options["error_type"] = "nrmsd"
        options["error_norm"] = "relative"
        options["matrix_ratio"] = 2
        options["eps"] = 0.001
        options["backend"] = "omp"

        for i_g, g in enumerate(grids):
            for i_o, o in enumerate(order):
                for i_n, n in enumerate(range(repetitions)):

                    options["order"] = [o] * problem.dim
                    options["order_max"] = o
                    options["grid"] = g
                    options["grid_options"] = grids_options[i_g]

                    n_coeffs = pygpc.get_num_coeffs_sparse(order_dim_max=options["order"],
                                                           order_glob_max=options["order_max"],
                                                           order_inter_max=options["interaction_order"],
                                                           dim=problem.dim)

                    grid = g(parameters_random=problem.parameters_random,
                             n_grid=options["matrix_ratio"] * n_coeffs,
                             options=options["grid_options"])

                    # define algorithm
                    algorithm = pygpc.Static(problem=problem, options=options, grid=grid)

                    # Initialize gPC Session
                    session = pygpc.Session(algorithm=algorithm)

                    # run gPC session
                    session, coeffs, results = session.run()

                    err[i_g, i_o, i_n] = pygpc.validate_gpc_mc(session=session,
                                                               coeffs=coeffs,
                                                               n_samples=int(1e4),
                                                               n_cpu=0,
                                                               output_idx=0,
                                                               fn_out=None,
                                                               plot=False)

                n_grid[i_o] = grid.n_grid

        err_mean = np.mean(err, axis=2)
        err_std = np.std(err, axis=2)

        if plot:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(1, 2, figsize=[12,5])

            for i in range(len(grids)):
                ax[0].errorbar(n_grid, err_mean[i, :], err_std[i, :], capsize=3, elinewidth=.5)
                ax[1].plot(n_grid, err_std[i, :])

            for a in ax:
                a.legend(grid_legend)
                a.set_xlabel("$N_g$", fontsize=12)
                a.grid()

            ax[0].set_ylabel("$\epsilon$", fontsize=12)
            ax[1].set_ylabel("std($\epsilon$)", fontsize=12)

            ax[0].set_title("gPC error vs original model (mean and std)")
            ax[1].set_title("gPC error vs original model (std)")

            plt.savefig(os.path.join(folder, test_name + ".png"), dpi=300)


if __name__ == '__main__':
    unittest.main()

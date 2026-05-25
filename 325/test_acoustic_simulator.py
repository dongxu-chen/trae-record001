import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acoustic_simulator import (
    RoomGeometry,
    SoundSource,
    DynamicSource,
    SourceManager,
    RT60Calculator,
    GPUAccelerator,
    AcousticSimulator,
    SoundFieldVisualizer,
    AbsorptionBand,
    PrecomputedIR,
    STANDARD_OCTAVE_BANDS,
    STANDARD_13_OCTAVE_BANDS,
    Auralizer,
    AuralizationResult,
    RoomOptimizer,
    AbsorptionMaterial,
    MATERIAL_DATABASE,
)


class TestRoomGeometry(unittest.TestCase):
    def test_2d_room(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=0.5, use_pra=False)
        self.assertEqual(room.ndim, 2)
        self.assertEqual(room.get_volume(), 20.0)
        self.assertEqual(room.absorption.shape[0], 4)
        self.assertEqual(room.absorption.shape[1], 7)
        avg_abs = room.get_average_absorption()
        self.assertTrue(np.allclose(avg_abs, 0.5))

    def test_3d_room(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0, 3.0]), absorption=0.5, use_pra=False)
        self.assertEqual(room.ndim, 3)
        self.assertEqual(room.get_volume(), 60.0)
        self.assertAlmostEqual(room.get_surface_area(), 94.0)
        self.assertEqual(room.absorption.shape[0], 6)
        self.assertEqual(room.absorption.shape[1], 7)

    def test_custom_absorption(self):
        absorption = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        room = RoomGeometry(dimensions=np.array([5.0, 4.0, 3.0]), absorption=absorption, use_pra=False)
        self.assertEqual(room.absorption.shape, (6, 7))
        for i in range(6):
            self.assertTrue(np.all(room.absorption[i, :] == absorption[i]))
        avg_abs = room.get_average_absorption()
        self.assertAlmostEqual(float(np.mean(avg_abs)), 0.35, places=5)

    def test_invalid_absorption(self):
        with self.assertRaises(ValueError):
            RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=[0.1, 0.2, 0.3], use_pra=False)


class TestSoundSource(unittest.TestCase):
    def test_source_creation(self):
        source = SoundSource(position=np.array([1.0, 2.0, 1.5]))
        np.testing.assert_array_equal(source.position, np.array([1.0, 2.0, 1.5]))
        self.assertEqual(source.amplitude, 1.0)
        self.assertEqual(source.delay, 0.0)

    def test_generate_impulse(self):
        source = SoundSource(position=np.array([1.0, 2.0]))
        sig = source.generate_impulse(fs=44100, amplitude=0.5)
        self.assertEqual(len(sig), 1)
        self.assertEqual(sig[0], 0.5)

    def test_generate_tone(self):
        source = SoundSource(position=np.array([1.0, 2.0]))
        fs = 44100
        sig = source.generate_tone(frequency=440, duration=1.0, fs=fs)
        self.assertEqual(len(sig), fs)
        self.assertEqual(source.frequency, 440)

    def test_generate_noise(self):
        source = SoundSource(position=np.array([1.0, 2.0]))
        fs = 44100
        sig = source.generate_noise(duration=0.1, fs=fs)
        self.assertEqual(len(sig), int(0.1 * fs))

    def test_source_copy(self):
        source1 = SoundSource(position=np.array([1.0, 2.0]), amplitude=0.5)
        source1.generate_impulse(fs=44100)
        source2 = source1.copy()
        np.testing.assert_array_equal(source1.position, source2.position)
        self.assertEqual(source1.amplitude, source2.amplitude)
        source2.position[0] = 5.0
        self.assertNotEqual(source1.position[0], source2.position[0])


class TestDynamicSource(unittest.TestCase):
    def test_linear_trajectory(self):
        source = DynamicSource(position=np.array([0.0, 0.0]))
        source.set_linear_trajectory(
            start_pos=np.array([0.0, 0.0]),
            end_pos=np.array([4.0, 3.0]),
            duration=2.0
        )
        np.testing.assert_array_almost_equal(source.get_position(0.0), [0.0, 0.0])
        np.testing.assert_array_almost_equal(source.get_position(1.0), [2.0, 1.5])
        np.testing.assert_array_almost_equal(source.get_position(2.0), [4.0, 3.0])
        np.testing.assert_array_almost_equal(source.get_position(3.0), [4.0, 3.0])

    def test_circular_trajectory(self):
        source = DynamicSource(position=np.array([4.0, 3.0]))
        source.set_circular_trajectory(
            center=np.array([4.0, 3.0]),
            radius=2.0,
            angular_velocity=np.pi / 2,
            start_time=0.0,
            duration=4.0
        )
        pos_0 = source.get_position(0.0)
        pos_1 = source.get_position(1.0)
        pos_2 = source.get_position(2.0)

        np.testing.assert_array_almost_equal(pos_0, [6.0, 3.0])
        np.testing.assert_array_almost_equal(pos_1, [4.0, 5.0], decimal=5)
        np.testing.assert_array_almost_equal(pos_2, [2.0, 3.0], decimal=5)

    def test_sinusoidal_trajectory(self):
        source = DynamicSource(position=np.array([4.0, 3.0]))
        source.set_sinusoidal_trajectory(
            center=np.array([4.0, 3.0]),
            amplitude=np.array([1.0, 0.0]),
            frequency=1.0,
            start_time=0.0,
            duration=2.0
        )
        pos_0 = source.get_position(0.0)
        pos_025 = source.get_position(0.25)
        pos_05 = source.get_position(0.5)

        np.testing.assert_array_almost_equal(pos_0, [4.0, 3.0])
        np.testing.assert_array_almost_equal(pos_025, [5.0, 3.0])
        np.testing.assert_array_almost_equal(pos_05, [4.0, 3.0], decimal=5)

    def test_custom_trajectory(self):
        def custom_traj(t):
            return np.array([t, t ** 2])

        source = DynamicSource(position=np.array([0.0, 0.0]), trajectory=custom_traj)
        np.testing.assert_array_almost_equal(source.get_position(2.0), [2.0, 4.0])


class TestSourceManager(unittest.TestCase):
    def test_add_source(self):
        manager = SourceManager()
        source = SoundSource(position=np.array([1.0, 2.0]))
        src_id = manager.add_source(source)
        self.assertEqual(len(manager), 1)
        self.assertEqual(manager.get_source(src_id), source)

    def test_remove_source(self):
        manager = SourceManager()
        source = SoundSource(position=np.array([1.0, 2.0]))
        src_id = manager.add_source(source)
        self.assertTrue(manager.remove_source(src_id))
        self.assertEqual(len(manager), 0)
        self.assertFalse(manager.remove_source(999))

    def test_get_positions(self):
        manager = SourceManager()
        manager.add_source(SoundSource(position=np.array([1.0, 2.0])))
        manager.add_source(SoundSource(position=np.array([3.0, 4.0])))

        positions = manager.get_positions()
        expected = np.array([[1.0, 2.0], [3.0, 4.0]])
        np.testing.assert_array_equal(positions, expected)

    def test_get_positions_dynamic(self):
        manager = SourceManager()
        dyn_source = DynamicSource(position=np.array([0.0, 0.0]))
        dyn_source.set_linear_trajectory([0.0, 0.0], [4.0, 4.0], 2.0)
        manager.add_source(dyn_source)

        pos_0 = manager.get_positions(time=0.0)
        pos_1 = manager.get_positions(time=1.0)

        np.testing.assert_array_almost_equal(pos_0, [[0.0, 0.0]])
        np.testing.assert_array_almost_equal(pos_1, [[2.0, 2.0]])

    def test_iteration(self):
        manager = SourceManager()
        s1 = SoundSource(position=np.array([1.0, 2.0]))
        s2 = SoundSource(position=np.array([3.0, 4.0]))
        manager.add_source(s1)
        manager.add_source(s2)

        sources = [s for s in manager]
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0], s1)
        self.assertEqual(sources[1], s2)


class TestGPUAccelerator(unittest.TestCase):
    def test_cpu_mode(self):
        gpu = GPUAccelerator(use_gpu=False)
        self.assertFalse(gpu.is_gpu_available)
        self.assertEqual(gpu.backend, "numpy")

    def test_basic_operations(self):
        gpu = GPUAccelerator(use_gpu=False)

        a = np.array([1.0, 2.0, 3.0])
        b = np.array([4.0, 5.0, 6.0])

        self.assertEqual(gpu.sum(a), 6.0)
        self.assertEqual(gpu.mean(a), 2.0)
        self.assertEqual(gpu.max(a), 3.0)
        self.assertEqual(gpu.min(a), 1.0)

    def test_distance_calculation(self):
        gpu = GPUAccelerator(use_gpu=False)

        sources = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        receivers = np.array([[3.0, 4.0, 0.0], [0.0, 0.0, 1.0]])

        distances = gpu.parallel_distance_calculation(sources, receivers)

        expected = np.array([[5.0, 1.0], [np.sqrt(20), np.sqrt(2)]])
        np.testing.assert_array_almost_equal(distances, expected)

    def test_pressure_calculation(self):
        gpu = GPUAccelerator(use_gpu=False)

        distances = np.array([[1.0, 2.0], [3.0, 4.0]])
        frequencies = np.array([100.0, 1000.0])

        pressure = gpu.parallel_pressure_calculation(distances, frequencies)
        self.assertEqual(pressure.shape, (2, 2, 2))


class TestRT60Calculator(unittest.TestCase):
    def setUp(self):
        self.rt60_calc = RT60Calculator(fs=44100)

    def test_edc_calculation(self):
        ir = np.zeros(4410)
        ir[0] = 1.0
        ir[100] = 0.5
        ir[200] = 0.25

        edc = self.rt60_calc._calculate_edc(ir)
        self.assertEqual(len(edc), len(ir))
        self.assertAlmostEqual(edc[0], 0.0, places=5)
        self.assertLess(edc[-1], -50)

    def test_sabine_formula(self):
        rt60 = self.rt60_calc.calculate_sabine_rt60(
            volume=100.0,
            surface_area=140.0,
            absorption_coeff=0.5
        )
        expected = 0.161 * 100.0 / (140.0 * 0.5)
        self.assertAlmostEqual(rt60, expected)

    def test_eyring_formula(self):
        rt60 = self.rt60_calc.calculate_eyring_rt60(
            volume=100.0,
            surface_area=140.0,
            absorption_coeff=0.5
        )
        expected = 0.161 * 100.0 / (-140.0 * np.log(0.5))
        self.assertAlmostEqual(rt60, expected)

    def test_room_modes_2d(self):
        room_dims = np.array([5.0, 4.0])
        modes = self.rt60_calc.analyze_room_modes(room_dims, max_freq=100)

        self.assertIn('frequencies', modes)
        self.assertIn('modes', modes)
        self.assertIn('spacing', modes)
        self.assertGreater(len(modes['frequencies']), 0)

    def test_room_modes_3d(self):
        room_dims = np.array([5.0, 4.0, 3.0])
        modes = self.rt60_calc.analyze_room_modes(room_dims, max_freq=100)
        self.assertGreater(len(modes['frequencies']), 0)

    def test_acoustic_parameters(self):
        fs = 44100
        duration = 1.0
        t = np.arange(int(fs * duration)) / fs

        ir = np.exp(-t * 5.0) * np.random.randn(len(t))
        ir[0] = 1.0

        clarity = self.rt60_calc.calculate_clarity(ir, threshold_time=0.05)
        definition = self.rt60_calc.calculate_definition(ir, threshold_time=0.05)
        center_time = self.rt60_calc.calculate_center_time(ir)

        self.assertIsInstance(clarity, float)
        self.assertIsInstance(definition, float)
        self.assertIsInstance(center_time, float)
        self.assertGreater(definition, 0)
        self.assertLess(definition, 100)


class TestAcousticSimulator(unittest.TestCase):
    def test_simulator_creation(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=0.5, use_pra=False)
        sim = AcousticSimulator(room_geometry=room, fs=44100, use_gpu=False)
        self.assertEqual(sim.fs, 44100)
        self.assertEqual(len(sim.source_manager), 0)
        self.assertEqual(len(sim.receivers), 0)

    def test_add_source_and_receiver(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=0.5, use_pra=False)
        sim = AcousticSimulator(room_geometry=room, fs=44100, use_gpu=False)

        source_id = sim.add_source(SoundSource(position=np.array([1.0, 1.0])))
        receiver_id = sim.add_receiver(np.array([4.0, 3.0]))

        self.assertEqual(source_id, 0)
        self.assertEqual(receiver_id, 0)
        self.assertEqual(len(sim.source_manager), 1)
        self.assertEqual(len(sim.receivers), 1)

    def test_receivers_grid(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=0.5, use_pra=False)
        sim = AcousticSimulator(room_geometry=room, fs=44100, use_gpu=False)

        positions = sim.add_receivers_grid(
            x_range=(1.0, 4.0),
            y_range=(1.0, 3.0),
            resolution=1.0
        )

        self.assertEqual(len(positions), 4 * 3)
        self.assertEqual(len(sim.receivers), 12)

    def test_mirror_sources_custom(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=0.5,
                           max_order=2, use_pra=False)
        sim = AcousticSimulator(room_geometry=room, fs=44100, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0])))
        sim.add_receiver(np.array([4.0, 3.0]))

        mirror_sources, orders, reflections = sim.compute_mirror_sources(max_order=2)

        self.assertGreater(len(mirror_sources), 0)
        self.assertEqual(len(mirror_sources), len(orders))
        self.assertTrue(np.all(orders <= 2))

    def test_impulse_response(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=0.5,
                           max_order=1, use_pra=False)
        sim = AcousticSimulator(room_geometry=room, fs=44100, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0])))
        sim.add_receiver(np.array([4.0, 3.0]))

        ir = sim.compute_impulse_responses(max_order=1, duration=0.5)

        self.assertEqual(ir.shape, (1, 1, int(0.5 * 44100)))
        self.assertGreater(np.max(np.abs(ir)), 0)

    def test_sound_pressure(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=0.5, use_pra=False)
        sim = AcousticSimulator(room_geometry=room, fs=44100, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0])))
        sim.add_receiver(np.array([4.0, 3.0]))

        frequencies = np.array([100.0, 500.0, 1000.0])
        pressure = sim.compute_sound_pressure(frequencies)

        self.assertEqual(pressure.shape, (3, 1, 1))

    def test_reset(self):
        room = RoomGeometry(dimensions=np.array([5.0, 4.0]), absorption=0.5, use_pra=False)
        sim = AcousticSimulator(room_geometry=room, fs=44100, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0])))
        sim.add_receiver(np.array([4.0, 3.0]))
        sim.compute_impulse_responses(max_order=1, duration=0.1)

        self.assertIsNotNone(sim.impulse_responses)
        sim.reset()
        self.assertIsNone(sim.impulse_responses)
        self.assertEqual(len(sim.source_manager), 0)
        self.assertEqual(len(sim.receivers), 0)


class TestDynamicSimulation(unittest.TestCase):
    def test_dynamic_source_simulation(self):
        room = RoomGeometry(dimensions=np.array([6.0, 6.0]), absorption=0.5,
                           max_order=1, use_pra=False)
        sim = AcousticSimulator(room_geometry=room, fs=16000, use_gpu=False)

        dyn_source = DynamicSource(position=np.array([1.0, 3.0]))
        dyn_source.set_linear_trajectory([1.0, 3.0], [5.0, 3.0], 2.0)
        dyn_source.generate_impulse(fs=16000)

        sim.add_receivers_grid(
            x_range=(2.0, 4.0),
            y_range=(2.0, 4.0),
            resolution=1.0
        )

        time_points = np.linspace(0, 2.0, 5)
        results = sim.simulate_dynamic_source(dyn_source, time_points)

        self.assertIn('time_points', results)
        self.assertIn('source_positions', results)
        self.assertIn('impulse_responses', results)
        self.assertIn('pressure_levels', results)

        self.assertEqual(results['source_positions'].shape, (5, 2))
        np.testing.assert_array_almost_equal(results['source_positions'][0], [1.0, 3.0])
        np.testing.assert_array_almost_equal(results['source_positions'][-1], [5.0, 3.0])


class TestVisualization(unittest.TestCase):
    def test_visualizer_creation(self):
        viz = SoundFieldVisualizer(dpi=100, figsize=(10, 8))
        self.assertEqual(viz.dpi, 100)
        self.assertEqual(viz.figsize, (10, 8))

    def test_plot_impulse_response(self):
        viz = SoundFieldVisualizer()
        fs = 44100
        t = np.arange(fs) / fs
        ir = np.exp(-t * 10) * np.sin(2 * np.pi * 440 * t)

        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax_returned = viz.plot_impulse_response(ir, fs, ax=ax, show=False)
        self.assertEqual(ax, ax_returned)
        plt.close(fig)

    def test_plot_edc(self):
        viz = SoundFieldVisualizer()
        fs = 44100
        edc = -np.linspace(0, 60, fs)

        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax_returned = viz.plot_edc(edc, fs, rt60=1.0, ax=ax, show=False)
        self.assertEqual(ax, ax_returned)
        plt.close(fig)

    def test_plot_sound_pressure_heatmap(self):
        viz = SoundFieldVisualizer()

        x = np.linspace(1.0, 4.0, 10)
        y = np.linspace(1.0, 3.0, 7)
        X, Y = np.meshgrid(x, y)
        positions = np.vstack([X.ravel(), Y.ravel()]).T

        pressure = np.random.rand(len(positions)) + 0.1
        room_dims = np.array([5.0, 4.0])

        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax_returned = viz.plot_sound_pressure_heatmap(
            positions, pressure, room_dims, ax=ax, show=False
        )
        self.assertEqual(ax, ax_returned)
        plt.close(fig)


class TestAbsorptionBand(unittest.TestCase):
    def test_absorption_band_creation(self):
        freqs = np.array([125, 250, 500, 1000])
        coeffs = np.array([0.1, 0.2, 0.3, 0.4])
        abs_band = AbsorptionBand(freqs, coeffs)

        np.testing.assert_array_equal(abs_band.frequencies, freqs)
        np.testing.assert_array_equal(abs_band.coefficients, coeffs)

    def test_get_absorption_at(self):
        freqs = np.array([125, 250, 500, 1000])
        coeffs = np.array([0.1, 0.2, 0.3, 0.4])
        abs_band = AbsorptionBand(freqs, coeffs)

        self.assertAlmostEqual(abs_band.get_absorption_at(250), 0.2)
        self.assertAlmostEqual(abs_band.get_absorption_at(300), 0.2)
        self.assertAlmostEqual(abs_band.get_absorption_at(600), 0.3)

    def test_interp_absorption(self):
        freqs = np.array([125, 250, 500, 1000])
        coeffs = np.array([0.1, 0.2, 0.4, 0.8])
        abs_band = AbsorptionBand(freqs, coeffs)

        self.assertAlmostEqual(abs_band.interp_absorption(250), 0.2)
        self.assertAlmostEqual(abs_band.interp_absorption(375), 0.3)

    def test_invalid_band(self):
        with self.assertRaises(ValueError):
            AbsorptionBand(np.array([125, 250]), np.array([0.1]))

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            AbsorptionBand(np.array([125, 250, 500]), np.array([0.1, 0.2]))


class TestAdaptiveOrder(unittest.TestCase):
    def test_adaptive_order_disabled(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            max_order=5,
            adaptive_order=False,
            use_pra=False
        )
        source_pos = np.array([1.0, 1.0, 1.5])
        order = room.compute_adaptive_max_order(source_pos)
        self.assertEqual(order, 5)

    def test_adaptive_order_small_room(self):
        room = RoomGeometry(
            dimensions=np.array([3.0, 2.5, 2.0]),
            absorption=0.8,
            adaptive_order=True,
            adaptive_order_db_threshold=60.0,
            use_pra=False
        )
        source_pos = np.array([0.5, 0.5, 1.0])
        receiver_pos = np.array([2.5, 2.0, 1.0])
        order = room.compute_adaptive_max_order(source_pos, receiver_pos)

        self.assertGreater(order, 0)
        self.assertLessEqual(order, 20)

    def test_adaptive_order_large_room_low_absorption(self):
        room = RoomGeometry(
            dimensions=np.array([10.0, 8.0, 4.0]),
            absorption=0.1,
            adaptive_order=True,
            adaptive_order_db_threshold=60.0,
            use_pra=False
        )
        source_pos = np.array([1.0, 1.0, 1.5])
        receiver_pos = np.array([9.0, 7.0, 2.5])
        order = room.compute_adaptive_max_order(source_pos, receiver_pos)

        self.assertGreater(order, 3)
        self.assertLessEqual(order, 20)

    def test_adaptive_order_db_threshold(self):
        room = RoomGeometry(
            dimensions=np.array([6.0, 5.0, 3.0]),
            absorption=0.5,
            adaptive_order=True,
            use_pra=False
        )
        source_pos = np.array([1.0, 1.0, 1.5])
        receiver_pos = np.array([5.0, 4.0, 1.5])

        room.adaptive_order_db_threshold = 40
        order_40 = room.compute_adaptive_max_order(source_pos, receiver_pos)

        room.adaptive_order_db_threshold = 80
        order_80 = room.compute_adaptive_max_order(source_pos, receiver_pos)

        self.assertGreaterEqual(order_80, order_40)

    def test_adaptive_order_multi(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            adaptive_order=True,
            use_pra=False
        )
        sources = np.array([[1.0, 1.0, 1.5], [4.0, 1.0, 1.5]])
        receivers = np.array([[2.5, 3.0, 1.5], [1.0, 3.5, 1.5]])

        order = room.compute_adaptive_max_order_multi(sources, receivers)
        self.assertGreater(order, 0)
        self.assertLessEqual(order, 20)


class TestBandAbsorptionRoom(unittest.TestCase):
    def test_scalar_absorption(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            band_type="octave",
            use_pra=False
        )
        self.assertEqual(room.absorption.shape, (6, 7))
        self.assertTrue(np.all(room.absorption == 0.5))

    def test_wall_absorption_array(self):
        absorption = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=absorption,
            band_type="octave",
            use_pra=False
        )
        self.assertEqual(room.absorption.shape, (6, 7))
        for i in range(6):
            self.assertTrue(np.all(room.absorption[i, :] == absorption[i]))

    def test_band_absorption_array(self):
        frequencies = STANDARD_OCTAVE_BANDS
        absorption = np.linspace(0.1, 0.7, 7)
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=absorption,
            band_type="octave",
            use_pra=False
        )
        self.assertEqual(room.absorption.shape, (6, 7))
        for i in range(7):
            self.assertTrue(np.all(room.absorption[:, i] == absorption[i]))

    def test_2d_absorption(self):
        absorption = np.random.rand(6, 7)
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=absorption,
            band_type="octave",
            use_pra=False
        )
        np.testing.assert_array_almost_equal(room.absorption, absorption)

    def test_absorption_band_object(self):
        frequencies = STANDARD_OCTAVE_BANDS
        coeffs = np.linspace(0.1, 0.7, 7)
        abs_band = AbsorptionBand(frequencies, coeffs)
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=abs_band,
            use_pra=False
        )
        self.assertEqual(room.absorption.shape, (6, 7))
        np.testing.assert_array_almost_equal(room.absorption_band.coefficients, coeffs)

    def test_13_octave_band(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            band_type="1/3_octave",
            use_pra=False
        )
        self.assertEqual(room.n_bands, 21)
        self.assertEqual(room.absorption.shape, (6, 21))
        np.testing.assert_array_equal(room.frequencies, STANDARD_13_OCTAVE_BANDS)

    def test_custom_frequencies(self):
        freqs = np.array([100, 200, 300, 400, 500])
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            frequencies=freqs,
            use_pra=False
        )
        self.assertEqual(room.n_bands, 5)
        np.testing.assert_array_equal(room.frequencies, freqs)

    def test_invalid_band_type(self):
        with self.assertRaises(ValueError):
            RoomGeometry(
                dimensions=np.array([5.0, 4.0, 3.0]),
                absorption=0.5,
                band_type="invalid",
                use_pra=False
            )

    def test_invalid_1d_absorption_length(self):
        with self.assertRaises(ValueError):
            RoomGeometry(
                dimensions=np.array([5.0, 4.0, 3.0]),
                absorption=np.array([0.1, 0.2, 0.3]),
                use_pra=False
            )

    def test_invalid_2d_absorption_shape(self):
        with self.assertRaises(ValueError):
            RoomGeometry(
                dimensions=np.array([5.0, 4.0, 3.0]),
                absorption=np.random.rand(5, 7),
                use_pra=False
            )


class TestBandImpulseResponses(unittest.TestCase):
    def test_band_ir_computation(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            max_order=2,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=16000, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim.add_receiver(np.array([4.0, 3.0, 1.5]))

        band_irs = sim.compute_band_impulse_responses(max_order=2, duration=0.5)
        self.assertEqual(band_irs.ndim, 4)
        self.assertEqual(band_irs.shape[0], 1)
        self.assertEqual(band_irs.shape[1], 1)
        self.assertEqual(band_irs.shape[2], room.n_bands)
        self.assertEqual(band_irs.shape[3], int(0.5 * 16000))

        self.assertIsNotNone(sim.band_impulse_responses)
        self.assertIsNotNone(sim.impulse_responses)

    def test_frequency_dependent_absorption(self):
        frequencies = STANDARD_OCTAVE_BANDS
        absorption_low = 0.2 * np.ones_like(frequencies)
        absorption_high = 0.8 * np.ones_like(frequencies)

        room_low = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=absorption_low,
            max_order=2,
            adaptive_order=False,
            use_pra=False
        )
        room_high = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=absorption_high,
            max_order=2,
            adaptive_order=False,
            use_pra=False
        )

        sim_low = AcousticSimulator(room_low, fs=8000, use_gpu=False)
        sim_low.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim_low.add_receiver(np.array([4.0, 3.0, 1.5]))
        ir_low = sim_low.compute_band_impulse_responses(max_order=2, duration=0.5)

        sim_high = AcousticSimulator(room_high, fs=8000, use_gpu=False)
        sim_high.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim_high.add_receiver(np.array([4.0, 3.0, 1.5]))
        ir_high = sim_high.compute_band_impulse_responses(max_order=2, duration=0.5)

        energy_low = np.sum(ir_low[0, 0, :, :] ** 2, axis=-1)
        energy_high = np.sum(ir_high[0, 0, :, :] ** 2, axis=-1)

        self.assertTrue(np.all(energy_low >= energy_high))

    def test_get_band_ir(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            max_order=2,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=8000, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim.add_receiver(np.array([4.0, 3.0, 1.5]))

        sim.compute_band_impulse_responses(max_order=2, duration=0.5)

        for band_idx in range(room.n_bands):
            ir = sim.get_impulse_response(0, 0, band_idx)
            self.assertEqual(len(ir), int(0.5 * 8000))

    def test_rt60_from_band_irs(self):
        room = RoomGeometry(
            dimensions=np.array([6.0, 5.0, 3.0]),
            absorption=0.5,
            max_order=3,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=16000, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim.add_receiver(np.array([5.0, 4.0, 1.5]))

        band_irs = sim.compute_band_impulse_responses(max_order=3, duration=1.0)

        rt60_calc = RT60Calculator(fs=16000)
        result = rt60_calc.calculate_rt60_from_band_irs(
            band_irs[0, 0, :, :],
            room.frequencies,
            method="t30"
        )

        self.assertIn('rt60_bands', result)
        self.assertEqual(len(result['rt60_bands']), room.n_bands)
        self.assertIn('edc_bands', result)
        self.assertEqual(len(result['edc_bands']), room.n_bands)

    def test_rt60_theoretical_bands(self):
        frequencies = STANDARD_OCTAVE_BANDS
        absorption = np.linspace(0.1, 0.7, 7)
        room = RoomGeometry(
            dimensions=np.array([6.0, 5.0, 3.0]),
            absorption=absorption,
            adaptive_order=False,
            use_pra=False
        )

        rt60_calc = RT60Calculator(fs=16000)
        result_sabine = rt60_calc.calculate_rt60_theoretical_bands(room, method="sabine")
        result_eyring = rt60_calc.calculate_rt60_theoretical_bands(room, method="eyring")

        self.assertEqual(len(result_sabine['rt60_bands']), 7)
        self.assertEqual(len(result_eyring['rt60_bands']), 7)
        self.assertTrue(np.all(result_sabine['rt60_bands'] > 0))
        self.assertTrue(np.all(result_eyring['rt60_bands'] > 0))


class TestOptimizedDynamicSource(unittest.TestCase):
    def test_precompute_static_part(self):
        room = RoomGeometry(
            dimensions=np.array([6.0, 5.0]),
            absorption=0.5,
            max_order=2,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=8000, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 2.5])))
        sim.add_receivers_grid((2.0, 4.0), (2.0, 4.0), resolution=1.0)

        static = sim.precompute_static_part(max_order=2)

        self.assertIsNotNone(static)
        self.assertIn('mirror_sources_base', static)
        self.assertIn('mirror_orders', static)
        self.assertIn('reflection_counts', static)
        self.assertIn('receiver_positions', static)

        self.assertIsNotNone(sim._precomputed_static)

    def test_precomputed_ir_interpolation(self):
        time_points = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        source_positions = np.array([[1.0, 2.5], [2.0, 2.5], [3.0, 2.5], [4.0, 2.5], [5.0, 2.5]])

        n_samples = 100
        irs = np.zeros((5, 4, 1, n_samples))
        for i in range(5):
            irs[i, 0, 0, i * 10] = 1.0

        precomputed = PrecomputedIR(
            time_points=time_points,
            source_positions=source_positions,
            impulse_responses=irs,
            interpolation_method="linear"
        )

        ir_mid = precomputed.get_ir_at_time(0.5)
        self.assertEqual(ir_mid.shape, (4, 1, n_samples))
        self.assertAlmostEqual(ir_mid[0, 0, 0], 0.5)
        self.assertAlmostEqual(ir_mid[0, 0, 10], 0.5)

        ir_exact = precomputed.get_ir_at_time(2.0)
        self.assertEqual(ir_exact[0, 0, 20], 1.0)

    def test_optimized_dynamic_simulation(self):
        room = RoomGeometry(
            dimensions=np.array([6.0, 5.0]),
            absorption=0.5,
            max_order=1,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=4000, use_gpu=False)

        dyn_source = DynamicSource(position=np.array([1.0, 2.5]))
        dyn_source.set_linear_trajectory([1.0, 2.5], [5.0, 2.5], 2.0)
        dyn_source.generate_impulse(fs=4000)

        sim.add_source(dyn_source)
        sim.add_receivers_grid((2.0, 4.0), (2.0, 4.0), resolution=1.0)

        time_points = np.linspace(0, 2.0, 10)

        sim.precompute_static_part(max_order=1)

        precomputed = sim.simulate_dynamic_source_optimized(
            dyn_source, time_points, max_order=1, duration=0.3
        )

        self.assertIsInstance(precomputed, PrecomputedIR)
        self.assertLessEqual(len(precomputed.time_points), len(time_points))

    def test_simulate_dynamic_with_optimized_flag(self):
        room = RoomGeometry(
            dimensions=np.array([6.0, 5.0]),
            absorption=0.5,
            max_order=1,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=4000, use_gpu=False)

        dyn_source = DynamicSource(position=np.array([1.0, 2.5]))
        dyn_source.set_linear_trajectory([1.0, 2.5], [5.0, 2.5], 2.0)
        dyn_source.generate_impulse(fs=4000)

        sim.add_source(dyn_source)
        sim.add_receiver(np.array([3.0, 3.0]))

        time_points = np.linspace(0, 2.0, 5)

        result_opt = sim.simulate_dynamic_source(
            dyn_source, time_points, use_optimized=True, max_order=1, duration=0.2
        )

        self.assertIn('precomputed_ir', result_opt)
        self.assertIsInstance(result_opt['precomputed_ir'], PrecomputedIR)
        self.assertEqual(len(result_opt['impulse_responses']), len(time_points))

    def test_optimized_vs_original_accuracy(self):
        room = RoomGeometry(
            dimensions=np.array([6.0, 5.0]),
            absorption=0.5,
            max_order=1,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=4000, use_gpu=False)

        dyn_source = DynamicSource(position=np.array([1.0, 2.5]))
        dyn_source.set_linear_trajectory([1.0, 2.5], [5.0, 2.5], 2.0)
        dyn_source.generate_impulse(fs=4000)

        sim.add_source(dyn_source)
        sim.add_receiver(np.array([3.0, 3.0]))

        time_points = np.linspace(0, 2.0, 5)

        result_orig = sim.simulate_dynamic_source(
            dyn_source, time_points, use_optimized=False, max_order=1, duration=0.2
        )

        result_opt = sim.simulate_dynamic_source(
            dyn_source, time_points, use_optimized=True, max_order=1, duration=0.2
        )

        for t_idx in range(len(time_points)):
            ir_orig = result_orig['impulse_responses'][t_idx, 0, 0, :]
            ir_opt = result_opt['impulse_responses'][t_idx, 0, 0, :]

            energy_orig = np.sum(ir_orig ** 2)
            energy_opt = np.sum(ir_opt ** 2)

            if energy_orig > 1e-10:
                rel_error = np.abs(energy_orig - energy_opt) / energy_orig
                self.assertLess(rel_error, 0.5)


class TestAirAbsorptionBand(unittest.TestCase):
    def test_default_air_absorption(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=16000, use_gpu=False)

        self.assertIsNotNone(sim.air_absorption_band)
        self.assertFalse(sim.air_absorption)
        self.assertEqual(len(sim.air_absorption_band.frequencies), room.n_bands)

    def test_set_air_absorption(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=16000, use_gpu=False)

        freqs = room.frequencies
        coeffs = 0.001 * (freqs / 1000) ** 2
        air_band = AbsorptionBand(freqs, coeffs)

        sim.set_air_absorption(air_band)
        self.assertTrue(sim.air_absorption)
        self.assertEqual(sim.air_absorption_band, air_band)

    def test_air_absorption_effect(self):
        room = RoomGeometry(
            dimensions=np.array([10.0, 8.0, 3.0]),
            absorption=0.9,
            max_order=1,
            adaptive_order=False,
            use_pra=False
        )
        sim1 = AcousticSimulator(room, fs=8000, use_gpu=False)
        sim1.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim1.add_receiver(np.array([9.0, 7.0, 1.5]))
        ir1 = sim1.compute_band_impulse_responses(max_order=1, duration=0.3)

        sim2 = AcousticSimulator(room, fs=8000, use_gpu=False)
        sim2.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim2.add_receiver(np.array([9.0, 7.0, 1.5]))

        freqs = room.frequencies
        air_coeffs = np.ones_like(freqs) * 1.0
        sim2.set_air_absorption(AbsorptionBand(freqs, air_coeffs))

        ir2 = sim2.compute_band_impulse_responses(max_order=1, duration=0.3)

        energy1 = np.sum(ir1[0, 0, :, :] ** 2, axis=-1)
        energy2 = np.sum(ir2[0, 0, :, :] ** 2, axis=-1)

        self.assertTrue(np.all(energy1 >= energy2))


class TestScatteringModel(unittest.TestCase):
    def test_scattering_initialization_scalar(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            scattering=0.2,
            use_pra=False
        )
        self.assertEqual(room.scattering.shape, (6, 7))
        self.assertTrue(np.all(room.scattering == 0.2))

    def test_scattering_initialization_wall_array(self):
        scattering = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            scattering=scattering,
            use_pra=False
        )
        self.assertEqual(room.scattering.shape, (6, 7))
        for i in range(6):
            self.assertTrue(np.all(room.scattering[i, :] == scattering[i]))

    def test_scattering_initialization_band_array(self):
        frequencies = STANDARD_OCTAVE_BANDS
        scattering_band = np.linspace(0.1, 0.5, 7)
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            scattering=scattering_band,
            use_pra=False
        )
        self.assertEqual(room.scattering.shape, (6, 7))
        for j in range(7):
            self.assertTrue(np.all(room.scattering[:, j] == scattering_band[j]))

    def test_scattering_initialization_2d_array(self):
        scattering = np.random.rand(6, 7) * 0.5
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            scattering=scattering,
            use_pra=False
        )
        np.testing.assert_array_almost_equal(room.scattering, scattering)

    def test_scattering_clip(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            scattering=1.5,
            use_pra=False
        )
        self.assertTrue(np.all(room.scattering <= 1.0))
        self.assertTrue(np.all(room.scattering >= 0.0))

    def test_specular_coefficient(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            scattering=0.36,
            use_pra=False
        )
        spec_coeff = room.get_specular_coefficient(0, 0)
        self.assertAlmostEqual(spec_coeff, 0.8, places=5)

    def test_scatter_coefficient(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            scattering=0.25,
            use_pra=False
        )
        scat_coeff = room.get_scatter_coefficient(0, 0)
        self.assertAlmostEqual(scat_coeff, 0.5, places=5)

    def test_scattering_absorption_band(self):
        frequencies = STANDARD_OCTAVE_BANDS
        scattering = 0.1 + 0.6 * (frequencies / 1000) ** 0.5
        scattering = np.clip(scattering, 0.05, 0.95)
        abs_band = AbsorptionBand(frequencies, scattering)

        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            scattering=abs_band,
            use_pra=False
        )
        self.assertEqual(room.scattering.shape, (6, 7))
        self.assertIsNotNone(room.scattering_band)

    def test_ir_with_scattering(self):
        room_no_scatter = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.3,
            scattering=0.0,
            max_order=2,
            adaptive_order=False,
            use_pra=False
        )
        sim1 = AcousticSimulator(room_no_scatter, fs=8000, use_gpu=False)
        sim1.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim1.add_receiver(np.array([4.0, 3.0, 1.5]))
        ir1 = sim1.compute_band_impulse_responses(max_order=2, duration=0.3)

        room_with_scatter = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.3,
            scattering=0.5,
            max_order=2,
            adaptive_order=False,
            use_pra=False
        )
        sim2 = AcousticSimulator(room_with_scatter, fs=8000, use_gpu=False)
        sim2.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim2.add_receiver(np.array([4.0, 3.0, 1.5]))
        ir2 = sim2.compute_band_impulse_responses(max_order=2, duration=0.3)

        energy1 = np.sum(ir1 ** 2)
        energy2 = np.sum(ir2 ** 2)
        self.assertGreater(energy2, energy1 * 0.5)


class TestAuralization(unittest.TestCase):
    def test_auralizer_creation(self):
        auralizer = Auralizer(fs=44100)
        self.assertEqual(auralizer.fs, 44100)

    def test_generate_dry_signal_sine(self):
        auralizer = Auralizer(fs=44100)
        signal = auralizer.generate_dry_signal("sine", duration=0.1, frequency=440.0)
        self.assertEqual(len(signal), int(0.1 * 44100))
        self.assertTrue(np.max(np.abs(signal)) > 0)

    def test_generate_dry_signal_types(self):
        auralizer = Auralizer(fs=22050)
        signal_types = ["sine", "square", "sawtooth", "triangle", "white_noise",
                        "pink_noise", "impulse", "speech_like"]
        for sig_type in signal_types:
            signal = auralizer.generate_dry_signal(sig_type, duration=0.05)
            self.assertEqual(len(signal), int(0.05 * 22050))

    def test_convolve_ir(self):
        auralizer = Auralizer(fs=44100)
        dry = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
        ir = np.array([1.0, 0.5, 0.25])
        wet = auralizer.convolve_ir(dry, ir, normalize_dry=False)
        expected = np.array([1.0, 0.5, 0.25, 0.0, 0.0, 0.0, 0.0])
        np.testing.assert_array_almost_equal(wet[:len(expected)], expected)

    def test_auralize(self):
        auralizer = Auralizer(fs=8000)
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            max_order=1,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=8000, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim.add_receiver(np.array([4.0, 3.0, 1.5]))
        band_irs = sim.compute_band_impulse_responses(max_order=1, duration=0.2)
        ir = np.sum(band_irs[0, 0, :, :], axis=0)

        result = auralizer.auralize(ir, dry_signal_type="sine", dry_duration=0.1)
        self.assertIsInstance(result, AuralizationResult)
        self.assertEqual(result.fs, 8000)
        self.assertTrue(len(result.wet_signal) > len(result.dry_signal))

    def test_auralize_bands(self):
        auralizer = Auralizer(fs=8000)
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            max_order=1,
            adaptive_order=False,
            use_pra=False
        )
        sim = AcousticSimulator(room, fs=8000, use_gpu=False)
        sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
        sim.add_receiver(np.array([4.0, 3.0, 1.5]))
        band_irs = sim.compute_band_impulse_responses(max_order=1, duration=0.2)

        dry = auralizer.generate_dry_signal("pink_noise", duration=0.1)
        result = auralizer.auralize_bands(band_irs, dry, room.frequencies)
        self.assertIsInstance(result, AuralizationResult)
        self.assertTrue(len(result.wet_signal) > 0)

    def test_auralization_result_normalize(self):
        auralizer = Auralizer(fs=44100)
        dry = np.array([1.0, 0.5, 0.25])
        ir = np.array([1.0, 0.5])
        result = auralizer.auralize(ir, dry_signal=dry)
        result.wet_signal = result.wet_signal * 2.0
        result.normalize(target_peak=0.95)
        self.assertAlmostEqual(result.get_peak_amplitude(), 0.95, places=2)

    def test_auralization_result_gain(self):
        auralizer = Auralizer(fs=44100)
        dry = np.array([1.0, 0.5, 0.25])
        ir = np.array([1.0, 0.5])
        result = auralizer.auralize(ir, dry_signal=dry)
        peak_before = result.get_peak_amplitude()
        result.apply_master_gain(6.0)
        peak_after = result.get_peak_amplitude()
        self.assertAlmostEqual(peak_after, peak_before * 2.0, places=2)

    def test_save_and_load_wav(self):
        import tempfile
        import os
        auralizer = Auralizer(fs=22050)
        signal = auralizer.generate_dry_signal("sine", duration=0.1, frequency=1000.0)

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name

        try:
            auralizer.save_wav(temp_path, signal)
            self.assertTrue(os.path.exists(temp_path))

            loaded_signal, loaded_fs = auralizer.load_wav(temp_path)
            self.assertEqual(loaded_fs, 22050)
            self.assertEqual(len(loaded_signal), len(signal))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_apply_eq(self):
        auralizer = Auralizer(fs=44100)
        signal = auralizer.generate_dry_signal("sine", duration=0.1, frequency=1000.0)
        eq_settings = {1000.0: 6.0}
        result = auralizer.apply_eq(signal, eq_settings)
        self.assertEqual(len(result), len(signal))


class TestRoomOptimizer(unittest.TestCase):
    def test_optimizer_creation(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.2,
            use_pra=False
        )
        optimizer = RoomOptimizer(room)
        self.assertIsNotNone(optimizer)
        self.assertEqual(len(optimizer.wall_names), 6)

    def test_material_database(self):
        self.assertGreater(len(MATERIAL_DATABASE), 0)
        for name, material in MATERIAL_DATABASE.items():
            self.assertIsInstance(material, AbsorptionMaterial)
            self.assertEqual(len(material.absorption_coefficients), 7)
            self.assertTrue(0 <= material.cost_per_sqm < 1000)

    def test_get_absorption_at(self):
        material = MATERIAL_DATABASE["acoustic_foam_50mm"]
        abs_1000hz = material.get_absorption_at(1000.0)
        self.assertGreater(abs_1000hz, 0)
        self.assertLessEqual(abs_1000hz, 1.0)

    def test_analyze_room(self):
        room = RoomGeometry(
            dimensions=np.array([8.0, 6.0, 3.0]),
            absorption=0.1,
            use_pra=False
        )
        optimizer = RoomOptimizer(room)
        analysis = optimizer.analyze_room(room_type="studio")
        self.assertIsNotNone(analysis)
        self.assertIn(analysis.overall_grade, ["A", "B", "C", "D", "F"])
        self.assertEqual(len(analysis.rt60_current), 7)
        self.assertEqual(len(analysis.rt60_target), 7)

    def test_analyze_room_custom_target(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            use_pra=False
        )
        optimizer = RoomOptimizer(room)
        target_rt60 = np.array([0.5, 0.45, 0.4, 0.35, 0.35, 0.3, 0.3])
        analysis = optimizer.analyze_room(target_rt60=target_rt60)
        np.testing.assert_array_almost_equal(analysis.rt60_target, target_rt60)

    def test_generate_suggestions(self):
        room = RoomGeometry(
            dimensions=np.array([10.0, 8.0, 4.0]),
            absorption=0.05,
            use_pra=False
        )
        optimizer = RoomOptimizer(room)
        analysis = optimizer.analyze_room(room_type="studio")
        self.assertGreater(len(analysis.suggestions), 0)
        for s in analysis.suggestions:
            self.assertIn(s.suggested_material, MATERIAL_DATABASE)
            self.assertGreater(s.area_sqm, 0)
            self.assertGreaterEqual(s.priority, 1)

    def test_apply_suggestion(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.1,
            use_pra=False
        )
        optimizer = RoomOptimizer(room)
        analysis = optimizer.analyze_room()
        self.assertGreater(len(analysis.suggestions), 0)

        suggestion = analysis.suggestions[0]
        new_room = optimizer.apply_suggestion(suggestion)
        if suggestion.wall_index >= 0:
            avg_old = np.mean(room.absorption[suggestion.wall_index, :])
            avg_new = np.mean(new_room.absorption[suggestion.wall_index, :])
            self.assertGreaterEqual(avg_new, avg_old)

    def test_simulate_optimization(self):
        room = RoomGeometry(
            dimensions=np.array([8.0, 6.0, 3.0]),
            absorption=0.05,
            use_pra=False
        )
        optimizer = RoomOptimizer(room)
        analysis = optimizer.analyze_room(room_type="office")
        self.assertGreater(len(analysis.suggestions), 0)

        result = optimizer.simulate_optimization(analysis.suggestions)
        self.assertIn("current_rt60", result)
        self.assertIn("optimized_rt60", result)
        self.assertIn("improvement", result)
        self.assertIn("total_cost", result)
        self.assertTrue(np.all(result["improvement"] >= 0))

    def test_get_target_rt60_different_rooms(self):
        room = RoomGeometry(
            dimensions=np.array([6.0, 5.0, 3.0]),
            absorption=0.3,
            use_pra=False
        )
        optimizer = RoomOptimizer(room)
        room_types = ["studio", "concert_hall", "home_theater", "office", "classroom", "recording_booth", "general"]

        for rt in room_types:
            target = optimizer._get_target_rt60(rt)
            self.assertEqual(len(target), 7)
            self.assertTrue(np.all(target >= 0.1))
            self.assertTrue(np.all(target <= 5.0))

    def test_calculate_grade(self):
        room = RoomGeometry(
            dimensions=np.array([5.0, 4.0, 3.0]),
            absorption=0.5,
            use_pra=False
        )
        optimizer = RoomOptimizer(room)

        dev_a = np.ones(7) * 0.05
        grade_a = optimizer._calculate_grade(dev_a)
        self.assertEqual(grade_a, "A")

        dev_f = np.ones(7) * 2.0
        grade_f = optimizer._calculate_grade(dev_f)
        self.assertEqual(grade_f, "F")


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

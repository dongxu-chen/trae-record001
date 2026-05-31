#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
from gui import MainWindow
from PyQt5.QtWidgets import QApplication


def main():
    parser = argparse.ArgumentParser(description='Mesh Subdivision Tool')
    parser.add_argument('--no-gui', action='store_true', help='Run without GUI (for testing)')
    parser.add_argument('--test', action='store_true', help='Run subdivision tests')
    args = parser.parse_args()

    if args.test:
        run_tests()
    elif args.no_gui:
        print("Running in headless mode...")
        run_headless()
    else:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())


def run_tests():
    print("Running subdivision tests...")

    import numpy as np
    import openmesh as om
    from subdivision import LoopSubdivision, CatmullClarkSubdivision, MeshUtils

    print("\n=== Test 1: Loop Subdivision on Tetrahedron ===")
    mesh = MeshUtils.create_tetrahedron()
    info = MeshUtils.get_mesh_info(mesh)
    print(f"Original mesh: {info['n_vertices']} vertices, {info['n_faces']} faces")

    subdiv = LoopSubdivision(mesh)
    for i in range(1, 4):
        mesh = subdiv.subdivide(1)
        info = MeshUtils.get_mesh_info(mesh)
        print(f"Level {i}: {info['n_vertices']} vertices, {info['n_faces']} faces")

    print("\n=== Test 2: Catmull-Clark Subdivision on Cube ===")
    mesh = MeshUtils.create_cube()
    info = MeshUtils.get_mesh_info(mesh)
    print(f"Original mesh: {info['n_vertices']} vertices, {info['n_faces']} faces")

    subdiv = CatmullClarkSubdivision(mesh)
    for i in range(1, 4):
        mesh = subdiv.subdivide(1)
        info = MeshUtils.get_mesh_info(mesh)
        print(f"Level {i}: {info['n_vertices']} vertices, {info['n_faces']} faces")

    print("\n=== Test 3: Normal Computation ===")
    mesh = MeshUtils.create_octahedron()
    normals = MeshUtils.compute_vertex_normals(mesh)
    print(f"Computed {len(normals)} vertex normals")
    print(f"First normal: {normals[0]}")

    print("\n=== Test 4: Mesh Export ===")
    mesh = MeshUtils.create_tetrahedron()
    subdiv = LoopSubdivision(mesh)
    mesh = subdiv.subdivide(2)

    MeshUtils.export_obj(mesh, 'test_output.obj')
    MeshUtils.export_off(mesh, 'test_output.off')
    MeshUtils.export_ply(mesh, 'test_output.ply')
    print("Exported test mesh to: test_output.obj, test_output.off, test_output.ply")

    print("\n=== All tests completed successfully! ===")


def run_headless():
    import numpy as np
    import openmesh as om
    from subdivision import LoopSubdivision, CatmullClarkSubdivision, MeshUtils

    mesh = MeshUtils.create_tetrahedron()
    subdiv = LoopSubdivision(mesh)
    mesh = subdiv.subdivide(3)

    info = MeshUtils.get_mesh_info(mesh)
    print(f"Subdivided mesh: {info['n_vertices']} vertices, {info['n_faces']} faces")

    MeshUtils.export_obj(mesh, 'output.obj')
    print("Mesh exported to output.obj")


if __name__ == '__main__':
    main()

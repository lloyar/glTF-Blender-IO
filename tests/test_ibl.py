import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_IBL_MODULE_PATH = _REPOSITORY_ROOT / 'addons/io_scene_gltf2/blender/exp/ibl.py'
_IBL_SPEC = importlib.util.spec_from_file_location('gltf2_test_ibl', _IBL_MODULE_PATH)
ibl = importlib.util.module_from_spec(_IBL_SPEC)
_IBL_SPEC.loader.exec_module(ibl)


class IblTest(unittest.TestCase):

    def test_rejects_unsupported_platform(self):
        with mock.patch.object(ibl.sys, 'platform', 'linux'):
            with self.assertRaisesRegex(RuntimeError, 'only on macOS and Windows'):
                ibl.generate_ibl_maps('environment.hdr', 'output')

    def run_generator(self, platform):
        calls = []

        def run_tool(command, *, check, cwd, env):
            calls.append((command, check, cwd, env))
            output_path = command[command.index('-outCubeMap') + 1]
            Path(output_path).touch()

        with tempfile.TemporaryDirectory() as temp_dir:
            environment_path = os.path.join(temp_dir, 'environment.hdr')
            Path(environment_path).touch()

            with mock.patch.object(ibl.sys, 'platform', platform), \
                    mock.patch.object(ibl.subprocess, 'run', side_effect=run_tool), \
                    mock.patch.dict(ibl.os.environ, {'PATH': 'system-path'}, clear=True):
                diffuse_path, specular_path = ibl.generate_ibl_maps(environment_path, temp_dir)

        return calls, diffuse_path, specular_path

    def assert_common_invocation(self, calls, diffuse_path, specular_path):
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][calls[0][0].index('-distribution') + 1], 'Lambertian')
        self.assertEqual(calls[1][0][calls[1][0].index('-distribution') + 1], 'GGX')
        self.assertIn('-targetFormat', calls[0][0])
        self.assertIn('E5B9G9R9_UFLOAT_PACK32', calls[0][0])
        self.assertIn('-zstdLevel', calls[0][0])
        self.assertTrue(calls[0][1])
        self.assertEqual(calls[0][2], os.path.dirname(diffuse_path))
        self.assertEqual(os.path.basename(diffuse_path), 'env_diffuse_rgb9e5_zstd.ktx2')
        self.assertEqual(os.path.basename(specular_path), 'env_specular_rgb9e5_zstd.ktx2')

    def test_invokes_bundled_macos_tool(self):
        calls, diffuse_path, specular_path = self.run_generator('darwin')

        self.assert_common_invocation(calls, diffuse_path, specular_path)
        self.assertTrue(calls[0][0][0].startswith(ibl._MACOS_TOOLS_DIR))
        self.assertEqual(calls[0][3]['VK_DRIVER_FILES'], calls[0][3]['VK_ICD_FILENAMES'])
        self.assertTrue(calls[0][3]['DYLD_LIBRARY_PATH'].startswith(ibl._MACOS_TOOLS_DIR))

    def test_invokes_bundled_windows_tool(self):
        calls, diffuse_path, specular_path = self.run_generator('win32')

        self.assert_common_invocation(calls, diffuse_path, specular_path)
        self.assertEqual(calls[0][0][0], os.path.join(ibl._WINDOWS_TOOLS_DIR, 'bin', 'cli.exe'))
        self.assertTrue(calls[0][3]['PATH'].startswith(os.path.join(ibl._WINDOWS_TOOLS_DIR, 'bin')))
        self.assertNotIn('DYLD_LIBRARY_PATH', calls[0][3])
        self.assertNotIn('VK_DRIVER_FILES', calls[0][3])


if __name__ == '__main__':
    unittest.main()

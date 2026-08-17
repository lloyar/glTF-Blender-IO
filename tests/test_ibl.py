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
        with mock.patch.object(ibl.sys, 'platform', 'win32'):
            with self.assertRaisesRegex(RuntimeError, 'only on macOS'):
                ibl.generate_ibl_maps('environment.hdr', 'output')

    def test_invokes_bundled_tool_for_diffuse_and_specular_maps(self):
        calls = []

        def run_tool(command, *, check, cwd, env):
            calls.append((command, check, cwd, env))
            output_path = command[command.index('-outCubeMap') + 1]
            Path(output_path).touch()

        with tempfile.TemporaryDirectory() as temp_dir:
            environment_path = os.path.join(temp_dir, 'environment.hdr')
            Path(environment_path).touch()

            with mock.patch.object(ibl.sys, 'platform', 'darwin'), \
                    mock.patch.object(ibl.subprocess, 'run', side_effect=run_tool):
                diffuse_path, specular_path = ibl.generate_ibl_maps(environment_path, temp_dir)

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][calls[0][0].index('-distribution') + 1], 'Lambertian')
        self.assertEqual(calls[1][0][calls[1][0].index('-distribution') + 1], 'GGX')
        self.assertIn('-targetFormat', calls[0][0])
        self.assertIn('E5B9G9R9_UFLOAT_PACK32', calls[0][0])
        self.assertIn('-zstdLevel', calls[0][0])
        self.assertTrue(calls[0][0][0].startswith(ibl._MACOS_TOOLS_DIR))
        self.assertTrue(calls[0][1])
        self.assertEqual(calls[0][2], os.path.dirname(diffuse_path))
        self.assertEqual(calls[0][3]['VK_DRIVER_FILES'], calls[0][3]['VK_ICD_FILENAMES'])
        self.assertTrue(calls[0][3]['DYLD_LIBRARY_PATH'].startswith(ibl._MACOS_TOOLS_DIR))
        self.assertEqual(os.path.basename(diffuse_path), 'env_diffuse_rgb9e5_zstd.ktx2')
        self.assertEqual(os.path.basename(specular_path), 'env_specular_rgb9e5_zstd.ktx2')


if __name__ == '__main__':
    unittest.main()

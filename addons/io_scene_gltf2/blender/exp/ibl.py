# Copyright 2018-2021 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import subprocess
import sys


_TARGET_FORMAT = 'E5B9G9R9_UFLOAT_PACK32'
_ZSTD_LEVEL = '3'
_MACOS_TOOLS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'ibl_tools', 'macOS'))


def generate_ibl_maps(environment_path, output_dir):
    """Generate RGB9E5/Zstd diffuse and specular KTX2 cube maps on macOS."""
    if sys.platform != 'darwin':
        raise RuntimeError('Bundled IBL generation is currently supported only on macOS')

    environment_path = os.path.abspath(environment_path)
    output_dir = os.path.abspath(output_dir)
    if not os.path.isfile(environment_path):
        raise FileNotFoundError(f'IBL source image does not exist: {environment_path}')
    if not os.path.isdir(output_dir):
        raise NotADirectoryError(f'IBL output directory does not exist: {output_dir}')

    cli_path = os.path.join(_MACOS_TOOLS_DIR, 'bin', 'cli')
    icd_path = os.path.join(_MACOS_TOOLS_DIR, 'vulkan', 'share', 'vulkan', 'icd.d', 'MoltenVK_icd.json')
    library_dirs = (
        os.path.join(_MACOS_TOOLS_DIR, 'lib'),
        os.path.join(_MACOS_TOOLS_DIR, 'ktx', 'lib'),
        os.path.join(_MACOS_TOOLS_DIR, 'vulkan', 'lib'),
    )
    required_paths = (
        cli_path,
        os.path.join(library_dirs[0], 'libGltfIblSampler.dylib'),
        os.path.join(library_dirs[1], 'libktx.5.dylib'),
        os.path.join(library_dirs[2], 'libvulkan.1.dylib'),
        os.path.join(library_dirs[2], 'libMoltenVK.dylib'),
        icd_path,
    )
    missing_paths = [path for path in required_paths if not os.path.isfile(path)]
    if missing_paths:
        raise FileNotFoundError('Incomplete bundled macOS IBL tools: ' + ', '.join(missing_paths))
    if not os.access(cli_path, os.X_OK):
        raise PermissionError(f'Bundled IBL tool is not executable: {cli_path}')

    tool_env = os.environ.copy()
    inherited_library_path = tool_env.get('DYLD_LIBRARY_PATH')
    if inherited_library_path:
        library_dirs += (inherited_library_path,)
    tool_env['DYLD_LIBRARY_PATH'] = os.pathsep.join(library_dirs)
    tool_env['VK_DRIVER_FILES'] = icd_path
    tool_env['VK_ICD_FILENAMES'] = icd_path

    diffuse_path = os.path.join(output_dir, 'env_diffuse_rgb9e5_zstd.ktx2')
    specular_path = os.path.join(output_dir, 'env_specular_rgb9e5_zstd.ktx2')
    common_args = (
        '-inputPath', environment_path,
        '-targetFormat', _TARGET_FORMAT,
        '-zstdLevel', _ZSTD_LEVEL,
    )
    commands = (
        (
            cli_path,
            '-outCubeMap', diffuse_path,
            '-distribution', 'Lambertian',
            '-cubeMapResolution', '32',
            *common_args,
        ),
        (
            cli_path,
            '-outCubeMap', specular_path,
            '-distribution', 'GGX',
            '-cubeMapResolution', '512',
            *common_args,
        ),
    )

    try:
        for command in commands:
            subprocess.run(command, check=True, cwd=output_dir, env=tool_env)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f'Bundled IBL tool failed with exit code {error.returncode}') from error
    except OSError as error:
        raise RuntimeError(f'Unable to run bundled IBL tool: {error}') from error

    missing_outputs = [path for path in (diffuse_path, specular_path) if not os.path.isfile(path)]
    if missing_outputs:
        raise RuntimeError('Bundled IBL tool did not generate: ' + ', '.join(missing_outputs))

    return diffuse_path, specular_path

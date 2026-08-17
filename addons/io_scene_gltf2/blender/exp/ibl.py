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
_TOOLS_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'ibl_tools'))
_MACOS_TOOLS_DIR = os.path.join(_TOOLS_ROOT, 'macOS')
_WINDOWS_TOOLS_DIR = os.path.join(_TOOLS_ROOT, 'win')


def is_supported_platform():
    return sys.platform in ('darwin', 'win32')


def _prepend_environment_path(environment, key, paths):
    environment_key = next((current_key for current_key in environment if current_key.upper() == key), key)
    inherited_path = environment.get(environment_key)
    if inherited_path:
        paths += (inherited_path,)
    environment[environment_key] = os.pathsep.join(paths)


def _get_platform_tool():
    tool_env = os.environ.copy()

    if sys.platform == 'darwin':
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
        _prepend_environment_path(tool_env, 'DYLD_LIBRARY_PATH', library_dirs)
        tool_env['VK_DRIVER_FILES'] = icd_path
        tool_env['VK_ICD_FILENAMES'] = icd_path
        executable_permission_required = True
    elif sys.platform == 'win32':
        runtime_dir = os.path.join(_WINDOWS_TOOLS_DIR, 'bin')
        cli_path = os.path.join(runtime_dir, 'cli.exe')
        required_paths = (
            cli_path,
            os.path.join(runtime_dir, 'GltfIblSampler.dll'),
            os.path.join(runtime_dir, 'ktx.dll'),
        )
        _prepend_environment_path(tool_env, 'PATH', (runtime_dir,))
        executable_permission_required = False
    else:
        raise RuntimeError('Bundled IBL generation is supported only on macOS and Windows')

    missing_paths = [path for path in required_paths if not os.path.isfile(path)]
    if missing_paths:
        raise FileNotFoundError('Incomplete bundled IBL tools: ' + ', '.join(missing_paths))
    if executable_permission_required and not os.access(cli_path, os.X_OK):
        raise PermissionError(f'Bundled IBL tool is not executable: {cli_path}')

    return cli_path, tool_env


def generate_ibl_maps(environment_path, output_dir):
    """Generate RGB9E5/Zstd diffuse and specular KTX2 cube maps."""
    if not is_supported_platform():
        raise RuntimeError('Bundled IBL generation is supported only on macOS and Windows')

    environment_path = os.path.abspath(environment_path)
    output_dir = os.path.abspath(output_dir)
    if not os.path.isfile(environment_path):
        raise FileNotFoundError(f'IBL source image does not exist: {environment_path}')
    if not os.path.isdir(output_dir):
        raise NotADirectoryError(f'IBL output directory does not exist: {output_dir}')

    cli_path, tool_env = _get_platform_tool()

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

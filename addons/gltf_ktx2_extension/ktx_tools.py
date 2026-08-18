# Copyright 2024 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
KTX Tools Management

Handles downloading, extracting, and locating the KTX-Software command-line tools
for encoding and decoding KTX2 textures.
"""

import os
import sys
import platform
import subprocess
import tempfile
import shutil
import struct
from pathlib import Path

# KTX-Software version to download
KTX_VERSION = "4.4.2"

# Base URL for downloading
GITHUB_BASE = f"https://github.com/KhronosGroup/KTX-Software/releases/download/v{KTX_VERSION}"


def get_platform_info():
    """
    Detect the current platform and architecture.

    Returns:
        tuple: (os_name, arch) e.g. ('Linux', 'x86_64'), ('Windows', 'x64'), ('Darwin', 'arm64')
    """
    os_name = platform.system()  # 'Linux', 'Windows', 'Darwin'
    machine = platform.machine().lower()

    # Normalize architecture names
    if machine in ('x86_64', 'amd64'):
        arch = 'x86_64'
    elif machine in ('aarch64', 'arm64'):
        arch = 'arm64'
    else:
        arch = machine

    return os_name, arch


def get_download_info():
    """
    Get the download URL and archive type for the current platform.

    Returns:
        tuple: (url, archive_type, extract_subdir) or (None, None, None) if unsupported
    """
    os_name, arch = get_platform_info()

    # Use GitHub releases for more reliable downloads
    github_base = f"https://github.com/KhronosGroup/KTX-Software/releases/download/v{KTX_VERSION}"

    if os_name == 'Linux':
        if arch == 'x86_64':
            filename = f"KTX-Software-{KTX_VERSION}-Linux-x86_64.tar.bz2"
        elif arch == 'arm64':
            filename = f"KTX-Software-{KTX_VERSION}-Linux-arm64.tar.bz2"
        else:
            return None, None, None
        return f"{github_base}/{filename}", 'tar.bz2', f"KTX-Software-{KTX_VERSION}-Linux-{arch}"

    elif os_name == 'Windows':
        # Windows uses installer (.exe), need 7-Zip to extract
        if arch == 'x86_64':
            filename = f"KTX-Software-{KTX_VERSION}-Windows-x64.exe"
        elif arch == 'arm64':
            filename = f"KTX-Software-{KTX_VERSION}-Windows-arm64.exe"
        else:
            return None, None, None
        return f"{github_base}/{filename}", 'exe', None

    elif os_name == 'Darwin':
        if arch == 'x86_64':
            filename = f"KTX-Software-{KTX_VERSION}-Darwin-x86_64.pkg"
        elif arch == 'arm64':
            filename = f"KTX-Software-{KTX_VERSION}-Darwin-arm64.pkg"
        else:
            return None, None, None
        return f"{github_base}/{filename}", 'pkg', None

    return None, None, None


def get_tools_directory():
    """
    Get the directory where KTX tools should be stored.

    Returns:
        Path: Directory path for storing tools
    """
    # Store in the addon's directory
    addon_dir = Path(__file__).parent
    # addon_dir = Path("/usr/local")
    tools_dir = addon_dir / "bin"
    return tools_dir


def get_tool_path(tool_name):
    """
    Get the full path to a KTX tool executable.

    Args:
        tool_name: Name of the tool ('toktx', 'ktx', etc.)

    Returns:
        Path: Full path to the executable, or None if not found
    """
    tools_dir = get_tools_directory()
    os_name, _ = get_platform_info()

    if os_name == 'Windows':
        exe_name = f"{tool_name}.exe"
    else:
        exe_name = tool_name

    tool_path = tools_dir / exe_name

    if tool_path.exists() and os.access(tool_path, os.X_OK):
        return tool_path

    return None


def are_tools_installed():
    """
    Check if the required KTX tools are installed.

    Returns:
        bool: True if tools are available
    """
    toktx = get_tool_path('ktx')
    return toktx is not None


def download_file(url, dest_path, progress_callback=None):
    """
    Download a file from URL to destination path.

    Args:
        url: URL to download from
        dest_path: Destination file path
        progress_callback: Optional callback(bytes_downloaded, total_bytes)

    Returns:
        bool: True if successful
    """
    import urllib.request
    import urllib.error
    import ssl

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ssl_context = ssl.create_default_context()
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': '*/*',
        }
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request, timeout=120, context=ssl_context)

        content_type = response.getheader('Content-Type', '')
        if 'text/html' in content_type.lower():
            print(f"Received HTML instead of binary (Content-Type: {content_type})")
            response.close()
            return False

        total_size = response.getheader('Content-Length')
        total_size = int(total_size) if total_size else None

        print(f"Downloading {total_size // 1024 // 1024 if total_size else '?'}MB...")

        downloaded = 0
        chunk_size = 65536

        with open(dest_path, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size:
                    progress_callback(downloaded, total_size)

        response.close()

        # Verify we got a valid file (not HTML)
        with open(dest_path, 'rb') as f:
            header = f.read(16)
            if header.startswith(b'<!') or header.startswith(b'<html') or header.startswith(b'<HTML'):
                print("Downloaded file appears to be HTML, not the expected archive")
                return False
            if str(dest_path).endswith('.tar.bz2') and not header.startswith(b'BZ'):
                print(f"Downloaded file does not appear to be bzip2 (header: {header[:4]})")
                return False

        print(f"Download complete: {downloaded // 1024}KB")
        return True

    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        return False

    except (urllib.error.URLError, OSError) as e:
        print(f"Download failed: {e}")
        return False


def extract_linux_archive(archive_path, tools_dir):
    """Extract tools from Linux tar.bz2 archive."""
    import tarfile

    tools_dir.mkdir(parents=True, exist_ok=True)

    # Create lib subdirectory for shared libraries
    lib_dir = tools_dir / 'lib'
    lib_dir.mkdir(parents=True, exist_ok=True)

    extracted_libs = []

    with tarfile.open(archive_path, 'r:bz2') as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue

            filename = os.path.basename(member.name)

            # Extract executables from bin directory
            if '/bin/' in member.name:
                if filename in ('toktx', 'ktx', 'ktxsc', 'ktxinfo'):
                    tar.extract(member, path=tools_dir.parent)
                    extracted_path = tools_dir.parent / member.name
                    dest_path = tools_dir / filename
                    shutil.move(str(extracted_path), str(dest_path))
                    os.chmod(dest_path, 0o755)
                    print(f"[KTX2] Extracted: {filename}")

            # Extract shared libraries from lib directory
            elif '/lib/' in member.name:
                if filename.startswith('libktx') and '.so' in filename:
                    tar.extract(member, path=tools_dir.parent)
                    extracted_path = tools_dir.parent / member.name
                    dest_path = lib_dir / filename
                    shutil.move(str(extracted_path), str(dest_path))
                    extracted_libs.append(filename)
                    print(f"[KTX2] Extracted library: {filename}")

    # Create symlinks for versioned libraries
    # e.g., libktx.so.4.4.2 -> libktx.so.4 -> libktx.so
    for lib_file in extracted_libs:
        lib_path = lib_dir / lib_file

        # Parse version from filename like libktx.so.4.4.2
        if '.so.' in lib_file:
            base_name = lib_file.split('.so.')[0]  # e.g., 'libktx'
            version = lib_file.split('.so.')[1]  # e.g., '4.4.2'

            # Create major version symlink (libktx.so.4 -> libktx.so.4.4.2)
            major_version = version.split('.')[0]
            major_symlink = lib_dir / f"{base_name}.so.{major_version}"
            if not major_symlink.exists():
                os.symlink(lib_file, major_symlink)
                print(f"[KTX2] Created symlink: {major_symlink.name} -> {lib_file}")

            # Create base symlink (libktx.so -> libktx.so.4.4.2)
            base_symlink = lib_dir / f"{base_name}.so"
            if not base_symlink.exists():
                os.symlink(lib_file, base_symlink)
                print(f"[KTX2] Created symlink: {base_symlink.name} -> {lib_file}")

    # Clean up extracted directories
    for item in tools_dir.parent.iterdir():
        if item.is_dir() and item.name.startswith('KTX-Software'):
            shutil.rmtree(item, ignore_errors=True)

    return True


# Direct download for the standalone reduced 7-Zip extractor (~600KB).
# Only handles .7z archives, but enough to bootstrap the full 7za.exe.
SEVEN_ZR_URL = "https://www.7-zip.org/a/7zr.exe"

# 7-Zip "extras" archive contains the standalone 7za.exe needed to extract
# the NSIS installer. Versioned URL — when 7-Zip releases a new version,
# old URLs 404, so we try a list of known versions newest-first.
SEVEN_ZIP_EXTRA_VERSIONS = ["2501", "2500", "2409", "2408", "2407"]


def find_system_7zip():
    """Locate an already-installed 7-Zip executable. Returns path or None."""
    candidates = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    for name in ("7z", "7za"):
        found = shutil.which(name)
        if found:
            return found
    return None


def ensure_7zip_available(progress_callback=None):
    """
    Find or download a 7-Zip executable capable of extracting NSIS installers.

    Strategy:
      1. Use a system-installed 7-Zip if present.
      2. Use a previously-cached 7za.exe in the addon's bin directory.
      3. Bootstrap: download 7zr.exe, then download the 7-Zip extras .7z and
         use 7zr to unpack 7za.exe out of it. Cache the result.

    Returns:
        str | None: Path to a 7-Zip executable, or None if unavailable.
    """
    sys_7z = find_system_7zip()
    if sys_7z:
        return sys_7z

    tools_dir = get_tools_directory()
    cached_7za = tools_dir / "7za.exe"
    if cached_7za.is_file():
        return str(cached_7za)

    if progress_callback:
        progress_callback("7-Zip not found - downloading portable 7-Zip...", 50)

    tools_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_dir = tools_dir / "_7zip_bootstrap"
    if bootstrap_dir.exists():
        shutil.rmtree(bootstrap_dir, ignore_errors=True)
    bootstrap_dir.mkdir(parents=True, exist_ok=True)

    seven_zr = bootstrap_dir / "7zr.exe"
    if not download_file(SEVEN_ZR_URL, seven_zr):
        print("[KTX2] Failed to download 7zr.exe")
        return None

    # The 7-Zip extras archive is versioned and old versions 404 when a new
    # release ships, so try newest-first.
    extra_archive = bootstrap_dir / "7z-extra.7z"
    extras_downloaded = False
    for version in SEVEN_ZIP_EXTRA_VERSIONS:
        url = f"https://www.7-zip.org/a/7z{version}-extra.7z"
        print(f"[KTX2] Trying {url}")
        if download_file(url, extra_archive):
            extras_downloaded = True
            break

    if not extras_downloaded:
        print("[KTX2] Could not download any 7-Zip extras archive")
        return None

    try:
        result = subprocess.run(
            [str(seven_zr), "x", str(extra_archive), f"-o{bootstrap_dir}", "-y"],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"[KTX2] 7zr extraction failed: {result.stderr.decode(errors='replace')}")
            return None
    except (subprocess.SubprocessError, OSError) as e:
        print(f"[KTX2] Failed to run 7zr: {e}")
        return None

    extracted_7za = next(bootstrap_dir.rglob("7za.exe"), None)
    if not extracted_7za:
        print("[KTX2] 7za.exe not found inside extras archive")
        return None

    shutil.copy2(extracted_7za, cached_7za)
    shutil.rmtree(bootstrap_dir, ignore_errors=True)
    print(f"[KTX2] Cached portable 7-Zip at {cached_7za}")
    return str(cached_7za)


def extract_windows_installer(installer_path, tools_dir, progress_callback=None):
    """Extract KTX tools from the Khronos Windows NSIS installer."""
    tools_dir.mkdir(parents=True, exist_ok=True)

    seven_zip = ensure_7zip_available(progress_callback)
    if not seven_zip:
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            result = subprocess.run(
                [seven_zip, 'x', str(installer_path), f'-o{tmpdir}', '-y'],
                capture_output=True,
                timeout=120,
            )
            if result.returncode != 0:
                print(f"[KTX2] 7-Zip extraction failed: {result.stderr.decode(errors='replace')}")
                return False

            for root, dirs, files in os.walk(tmpdir):
                for filename in files:
                    if filename in ('toktx.exe', 'ktx.exe', 'ktxsc.exe', 'ktxinfo.exe'):
                        src = Path(root) / filename
                        dst = tools_dir / filename
                        shutil.copy2(src, dst)
                    elif filename.lower().endswith('.dll'):
                        src = Path(root) / filename
                        dst = tools_dir / filename
                        shutil.copy2(src, dst)

            return (tools_dir / 'toktx.exe').exists()
        except subprocess.SubprocessError as e:
            print(f"[KTX2] Failed to run 7-Zip: {e}")
            return False


def extract_macos_package(pkg_path, tools_dir):
    """Extract tools from macOS .pkg file."""
    tools_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        try:
            # Expand the pkg
            subprocess.run(
                ['pkgutil', '--expand', str(pkg_path), str(tmpdir / 'expanded')],
                capture_output=True,
                check=True,
                timeout=60
            )

            # Find and extract the payload
            payload_path = tmpdir / 'expanded' / 'ktx-tools.pkg' / 'Payload'
            if not payload_path.exists():
                # Try alternative structure
                for p in (tmpdir / 'expanded').rglob('Payload'):
                    payload_path = p
                    break

            if payload_path.exists():
                # Extract payload (it's a cpio archive, possibly gzipped)
                extract_dir = tmpdir / 'extracted'
                extract_dir.mkdir()

                # Try gunzip + cpio
                try:
                    with subprocess.Popen(
                            ['gunzip', '-c', str(payload_path)],
                            stdout=subprocess.PIPE
                    ) as gunzip:
                        subprocess.run(
                            ['cpio', '-id'],
                            stdin=gunzip.stdout,
                            cwd=str(extract_dir),
                            capture_output=True,
                            timeout=60
                        )
                except FileNotFoundError:
                    # gunzip not available, try with Python gzip
                    import gzip
                    with gzip.open(payload_path, 'rb') as f:
                        # This is more complex, skip for now
                        pass

                # Find and copy tools
                for root, dirs, files in os.walk(extract_dir):
                    for filename in files:
                        if filename in ('toktx', 'ktx', 'ktxsc', 'ktxinfo'):
                            src = Path(root) / filename
                            dst = tools_dir / filename
                            shutil.copy2(src, dst)
                            os.chmod(dst, 0o755)

                return (tools_dir / 'toktx').exists()

        except subprocess.SubprocessError as e:
            print(f"Failed to extract macOS package: {e}")

    return False


def install_tools(progress_callback=None):
    """
    Download and install KTX tools for the current platform.

    Args:
        progress_callback: Optional callback(status_message, progress_percent)

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    os_name, arch = get_platform_info()
    url, archive_type, _ = get_download_info()

    if url is None:
        return False, f"Unsupported platform: {os_name} {arch}"

    tools_dir = get_tools_directory()

    # Create temp directory for download
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        archive_path = tmpdir / f"ktx_tools.{archive_type}"

        # Download
        if progress_callback:
            progress_callback("Downloading KTX tools...", 0)

        def download_progress(downloaded, total):
            if progress_callback:
                percent = int(downloaded / total * 50)  # Download is 0-50%
                progress_callback(f"Downloading... {downloaded // 1024 // 1024}MB", percent)

        if not download_file(url, archive_path, download_progress):
            return False, "Failed to download KTX tools. Check your internet connection."

        # Extract
        if progress_callback:
            progress_callback("Extracting tools...", 50)

        try:
            if archive_type == 'tar.bz2':
                success = extract_linux_archive(archive_path, tools_dir)
            elif archive_type == 'exe':
                success = extract_windows_installer(archive_path, tools_dir, progress_callback)
            elif archive_type == 'pkg':
                success = extract_macos_package(archive_path, tools_dir)
            else:
                return False, f"Unknown archive type: {archive_type}"

            if not success:
                return False, "Failed to extract KTX tools from archive."

        except Exception as e:
            return False, f"Extraction failed: {str(e)}"

    # Verify installation
    if progress_callback:
        progress_callback("Verifying installation...", 90)

    if not are_tools_installed():
        return False, "Tools were extracted but verification failed."

    if progress_callback:
        progress_callback("Installation complete!", 100)

    return True, None


def get_tool_environment():
    """
    Get environment variables for running KTX tools.

    Sets LD_LIBRARY_PATH (Linux) or PATH (Windows) to include the lib directory.
    """
    env = os.environ.copy()
    tools_dir = get_tools_directory()
    lib_dir = tools_dir / 'lib'

    os_name, _ = get_platform_info()

    if os_name == 'Linux':
        # Add lib directory to LD_LIBRARY_PATH
        current_ld_path = env.get('LD_LIBRARY_PATH', '')
        if current_ld_path:
            env['LD_LIBRARY_PATH'] = f"{lib_dir}:{current_ld_path}"
        else:
            env['LD_LIBRARY_PATH'] = str(lib_dir)
    elif os_name == 'Windows':
        # Add tools and lib directories to PATH for DLLs
        current_path = env.get('PATH', '')
        env['PATH'] = f"{tools_dir};{lib_dir};{current_path}"
    elif os_name == 'Darwin':
        # Add lib directory to DYLD_LIBRARY_PATH
        current_dyld_path = env.get('DYLD_LIBRARY_PATH', '')
        if current_dyld_path:
            env['DYLD_LIBRARY_PATH'] = f"{lib_dir}:{current_dyld_path}"
        else:
            env['DYLD_LIBRARY_PATH'] = str(lib_dir)

    return env


def get_image_dimensions(image_path):
    """Read the dimensions of a PNG or JPEG without external dependencies."""
    try:
        with open(image_path, 'rb') as image_file:
            header = image_file.read(24)

            if header.startswith(b'\x89PNG\r\n\x1a\n') and header[12:16] == b'IHDR':
                return struct.unpack('>II', header[16:24])

            if header[:2] != b'\xff\xd8':
                return None

            image_file.seek(2)
            start_of_frame_markers = {
                0xC0, 0xC1, 0xC2, 0xC3,
                0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB,
                0xCD, 0xCE, 0xCF,
            }

            while True:
                marker_prefix = image_file.read(1)
                while marker_prefix and marker_prefix != b'\xff':
                    marker_prefix = image_file.read(1)
                if not marker_prefix:
                    return None

                marker_data = image_file.read(1)
                while marker_data == b'\xff':
                    marker_data = image_file.read(1)
                if not marker_data:
                    return None

                marker = marker_data[0]
                if marker == 0x00:
                    continue
                if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                    continue

                segment_length_data = image_file.read(2)
                if len(segment_length_data) != 2:
                    return None
                segment_length = struct.unpack('>H', segment_length_data)[0]
                if segment_length < 2:
                    return None

                if marker in start_of_frame_markers:
                    frame_header = image_file.read(5)
                    if len(frame_header) != 5:
                        return None
                    height, width = struct.unpack('>HH', frame_header[1:5])
                    return width, height

                image_file.seek(segment_length - 2, os.SEEK_CUR)
    except (OSError, struct.error):
        return None


def get_astc_aligned_dimensions(image_path, block_size, scale=1.0):
    """Calculate ASTC-compatible dimensions after applying the requested scale."""
    try:
        block_width, block_height = (int(value) for value in block_size.lower().split('x', 1))
    except (AttributeError, TypeError, ValueError):
        return None

    if block_width <= 0 or block_height <= 0 or scale <= 0:
        return None

    source_dimensions = get_image_dimensions(image_path)
    if source_dimensions is None:
        return None

    source_width, source_height = source_dimensions
    scaled_width = max(1, int(source_width * scale))
    scaled_height = max(1, int(source_height * scale))
    aligned_width = ((scaled_width + block_width - 1) // block_width) * block_width
    aligned_height = ((scaled_height + block_height - 1) // block_height) * block_height

    return source_dimensions, (scaled_width, scaled_height), (aligned_width, aligned_height)


def run_toktx(input_path, output_path, options=None):
    """
    Run the toktx tool to convert an image to KTX2.

    Args:
        input_path: Path to input image (PNG, JPEG, etc.)
        output_path: Path for output KTX2 file
        options: Dict of options:
            - target_format: 'BASISU' or 'ASTC'
            - format: 'ETC1S' or 'UASTC' (for BASISU)
            - quality: 1-255 for ETC1S, 0-4 for UASTC
            - compression: 0-5 for ETC1S, 1-22 for UASTC
            - mipmaps: bool
            - astc_block_size: '4x4', '5x5', '6x6', '8x8' (for ASTC)
            - oetf: Transfer function (linear|srgb)
            - target_type: Target type (R, RG, RGB, RGBA)
            - resize: Optional explicit (width, height) passed to ktx create

    Returns:
        tuple: (success: bool, error_message: str or None)

    Notes on target formats:
        - BASISU: Basis Universal (ETC1S or UASTC) - universal, transcodes at runtime
                  to any GPU format (BC7, ASTC, ETC2, etc.)
        - ASTC: Native ASTC format - direct GPU upload on ASTC-capable hardware
                (mobile devices, Apple Silicon). No transcoding needed.
    """
    toktx_path = get_tool_path('ktx')
    if not toktx_path:
        return False, "toktx tool not found. Please install KTX tools first."

    options = options or {}

    cmd = [str(toktx_path)]
    cmd.extend(['create'])

    target_format = options.get('target_format', 'ASTC')

    if target_format == 'ASTC':
        # ktx create --assign-tf srgb --format ASTC_8x8_SRGB_BLOCK ./tmpbgh6p111.png ./output.ktx2 --zstd 3 --astc-quality medium
        # Native ASTC compression - direct GPU upload on ASTC hardware
        # --assign-tf srgb --assign-primaries bt709
        # --assign-tf linear --assign-primaries none

        block_size = options.get('astc_block_size', '8x8')
        if options.get('oetf', 'srgb') == 'linear':
            cmd.extend(['--assign-primaries', 'none', '--format', f'ASTC_{block_size}_UNORM_BLOCK'])
        else:
            cmd.extend(['--assign-primaries', 'bt709', '--format', f'ASTC_{block_size}_SRGB_BLOCK'])

        # cmd.extend(['--encode', 'astc'])
        # cmd.extend(['--astc_blk_d', block_size])
        cmd.extend(['--astc-quality', 'medium'])
        compression = options.get('compression', 3)
        cmd.extend(['--zstd', str(compression)])
    else:
        # Basis Universal (ETC1S or UASTC) - universal format
        # Can be transcoded to BC7, ASTC, ETC2, etc. at runtime
        fmt = options.get('format', 'ETC1S')
        if fmt == 'UASTC':
            cmd.extend(['--encode', 'uastc'])
            quality = options.get('quality', 2)
            cmd.extend(['--uastc_quality', str(quality)])
            compression = options.get('compression', 3)
            cmd.extend(['--zcmp', str(compression)])
        else:
            # ETC1S (default)
            cmd.extend(['--encode', 'etc1s'])
            quality = options.get('quality', 128)
            cmd.extend(['--qlevel', str(quality)])
            compression = options.get('compression', 1)
            cmd.extend(['--clevel', str(compression)])

    # Transfer function
    oetf = options.get('oetf', 'srgb')
    cmd.extend(['--assign-tf', oetf])

    # # # Target type
    # target_type = options.get('target_type', 'RGBA')
    # cmd.extend(['--target_type', target_type])

    # Resize native ASTC textures to block-aligned dimensions. Passing exact dimensions
    # also incorporates the user-selected downsample factor in a single resampling step.
    resize = options.get('resize')
    if resize is not None:
        width, height = resize
        cmd.extend(['--width', str(width), '--height', str(height)])
    else:
        scale = options.get('scale', 1.0)
        cmd.extend(['--scale', str(scale)])

    # Mipmaps
    if options.get('mipmaps', False):
        cmd.append('--generate-mipmap')


    # Output and input
    cmd.append(str(input_path))
    cmd.append(str(output_path))

    print(cmd)

    try:
        env = get_tool_environment()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env
        )

        if result.returncode != 0:
            return False, f"toktx failed: {result.stderr}"

        return True, None

    except subprocess.TimeoutExpired:
        return False, "toktx timed out"
    except Exception as e:
        return False, f"Failed to run toktx: {str(e)}"


def run_ktx_extract(input_path, output_path):
    """
    Run the ktx tool to extract/transcode a KTX2 file to PNG.

    Args:
        input_path: Path to input KTX2 file
        output_path: Path for output PNG file

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    ktx_path = get_tool_path('ktx')
    if not ktx_path:
        return False, "ktx tool not found. Please install KTX tools first."

    cmd = [
        str(ktx_path),
        'extract',
        str(input_path),
        str(output_path)
    ]

    try:
        env = get_tool_environment()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=120
        )

        if result.returncode != 0:
            return False, f"ktx extract failed: {result.stderr}"

        return True, None

    except subprocess.TimeoutExpired:
        return False, "ktx extract timed out"
    except Exception as e:
        return False, f"Failed to run ktx: {str(e)}"

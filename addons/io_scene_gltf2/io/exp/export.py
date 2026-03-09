# Copyright 2018-2021 The glTF-Blender-IO authors.
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

#
# Imports
#

import json
import struct
from ...io.exp.user_extensions import export_user_extensions

#
# Globals
#

#
# Functions
#
from collections import OrderedDict


def save_gltf(gltf, export_settings, encoder, glb_buffer):
    # Use a class here, to be able to pass data by reference to hook (to be able to change them inside hook)
    class GlTF_format:
        def __init__(self, indent, separators):
            self.indent = indent
            self.separators = separators

    gltf_format = GlTF_format(None, (',', ':'))

    if export_settings['gltf_format'] != 'GLB':
        gltf_format.indent = "\t"
        # The comma is typically followed by a newline, so no trailing whitespace is needed on it.
        # No space before and after ':' to save space
        gltf_format.separators = (',', ':')

    sort_order = [
        "asset",
        "extensionsUsed",
        "extensionsRequired",
        "extensions",
        "extras",
        "scene",
        "scenes",
        "nodes",
        "cameras",
        "animations",
        "materials",
        "meshes",
        "textures",
        "images",
        "skins",
        "accessors",
        "bufferViews",
        "samplers",
        "buffers"
    ]

    export_user_extensions('gather_gltf_encoded_hook', export_settings, gltf_format, sort_order)

    gltf_ordered = OrderedDict(sorted(gltf.items(), key=lambda item: sort_order.index(item[0])))
    gltf_encoded = json.dumps(
        gltf_ordered,
        ensure_ascii=False,
        indent=gltf_format.indent,
        separators=gltf_format.separators,
        cls=encoder,
        allow_nan=False)

    #

    if export_settings['gltf_format'] != 'GLB':
        file = open(export_settings['gltf_filepath'], "w", encoding="utf8", newline="\n")
        file.write(gltf_encoded)
        file.write("\n")
        file.close()

        binary = export_settings['gltf_binary']
        if len(binary) > 0 and not export_settings['gltf_embed_buffers']:
            file = open(export_settings['gltf_filedirectory'] + export_settings['gltf_binaryfilename'], "wb")
            file.write(binary)
            file.close()

    else:
        gltf_data = gltf_encoded.encode()
        binary = glb_buffer

        length_gltf = len(gltf_data)
        spaces_gltf = (4 - (length_gltf & 3)) & 3
        length_gltf += spaces_gltf

        length_bin = len(binary)
        zeros_bin = (4 - (length_bin & 3)) & 3
        length_bin += zeros_bin

        length = 12 + 8 + length_gltf
        if length_bin > 0:
            length += 8 + length_bin

        # Build the full GLB payload first, then write once.
        glb_data = bytearray()

        # Header (Version 2)
        glb_data.extend(struct.pack("I", 20 + length_gltf))
        glb_data.extend(struct.pack("I", length_bin))
        # glb_data.extend('glTF'.encode())
        # glb_data.extend(struct.pack("I", 2))
        glb_data.extend(struct.pack("I", length))

        # Chunk 0 (JSON)
        glb_data.extend(struct.pack("I", length_gltf))
        glb_data.extend(b'JSON')
        glb_data.extend(gltf_data)
        glb_data.extend(b' ' * spaces_gltf)

        _xor_encrypt(glb_data)

        # Chunk 1 (BIN)
        if length_bin > 0:
            glb_data.extend(struct.pack("I", length_bin))
            glb_data.extend(b'BIN\0')
            glb_data.extend(binary)
            glb_data.extend(b'\0' * zeros_bin)

        with open(export_settings['gltf_filepath'].replace('glb', 'dsm'), "wb") as file:
            file.write(glb_data)

    return True


def _xor_encrypt(data: bytearray):
    key_bytes = b"pA0+sP9|gR1&wO7;kS3!oU2{gC2/xS1?vN4<eL8+rM6.jE5.eC9-eI3,aI1%rB3,sH9$jP2;hY2{aO3#zV0!dX7#yF3,eO7/eS3@pM8%hD7}dZ0,lS9(mQ4~aL6]eK5*xY2#rR5?kB7=lO3)pN8?iN1`bD7)pY0<yV2&nX8[gK0~mW5]jF6(rI4]tN2_eL8.xU7}kV6$gD6(pW3!qD2?pI7)gN2)oA2/dA6`pM6=rG6?aZ5;xH3>lX3/yE9#dS3="
    key_len = len(key_bytes)
    for i, b in enumerate(data):
        data[i] = b ^ key_bytes[i % key_len]

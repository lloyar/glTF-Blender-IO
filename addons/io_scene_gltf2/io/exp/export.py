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
    key_bytes = b"wjr~_v9Hs2bB!Dn*HNIeUd@W%+c^^*swgbkkbtA%vmFp!t*xhZ_tsaIp74ZIY9N1yUJq)mARvtSY^WxfwKQRLZPf7NZlZ%^5iA(ydkqr6YSW%$2wNYUQwtvi6sh*vkJpCTtijsZGoqoG!!ZW!jKAgnqbJN*HdMqZH~z+Gs3lW24u+to2gT0i8Cu8d_n+_#RrM*Qi!_t~gws6_&J1MrFC8o%1)qGyY6nmMk9Eu0uHFYQA)0PY$7K%INF4nE8gh3PY(#Ks8DWgaqEkP5tXDzAwzBnR1YN9RF@rv)HNQ5_3&1JkqrW2x1zb1~(!OmJMv8qqXHBLn3h3Edg9VOH_C1jWsy6!yPPldkm00~HsGocy5)1t48F$@6qhI^C*@Sazf7sUVeb0PFBeQCfdLAIeNBU4OQ$RzC6#n*DPQzmTfO(u+RFJmU^mnNxmOyrAWPcVoG%xc~bnX+I)Itm9ikc@tgalCW8hAS0~l!7mRt$1^bFb7@36%81oQYQjK5ZOSMB9P~JJcBv9t!iHgk22KRd+Rtw*L8q2(b4Dl#kk&QMvQ$NzNxl#DmSR"
    key_len = len(key_bytes)
    for i, b in enumerate(data):
        data[i] = b ^ key_bytes[i % key_len]

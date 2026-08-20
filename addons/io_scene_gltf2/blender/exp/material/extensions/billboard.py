# Copyright 2018-2022 The glTF-Blender-IO authors.
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

from .....io.com.gltf2_io_extensions import Extension
from ..search_node_tree import has_ds_billboard_node


DS_MATERIALS_BILLBOARD_EXTENSION_NAME = "DS_materials_billboard"


def export_billboard(blender_material):
    if not has_ds_billboard_node(blender_material.node_tree):
        return None

    return Extension(DS_MATERIALS_BILLBOARD_EXTENSION_NAME, {}, required=False)

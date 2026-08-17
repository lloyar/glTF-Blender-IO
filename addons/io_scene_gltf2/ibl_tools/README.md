# Bundled IBL tools

The exporter currently enables bundled IBL generation on macOS only. The Python runner is
`blender/exp/ibl.py` and expects this runtime layout:

```text
macOS/
├── bin/cli
├── lib/libGltfIblSampler.dylib
├── ktx/lib/libktx.5.dylib
└── vulkan/
    ├── lib/libvulkan.1.dylib
    ├── lib/libMoltenVK.dylib
    └── share/vulkan/icd.d/MoltenVK_icd.json
```

The runner prepends these local library directories to `DYLD_LIBRARY_PATH` and explicitly selects the bundled
MoltenVK manifest. The sampler library also has loader-relative rpaths, so it does not depend on a system KTX or
Vulkan SDK installation at runtime.

The CLI directly writes RGB9E5 KTX2 cube maps with Zstd supercompression. No post-processing converter is used.
Windows is intentionally disabled until a compatible build of the same tool is added.

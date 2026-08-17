# Bundled IBL tools

The exporter enables bundled IBL generation on macOS and Windows. The Python runner is
`blender/exp/ibl.py` and expects these runtime layouts:

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

```text
win/
└── bin/
    ├── cli.exe
    ├── GltfIblSampler.dll
    └── ktx.dll
```

The runner prepends these local library directories to `DYLD_LIBRARY_PATH` and explicitly selects the bundled
MoltenVK manifest. The sampler library also has loader-relative rpaths, so it does not depend on a system KTX or
Vulkan SDK installation at runtime.

On Windows, all required sampler and KTX runtime files are colocated with `cli.exe`. The runner prepends that
directory to `PATH`; Vulkan is provided by the system GPU driver/runtime.

The CLI directly writes RGB9E5 KTX2 cube maps with Zstd supercompression. No post-processing converter is used.

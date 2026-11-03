"""One-shot probe: can this workspace launch a T4 GPU container at all?

Reuses the pilot image so the build hits the cache. Fails fast and cheap if the
workspace has no payment method on file.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import modal  # noqa: E402

from modal_pilot import image  # noqa: E402

app = modal.App('apart-gpu-probe')


@app.function(image=image, gpu='T4', timeout=120, max_containers=1, retries=0)
def probe():
    import torch
    return {'gpu': torch.cuda.get_device_name(0),
            'torch': torch.__version__,
            'cuda': torch.version.cuda,
            'vram_gb': round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)}


@app.local_entrypoint()
def main():
    try:
        print('PROBE_OK', probe.remote())
    except Exception as exc:                     # report the exact blocker, do not retry
        print('PROBE_FAILED', type(exc).__name__, str(exc))

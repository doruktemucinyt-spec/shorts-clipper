"""Pipeline paketi. Import edilince iki Windows sorununu bastan cozer.

1) TLS: Bu makinede araya giren bir guvenlik yazilimi var; kok sertifikasi
   Windows sertifika deposunda kayitli ama certifi paketinde yok. truststore
   Python'u Windows deposunu kullanmaya zorlar (yoksa yt-dlp ve model
   indirmeleri SSL hatasi verir).

2) CUDA: pip ile gelen nvidia-cublas / nvidia-cudnn DLL'leri
   site-packages/nvidia/*/bin altina kuruluyor ama Windows'un DLL arama
   yolunda olmadigi icin ctranslate2 "cublas64_12.dll bulunamadi" der.
   add_dll_directory ile bu klasorleri kaydediyoruz.
"""
import os
import site
from pathlib import Path

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass


def _register_cuda_dlls() -> list:
    roots = list(site.getsitepackages())
    try:
        roots.append(site.getusersitepackages())
    except Exception:
        pass

    added = []
    for root in roots:
        base = Path(root) / "nvidia"
        if not base.is_dir():
            continue
        for bindir in sorted(base.glob("*/bin")):
            if not bindir.is_dir():
                continue
            try:
                os.add_dll_directory(str(bindir))
                added.append(str(bindir))
            except Exception:
                continue
    if added:
        os.environ["PATH"] = os.pathsep.join(added) + os.pathsep + os.environ.get("PATH", "")
    return added


CUDA_DLL_DIRS = _register_cuda_dlls()

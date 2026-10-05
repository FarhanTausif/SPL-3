"""Small, explicit API catalogs. Absence is not contradiction in partial catalogs."""
from __future__ import annotations
from functools import lru_cache
import time
import sys
from urllib.parse import quote
import httpx

VERSION = "2026.1"
# Allowed keywords and positional arity for selected stable APIs; None means unknown.
APIS = {
    "python": {
        "json.dumps": (1, 1, ["skipkeys", "ensure_ascii", "check_circular", "allow_nan", "cls", "indent", "separators", "default", "sort_keys"]),
        "json.loads": (1, 1, ["cls", "object_hook", "parse_float", "parse_int", "parse_constant", "object_pairs_hook"]),
        "json.dump": (2, 2, ["skipkeys", "ensure_ascii", "check_circular", "allow_nan", "cls", "indent", "separators", "default", "sort_keys"]),
        "json.load": (1, 1, ["cls", "object_hook", "parse_float", "parse_int", "parse_constant", "object_pairs_hook"]),
        "math.sqrt": (1, 1, []), "math.floor": (1, 1, []), "math.ceil": (1, 1, []),
        "math.sin": (1, 1, []), "math.cos": (1, 1, []), "math.pow": (2, 2, []),
        "os.getcwd": (0, 0, []), "os.system": (1, 1, []),
        "requests.get": (1, 1, None), "requests.post": (1, 3, None),
        "fastapi.FastAPI": (0, 0, None),
    },
    "javascript": {"JSON.parse": (1, 2, []), "JSON.stringify": (1, 3, []), "console.log": (0, None, [])},
    "typescript": {"JSON.parse": (1, 2, []), "JSON.stringify": (1, 3, []), "console.log": (0, None, [])},
    "go": {"fmt.Println": (0, None, []), "fmt.Printf": (1, None, []), "fmt.Sprintf": (1, None, [])},
    "rust": {"std::fs::read_to_string": (1, 1, [])},
    "java": {"System.out.println": (0, 1, []), "Math.sqrt": (1, 1, [])},
    "c": {"printf": (1, None, []), "strlen": (1, 1, [])},
    "cpp": {"std::sqrt": (1, 1, []), "std::getline": (2, 3, [])},
}
# Only these catalogs are complete enough to contradict an absent member.
COMPLETE_MODULES = {"python": {"json": {"dump", "dumps", "load", "loads", "JSONDecoder", "JSONEncoder", "JSONDecodeError"}}}
STANDARD = {
    "python": set(sys.stdlib_module_names),
    "javascript": {"fs", "path", "http", "https", "url", "util", "events", "stream", "crypto", "buffer", "assert", "os"},
    "typescript": {"fs", "path", "http", "https", "url", "util", "events", "stream", "crypto", "buffer", "assert", "os"},
    "java": {"java", "javax"},
    "go": {"fmt", "os", "io", "net", "http", "strings", "strconv", "encoding", "math", "time", "sync", "context", "errors", "sort", "bytes", "bufio", "path", "regexp"},
    "rust": {"std", "core", "alloc"},
    "c": {"stdio.h", "stdlib.h", "string.h", "math.h", "stdint.h", "stdbool.h", "stddef.h", "time.h", "ctype.h"},
    "cpp": {"iostream", "vector", "string", "map", "set", "algorithm", "memory", "cmath", "utility", "fstream", "sstream", "stdexcept"},
}
_CACHE: dict[tuple[str, str], tuple[float, tuple[str, str]]] = {}


def package_status(language: str, name: str, online: bool = False) -> tuple[str, str]:
    name = name.strip('"<>').removeprefix("node:")
    root = name.split('.')[0] if language in {"python", "java"} else name.split('/')[0]
    known_paths = {'python': {'os.path', 'urllib.parse', 'urllib.request', 'http.client', 'collections.abc', 'concurrent.futures', 'xml.etree.ElementTree'},
                   'java': {'java.util.List', 'java.util.ArrayList', 'java.util.Map', 'java.util.HashMap', 'java.io.File', 'java.nio.file.Files', 'java.nio.file.Path'},
                   'javascript': {'fs/promises'}, 'typescript': {'fs/promises'},
                   'go': {'net/http', 'encoding/json', 'path/filepath', 'math/rand', 'io/ioutil'},
                   'rust': {'std::fs', 'std::io', 'std::collections', 'std::thread', 'std::sync'}}
    if name in STANDARD.get(language, set()) or name in known_paths.get(language, set()):
        return "supported", f"Standard library catalog {VERSION}: {name}"
    if root in STANDARD.get(language, set()):
        return "uncertain", f"Standard namespace {root} exists, but no catalog confirms member/module {name}."
    if name.startswith(('.', '/')) or language in {"c", "cpp", "java", "go"}:
        return "uncertain", "Project/build metadata is required to resolve this dependency."
    if not online:
        return "uncertain", "No local catalog evidence; external package lookups are disabled."
    package = name.split('/')[0] if not name.startswith('@') else '/'.join(name.split('/')[:2])
    key = (language, package)
    cached = _CACHE.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    urls = {
        "python": f"https://pypi.org/pypi/{quote(root, safe='')}/json",
        "javascript": f"https://registry.npmjs.org/{quote(package, safe='')}",
        "typescript": f"https://registry.npmjs.org/{quote(package, safe='')}",
        "rust": f"https://crates.io/api/v1/crates/{quote(root, safe='')}",
    }
    try:
        response = httpx.get(urls[language], timeout=5, headers={"User-Agent": "DeHalu/0.2 package-metadata"})
        if response.status_code == 404:
            result = ("unsupported", f"Registry returned 404 for {package}; lookup {urls[language]}")
        elif response.is_success:
            result = ("supported", f"Registry confirms package {package}; API compatibility remains separate.")
        else:
            result = ("uncertain", f"Registry unavailable ({response.status_code}).")
    except (httpx.HTTPError, KeyError):
        result = ("uncertain", "Package registry lookup unavailable.")
    _CACHE[key] = (time.monotonic() + (3600 if result[0] != "uncertain" else 30), result)
    return result

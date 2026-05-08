#!/usr/bin/env python3
"""Generate a high-level component diagram from a GitHub repository."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".kt",
    ".swift",
    ".cs",
    ".php",
    ".rb",
}

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
    "coverage",
    "target",
    "out",
}

SKIP_FILE_PATTERNS = (
    ".min.js",
    ".lock",
)

IMPORT_PATTERNS = {
    ".py": [
        re.compile(r"^\s*from\s+([a-zA-Z_][\w\.]*)\s+import\s+", re.MULTILINE),
        re.compile(r"^\s*import\s+([a-zA-Z_][\w\.]*)", re.MULTILINE),
    ],
    ".js": [
        re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"),
        re.compile(r"require\(['\"]([^'\"]+)['\"]\)"),
    ],
    ".jsx": [
        re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"),
        re.compile(r"require\(['\"]([^'\"]+)['\"]\)"),
    ],
    ".ts": [
        re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"),
        re.compile(r"require\(['\"]([^'\"]+)['\"]\)"),
    ],
    ".tsx": [
        re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"),
        re.compile(r"require\(['\"]([^'\"]+)['\"]\)"),
    ],
    ".java": [
        re.compile(r"^\s*import\s+([a-zA-Z_][\w\.]*)\s*;", re.MULTILINE),
    ],
    ".go": [
        re.compile(r"^\s*import\s+\"([^\"]+)\"", re.MULTILINE),
        re.compile(r"^\s*import\s+\((.*?)\)", re.MULTILINE | re.DOTALL),
    ],
    ".rs": [
        re.compile(r"^\s*use\s+([a-zA-Z_][\w:]+)", re.MULTILINE),
    ],
}


@dataclass
class Component:
    name: str
    files: int = 0
    languages: Counter[str] = field(default_factory=Counter)
    dependencies: Counter[str] = field(default_factory=Counter)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a high-level Mermaid component diagram from a GitHub repo."
    )
    parser.add_argument("github_url", help="GitHub repository URL (https://github.com/org/repo)")
    parser.add_argument(
        "--output",
        default="component-diagram.mmd",
        help="Output Mermaid file path (default: component-diagram.mmd)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=8000,
        help="Maximum number of code files to process (default: 8000)",
    )
    parser.add_argument(
        "--keep-clone",
        action="store_true",
        help="Keep temporary cloned repository directory for inspection",
    )
    return parser.parse_args()


def clone_repo(repo_url: str, keep_clone: bool) -> tuple[Path, Path | None]:
    local_tmp_root = Path.cwd() / ".component_diagram_tmp"
    local_tmp_root.mkdir(parents=True, exist_ok=True)
    temp_root = Path(
        subprocess.check_output(
            ["mktemp", "-d", str(local_tmp_root / "clone-XXXXXX")], text=True
        ).strip()
    )
    repo_path = temp_root / "repo"
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if keep_clone:
        return repo_path, temp_root
    return repo_path, None


def extension_to_language(ext: str) -> str:
    mapping = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".kt": "Kotlin",
        ".swift": "Swift",
        ".cs": "C#",
        ".php": "PHP",
        ".rb": "Ruby",
    }
    return mapping.get(ext, ext.lstrip(".").upper())


def iter_code_files(repo_path: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        root_path = Path(root)
        for file_name in files:
            path = root_path / file_name
            if any(path.name.endswith(p) for p in SKIP_FILE_PATTERNS):
                continue
            if path.suffix.lower() in CODE_EXTENSIONS:
                yield path


def detect_component(repo_path: Path, file_path: Path) -> str:
    rel = file_path.relative_to(repo_path)
    parts = rel.parts
    if len(parts) == 1:
        return "root"

    first = parts[0].lower()
    # Common monorepo package roots.
    if first in {"packages", "services", "apps", "modules"} and len(parts) > 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def parse_imports(file_path: Path) -> list[str]:
    patterns = IMPORT_PATTERNS.get(file_path.suffix.lower(), [])
    if not patterns:
        return []
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    imports: list[str] = []
    for pattern in patterns:
        for match in pattern.findall(text):
            if isinstance(match, tuple):
                match = match[0]
            if not match:
                continue
            if file_path.suffix.lower() == ".go" and "\n" in match:
                imports.extend(
                    m.strip().strip('"')
                    for m in match.splitlines()
                    if m.strip().startswith('"') and m.strip().endswith('"')
                )
            else:
                imports.append(match.strip())
    return imports


def import_to_component(import_path: str) -> str | None:
    # Skip external library imports.
    if import_path.startswith((".", "@", "/")):
        cleaned = import_path.lstrip("./@/")
        if not cleaned:
            return None
        return cleaned.split("/")[0].split(".")[0]

    # Dotted imports for Python/Java.
    head = import_path.split(".")[0].split("/")[0]
    if head in {"com", "org", "io", "net", "github", "std", "java"}:
        return None
    if len(head) <= 1:
        return None
    return head


def analyze_repo(repo_path: Path, max_files: int) -> dict[str, Component]:
    components: dict[str, Component] = {}
    file_to_component: dict[Path, str] = {}

    for idx, file_path in enumerate(iter_code_files(repo_path)):
        if idx >= max_files:
            break
        comp_name = detect_component(repo_path, file_path)
        file_to_component[file_path] = comp_name
        if comp_name not in components:
            components[comp_name] = Component(name=comp_name)
        comp = components[comp_name]
        comp.files += 1
        comp.languages[extension_to_language(file_path.suffix.lower())] += 1

    # Second pass for dependencies.
    component_names = set(components.keys())
    for file_path, src_component in file_to_component.items():
        imports = parse_imports(file_path)
        for imported in imports:
            target = import_to_component(imported)
            if not target:
                continue
            # Try to match local component names by exact, case-insensitive, and prefix.
            target_match = None
            if target in component_names:
                target_match = target
            else:
                low = target.lower()
                for comp_name in component_names:
                    if comp_name.lower() == low or comp_name.lower().endswith(f"/{low}"):
                        target_match = comp_name
                        break
            if target_match and target_match != src_component:
                components[src_component].dependencies[target_match] += 1

    return components


def sanitize_id(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def top_languages(counter: Counter[str], limit: int = 2) -> str:
    langs = [name for name, _ in counter.most_common(limit)]
    return ", ".join(langs) if langs else "Unknown"


def build_mermaid(components: dict[str, Component]) -> str:
    lines = ["flowchart TD", "  %% Auto-generated high-level component diagram"]
    for comp_name in sorted(components.keys()):
        comp = components[comp_name]
        node_id = sanitize_id(comp_name)
        label = f"{comp.name}\\n{comp.files} files\\n{top_languages(comp.languages)}"
        lines.append(f'  {node_id}["{label}"]')

    edges = defaultdict(int)
    for comp in components.values():
        for dst, weight in comp.dependencies.items():
            edges[(comp.name, dst)] += weight

    for (src, dst), weight in sorted(edges.items()):
        src_id = sanitize_id(src)
        dst_id = sanitize_id(dst)
        lines.append(f"  {src_id} -->|{weight}| {dst_id}")

    if len(lines) == 2:
        lines.append('  empty["No components detected"]')
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    repo_temp_root: Path | None = None
    try:
        repo_path, repo_temp_root = clone_repo(args.github_url, args.keep_clone)
        components = analyze_repo(repo_path, max_files=args.max_files)
        mermaid = build_mermaid(components)
        output_path = Path(args.output).resolve()
        output_path.write_text(mermaid, encoding="utf-8")
        print(f"Generated Mermaid diagram at: {output_path}")
        print(f"Detected {len(components)} components")
        if args.keep_clone:
            print(f"Cloned repo kept at: {repo_path}")
    except subprocess.CalledProcessError:
        raise SystemExit("Failed to clone repository. Check URL and network access.")
    finally:
        if repo_temp_root is not None and not args.keep_clone:
            shutil.rmtree(repo_temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()

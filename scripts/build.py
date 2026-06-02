"""
Build encrypted plugin release zips for publishing.

Usage:
    python scripts/build.py copy_manga
    python scripts/build.py copy_manga --scrollpack ../ScrollPack
    python scripts/build.py --all
"""
import os
import sys
import shutil
import tempfile
import argparse


REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _import_crypto():
    for base in [
        os.path.join(REPO_DIR, "..", "ScrollPack-crypto"),
        os.path.join(REPO_DIR, "..", "ScrollPack", "plugins"),  # fallback
        os.environ.get("SCROLLPACK_DIR", ""),
    ]:
        if base and os.path.isdir(base):
            sys.path.insert(0, os.path.abspath(base))
            break
    try:
        from scrollpack_crypto import encrypt_plugin
        return encrypt_plugin
    except ImportError:
        from crypto import encrypt_plugin
        return encrypt_plugin


def build_release(plugin_id, scrollpack_dir, output_dir):
    encrypt_plugin = _import_crypto()

    src_dir = os.path.join(scrollpack_dir, "plugins", plugin_id)
    if not os.path.isdir(src_dir):
        print(f"Plugin '{plugin_id}' not found at {src_dir}")
        return False

    manifest = os.path.join(src_dir, "plugin.json")
    if not os.path.isfile(manifest):
        print(f"Plugin '{plugin_id}' has no plugin.json")
        return False

    with tempfile.TemporaryDirectory() as tmp:
        print(f"Copying {plugin_id}...")
        shutil.copytree(src_dir, os.path.join(tmp, plugin_id),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        work_dir = os.path.join(tmp, plugin_id)
        print(f"Encrypting {plugin_id}...")
        encrypt_plugin(work_dir)

        zip_path = os.path.join(output_dir, f"{plugin_id}.zip")
        print(f"Zipping -> {zip_path}")
        shutil.make_archive(
            os.path.join(output_dir, plugin_id), "zip",
            os.path.dirname(work_dir), plugin_id,
        )

        print(f"Done: {plugin_id}.zip ({os.path.getsize(zip_path)} bytes)")
        return True


def main():
    parser = argparse.ArgumentParser(description="Build encrypted plugin releases")
    parser.add_argument("plugins", nargs="*", help="Plugin IDs to build")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--scrollpack", default=None,
                        help="Path to ScrollPack project")
    args = parser.parse_args()

    scrollpack_dir = args.scrollpack or os.path.join(REPO_DIR, "..", "ScrollPack")
    scrollpack_dir = os.path.abspath(scrollpack_dir)
    output_dir = os.path.join(REPO_DIR, "plugins")
    os.makedirs(output_dir, exist_ok=True)

    if args.all:
        plugins_dir = os.path.join(scrollpack_dir, "plugins")
        plugin_ids = [
            d for d in os.listdir(plugins_dir)
            if os.path.isdir(os.path.join(plugins_dir, d))
            and os.path.isfile(os.path.join(plugins_dir, d, "plugin.json"))
            and d != "plugin_template"
        ]
    elif args.plugins:
        plugin_ids = args.plugins
    else:
        parser.print_help()
        return

    for pid in plugin_ids:
        print(f"\n--- {pid} ---")
        build_release(pid, scrollpack_dir, output_dir)

    print(f"\nDone. Output: {output_dir}")


if __name__ == "__main__":
    main()

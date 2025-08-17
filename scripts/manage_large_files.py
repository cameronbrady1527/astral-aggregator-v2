#!/usr/bin/env python3
"""
Large File Manager for Aggregator Project

This script helps manage large files that can slow down Cursor/VS Code
by providing options to:
1. Move large files outside the project
2. Compress large files
3. Clean up old output directories
4. Create symlinks for comparison scripts
"""

import os
import shutil
import json
import gzip
from pathlib import Path
from datetime import datetime, timedelta
import argparse
from typing import List, Dict, Any


class LargeFileManager:
    def __init__(self, project_root: str = ".", external_dir: str = "../aggregator-data"):
        self.project_root = Path(project_root).resolve()
        self.output_dir = self.project_root / "output"
        self.external_dir = Path(external_dir).resolve()
        self.changes_dir = self.project_root / "changes"
        
        # Ensure external directory exists
        self.external_dir.mkdir(exist_ok=True)
    
    def find_large_files(self, min_size_mb: int = 50) -> List[Dict[str, Any]]:
        """Find files larger than the specified size in MB."""
        large_files = []
        min_size_bytes = min_size_mb * 1024 * 1024
        
        if not self.output_dir.exists():
            return large_files
        
        for file_path in self.output_dir.rglob("*"):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    if size > min_size_bytes:
                        large_files.append({
                            'path': file_path,
                            'size_mb': size / (1024 * 1024),
                            'relative_path': file_path.relative_to(self.project_root),
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime)
                        })
                except (OSError, PermissionError):
                    continue
        
        # Sort by size (largest first)
        large_files.sort(key=lambda x: x['size_mb'], reverse=True)
        return large_files
    
    def move_file_external(self, file_path: Path, create_symlink: bool = True) -> str:
        """Move a file to external directory and optionally create a symlink."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Create external path
        external_path = self.external_dir / file_path.name
        
        # Move file
        shutil.move(str(file_path), str(external_path))
        
        # Create symlink if requested
        if create_symlink:
            try:
                # On Windows, create a junction or copy the file
                if os.name == 'nt':
                    # Windows: copy file back as a small placeholder
                    self._create_windows_placeholder(file_path, external_path)
                else:
                    # Unix: create symlink
                    os.symlink(str(external_path), str(file_path))
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not create symlink/junction: {e}")
        
        return str(external_path)
    
    def _create_windows_placeholder(self, original_path: Path, external_path: Path):
        """Create a small placeholder file on Windows that points to the external location."""
        placeholder_data = {
            "external_location": str(external_path),
            "moved_at": datetime.now().isoformat(),
            "note": "This file has been moved to external storage. Use the external_location path to access it."
        }
        
        with open(original_path, 'w') as f:
            json.dump(placeholder_data, f, indent=2)
    
    def compress_file(self, file_path: Path, remove_original: bool = False) -> str:
        """Compress a file using gzip."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        if remove_original:
            file_path.unlink()
        
        return str(compressed_path)
    
    def cleanup_old_outputs(self, days_to_keep: int = 7) -> List[str]:
        """Remove output directories older than specified days."""
        if not self.output_dir.exists():
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        removed_dirs = []
        
        for dir_path in self.output_dir.iterdir():
            if dir_path.is_dir():
                try:
                    # Check if directory name contains a timestamp
                    dir_name = dir_path.name
                    if '_' in dir_name and any(part.isdigit() for part in dir_name.split('_')):
                        # Try to extract timestamp from directory name
                        timestamp_str = self._extract_timestamp_from_dirname(dir_name)
                        if timestamp_str:
                            try:
                                dir_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                                if dir_date < cutoff_date:
                                    shutil.rmtree(dir_path)
                                    removed_dirs.append(str(dir_path))
                            except ValueError:
                                # If we can't parse the timestamp, skip this directory
                                continue
                except (OSError, PermissionError) as e:
                    print(f"Warning: Could not remove {dir_path}: {e}")
        
        return removed_dirs
    
    def _extract_timestamp_from_dirname(self, dirname: str) -> str:
        """Extract timestamp from directory name."""
        parts = dirname.split('_')
        for i, part in enumerate(parts):
            if len(part) == 8 and part.isdigit() and part.startswith('20'):
                # Found date part, look for time part
                if i + 1 < len(parts) and len(parts[i + 1]) == 6 and parts[i + 1].isdigit():
                    return f"{part}_{parts[i + 1]}"
        return None
    
    def list_external_files(self) -> List[Dict[str, Any]]:
        """List all files in the external directory."""
        if not self.external_dir.exists():
            return []
        
        external_files = []
        for file_path in self.external_dir.iterdir():
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    external_files.append({
                        'name': file_path.name,
                        'size_mb': size / (1024 * 1024),
                        'path': str(file_path),
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime)
                    })
                except (OSError, PermissionError):
                    continue
        
        return sorted(external_files, key=lambda x: x['size_mb'], reverse=True)
    
    def restore_file(self, external_filename: str, target_path: Path = None) -> str:
        """Restore a file from external storage."""
        external_path = self.external_dir / external_filename
        if not external_path.exists():
            raise FileNotFoundError(f"External file not found: {external_path}")
        
        if target_path is None:
            # Restore to original location if it was a placeholder
            target_path = self.output_dir / external_filename
        
        shutil.copy2(str(external_path), str(target_path))
        return str(target_path)


def main():
    parser = argparse.ArgumentParser(description="Manage large files in the aggregator project")
    parser.add_argument("--min-size", type=int, default=50, 
                       help="Minimum file size in MB to consider 'large' (default: 50)")
    parser.add_argument("--external-dir", default="../aggregator-data",
                       help="External directory for large files (default: ../aggregator-data)")
    parser.add_argument("--cleanup-days", type=int, default=7,
                       help="Remove output directories older than N days (default: 7)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List large files")
    list_parser.add_argument("--external", action="store_true", 
                           help="Also list files in external directory")
    
    # Move command
    move_parser = subparsers.add_parser("move", help="Move large files to external storage")
    move_parser.add_argument("file", help="File to move (relative to output directory)")
    move_parser.add_argument("--no-symlink", action="store_true", 
                           help="Don't create symlink/placeholder")
    
    # Compress command
    compress_parser = subparsers.add_parser("compress", help="Compress large files")
    compress_parser.add_argument("file", help="File to compress (relative to output directory)")
    compress_parser.add_argument("--remove", action="store_true", 
                               help="Remove original file after compression")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old output directories")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore file from external storage")
    restore_parser.add_argument("external_file", help="Name of file in external directory")
    restore_parser.add_argument("--target", help="Target path (default: original location)")
    
    args = parser.parse_args()
    
    manager = LargeFileManager(external_dir=args.external_dir)
    
    if args.command == "list":
        print("Large files in project:")
        large_files = manager.find_large_files(args.min_size)
        if large_files:
            for file_info in large_files:
                print(f"  {file_info['relative_path']} - {file_info['size_mb']:.1f} MB")
        else:
            print("  No large files found")
        
        if args.external:
            print("\nFiles in external directory:")
            external_files = manager.list_external_files()
            if external_files:
                for file_info in external_files:
                    print(f"  {file_info['name']} - {file_info['size_mb']:.1f} MB")
            else:
                print("  No external files found")
    
    elif args.command == "move":
        file_path = manager.output_dir / args.file
        try:
            external_path = manager.move_file_external(file_path, not args.no_symlink)
            print(f"Moved {file_path} to {external_path}")
        except Exception as e:
            print(f"Error moving file: {e}")
    
    elif args.command == "compress":
        file_path = manager.output_dir / args.file
        try:
            compressed_path = manager.compress_file(file_path, args.remove)
            print(f"Compressed {file_path} to {compressed_path}")
        except Exception as e:
            print(f"Error compressing file: {e}")
    
    elif args.command == "cleanup":
        removed_dirs = manager.cleanup_old_outputs(args.cleanup_days)
        if removed_dirs:
            print(f"Removed {len(removed_dirs)} old output directories:")
            for dir_path in removed_dirs:
                print(f"  {dir_path}")
        else:
            print("No old output directories to remove")
    
    elif args.command == "restore":
        try:
            target_path = Path(args.target) if args.target else None
            restored_path = manager.restore_file(args.external_file, target_path)
            print(f"Restored {args.external_file} to {restored_path}")
        except Exception as e:
            print(f"Error restoring file: {e}")
    
    else:
        # No command specified, show help
        parser.print_help()


if __name__ == "__main__":
    main()

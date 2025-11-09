#!/usr/bin/env python3
"""
EXIF Analyzer - Reads EXIF data from RAW image files and extracts camera metadata
Supports multiple camera brands (Canon, Olympus, OM Digital Solutions, etc.)

Author: Javi Aparicio
Copyright: (c) 2025 Javi Aparicio - javiapariciofoto.ch
"""

__version__ = "1.0.0"
__author__ = "Javi Aparicio"
__copyright__ = "(c) 2025 Javi Aparicio - javiapariciofoto.ch"

import re
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import Counter, defaultdict
from multiprocessing import Pool, cpu_count
from functools import partial


def normalize_lens_name(lens_name: str) -> str:
    """
    Normalize lens name to a canonical form for comparison.
    Handles case differences and common variations.
    
    Args:
        lens_name: Original lens name from EXIF
        
    Returns:
        Normalized lens name (lowercase, standardized)
    """
    if not lens_name:
        return ""
    
    # Convert to lowercase for case-insensitive comparison
    normalized = lens_name.lower()
    
    # Normalize common variations
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Remove leading/trailing whitespace
    normalized = normalized.strip()
    
    return normalized


def extract_exif_from_raw(file_path: Path) -> str:
    """
    Extract EXIF data from a RAW image file using ExifTool.
    
    Args:
        file_path: Path to the RAW image file
        
    Returns:
        ExifTool output as a string
    """
    exiftool_path = shutil.which('exiftool')
    if not exiftool_path:
        raise RuntimeError("ExifTool not found. Please install ExifTool.")
    
    try:
        result = subprocess.run(
            [exiftool_path, str(file_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=30  # Add timeout to prevent hanging
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout processing {file_path.name}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running ExifTool on {file_path.name}: {e.stderr}")


def process_single_file(raw_file: Path, base_directory: Path) -> Optional[Dict[str, Any]]:
    """
    Process a single RAW file and extract EXIF data.
    This function is designed to be used with multiprocessing.
    
    Args:
        raw_file: Path to the RAW image file
        base_directory: Base directory for relative path calculation
        
    Returns:
        Dictionary containing extracted metadata, or None if error
    """
    try:
        # Extract EXIF data using ExifTool
        exif_output = extract_exif_from_raw(raw_file)
        # Parse the ExifTool output
        data = parse_exif_output(exif_output, str(raw_file.relative_to(base_directory)))
        return data
    except Exception as e:
        print(f"Error processing {raw_file.name}: {e}")
        return None


def parse_exif_output(exif_output: str, file_name: str) -> Dict[str, Any]:
    """
    Parse ExifTool output and extract relevant metadata.
    
    Args:
        exif_output: ExifTool output text
        file_name: Name of the source file
        
    Returns:
        Dictionary containing extracted metadata
    """
    data = {
        'file_name': file_name,
        'camera': None,
        'lens': None,
        'iso': None,
        'speed': None,
        'aperture': None,
        'focal_length': None
    }
    
    lines = exif_output.split('\n')
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Parse key-value pairs (format: "Key : Value")
        if ':' not in line:
            continue
            
        parts = line.split(':', 1)
        if len(parts) != 2:
            continue
            
        key = parts[0].strip()
        value = parts[1].strip()
        
        # Extract Camera Model
        if not data['camera']:
            if key == 'Camera Model Name':
                data['camera'] = value
            elif key == 'Camera Type 2' and not data['camera']:
                data['camera'] = value
        
        # Extract Lens (prioritize more specific fields)
        # Priority: RF Lens Type > Lens ID > Lens Type > Lens Model > Lens Info
        # Always prefer more specific fields, even if found later in the file
        if key == 'RF Lens Type':
            # Highest priority - always use this (Canon specific)
            data['lens'] = value
        elif key == 'Lens ID':
            # High priority - prefer over Lens Model as it's usually more complete
            data['lens'] = value
        elif key == 'Lens Type':
            # Use Lens Type if we don't have a better field
            if not data['lens']:
                data['lens'] = value
        elif key == 'Lens Model':
            # Use Lens Model only if we don't have a better field
            if not data['lens']:
                data['lens'] = value
        elif key == 'Lens Info':
            # Only use as fallback if no other lens field found
            if not data['lens']:
                data['lens'] = value
        
        # Extract ISO
        if not data['iso']:
            if key == 'ISO':
                # Extract numeric value
                iso_match = re.search(r'(\d+)', value)
                if iso_match:
                    data['iso'] = int(iso_match.group(1))
            elif key == 'Camera ISO' and 'Auto' not in value:
                iso_match = re.search(r'(\d+)', value)
                if iso_match:
                    data['iso'] = int(iso_match.group(1))
        
        # Extract Shutter Speed
        if not data['speed']:
            if key == 'Shutter Speed':
                data['speed'] = value
            elif key == 'Exposure Time':
                data['speed'] = value
            elif key == 'Shutter Speed Value':
                data['speed'] = value
        
        # Extract Aperture
        if not data['aperture']:
            if key == 'Aperture':
                # Extract f-number
                aperture_match = re.search(r'([\d.]+)', value)
                if aperture_match:
                    data['aperture'] = f"f/{aperture_match.group(1)}"
            elif key == 'F Number':
                aperture_match = re.search(r'([\d.]+)', value)
                if aperture_match:
                    data['aperture'] = f"f/{aperture_match.group(1)}"
            elif key == 'Aperture Value':
                aperture_match = re.search(r'([\d.]+)', value)
                if aperture_match:
                    data['aperture'] = f"f/{aperture_match.group(1)}"
        
        # Extract Focal Length
        if not data['focal_length']:
            if key == 'Focal Length':
                # Extract numeric value and unit (e.g., "37 mm" or "19.0 mm")
                focal_match = re.search(r'([\d.]+)\s*mm', value, re.IGNORECASE)
                if focal_match:
                    focal_value = float(focal_match.group(1))
                    # Round to reasonable precision and format
                    if focal_value == int(focal_value):
                        data['focal_length'] = f"{int(focal_value)}mm"
                    else:
                        data['focal_length'] = f"{focal_value:.1f}mm"
    
    return data


def load_raw_files(directory: Path, recursive: bool = True, num_workers: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Load EXIF data from all RAW image files in a directory.
    
    Supports common RAW formats: .CR3, .CR2, .ORF, .NEF, .ARW, .RAF, .RW2, .DNG
    
    Args:
        directory: Directory containing RAW image files
        recursive: If True, search subdirectories recursively
        num_workers: Number of parallel workers (default: CPU count)
        
    Returns:
        List of dictionaries containing metadata from each file
    """
    # Common RAW file extensions
    raw_extensions = ['.cr3', '.cr2', '.orf', '.nef', '.arw', '.raf', '.rw2', '.dng', 
                      '.3fr', '.ari', '.bay', '.cap', '.data', '.dcs', '.dcr', '.drf',
                      '.eip', '.erf', '.fff', '.gpr', '.iiq', '.k25', '.kdc', '.mdc',
                      '.mef', '.mos', '.mrw', '.nrw', '.obm', '.pef', '.ptx', '.pxn',
                      '.r3d', '.raf', '.raw', '.rwl', '.rwz', '.sr2', '.srf', '.srw',
                      '.tif', '.x3f']
    
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")
    
    raw_files = []
    pattern = '**/*' if recursive else '*'
    
    for ext in raw_extensions:
        # Search for both lowercase and uppercase extensions
        raw_files.extend(directory.glob(f'{pattern}{ext}'))
        raw_files.extend(directory.glob(f'{pattern}{ext.upper()}'))
    
    raw_files = sorted(set(raw_files))  # Remove duplicates and sort
    
    if not raw_files:
        return []
    
    print(f"Found {len(raw_files)} RAW file(s) in {directory}")
    
    # Determine number of workers
    if num_workers is None:
        num_workers = cpu_count()
    
    # For small batches, use fewer workers
    num_workers = min(num_workers, len(raw_files))
    
    print(f"Processing files with {num_workers} worker(s)...")
    
    # Process files in parallel
    if num_workers > 1 and len(raw_files) > 1:
        # Use multiprocessing for parallel processing
        with Pool(processes=num_workers) as pool:
            # Create a partial function with base_directory fixed
            process_func = partial(process_single_file, base_directory=directory)
            # Process files in parallel
            results = pool.map(process_func, raw_files)
            # Filter out None results (errors)
            results = [r for r in results if r is not None]
    else:
        # Sequential processing for single file or single worker
        results = []
        for raw_file in raw_files:
            data = process_single_file(raw_file, directory)
            if data:
                results.append(data)
    
    return results


def generate_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate statistics from EXIF data.
    Normalizes lens names to handle case differences and variations.
    
    Args:
        results: List of dictionaries containing metadata
        
    Returns:
        Dictionary containing various statistics
    """
    # Track lens name variations: normalized -> {original: count}
    lens_variations = defaultdict(lambda: defaultdict(int))
    # Track which original name to use as canonical for each normalized name
    lens_canonical_map = {}
    
    stats = {
        'total_photos': len(results),
        'cameras': Counter(),
        'lenses': Counter(),
        'iso_values': Counter(),
        'shutter_speeds': Counter(),
        'apertures_by_lens': defaultdict(Counter),  # lens -> {aperture: count}
        'apertures': Counter(),
        'focal_lengths_by_lens': defaultdict(Counter),  # lens -> {focal_length: count}
        'focal_lengths': Counter(),
    }
    
    # First pass: collect all lens variations and their counts
    for data in results:
        if data['lens']:
            normalized = normalize_lens_name(data['lens'])
            lens_variations[normalized][data['lens']] += 1
    
    # Determine canonical name for each normalized lens (use the most common variation)
    for normalized, variations in lens_variations.items():
        # Find the most common original variation
        canonical = max(variations.items(), key=lambda x: x[1])[0]
        lens_canonical_map[normalized] = canonical
    
    # Second pass: generate statistics using normalized lens names
    for data in results:
        # Count cameras
        if data['camera']:
            stats['cameras'][data['camera']] += 1
        
        # Count lenses (using canonical names)
        if data['lens']:
            normalized = normalize_lens_name(data['lens'])
            canonical = lens_canonical_map[normalized]
            stats['lenses'][canonical] += 1
        
        # Count ISO values
        if data['iso']:
            stats['iso_values'][data['iso']] += 1
        
        # Count shutter speeds
        if data['speed']:
            stats['shutter_speeds'][data['speed']] += 1
        
        # Count apertures (overall)
        if data['aperture']:
            stats['apertures'][data['aperture']] += 1
        
        # Group apertures by lens (using canonical names)
        if data['lens'] and data['aperture']:
            normalized = normalize_lens_name(data['lens'])
            canonical = lens_canonical_map[normalized]
            stats['apertures_by_lens'][canonical][data['aperture']] += 1
        
        # Count focal lengths (overall)
        if data['focal_length']:
            stats['focal_lengths'][data['focal_length']] += 1
        
        # Group focal lengths by lens (using canonical names)
        if data['lens'] and data['focal_length']:
            normalized = normalize_lens_name(data['lens'])
            canonical = lens_canonical_map[normalized]
            stats['focal_lengths_by_lens'][canonical][data['focal_length']] += 1
    
    return stats


def display_statistics(stats: Dict[str, Any]) -> None:
    """
    Display statistics in a formatted way.
    
    Args:
        stats: Dictionary containing statistics
    """
    print("\n" + "="*80)
    print("PHOTOGRAPHY STATISTICS")
    print("="*80 + "\n")
    
    print(f"Total Photos Analyzed: {stats['total_photos']}\n")
    
    # Camera Statistics (Top 10)
    if stats['cameras']:
        print("="*80)
        print("CAMERA USAGE (Top 10)")
        print("="*80)
        for camera, count in stats['cameras'].most_common(10):
            percentage = (count / stats['total_photos']) * 100
            print(f"  {camera:50s} {count:4d} photos ({percentage:5.1f}%)")
        print()
    
    # Lens Statistics (Top 10)
    if stats['lenses']:
        print("="*80)
        print("LENS USAGE (Top 10)")
        print("="*80)
        for lens, count in stats['lenses'].most_common(10):
            percentage = (count / stats['total_photos']) * 100
            print(f"  {lens:50s} {count:4d} photos ({percentage:5.1f}%)")
        print()
    
    # Aperture Statistics by Lens (Top 10 per lens)
    if stats['apertures_by_lens']:
        print("="*80)
        print("APERTURE USAGE BY LENS (Top 10 per lens)")
        print("="*80)
        for lens in sorted(stats['apertures_by_lens'].keys()):
            print(f"\n  {lens}")
            print("  " + "-" * 76)
            apertures = stats['apertures_by_lens'][lens]
            # Sort apertures by count (most used first), then by f-number
            sorted_apertures = sorted(
                apertures.items(),
                key=lambda x: (-x[1], float(re.search(r'([\d.]+)', x[0]).group(1)) if re.search(r'([\d.]+)', x[0]) else 0)
            )[:10]  # Limit to top 10
            for aperture, count in sorted_apertures:
                percentage = (count / stats['lenses'][lens]) * 100
                print(f"    {aperture:15s} {count:4d} times ({percentage:5.1f}%)")
        print()
    
    # Focal Length Statistics by Lens (Top 10 per lens)
    if stats['focal_lengths_by_lens']:
        print("="*80)
        print("FOCAL LENGTH USAGE BY LENS (Top 10 per lens)")
        print("="*80)
        for lens in sorted(stats['focal_lengths_by_lens'].keys()):
            print(f"\n  {lens}")
            print("  " + "-" * 76)
            focal_lengths = stats['focal_lengths_by_lens'][lens]
            # Sort focal lengths by count (most used first), then by numeric value
            def sort_focal(focal_str):
                """Extract numeric value from focal length string for sorting"""
                match = re.search(r'([\d.]+)', focal_str)
                return float(match.group(1)) if match else 0
            
            sorted_focals = sorted(
                focal_lengths.items(),
                key=lambda x: (-x[1], sort_focal(x[0]))
            )[:10]  # Limit to top 10
            for focal_length, count in sorted_focals:
                percentage = (count / stats['lenses'][lens]) * 100
                print(f"    {focal_length:15s} {count:4d} times ({percentage:5.1f}%)")
        print()
    
    # ISO Statistics (Top 10)
    if stats['iso_values']:
        print("="*80)
        print("ISO SENSITIVITY USAGE (Top 10)")
        print("="*80)
        # Sort by count (most used first), then by ISO value
        sorted_iso = sorted(
            stats['iso_values'].items(),
            key=lambda x: (-x[1], x[0])
        )[:10]  # Limit to top 10
        for iso, count in sorted_iso:
            percentage = (count / stats['total_photos']) * 100
            print(f"  ISO {iso:5d} {count:4d} photos ({percentage:5.1f}%)")
        print()
    
    # Shutter Speed Statistics (Top 10)
    if stats['shutter_speeds']:
        print("="*80)
        print("SHUTTER SPEED USAGE (Top 10)")
        print("="*80)
        # Sort shutter speeds by count (most used first), then by speed value
        def sort_speed(speed_str):
            """Sort speeds: fractions first, then whole numbers"""
            if '/' in speed_str:
                try:
                    num, den = speed_str.split('/')
                    return float(num) / float(den)
                except:
                    return float('inf')
            else:
                try:
                    return float(speed_str)
                except:
                    return float('inf')
        
        sorted_speeds = sorted(
            stats['shutter_speeds'].items(),
            key=lambda x: (-x[1], sort_speed(x[0]))
        )[:10]  # Limit to top 10
        for speed, count in sorted_speeds:
            percentage = (count / stats['total_photos']) * 100
            print(f"  {speed:15s} {count:4d} photos ({percentage:5.1f}%)")
        print()
    
    # Overall Aperture Statistics (Top 10)
    if stats['apertures']:
        print("="*80)
        print("OVERALL APERTURE USAGE (Top 10)")
        print("="*80)
        # Sort apertures by count (most used first), then by f-number
        sorted_apertures = sorted(
            stats['apertures'].items(),
            key=lambda x: (-x[1], float(re.search(r'([\d.]+)', x[0]).group(1)) if re.search(r'([\d.]+)', x[0]) else 0)
        )[:10]  # Limit to top 10
        for aperture, count in sorted_apertures:
            percentage = (count / stats['total_photos']) * 100
            print(f"  {aperture:15s} {count:4d} photos ({percentage:5.1f}%)")
        print()
    
    # Overall Focal Length Statistics (Top 10)
    if stats['focal_lengths']:
        print("="*80)
        print("OVERALL FOCAL LENGTH USAGE (Top 10)")
        print("="*80)
        # Sort focal lengths by count (most used first), then by numeric value
        def sort_focal(focal_str):
            """Extract numeric value from focal length string for sorting"""
            match = re.search(r'([\d.]+)', focal_str)
            return float(match.group(1)) if match else 0
        
        sorted_focals = sorted(
            stats['focal_lengths'].items(),
            key=lambda x: (-x[1], sort_focal(x[0]))
        )[:10]  # Limit to top 10
        for focal_length, count in sorted_focals:
            percentage = (count / stats['total_photos']) * 100
            print(f"  {focal_length:15s} {count:4d} photos ({percentage:5.1f}%)")
        print()


def display_results(results: List[Dict[str, Any]]) -> None:
    """
    Display the extracted EXIF data in a formatted way.
    
    Args:
        results: List of dictionaries containing metadata
    """
    print("\n" + "="*80)
    print("EXIF DATA ANALYSIS")
    print("="*80 + "\n")
    
    for i, data in enumerate(results, 1):
        print(f"File {i}: {data['file_name']}")
        print(f"  Camera:      {data['camera'] or 'N/A'}")
        print(f"  Lens:        {data['lens'] or 'N/A'}")
        print(f"  ISO:         {data['iso'] or 'N/A'}")
        print(f"  Speed:       {data['speed'] or 'N/A'}")
        print(f"  Aperture:    {data['aperture'] or 'N/A'}")
        print(f"  Focal Length: {data['focal_length'] or 'N/A'}")
        print()


def print_banner():
    """Print script banner with version and copyright information."""
    print("="*80)
    print("EXIF Analyzer")
    print(f"Version {__version__}")
    print(f"Author: {__author__}")
    print(f"Copyright: {__copyright__}")
    print("="*80)
    print()


def main(source_dir: Optional[Path] = None, show_details: bool = False, show_stats: bool = True, recursive: bool = True, num_workers: Optional[int] = None):
    """
    Main function to run the EXIF analyzer.
    
    Args:
        source_dir: Directory containing RAW image files. If None, uses script directory.
        show_details: If True, show detailed EXIF data for each file
        show_stats: If True, show statistics summary
        recursive: If True, search subdirectories recursively
        num_workers: Number of parallel workers (default: CPU count)
    """
    # Print banner
    print_banner()
    
    # Use provided directory or default to script directory
    if source_dir is None:
        source_dir = Path(__file__).parent
    else:
        source_dir = Path(source_dir).resolve()
    
    # Load all RAW files and extract EXIF data
    try:
        import time
        start_time = time.time()
        results = load_raw_files(source_dir, recursive=recursive, num_workers=num_workers)
        elapsed_time = time.time() - start_time
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"Error: {e}")
        return None
    
    if not results:
        print(f"No RAW image files with EXIF data found in {source_dir}")
        return None
    
    print(f"\nSuccessfully processed {len(results)} file(s) with EXIF data in {elapsed_time:.1f} seconds\n")
    
    # Display detailed results if requested
    if show_details:
        display_results(results)
    
    # Generate and display statistics
    if show_stats:
        stats = generate_statistics(results)
        display_statistics(stats)
    
    # Return the data structure for programmatic use
    return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze EXIF data from RAW image files and generate statistics',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Analyze files in current directory
  %(prog)s /path/to/photos                    # Analyze files in specified directory
  %(prog)s /path/to/photos --details          # Show detailed EXIF data for each file
  %(prog)s /path/to/photos --no-recursive     # Don't search subdirectories
  %(prog)s /path/to/photos --no-stats         # Only show detailed data, no statistics
        """
    )
    
    parser.add_argument(
        'source',
        nargs='?',
        type=str,
        default=None,
        help='Source directory containing RAW image files (default: script directory)'
    )
    
    parser.add_argument(
        '-d', '--details',
        action='store_true',
        help='Show detailed EXIF data for each file'
    )
    
    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='Don\'t show statistics summary'
    )
    
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Don\'t search subdirectories recursively'
    )
    
    parser.add_argument(
        '-j', '--jobs',
        type=int,
        default=None,
        metavar='N',
        help=f'Number of parallel workers (default: number of CPU cores, currently {cpu_count()})'
    )
    
    args = parser.parse_args()
    
    # Convert source to Path if provided
    source_dir = Path(args.source) if args.source else None
    
    results = main(
        source_dir=source_dir,
        show_details=args.details,
        show_stats=not args.no_stats,
        recursive=not args.no_recursive,
        num_workers=args.jobs
    )


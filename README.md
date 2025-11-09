# EXIF Analyzer

A powerful Python tool for analyzing EXIF metadata from RAW image files. Extract and analyze camera settings, lens usage, and photography statistics from your photo collection.

## Features

- **Multi-format Support**: Works with all major RAW formats (Canon CR3/CR2, Olympus ORF, Nikon NEF, Sony ARW, and many more)
- **Fast Parallel Processing**: Utilizes multiprocessing to analyze hundreds of photos quickly
- **Comprehensive Statistics**: Generate detailed usage statistics for:
  - Camera models
  - Lenses
  - ISO sensitivity
  - Shutter speeds
  - Apertures (grouped by lens)
  - Focal lengths (grouped by lens)
- **Recursive Search**: Automatically searches subdirectories for RAW files
- **Top 10 Rankings**: Shows the most frequently used settings in each category

## Requirements

- Python 3.6 or higher
- [ExifTool](https://exiftool.org/) - Must be installed and available in your system PATH

### Installing ExifTool

**macOS:**
```bash
brew install exiftool
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install libimage-exiftool-perl
```

**Windows:**
Download from [ExifTool website](https://exiftool.org/) and add to PATH

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/exif-analyzer.git
cd exif-analyzer
```

2. No additional Python packages are required (uses only standard library)

## Usage

### Basic Usage

Analyze RAW files in the current directory:
```bash
python3 exif_analyzer.py
```

Analyze RAW files in a specific directory:
```bash
python3 exif_analyzer.py /path/to/photos
```

### Command Line Options

```bash
usage: exif_analyzer.py [-h] [-d] [--no-stats] [--no-recursive] [-j N] [source]

positional arguments:
  source                Source directory containing RAW image files (default: script directory)

options:
  -h, --help           show this help message and exit
  -d, --details        Show detailed EXIF data for each file
  --no-stats           Don't show statistics summary
  --no-recursive       Don't search subdirectories recursively
  -j, --jobs N         Number of parallel workers (default: number of CPU cores)
```

### Examples

**Show detailed EXIF data for each file:**
```bash
python3 exif_analyzer.py /path/to/photos --details
```

**Analyze only current directory (no subdirectories):**
```bash
python3 exif_analyzer.py /path/to/photos --no-recursive
```

**Use 4 parallel workers:**
```bash
python3 exif_analyzer.py /path/to/photos -j 4
```

**Show only detailed data, no statistics:**
```bash
python3 exif_analyzer.py /path/to/photos --details --no-stats
```

## Output

The script provides comprehensive statistics including:

### Camera Usage
Shows which cameras you use most frequently

### Lens Usage
Lists your most-used lenses with usage percentages

### Aperture Usage by Lens
For each lens, shows which apertures you use most often - perfect for understanding your shooting preferences

### Focal Length Usage by Lens
For each lens, shows which focal lengths you prefer - great for zoom lens analysis

### ISO Sensitivity Usage
Distribution of ISO settings across your photos

### Shutter Speed Usage
Most commonly used shutter speeds

### Overall Statistics
Aggregate statistics across all photos

## Supported RAW Formats

- Canon: CR3, CR2
- Olympus/OM System: ORF
- Nikon: NEF
- Sony: ARW
- Panasonic: RW2
- Fujifilm: RAF
- Pentax: PEF, DNG
- And many more (see code for complete list)

## Performance

The script uses parallel processing to analyze multiple files simultaneously. For a collection of ~400 photos:
- **Sequential processing**: ~400 × average processing time
- **Parallel processing (8 cores)**: ~50× faster

Processing time depends on:
- Number of files
- File sizes
- Number of CPU cores available
- Storage speed (SSD vs HDD)

## Use Cases

- **Photography Analysis**: Understand your shooting habits and preferences
- **Equipment Planning**: Identify which lenses and settings you use most
- **Portfolio Review**: Analyze technical aspects of your photo collection
- **Learning Tool**: Study your own photography patterns

## Example Output

```
================================================================================
EXIF Analyzer
Version 1.0.0
Author: Javi Aparicio
Copyright: (c) 2025 Javi Aparicio - javiapariciofoto.ch
================================================================================

Found 400 RAW file(s) in /path/to/photos
Processing files with 8 worker(s)...

Successfully processed 400 file(s) with EXIF data in 12.3 seconds

================================================================================
PHOTOGRAPHY STATISTICS
================================================================================

Total Photos Analyzed: 400

================================================================================
LENS USAGE (Top 10)
================================================================================
  Olympus M.Zuiko Digital ED 12-40mm F2.8 Pro         250 photos ( 62.5%)
  Canon RF 24-105mm F4L IS USM                        150 photos ( 37.5%)

================================================================================
APERTURE USAGE BY LENS (Top 10 per lens)
================================================================================

  Canon RF 24-105mm F4L IS USM
  ----------------------------------------------------------------------------
    f/4.0             85 times ( 56.7%)
    f/5.6             45 times ( 30.0%)
    f/8.0             20 times ( 13.3%)

  Olympus M.Zuiko Digital ED 12-40mm F2.8 Pro
  ----------------------------------------------------------------------------
    f/5.6            120 times ( 48.0%)
    f/8.0             80 times ( 32.0%)
    f/6.3             50 times ( 20.0%)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions, issues, and feature requests are welcome!

## Author

**Javi Aparicio**
- Website: [javiapariciofoto.ch](javiapariciofoto.ch)

## Acknowledgments

- Built using [ExifTool](https://exiftool.org/) by Phil Harvey
- Supports all major camera brands and RAW formats


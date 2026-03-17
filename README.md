# PyAssetStudio
PyAssetStudio is a simple viewer for Unity AssetBundle files, built using [UnityPy](https://github.com/K0lb3/UnityPy). It provides a lightweight alternative to AssetStudioGUI with basic functionality for inspecting and extracting assets from Unity games and applications.
## Features
- **Drag and Drop Support**: Easily open AssetBundle files by dragging them onto the application window.
- **Command Line Interface**: Open files directly via command line arguments (useful for "Open with" file associations).
- **Windows File Association**: Register the application to open AssetBundle files (.assetbundle, .unity3d, etc.) by double-clicking.
- **Asset Inspection**: View information about assets contained within bundles, including type, name, size, and path ID.
- **Basic Extraction**: Extract assets to disk for further use or analysis.
## Why This Project?
While tools like AssetStudioGUI offer comprehensive asset viewing and extraction capabilities, they can be heavyweight and may require additional dependencies. PyAssetStudio aims to provide:
- A **minimalistic** and **easy-to-use** interface for quick asset inspection.
- A **Python-based** solution that is easy to modify and extend.
- **Portability** across platforms where Python and UnityPy are available.
- A **learning resource** for those interested in understanding how Unity asset bundles work and how to parse them with UnityPy.
## Getting Started
### Prerequisites
- Python 3.7+
- Required Python packages (see `requirements.txt`)
### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/PyAssetStudio.git
   cd PyAssetStudio
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
### Usage
Run the main script:
```bash
python asset_studio.py
```
You can then drag and drop AssetBundle files onto the window, or use the command line:
```bash
python asset_studio.py path/to/your/file.assetbundle
```
### File Association (Windows)
To set up double-click opening of AssetBundle files:
1. Run `register_file_association.bat` as Administrator.
2. This will associate .assetbundle and .unity3d files with PyAssetStudio.
## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
## License
This project is open source and available under the [MIT License](LICENSE).
## Acknowledgments
- [UnityPy](https://github.com/K0lb3/UnityPy) for the powerful Unity asset parsing library.
- The AssetStudio team for inspiration and reference implementation.

"""
PyAssetStudio - A simple AssetBundle viewer using UnityPy
Similar to AssetStudioGUI but with basic functionality

Supports:
- Drag and drop files
- Command line arguments (for "Open with" functionality)
- Windows file association
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import UnityPy
from UnityPy.enums import ClassIDType
import os
import sys
import threading
from typing import Dict, List, Any, Optional

from unitypy_compat import apply_unitypy_version_tolerance


apply_unitypy_version_tolerance()

# Try to import tkinterdnd2 for drag and drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except ImportError:
    HAS_DND = False


class AssetInfo:
    """Store information about a single asset"""

    def __init__(self, obj, container_path: str = "", source_file: str = ""):
        self.obj = obj
        self.container_path = container_path
        self.source_file = source_file
        self.path_id = obj.path_id
        self.type = obj.type.name
        self.name = self._get_name()
        self.size = obj.byte_size

    def _get_name(self) -> str:
        """Try to get the name of the asset with multiple fallback strategies"""
        name = None

        try:
            data = self.obj.read()

            # Strategy 1: Direct name attribute
            if hasattr(data, "name") and data.name:
                name = data.name
            elif hasattr(data, "m_Name") and data.m_Name:
                name = data.m_Name

            # Strategy 2: Type-specific name extraction
            if not name:
                if self.obj.type == ClassIDType.Shader:
                    # Try to get shader name from parsed name
                    if hasattr(data, "m_ParsedForm"):
                        parsed = data.m_ParsedForm
                        if hasattr(parsed, "m_Name") and parsed.m_Name:
                            name = parsed.m_Name
                    # Fallback to m_Script if available
                    if not name and hasattr(data, "m_Script") and data.m_Script:
                        script = data.m_Script
                        if isinstance(script, bytes):
                            script = script.decode("utf-8", errors="replace")
                        # Extract shader name from first line
                        lines = script.split("\n")
                        for line in lines[:5]:
                            if "Shader" in line and '"' in line:
                                start = line.find('"') + 1
                                end = line.find('"', start)
                                if start > 0 and end > start:
                                    name = line[start:end]
                                    break

                elif self.obj.type == ClassIDType.MonoBehaviour:
                    # Try script reference name
                    if hasattr(data, "m_Script") and data.m_Script:
                        script_ref = data.m_Script
                        if hasattr(script_ref, "read"):
                            try:
                                script_data = script_ref.read()
                                if (
                                    hasattr(script_data, "m_Name")
                                    and script_data.m_Name
                                ):
                                    name = f"MonoBehaviour ({script_data.m_Name})"
                            except:
                                pass

                elif self.obj.type == ClassIDType.Material:
                    if hasattr(data, "m_Shader") and data.m_Shader:
                        shader_ref = data.m_Shader
                        if hasattr(shader_ref, "read"):
                            try:
                                shader_data = shader_ref.read()
                                if (
                                    hasattr(shader_data, "m_Name")
                                    and shader_data.m_Name
                                ):
                                    name = f"Material ({shader_data.m_Name})"
                            except:
                                pass

        except Exception:
            pass

        # Strategy 3: Use container path if available
        if not name and self.container_path:
            # Extract filename from container path
            path_name = self.container_path.split("/")[-1]
            if path_name:
                name = path_name

        # Strategy 4: Use source file name with type
        if not name and self.source_file:
            base_name = os.path.basename(self.source_file)
            name = f"{base_name} [{self.obj.type.name}]"

        # Final fallback
        if not name:
            name = f"PathID_{self.path_id}"

        return name

    def get_details(self) -> Dict[str, Any]:
        """Get detailed information about the asset"""
        details = {
            "Path ID": self.path_id,
            "Type": self.type,
            "Name": self.name,
            "Size": f"{self.size:,} bytes",
            "Container": self.container_path or "(none)",
            "Source File": os.path.basename(self.source_file)
            if self.source_file
            else "(unknown)",
        }

        try:
            data = self.obj.read()
            # Add type-specific details
            if self.obj.type == ClassIDType.Texture2D:
                details["Width"] = getattr(data, "m_Width", "N/A")
                details["Height"] = getattr(data, "m_Height", "N/A")
                details["Format"] = getattr(data, "m_TextureFormat", "N/A")
            elif self.obj.type == ClassIDType.AudioClip:
                details["Channels"] = getattr(data, "m_Channels", "N/A")
                details["Frequency"] = getattr(data, "m_Frequency", "N/A")
                details["Length"] = getattr(data, "m_Length", "N/A")
            elif self.obj.type == ClassIDType.Mesh:
                details["Vertices"] = getattr(data, "m_VertexCount", "N/A")
                details["Submeshes"] = (
                    len(getattr(data, "m_SubMeshes", []))
                    if hasattr(data, "m_SubMeshes")
                    else "N/A"
                )
            elif self.obj.type == ClassIDType.TextAsset:
                script = getattr(data, "m_Script", None)
                if script:
                    if isinstance(script, bytes):
                        details["Content Length"] = f"{len(script):,} bytes"
                    else:
                        details["Content Length"] = f"{len(str(script)):,} chars"
            elif self.obj.type == ClassIDType.MonoBehaviour:
                script_ref = getattr(data, "m_Script", None)
                if script_ref and hasattr(script_ref, "read"):
                    try:
                        script_data = script_ref.read()
                        details["Script Class"] = getattr(script_data, "m_Name", "N/A")
                    except:
                        details["Script Class"] = "N/A"
            elif self.obj.type == ClassIDType.Sprite:
                details["Rect"] = str(getattr(data, "m_Rect", "N/A"))
            elif self.obj.type == ClassIDType.Shader:
                if hasattr(data, "m_ParsedForm") and data.m_ParsedForm:
                    parsed = data.m_ParsedForm
                    details["Shader Name"] = getattr(parsed, "m_Name", "N/A")
                    if hasattr(parsed, "m_FallbackName") and parsed.m_FallbackName:
                        details["Fallback"] = parsed.m_FallbackName
                    if (
                        hasattr(parsed, "m_CustomEditorName")
                        and parsed.m_CustomEditorName
                    ):
                        details["Custom Editor"] = parsed.m_CustomEditorName
                    if hasattr(parsed, "m_SubShaders"):
                        details["SubShaders"] = len(parsed.m_SubShaders)
                        total_passes = sum(
                            len(getattr(s, "m_Passes", [])) for s in parsed.m_SubShaders
                        )
                        details["Total Passes"] = total_passes
                    if hasattr(parsed, "m_PropInfo") and parsed.m_PropInfo:
                        props = getattr(parsed.m_PropInfo, "m_Props", [])
                        if props:
                            details["Properties"] = len(props)

        except Exception as e:
            details["Read Error"] = str(e)

        return details

    def get_text_content(self) -> Optional[str]:
        """Get text content if this is a text-based asset"""
        try:
            data = self.obj.read()

            # TextAsset
            if self.obj.type == ClassIDType.TextAsset:
                script = getattr(data, "m_Script", None)
                if script:
                    if isinstance(script, bytes):
                        return script.decode("utf-8", errors="replace")
                    return str(script)

            # Shader - use UnityPy's built-in export to decompile
            elif self.obj.type == ClassIDType.Shader:
                # Primary method: use UnityPy's ShaderConverter to decompile
                try:
                    exported = data.export()
                    if exported and exported.strip():
                        return exported
                except Exception as export_err:
                    pass

                # Fallback: show parsed form metadata
                content_parts = []
                if hasattr(data, "m_ParsedForm") and data.m_ParsedForm:
                    parsed = data.m_ParsedForm
                    content_parts.append(f"[Shader export failed: {export_err}]\n\n")
                    content_parts.append("=== Parsed Form (metadata only) ===\n\n")
                    if hasattr(parsed, "m_Name"):
                        content_parts.append(f"Name: {parsed.m_Name}\n")
                    if hasattr(parsed, "m_SubShaders"):
                        content_parts.append(
                            f"SubShaders: {len(parsed.m_SubShaders)}\n"
                        )
                    if hasattr(parsed, "m_PropInfo") and parsed.m_PropInfo:
                        props = getattr(parsed.m_PropInfo, "m_Props", [])
                        if props:
                            content_parts.append(f"\nProperties ({len(props)}):\n")
                            for prop in props[:50]:
                                if hasattr(prop, "m_Name"):
                                    prop_type = getattr(prop, "m_Type", "?")
                                    prop_desc = getattr(prop, "m_Description", "")
                                    desc_str = f' "{prop_desc}"' if prop_desc else ""
                                    content_parts.append(
                                        f"  {prop.m_Name}{desc_str} ({prop_type})\n"
                                    )

                if content_parts:
                    return "".join(content_parts)

                return "[Compiled shader - could not decompile]"

            # MonoBehaviour - try to dump as readable format
            elif self.obj.type == ClassIDType.MonoBehaviour:
                try:
                    tree = self.obj.read_typetree()
                    if tree:
                        return self._format_tree(tree)
                except:
                    pass

        except Exception as e:
            return f"[Error reading content: {e}]"

        return None

    def _format_tree(self, data, indent: int = 0) -> str:
        """Format type tree data as readable text"""
        lines = []
        prefix = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._format_tree(value, indent + 1))
                else:
                    str_val = str(value)
                    if len(str_val) > 200:
                        str_val = str_val[:200] + "..."
                    lines.append(f"{prefix}{key}: {str_val}")
        elif isinstance(data, list):
            for i, item in enumerate(data[:100]):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}[{i}]:")
                    lines.append(self._format_tree(item, indent + 1))
                else:
                    lines.append(f"{prefix}[{i}]: {item}")
            if len(data) > 100:
                lines.append(f"{prefix}... and {len(data) - 100} more items")
        else:
            lines.append(f"{prefix}{data}")

        return "\n".join(lines)


class PyAssetStudio:
    """Main application class"""

    def __init__(self, root: tk.Tk, initial_files: List[str] = None):
        self.root = root
        self.root.title("PyAssetStudio")
        self.root.geometry("1200x700")

        # Data storage
        self.assets: Dict[str, AssetInfo] = {}  # item_id -> AssetInfo
        self.loaded_files: List[str] = []
        self.current_env = None
        self.initial_files = initial_files or []

        self._setup_ui()
        self._setup_menu()
        self._setup_bindings()
        self._setup_drag_drop()

        # Load initial files after UI is ready
        if self.initial_files:
            self.root.after(100, lambda: self._load_files(self.initial_files))

    def _setup_ui(self):
        """Setup the main UI components"""
        # Main paned window
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left frame - Asset tree
        left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(left_frame, weight=2)

        # Search frame
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(search_frame, text="Filter:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_filter_changed)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Type filter
        ttk.Label(search_frame, text="Type:").pack(side=tk.LEFT, padx=(10, 0))
        self.type_filter_var = tk.StringVar(value="All")
        self.type_filter_combo = ttk.Combobox(
            search_frame, textvariable=self.type_filter_var, state="readonly", width=15
        )
        self.type_filter_combo["values"] = ["All"]
        self.type_filter_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.type_filter_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Tree view with columns
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "type", "size", "path_id")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="extended"
        )

        # Column headings
        self.tree.heading("name", text="Name", command=lambda: self._sort_tree("name"))
        self.tree.heading("type", text="Type", command=lambda: self._sort_tree("type"))
        self.tree.heading("size", text="Size", command=lambda: self._sort_tree("size"))
        self.tree.heading(
            "path_id", text="Path ID", command=lambda: self._sort_tree("path_id")
        )

        # Column widths
        self.tree.column("name", width=300, minwidth=100)
        self.tree.column("type", width=120, minwidth=80)
        self.tree.column("size", width=100, minwidth=60)
        self.tree.column("path_id", width=100, minwidth=60)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Right frame - Details
        right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(right_frame, weight=1)

        ttk.Label(
            right_frame, text="Asset Details", font=("TkDefaultFont", 10, "bold")
        ).pack(anchor=tk.W)

        # Details text with both scrollbars
        details_frame = ttk.Frame(right_frame)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.details_text = tk.Text(
            details_frame, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 10)
        )
        details_vsb = ttk.Scrollbar(
            details_frame, orient=tk.VERTICAL, command=self.details_text.yview
        )
        details_hsb = ttk.Scrollbar(
            details_frame, orient=tk.HORIZONTAL, command=self.details_text.xview
        )
        self.details_text.configure(
            yscrollcommand=details_vsb.set, xscrollcommand=details_hsb.set
        )

        # Grid layout for details text with scrollbars
        self.details_text.grid(row=0, column=0, sticky="nsew")
        details_vsb.grid(row=0, column=1, sticky="ns")
        details_hsb.grid(row=1, column=0, sticky="ew")
        details_frame.grid_rowconfigure(0, weight=1)
        details_frame.grid_columnconfigure(0, weight=1)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")

    def _setup_menu(self):
        """Setup the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Open File...", command=self._open_file, accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Open Folder...",
            command=self._open_folder,
            accelerator="Ctrl+Shift+O",
        )
        file_menu.add_separator()
        file_menu.add_command(label="Clear", command=self._clear_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Export menu
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Export", menu=export_menu)
        export_menu.add_command(
            label="Export Selected...", command=self._export_selected
        )
        export_menu.add_command(label="Export All...", command=self._export_all)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _setup_bindings(self):
        """Setup keyboard bindings"""
        self.root.bind("<Control-o>", lambda e: self._open_file())
        self.root.bind("<Control-O>", lambda e: self._open_folder())
        self.root.bind("<Control-Shift-o>", lambda e: self._open_folder())
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _setup_drag_drop(self):
        """Setup drag and drop support"""
        if HAS_DND:
            # Register for drag and drop
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)
            self.status_var.set("Ready - Drag and drop files here to open")
        else:
            self.status_var.set("Ready (install tkinterdnd2 for drag & drop)")

    def _on_drop(self, event):
        """Handle dropped files"""
        files = self._parse_drop_data(event.data)
        if files:
            self._load_files(files)

    def _parse_drop_data(self, data: str) -> List[str]:
        """Parse drag and drop data to extract file paths"""
        import re

        files = []
        # Handle Windows format with braces for paths with spaces
        if "{" in data:
            matches = re.findall(r"\{([^}]+)\}|(\S+)", data)
            for match in matches:
                path = match[0] or match[1]
                if path and os.path.exists(path):
                    files.append(path)
        else:
            # Simple space or newline separated
            for path in data.replace("\r", "").split("\n"):
                path = path.strip()
                if path and os.path.exists(path):
                    files.append(path)
        return files

    def _open_file(self):
        """Open a single file"""
        filetypes = [
            ("All supported files", "*.ab;*.bundle;*.unity3d;*.assets;*"),
            ("AssetBundle files", "*.ab;*.bundle;*.unity3d"),
            ("Assets files", "*.assets"),
            ("All files", "*.*"),
        ]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self._load_files([filepath])

    def _open_folder(self):
        """Open a folder and load all asset files"""
        folder = filedialog.askdirectory()
        if folder:
            files = []
            for root, dirs, filenames in os.walk(folder):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    files.append(filepath)
            if files:
                self._load_files(files)
            else:
                messagebox.showinfo("Info", "No files found in the selected folder.")

    def _load_files(self, files: List[str]):
        """Load asset files in a background thread"""
        self.progress.pack(fill=tk.X, side=tk.BOTTOM, before=self.status_bar)
        self.progress.start()
        self.status_var.set(f"Loading {len(files)} file(s)...")

        def load_thread():
            try:
                self._do_load_files(files)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, self._loading_complete)

        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()

    def _do_load_files(self, files: List[str]):
        """Actually load the files (runs in background thread)"""
        all_types = set(["All"])

        for filepath in files:
            try:
                env = UnityPy.load(filepath)
                self.loaded_files.append(filepath)

                # Load dependencies (including .resS/.ress files)
                try:
                    if hasattr(env, "file") and env.file:
                        env.file.load_dependencies()
                except Exception as dep_err:
                    print(
                        f"Warning: Could not load dependencies for {filepath}: {dep_err}"
                    )

                # Build container map
                container_map = {}
                for container_path, obj in env.container.items():
                    container_map[obj.path_id] = container_path

                # Process all objects
                for obj in env.objects:
                    container_path = container_map.get(obj.path_id, "")
                    asset_info = AssetInfo(obj, container_path, filepath)

                    # Generate unique item ID
                    item_id = f"{filepath}_{obj.path_id}"
                    self.assets[item_id] = asset_info
                    all_types.add(asset_info.type)

                    # Add to tree (in main thread)
                    self.root.after(
                        0,
                        lambda aid=item_id, ai=asset_info: self._add_tree_item(aid, ai),
                    )

            except Exception as e:
                print(f"Error loading {filepath}: {e}")

        # Update type filter
        self.root.after(0, lambda: self._update_type_filter(sorted(all_types)))

    def _add_tree_item(self, item_id: str, asset_info: AssetInfo):
        """Add an item to the tree view"""
        self.tree.insert(
            "",
            tk.END,
            iid=item_id,
            values=(
                asset_info.name,
                asset_info.type,
                f"{asset_info.size:,}",
                asset_info.path_id,
            ),
        )

    def _update_type_filter(self, types: List[str]):
        """Update the type filter combobox"""
        self.type_filter_combo["values"] = types

    def _loading_complete(self):
        """Called when loading is complete"""
        self.progress.stop()
        self.progress.pack_forget()

        # Calculate total size of all assets
        total_size = sum(asset.size for asset in self.assets.values())

        # Format size for display
        if total_size >= 1024**3:
            size_str = f"{total_size / (1024**3):.2f} GB"
        elif total_size >= 1024**2:
            size_str = f"{total_size / (1024**2):.2f} MB"
        elif total_size >= 1024:
            size_str = f"{total_size / 1024:.2f} KB"
        else:
            size_str = f"{total_size} bytes"

        self.status_var.set(
            f"Loaded {len(self.assets)} assets from {len(self.loaded_files)} file(s) | Total: {size_str} ({total_size:,} bytes)"
        )

        # Sort by size descending by default after loading
        self._sort_tree("size", initial_sort=True)

    def _clear_all(self):
        """Clear all loaded data"""
        self.tree.delete(*self.tree.get_children())
        self.assets.clear()
        self.loaded_files.clear()
        self.type_filter_combo["values"] = ["All"]
        self.type_filter_var.set("All")
        self.search_var.set("")
        self._clear_details()
        self.status_var.set("Ready")

    def _on_tree_select(self, event):
        """Handle tree selection"""
        selection = self.tree.selection()
        if len(selection) == 1:
            item_id = selection[0]
            if item_id in self.assets:
                self._show_details(self.assets[item_id])
        elif len(selection) > 1:
            self._show_multi_selection(len(selection))
        else:
            self._clear_details()

    def _on_tree_double_click(self, event):
        """Handle double-click on tree item"""
        selection = self.tree.selection()
        if len(selection) == 1:
            item_id = selection[0]
            if item_id in self.assets:
                # Could add preview functionality here
                pass

    def _show_details(self, asset_info: AssetInfo):
        """Show details for selected asset"""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)

        # Show basic details
        details = asset_info.get_details()
        for key, value in details.items():
            self.details_text.insert(tk.END, f"{key}: {value}\n")

        # Show text content if available
        text_content = asset_info.get_text_content()
        if text_content:
            self.details_text.insert(tk.END, "\n" + "=" * 50 + "\n")
            self.details_text.insert(tk.END, "Content:\n")
            self.details_text.insert(tk.END, "=" * 50 + "\n\n")
            # Limit content length for display
            if len(text_content) > 50000:
                text_content = text_content[
                    :50000
                ] + "\n\n... [Content truncated, total {:,} chars]".format(
                    len(text_content)
                )
            self.details_text.insert(tk.END, text_content)

        self.details_text.config(state=tk.DISABLED)

    def _show_multi_selection(self, count: int):
        """Show info for multiple selection"""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, f"{count} items selected")
        self.details_text.config(state=tk.DISABLED)

    def _clear_details(self):
        """Clear the details panel"""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state=tk.DISABLED)

    def _on_filter_changed(self, *args):
        """Handle filter change"""
        search_text = self.search_var.get().lower()
        type_filter = self.type_filter_var.get()

        # Show/hide items based on filter
        for item_id, asset_info in self.assets.items():
            show = True

            # Check name filter
            if search_text and search_text not in asset_info.name.lower():
                show = False

            # Check type filter
            if type_filter != "All" and asset_info.type != type_filter:
                show = False

            # Update visibility
            try:
                if show:
                    # Check if item exists, if not add it
                    if not self.tree.exists(item_id):
                        self.tree.insert(
                            "",
                            tk.END,
                            iid=item_id,
                            values=(
                                asset_info.name,
                                asset_info.type,
                                f"{asset_info.size:,}",
                                asset_info.path_id,
                            ),
                        )
                else:
                    if self.tree.exists(item_id):
                        self.tree.delete(item_id)
            except tk.TclError:
                pass

    def _sort_tree(self, column: str, initial_sort: bool = False):
        """Sort tree by column"""
        items = [
            (self.tree.set(item, column), item) for item in self.tree.get_children()
        ]

        # Determine sort order
        if initial_sort and column == "size":
            # For initial sort on size, default to descending
            reverse = True
        elif hasattr(self, "_last_sort") and self._last_sort == column:
            reverse = not getattr(self, "_last_reverse", False)
        else:
            reverse = False
        self._last_sort = column
        self._last_reverse = reverse

        # Sort items
        if column == "size":
            items.sort(key=lambda x: int(x[0].replace(",", "")), reverse=reverse)
        elif column == "path_id":
            items.sort(key=lambda x: int(x[0]), reverse=reverse)
        else:
            items.sort(key=lambda x: x[0].lower(), reverse=reverse)

        # Rearrange items
        for index, (_, item) in enumerate(items):
            self.tree.move(item, "", index)

    def _export_selected(self):
        """Export selected assets"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Info", "No assets selected.")
            return

        folder = filedialog.askdirectory(title="Select Export Folder")
        if not folder:
            return

        exported = 0
        for item_id in selection:
            if item_id in self.assets:
                if self._export_asset(self.assets[item_id], folder):
                    exported += 1

        messagebox.showinfo("Export Complete", f"Exported {exported} asset(s).")

    def _export_all(self):
        """Export all assets"""
        if not self.assets:
            messagebox.showinfo("Info", "No assets loaded.")
            return

        folder = filedialog.askdirectory(title="Select Export Folder")
        if not folder:
            return

        exported = 0
        for asset_info in self.assets.values():
            if self._export_asset(asset_info, folder):
                exported += 1

        messagebox.showinfo("Export Complete", f"Exported {exported} asset(s).")

    def _export_asset(self, asset_info: AssetInfo, folder: str) -> bool:
        """Export a single asset"""
        try:
            data = asset_info.obj.read()

            # Sanitize asset name: replace path separators to avoid
            # FileNotFoundError from names like "MLBBBuiltin/Legacy Shaders/VertexLit"
            safe_name = asset_info.name.replace("/", "_").replace("\\", "_")

            if asset_info.obj.type == ClassIDType.Texture2D:
                # Export as PNG
                img = data.image
                filepath = os.path.join(folder, f"{safe_name}.png")
                img.save(filepath)
                return True

            elif asset_info.obj.type == ClassIDType.TextAsset:
                # Export as text
                script = data.m_Script
                if isinstance(script, bytes):
                    script = script.decode("utf-8", errors="replace")
                filepath = os.path.join(folder, f"{safe_name}.txt")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(script)
                return True

            elif asset_info.obj.type == ClassIDType.AudioClip:
                # Export audio
                for name, audio_data in data.samples.items():
                    safe_audio_name = name.replace("/", "_").replace("\\", "_")
                    filepath = os.path.join(folder, f"{safe_audio_name}")
                    with open(filepath, "wb") as f:
                        f.write(audio_data)
                return True

            elif asset_info.obj.type == ClassIDType.Sprite:
                # Export sprite as PNG
                img = data.image
                filepath = os.path.join(folder, f"{safe_name}.png")
                img.save(filepath)
                return True

            elif asset_info.obj.type == ClassIDType.Shader:
                # Export shader using UnityPy's built-in decompiler
                filepath = os.path.join(folder, f"{safe_name}.shader")
                try:
                    exported = data.export()
                    if exported and exported.strip():
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(exported)
                        return True
                except Exception:
                    pass
                # Fallback: export raw data
                raw_data = asset_info.obj.get_raw_data()
                filepath = os.path.join(
                    folder, f"{safe_name}_{asset_info.path_id}.shader.dat"
                )
                with open(filepath, "wb") as f:
                    f.write(raw_data)
                return True

            else:
                # Export raw data for other types
                raw_data = asset_info.obj.get_raw_data()
                filepath = os.path.join(folder, f"{safe_name}_{asset_info.path_id}.dat")
                with open(filepath, "wb") as f:
                    f.write(raw_data)
                return True

        except Exception as e:
            print(f"Error exporting {asset_info.name}: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About PyAssetStudio",
            "PyAssetStudio v1.0\n\n"
            "A simple AssetBundle viewer\n"
            "Built with UnityPy and Tkinter\n\n"
            "Similar to AssetStudioGUI",
        )


def main():
    # Parse command line arguments (for "Open with" functionality)
    initial_files = []
    for arg in sys.argv[1:]:
        if os.path.exists(arg):
            initial_files.append(arg)

    # Use TkinterDnD if available for drag and drop support
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = PyAssetStudio(root, initial_files)
    root.mainloop()


def create_file_association():
    """Create Windows file association (run as admin)"""
    import winreg
    import sys

    exe_path = sys.executable
    script_path = os.path.abspath(__file__)

    # File types to associate
    extensions = [".unity3d", ".ab", ".bundle", ".assets"]

    try:
        for ext in extensions:
            # Create extension key
            key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ext)
            winreg.SetValue(key, "", winreg.REG_SZ, "PyAssetStudio")
            winreg.CloseKey(key)

        # Create PyAssetStudio key
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "PyAssetStudio")
        winreg.SetValue(key, "", winreg.REG_SZ, "Unity Asset Bundle")
        winreg.CloseKey(key)

        # Create shell\open\command
        key = winreg.CreateKey(
            winreg.HKEY_CLASSES_ROOT, r"PyAssetStudio\shell\open\command"
        )
        winreg.SetValue(key, "", winreg.REG_SZ, f'"{exe_path}" "{script_path}" "%1"')
        winreg.CloseKey(key)

        print("File associations created successfully!")
        print("Associated extensions:", extensions)
    except PermissionError:
        print("Error: Run as administrator to create file associations")
    except Exception as e:
        print(f"Error creating file associations: {e}")


if __name__ == "__main__":
    # Check if we should create file associations
    if len(sys.argv) > 1 and sys.argv[1] == "--register":
        create_file_association()
    else:
        main()

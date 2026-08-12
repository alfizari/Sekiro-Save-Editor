import os
import struct
import hashlib
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from pathlib import Path

# ===== BACKEND CODE FROM YOUR SCRIPT =====

MODE = None
FILE_PATH = None
current_data = None

# Offsets
steam_id = 0x33E54
emblem_off = 0x3459A
attacks_off = 0x3449C
skill_points_off = 0x345B4
gaurd_off = 0x34488
hp_off = 0x3446C
souls_off = 0x344D0

working_directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(working_directory)

# Load JSONs
def load_and_copy_json(file_name):
    file_path = os.path.join(working_directory, file_name)
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

weapons_json = load_and_copy_json('weapons.json')
goods_json = load_and_copy_json('goods.json')
armor_json = load_and_copy_json('armor.json')

def write_value_at_offset(data, offset, value, byte_size=4):
    value_bytes = value.to_bytes(byte_size, 'little')
    return data[:offset] + value_bytes + data[offset+byte_size:]

def read_file(file_path):
    with open(file_path, 'rb') as f:
        return f.read()

def write_file(file_path, data):
    with open(file_path, 'wb') as f:
        f.write(data)
    return True

def split_pc_files(data):
    split_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'split_files')
    os.makedirs(split_dir, exist_ok=True)
    
    bnd_data = data[:0x300]
    write_file(os.path.join(split_dir, 'header'), bnd_data)
    
    start_offset = 0x310
    for i in range(10):
        user_data = data[start_offset:start_offset+0x100000]
        start_offset += 0x100010
        write_file(os.path.join(split_dir, f"userdata000{i}"), user_data)
    
    rest_of_data = data[start_offset-0x10:]
    write_file(os.path.join(split_dir, 'ud10-11'), rest_of_data)
    return True

def merge_pc_files(output_path):
    split_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'split_files')
    
    pc_header = read_file(os.path.join(split_dir, 'header'))
    ud_buff = b""
    
    for i in range(10):
        bf_data = read_file(os.path.join(split_dir, f'userdata000{i}'))
        m = hashlib.md5(bf_data).digest()
        ud_buff += (m + bf_data)
    
    ud_rem = read_file(os.path.join(split_dir, 'ud10-11'))
    out_data = pc_header + ud_buff + ud_rem
    write_file(output_path, out_data)
    return True

def show_ud_files():
    split_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "split_files")
    if not os.path.exists(split_dir):
        return []
    return sorted([
        os.path.join(split_dir, f)
        for f in os.listdir(split_dir)
        if os.path.isfile(os.path.join(split_dir, f)) and f.startswith("userdata")
    ])

# Item type constants
ITEM_TYPE_EMPTY = 0x00000000
ITEM_TYPE_WEAPON = 0x80000000
ITEM_TYPE_ARMOR = 0x90000000
ITEM_TYPE_GOOD = 0xB0000000

class GA_Item:
    BASE_SIZE = 0x3C
    def __init__(self, gaitem_handle, item_id, quantity, index, offset):
        self.gaitem_handle = gaitem_handle
        self.item_id = item_id
        self.quantity = quantity
        self.index = index
        self.offset = offset
        self.size = self.BASE_SIZE

    @classmethod
    def from_bytes(cls, data, offset=0):
        gaitem_handle, item_id = struct.unpack_from("<II", data, offset)
        return cls(gaitem_handle, item_id, 0, 0, offset)

class INVENTORY:
    BASE_SIZE = 16
    def __init__(self, gaitem_handle, item_id, quantity, index, offset):
        self.gaitem_handle = gaitem_handle
        self.item_id = item_id
        self.quantity = quantity
        self.index = index
        self.offset = offset
        self.size = self.BASE_SIZE

    @classmethod
    def from_bytes(cls, data, offset=0):
        gaitem_handle, item_id, quantity, index = struct.unpack_from("<IIII", data, offset)
        return cls(gaitem_handle, item_id, quantity, index, offset)

def parse_ga(data_type, start_offset, end_offset):
    ga_items = []
    offset = start_offset
    while offset < end_offset:
        item = GA_Item.from_bytes(data_type, offset)
        ga_items.append(item)
        offset += item.size
    return ga_items

def parse_inventory(data, start_offset, end_offset):
    inventory_item = []
    offset = start_offset
    while offset < end_offset:
        item = INVENTORY.from_bytes(data, offset)
        inventory_item.append(item)
        offset += item.size
    return inventory_item

def parse_inventory_key(data, start_offset, end_offset):
    inventory_item_key = []
    offset = start_offset
    while offset < end_offset:
        item = INVENTORY.from_bytes(data, offset)
        inventory_item_key.append(item)
        offset += item.size
    return inventory_item_key

def load_data(data):
    stats = {}
    try:
        stats['steam_id'] = struct.unpack_from('<Q', data, steam_id)[0]
        stats['attack'] = struct.unpack_from('<B', data, attacks_off)[0]
        stats['NG+'] = struct.unpack_from('<B', data, 0x33F34)[0]
        stats['guard'] = struct.unpack_from('<I', data, gaurd_off)[0]
        stats['emblem'] = struct.unpack_from('<B', data, emblem_off)[0]
        stats['skill_points'] = struct.unpack_from('<I', data, skill_points_off)[0]
        stats['hp'] = struct.unpack_from('<I', data, hp_off)[0]
        stats['souls'] = struct.unpack_from('<I', data, souls_off)[0]
    except:
        pass
    return stats

def get_inventory_data(data):
    weapons, armors, goods, empty, all_items = [], [], [], [], []
    
    start_offset = 0x8F70C
    end_offset = start_offset + 0x7000
    items = parse_inventory(data, start_offset, end_offset)
    
    for item in items:
        type_bits = item.gaitem_handle & 0xF0000000
        item_id = item.item_id & 0x00FFFFFF
        all_items.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
        
        if type_bits == ITEM_TYPE_WEAPON:
            weapons.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
        elif type_bits == ITEM_TYPE_ARMOR:
            armors.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
        elif type_bits == ITEM_TYPE_GOOD:
            goods.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
        elif type_bits == ITEM_TYPE_EMPTY:
            empty.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
    
    return weapons, armors, goods, empty, all_items

def get_storage_data(data):
    goods_storage, empty_storage, all_items_storage = [], [], []
    
    start_offset = 0x987A0
    end_offset = start_offset + 0x9000
    items = parse_inventory(data, start_offset, end_offset)
    
    for item in items:
        type_bits = item.gaitem_handle & 0xF0000000
        item_id = item.item_id & 0x00FFFFFF
        all_items_storage.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
        
        if type_bits == ITEM_TYPE_GOOD:
            goods_storage.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
        elif type_bits == ITEM_TYPE_EMPTY:
            empty_storage.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
    
    return goods_storage, empty_storage, all_items_storage

def get_inventory_data_key(data):
    goods_key, empty_key, all_items_key = [], [], []
    
    start_offset = 0x9670C
    end_offset = start_offset + 0x2000
    items = parse_inventory(data, start_offset, end_offset)
    
    for item in items:
        type_bits = item.gaitem_handle & 0xF0000000
        item_id = item.item_id & 0x00FFFFFF
        all_items_key.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
        
        if type_bits == ITEM_TYPE_GOOD:
            goods_key.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
        elif type_bits == ITEM_TYPE_EMPTY:
            empty_key.append((item.gaitem_handle, item_id, item.quantity, item.index, item.offset))
    
    return goods_key, empty_key, all_items_key

def update_skill_point(data, value):
    if value > 0x3B9AC9FF:
        value = 0x3B9AC9FF
    return write_value_at_offset(data, skill_points_off, value, 4)

def update_max_emblem_limit(data, value):
    if value > 0x62:
        value = 0x62
    return write_value_at_offset(data, emblem_off, value, 1)

def update_gaurd(data, value):
    if value > 0xFFFFFFFF:
        value = 0xFFFFFFFF
    return write_value_at_offset(data, gaurd_off, value, 4)

def update_hp(data, value):
    if value > 0xFFFFFFFF:
        value = 0xFFFFFFFF
    return write_value_at_offset(data, hp_off, value, 4)

def update_souls(data, value):
    if value > 0xFFFFFFFF:
        value = 0xFFFFFFFF
    return write_value_at_offset(data, souls_off, value, 4)

def update_attk(data, value):
    if value > 0x62:
        value = 0x62
    return write_value_at_offset(data, attacks_off, value, 1)

def update_ng(data, value):
    if value > 0xFF:
        value = 0xFF
    return write_value_at_offset(data, 0x33F34, value, 1)

def reset_skill_points(data):
    return write_value_at_offset(data, 0x345A8, 0, 0x10)

def inventory_counters(data):

    data=bytearray(data)
    first_counter_offset = 0x8F700
    first_val = struct.unpack_from("<H", data, first_counter_offset)[0]
    first_val += 1

    struct.pack_into("<H", data, first_counter_offset, first_val)

    second_counter_offset = 0x8F6FC
    second_val = struct.unpack_from("<H", data, second_counter_offset)[0]
    second_val += 1

    struct.pack_into("<H", data, second_counter_offset, second_val)

    #storage counter
    storage_counter_offset = 0xA1954
    storage_val = struct.unpack_from("<H", data, storage_counter_offset)[0]
    storage_val += 1
    struct.pack_into("<H", data, storage_counter_offset, storage_val)

    return data

def update_good_quantity(data, item_offset, new_quantity):
    if new_quantity > 99:
        new_quantity = 99
    quantity_offset = item_offset + 8
    return data[:quantity_offset] + new_quantity.to_bytes(4, 'little') + data[quantity_offset+4:]

def delete_good_item(data, item_offset):
    """Delete a good item by setting its 16-byte inventory slot to zeros"""
    zero_slot = b'\x00' * 16  # INVENTORY.BASE_SIZE = 16
    return data[:item_offset] + zero_slot + data[item_offset+16:]

def parse_lookup(data, start_offset, end_offset):
    storage_items = []
    offset = start_offset
    while offset < end_offset:
        item_id, quantity = struct.unpack_from("<II", data, offset)
        storage_items.append((item_id, quantity, offset))
        offset += 8
    return storage_items

def lookup_print(data):
    storage_all = []
    storage_empty = []

    start_offset = 0xA1958
    end_offset = start_offset + 0x4000

    for item_id, quantity, offset in parse_lookup(data, start_offset, end_offset):
        if item_id == 0:
            storage_empty.append((item_id, quantity, offset))
        else:
            storage_all.append((item_id, quantity, offset))

    print(f"Storage Items: {len(storage_all)}")
    return storage_all, storage_empty

def spawn_goods(data, item_name, item_quantity, Stack=False, quantity_override=False):
    weapons, armors, goods, empty, all_items = get_inventory_data(data)
    
    goods_lookup = {item["name"]: item["id"] for item in goods_json}
    
    if not data:
        return None
    
    if item_name not in goods_lookup:
        return None
    
    item_id_int = int(goods_lookup[item_name])
    
    if not quantity_override:
        if item_quantity > 99:
            item_quantity = 99
    
    if Stack == False:
        for i, (gaitem_handle, item_id, quantity, index, offset) in enumerate(goods):
            if item_id_int == item_id:
                quantity_offset = offset + 8
                data = (
                    data[:quantity_offset] 
                    + item_quantity.to_bytes(4, 'little') 
                    + data[quantity_offset+4:]
                )
                return data
    
    if not empty:
        return None
    
    empty_offset = empty[0][4]
    
    indexes = [item[3] & 0x0FFF for item in all_items]
    indexes.sort()
    highest_index = int(indexes[-1]) if indexes else 0
    highest_index += 1
    
    random_bytes = os.urandom(1)
    
    goods_slot = (
        item_id_int.to_bytes(4, 'little') +
        item_id_int.to_bytes(4, 'little') +
        item_quantity.to_bytes(4, 'little') +
        highest_index.to_bytes(4, 'little')
    )

    
    goods_slot = bytearray(goods_slot)
    goods_slot[3] = 0xB0
    goods_slot[7] = 0x40
    goods_slot[14] = random_bytes[0]
    
    data = data[:empty_offset] + bytes(goods_slot) + data[empty_offset+16:]
    data = inventory_counters(data)

    item_quantity=1
    #storage slot? 4 bytes item id ends with 40, 4 bytes quantity
    lookup_slot = (
        item_id_int.to_bytes(4, 'little') +
        item_quantity.to_bytes(4, 'little')
    )

    lookup_slot = bytearray(lookup_slot)
    lookup_slot[0x03]=0x40

    _, lookup_empty = lookup_print(data)

    if not lookup_empty:
        return None 

    empty_lookup_offset = lookup_empty[0][2]
    data = data[:empty_lookup_offset] + lookup_slot + data[empty_lookup_offset+8:]

    # storage_offset=
    return data

def spawn_weapon_armor(data, item_name, item_type):
    weapons, armors, goods, empty, all_items = get_inventory_data(data)
    
    weapons_lookup = {item["name"]: item["id"] for item in weapons_json}
    armors_lookup = {item["name"]: item["id"] for item in armor_json}
    
    # Find GA empty slots
    start_offset = 0x35614
    end_offset = start_offset + 0x59fc4 + 0x3c
    ga_items_list = parse_ga(data, start_offset, end_offset)
    
    ga_empty = []
    for item in ga_items_list:
        type_bits = item.gaitem_handle & 0xF0000000
        if type_bits == ITEM_TYPE_EMPTY:
            ga_empty.append((item.gaitem_handle, item.item_id, item.offset))
    
    if not data:
        return None
    
    if item_type == 'weapon' and item_name in weapons_lookup:
        item_id_int = int(weapons_lookup[item_name])
    elif item_type == 'armor' and item_name in armors_lookup:
        item_id_int = int(armors_lookup[item_name])
    else:
        return None
    
    # Get highest GA index
    highest_index_list = [item[0] & 0xFFFF0000 for item in (weapons + armors)]
    highest_index_list.sort()
    highest_index = int(highest_index_list[-1]) if highest_index_list else 0
    new_index = highest_index + 1
    
    # Create GA entry
    ga_slot_entry = (
        new_index.to_bytes(4, 'little') +
        item_id_int.to_bytes(4, 'little') +
        (0).to_bytes(0x34, 'little')
    )
    
    ga_slot_entry = bytearray(ga_slot_entry)
    ga_slot_entry[3] = 0x80 if item_type == 'weapon' else 0x90
    ga_slot_entry[2] = 0x80
    ga_slot_entry[16] = 0x01
    
    if item_type == 'armor':
        ga_slot_entry[7] = 0x10
        ga_slot_entry[8] = 0xe7
        ga_slot_entry[9] = 0x03
    
    if not ga_empty:
        return None
    
    empty_ga_offset = ga_empty[0][2]
    data = data[:empty_ga_offset] + ga_slot_entry + data[empty_ga_offset+0x3C:]
    
    # Create inventory entry
    if not empty:
        return None
    
    empty_offset = empty[0][4]
    indexes = [item[3] & 0x0FFF for item in all_items]
    indexes.sort()
    highest_index = int(indexes[-1]) if indexes else 0
    highest_index += 1
    
    random_bytes = os.urandom(2)
    item_quantity = 1
    
    goods_slot = (
        new_index.to_bytes(4, 'little') +
        item_id_int.to_bytes(4, 'little') +
        item_quantity.to_bytes(4, 'little') +
        highest_index.to_bytes(4, 'little')
    )
    
    goods_slot = bytearray(goods_slot)
    goods_slot[3] = 0x80 if item_type == 'weapon' else 0x90
    goods_slot[2] = 0x80
    if item_type == 'armor':
        goods_slot[7] = 0x10
    
    goods_slot[14:14+2] = random_bytes
    
    data = data[:empty_offset] + goods_slot + data[empty_offset+16:]
    data = inventory_counters(data)
    
    return data

# Create lookups
item_lookup = {}
for item in weapons_json + armor_json + goods_json:
    item_lookup[int(item["id"])] = item["name"]

goods_lookup = {item["name"]: item["id"] for item in goods_json}
weapons_lookup = {item["name"]: item["id"] for item in weapons_json}
armors_lookup = {item["name"]: item["id"] for item in armor_json}

# ===== GUI CODE =====

class SearchableCombobox(ttk.Combobox):
    """Custom Combobox that filters values as you type"""
    def __init__(self, parent, *args, **kwargs):
        self.all_values = kwargs.get('values', [])
        super().__init__(parent, *args, **kwargs)
        self.bind('<KeyRelease>', self._on_keyrelease)
    
    def _on_keyrelease(self, event):
        if event.keysym in ('Up', 'Down', 'Left', 'Right'):
            return
        
        value = self.get()
        if value == '':
            self['values'] = self.all_values
        else:
            filtered = [item for item in self.all_values if value.lower() in item.lower()]
            self['values'] = filtered

class SekiroSaveEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Sekiro Save Editor")
        self.root.geometry("1000x750")
        
        # Style
        self.setup_styles()
        
        # Global data
        self.current_data = None
        self.mode = None
        self.file_path = None
        self.original_file_path = None
        self.slot_files = []
        self.current_slot = -1
        self.slot_data = {}  # Store data for each slot
        
        # Menu
        self.create_menu()
        
        # Slot selector frame (hidden by default)
        self.slot_frame = ttk.Frame(root)
        
        # Main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Status bar
        self.status_var = tk.StringVar(value="No file loaded")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken")
        self.status_bar.pack(fill="x", side="bottom")
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Create tabs
        self.create_file_tab()
        self.create_stats_tab()
        self.create_inventory_tab()
        self.create_spawning_tab()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'))
        
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Save File", command=self.open_file)
        file_menu.add_command(label="Save File", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
    def create_file_tab(self):
        self.file_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.file_tab, text="File")
        
        title = ttk.Label(self.file_tab, text="Save File Manager", style='Title.TLabel')
        title.pack(pady=20)
        
        button_frame = ttk.Frame(self.file_tab)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Open Save File", command=self.open_file).pack(padx=10, pady=10)
        ttk.Button(button_frame, text="Save File", command=self.save_file).pack(padx=10, pady=10)
        ttk.Button(button_frame, text="Import Slot", command=self.import_slot).pack(padx=10, pady=10)
        
        info_frame = ttk.LabelFrame(self.file_tab, text="File Information")
        info_frame.pack(fill="x", padx=20, pady=20)
        
        ttk.Label(info_frame, text="Mode:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.mode_var = tk.StringVar(value="Not loaded")
        ttk.Label(info_frame, textvariable=self.mode_var).grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        ttk.Label(info_frame, text="File Path:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.path_var = tk.StringVar(value="Not loaded")
        ttk.Label(info_frame, textvariable=self.path_var, wraplength=400).grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Slot selector (hidden initially)
        self.slot_selector_frame = ttk.LabelFrame(self.file_tab, text="Save Slots (PC Only)")
        self.slot_selector_frame.pack(fill="x", padx=20, pady=10)
        self.slot_selector_frame.pack_forget()
        
        self.slot_var = tk.StringVar()
        self.slot_combo = ttk.Combobox(self.slot_selector_frame, textvariable=self.slot_var, state="readonly", width=40)
        self.slot_combo.pack(padx=10, pady=10)
        self.slot_combo.bind("<<ComboboxSelected>>", self.switch_slot)
        
    def create_stats_tab(self):
        self.stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_tab, text="Stats")
        
        canvas = tk.Canvas(self.stats_tab)
        scrollbar = ttk.Scrollbar(self.stats_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        title = ttk.Label(scrollable_frame, text="Character Stats", style='Title.TLabel')
        title.pack(pady=10)
        
        stats_frame = ttk.LabelFrame(scrollable_frame, text="Stats")
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        self.stats_entries = {}
        
        stats_config = [
            ("HP", "hp", 0, 0xFFFFFFFF),
            ("Attack Power", "attack", 0, 0x62),
            ("New Game +", "NG+",0, 0xFF),
            ("Guard", "guard", 0, 0xFFFFFFFF),
            ("Emblems", "emblem", 0, 0x62),
            ("Skill Points", "skill_points", 0, 0x3B9AC9FF),
            ("Souls", "souls", 0, 0xFFFFFFFF),
        ]
        
        for idx, (label, key, min_val, max_val) in enumerate(stats_config):
            ttk.Label(stats_frame, text=f"{label}:").grid(row=idx, column=0, sticky="w", padx=10, pady=8)
            entry = ttk.Spinbox(stats_frame, from_=min_val, to=max_val, width=15)
            entry.grid(row=idx, column=1, sticky="w", padx=10, pady=8)
            self.stats_entries[key] = (entry, min_val, max_val)
        
        buttons_frame = ttk.Frame(scrollable_frame)
        buttons_frame.pack(fill="x", padx=10, pady=20)
        
        ttk.Button(buttons_frame, text="Apply Stats", command=self.apply_stats).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="Reload Stats", command=self.load_stats).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="Reset Skill Points", command=self.reset_skill_points_func).pack(side="left", padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_inventory_tab(self):
        self.inventory_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.inventory_tab, text="Inventory")
        
        self.inv_notebook = ttk.Notebook(self.inventory_tab)
        self.inv_notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.weapons_frame = ttk.Frame(self.inv_notebook)
        self.inv_notebook.add(self.weapons_frame, text="Weapons")
        self.create_items_tree(self.weapons_frame, "weapons")
        
        self.armor_frame = ttk.Frame(self.inv_notebook)
        self.inv_notebook.add(self.armor_frame, text="Armor")
        self.create_items_tree(self.armor_frame, "armor")
        
        self.goods_frame = ttk.Frame(self.inv_notebook)
        self.inv_notebook.add(self.goods_frame, text="Goods")
        self.create_goods_tree()
        
        self.storage_frame = ttk.Frame(self.inv_notebook)
        self.inv_notebook.add(self.storage_frame, text="Storage")
        self.create_storage_tree()
        
    def create_spawning_tab(self):
        self.spawning_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.spawning_tab, text="Spawning")
        
        canvas = tk.Canvas(self.spawning_tab)
        scrollbar = ttk.Scrollbar(self.spawning_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        title = ttk.Label(scrollable_frame, text="Item Spawning", style='Title.TLabel')
        title.pack(pady=10)
        
        # Weapons
        weapons_frame = ttk.LabelFrame(scrollable_frame, text="Spawn Weapons")
        weapons_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(weapons_frame, text="Weapon:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.weapon_combo = SearchableCombobox(weapons_frame, values=[w["name"] for w in weapons_json], state="normal", width=40)
        self.weapon_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(weapons_frame, text="Spawn Weapon", command=self.spawn_weapon).grid(row=0, column=2, padx=5, pady=8)
        
        # Armor
        armor_frame = ttk.LabelFrame(scrollable_frame, text="Spawn Armor")
        armor_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(armor_frame, text="Armor:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.armor_combo = SearchableCombobox(armor_frame, values=[a["name"] for a in armor_json], state="normal", width=40)
        self.armor_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(armor_frame, text="Spawn Armor", command=self.spawn_armor).grid(row=0, column=2, padx=5, pady=8)
        
        # Goods
        goods_frame = ttk.LabelFrame(scrollable_frame, text="Spawn Goods")
        goods_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(goods_frame, text="Good:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.good_combo = SearchableCombobox(goods_frame, values=[g["name"] for g in goods_json], state="normal", width=30)
        self.good_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        
        ttk.Label(goods_frame, text="Quantity:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.good_quantity = ttk.Spinbox(goods_frame, from_=1, to=99, width=10)
        self.good_quantity.insert(0, "1")
        self.good_quantity.grid(row=1, column=1, sticky="w", padx=10, pady=8)
        
        ttk.Button(goods_frame, text="Spawn Good", command=self.spawn_good).grid(row=1, column=2, padx=5, pady=8)
        
        # Status
        self.spawn_status = tk.StringVar(value="Ready")
        status_label = ttk.Label(scrollable_frame, textvariable=self.spawn_status, relief="sunken")
        status_label.pack(fill="x", padx=10, pady=10)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_items_tree(self, parent, item_type):
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Item Name", "ID", "Quantity")
        tree = ttk.Treeview(tree_frame, columns=columns, height=20)
        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("Item Name", anchor="w", width=300)
        tree.column("ID", anchor="center", width=100)
        tree.column("Quantity", anchor="center", width=100)
        
        tree.heading("#0", text="", anchor="w")
        tree.heading("Item Name", text="Item Name", anchor="w")
        tree.heading("ID", text="ID", anchor="center")
        tree.heading("Quantity", text="Quantity", anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        setattr(self, f"{item_type}_tree", tree)
        
    def create_goods_tree(self):
        """Create goods display with dedicated editor panel"""
        main_frame = ttk.Frame(self.goods_frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Tree on the left
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(side="left", fill="both", expand=True)

        columns = ("Item Name", "ID", "Quantity")
        tree = ttk.Treeview(tree_frame, columns=columns, height=20)

        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("Item Name", anchor="w", width=250)
        tree.column("ID", anchor="center", width=100)
        tree.column("Quantity", anchor="center", width=100)

        tree.heading("#0", text="", anchor="w")
        tree.heading("Item Name", text="Item Name", anchor="w")
        tree.heading("ID", text="Item ID", anchor="center")
        tree.heading("Quantity", text="Quantity", anchor="center")

        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=tree.yview
        )
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Selection handler
        tree.bind("<<TreeviewSelect>>", self.on_goods_select)

        self.goods_tree = tree
        self.goods_data = {}

        # =========================
        # Editor panel on the right
        # =========================

        editor_frame = ttk.LabelFrame(
            main_frame,
            text="Edit Good",
            padding=10
        )
        editor_frame.pack(
            side="right",
            fill="both",
            padx=(10, 0)
        )

        # Item name
        ttk.Label(
            editor_frame,
            text="Item Name:"
        ).pack(anchor="w", pady=5)

        self.goods_item_name = tk.StringVar()

        ttk.Label(
            editor_frame,
            textvariable=self.goods_item_name,
            relief="sunken",
            width=25
        ).pack(anchor="w", pady=5)

        # Item ID
        ttk.Label(
            editor_frame,
            text="Item ID:"
        ).pack(anchor="w", pady=5)

        self.goods_item_id = tk.StringVar()

        ttk.Label(
            editor_frame,
            textvariable=self.goods_item_id,
            relief="sunken",
            width=25
        ).pack(anchor="w", pady=5)

        # Quantity
        ttk.Label(
            editor_frame,
            text="New Quantity:"
        ).pack(anchor="w", pady=5)

        self.goods_qty_spinbox = ttk.Spinbox(
            editor_frame,
            from_=0,
            to=99,
            width=25
        )
        self.goods_qty_spinbox.pack(anchor="w", pady=5)

        # Update button
        ttk.Button(
            editor_frame,
            text="Update Quantity",
            command=self.update_goods_quantity
        ).pack(anchor="w", pady=10)

        # Delete button
        ttk.Button(
            editor_frame,
            text="Delete Item",
            command=self.delete_selected_good
        ).pack(anchor="w", pady=5)

    def update_goods_quantity(self):
        """Update the selected good quantity"""

        if not hasattr(self, '_current_goods_iid'):
            messagebox.showwarning(
                "Warning",
                "No item selected"
            )
            return

        try:
            new_qty = int(self.goods_qty_spinbox.get())

            if new_qty < 0 or new_qty > 99:
                messagebox.showerror(
                    "Error",
                    "Quantity must be between 0 and 99"
                )
                return

            iid = self._current_goods_iid

            offset = self.goods_data[iid]["offset"]

            self.current_data = update_good_quantity(
                self.current_data,
                offset,
                new_qty
            )

            # Update internal data
            self.goods_data[iid]["current_qty"] = new_qty

            # Update tree
            values = self.goods_tree.item(iid)["values"]

            self.goods_tree.item(
                iid,
                values=(
                    values[0],
                    values[1],
                    new_qty
                )
            )

            messagebox.showinfo(
                "Success",
                f"Quantity updated to {new_qty}"
            )

        except ValueError:
            messagebox.showerror(
                "Error",
                "Invalid quantity value"
            )

    def on_goods_select(self, event):
        """Handle goods tree selection"""
        selection = self.goods_tree.selection()

        if not selection:
            return

        iid = selection[0]

        if iid not in self.goods_data:
            return

        data = self.goods_data[iid]

        self.goods_item_name.set(data["name"])
        self.goods_item_id.set(str(data["item_id"]))

        self.goods_qty_spinbox.delete(0, tk.END)
        self.goods_qty_spinbox.insert(0, str(data["current_qty"]))

        self._current_goods_iid = iid

    def delete_selected_good(self):
        """Delete the currently selected good"""

        if not hasattr(self, '_current_goods_iid'):
            messagebox.showwarning(
                "Warning",
                "No item selected"
            )
            return

        iid = self._current_goods_iid

        if iid not in self.goods_data:
            messagebox.showwarning(
                "Warning",
                "Invalid selection"
            )
            return

        item_data = self.goods_data[iid]
        item_name = item_data["name"]

        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Delete '{item_name}'?"
        ):
            return

        try:
            offset = item_data["offset"]

            # Zero the 16-byte inventory slot
            self.current_data = delete_good_item(
                self.current_data,
                offset
            )

            # Remove from tree
            self.goods_tree.delete(iid)

            # Remove from data
            del self.goods_data[iid]

            # Clear editor
            self.goods_item_name.set("")
            self.goods_item_id.set("")
            self.goods_qty_spinbox.delete(0, tk.END)

            if hasattr(self, '_current_goods_iid'):
                del self._current_goods_iid

            messagebox.showinfo(
                "Success",
                f"'{item_name}' deleted successfully"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to delete item: {str(e)}"
            )
        
    def create_storage_tree(self):
        """Create storage display with inline quantity editing"""
        main_frame = ttk.Frame(self.storage_frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tree on the left
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(side="left", fill="both", expand=True)
        
        columns = ("Item Name", "ID", "Quantity")
        tree = ttk.Treeview(tree_frame, columns=columns, height=20)
        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("Item Name", anchor="w", width=250)
        tree.column("ID", anchor="center", width=100)
        tree.column("Quantity", anchor="center", width=100)
        
        tree.heading("#0", text="", anchor="w")
        tree.heading("Item Name", text="Item Name", anchor="w")
        tree.heading("ID", text="ID", anchor="center")
        tree.heading("Quantity", text="Quantity", anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        tree.bind("<<TreeviewSelect>>", self.on_storage_select)
        
        self.storage_tree = tree
        self.storage_data = {}
        
        # Editor panel on the right
        editor_frame = ttk.LabelFrame(main_frame, text="Edit Quantity", padding=10)
        editor_frame.pack(side="right", fill="both", padx=(10, 0))
        
        ttk.Label(editor_frame, text="Item Name:").pack(anchor="w", pady=5)
        self.storage_item_name = tk.StringVar()
        ttk.Label(editor_frame, textvariable=self.storage_item_name, relief="sunken", width=25).pack(anchor="w", pady=5)
        
        ttk.Label(editor_frame, text="Item ID:").pack(anchor="w", pady=5)
        self.storage_item_id = tk.StringVar()
        ttk.Label(editor_frame, textvariable=self.storage_item_id, relief="sunken", width=25).pack(anchor="w", pady=5)
        
        ttk.Label(editor_frame, text="New Quantity:").pack(anchor="w", pady=5)
        self.storage_qty_spinbox = ttk.Spinbox(editor_frame, from_=0, to=99, width=25)
        self.storage_qty_spinbox.pack(anchor="w", pady=5)
        
        ttk.Button(editor_frame, text="Update Quantity", command=self.update_storage_quantity).pack(anchor="w", pady=10)
        
    def on_storage_select(self, event):
        """Handle storage tree selection"""
        selection = self.storage_tree.selection()
        if not selection:
            return
        
        iid = selection[0]
        if iid not in self.storage_data:
            return
        
        data = self.storage_data[iid]
        self.storage_item_name.set(data["name"])
        self.storage_item_id.set(str(data["item_id"]))
        self.storage_qty_spinbox.delete(0, tk.END)
        self.storage_qty_spinbox.insert(0, str(data["current_qty"]))
        self._current_storage_iid = iid
        
    def update_storage_quantity(self):
        """Update the selected storage item quantity"""
        if not hasattr(self, '_current_storage_iid'):
            messagebox.showwarning("Warning", "No item selected")
            return
        
        try:
            new_qty = int(self.storage_qty_spinbox.get())
            if new_qty < 0 or new_qty > 99:
                messagebox.showerror("Error", "Quantity must be between 0 and 99")
                return
            
            iid = self._current_storage_iid
            offset = self.storage_data[iid]["offset"]
            self.current_data = update_good_quantity(self.current_data, offset, new_qty)
            self.storage_data[iid]["current_qty"] = new_qty
            
            values = self.storage_tree.item(iid)["values"]
            self.storage_tree.item(iid, values=(values[0], values[1], new_qty))
            messagebox.showinfo("Success", f"Quantity updated to {new_qty}")
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity value")
        
    def show_goods_context_menu(self, event):
        """Show right-click context menu for goods"""
        selection = self.goods_tree.selection()
        if not selection:
            return
        
        iid = selection[0]
        if iid not in self.goods_data:
            return
        
        # Create context menu
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Edit Quantity", command=lambda: self.on_goods_double_click(None))
        context_menu.add_command(label="Delete Item", command=lambda: self.delete_good(iid))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def on_delete_key_pressed(self, event):
        """Handle Delete key press on goods tree"""
        selection = self.goods_tree.selection()
        if selection:
            iid = selection[0]
            if iid in self.goods_data:
                self.delete_good(iid)
    
    def delete_good(self, iid):
        """Delete a good item from inventory"""
        if iid not in self.goods_data:
            messagebox.showwarning("Warning", "Invalid selection")
            return
        
        # Get item info
        item_data = self.goods_data[iid]
        item_name = self.goods_tree.item(iid)["values"][0]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", f"Delete '{item_name}'?"):
            return
        
        try:
            offset = item_data["offset"]
            # Delete by setting the 16-byte slot to zeros
            self.current_data = delete_good_item(self.current_data, offset)
            
            # Remove from display
            self.goods_tree.delete(iid)
            del self.goods_data[iid]
            
            messagebox.showinfo("Success", f"'{item_name}' deleted successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete item: {str(e)}")

    def open_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        
        file_name = os.path.basename(path)
        data = read_file(path)
        
        if file_name == 'S0000.sl2':
            self.mode = 'PC'
            self.original_file_path = path
            split_pc_files(data)
            
            self.slot_files = show_ud_files()
            if not self.slot_files:
                messagebox.showerror("Error", "No save slots found")
                return
            
            # Show slot selector
            slot_names = [f"Slot {i}" for i in range(len(self.slot_files))]
            self.slot_combo['values'] = slot_names
            self.slot_combo.current(0)
            self.slot_selector_frame.pack(fill="x", padx=20, pady=10)
            
            # Load first slot
            self.switch_slot(None)
        else:
            self.mode = 'PS4'
            self.file_path = path
            self.current_data = data
            self.slot_selector_frame.pack_forget()
            self.update_ui()
        
        self.mode_var.set(self.mode)
        if self.file_path:
            self.path_var.set(self.file_path)
        else:
            self.path_var.set(f"PC Save with {len(self.slot_files)} slots")
        self.status_var.set(f"Loaded: {file_name}")
        
    def switch_slot(self, event):
        if not self.slot_files:
            return
        
        slot_index = self.slot_combo.current()
        if slot_index < 0:
            return
        
        self.file_path = self.slot_files[slot_index]
        self.current_slot = slot_index
        self.current_data = read_file(self.file_path)
        self.update_ui()
        self.status_var.set(f"Loaded: Slot {slot_index}")
        
    def update_ui(self):
        if not self.current_data:
            return
        
        self.load_stats()
        self.load_inventory()
        
    def load_stats(self):
        if not self.current_data:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        stats = load_data(self.current_data)
        
        for key, (entry, min_val, max_val) in self.stats_entries.items():
            value = stats.get(key, 0)
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
            
    def apply_stats(self):
        if not self.current_data:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        try:
            data = self.current_data
            
            if "hp" in self.stats_entries:
                hp_val = int(self.stats_entries["hp"][0].get())
                data = update_hp(data, hp_val)
            
            if "attack" in self.stats_entries:
                atk_val = int(self.stats_entries["attack"][0].get())
                data = update_attk(data, atk_val)
            
            if "guard" in self.stats_entries:
                guard_val = int(self.stats_entries["guard"][0].get())
                data = update_gaurd(data, guard_val)

            if "NG+" in self.stats_entries:
                ng_val = int(self.stats_entries["NG+"][0].get())
                data = update_ng(data, ng_val)
            
            if "emblem" in self.stats_entries:
                emblem_val = int(self.stats_entries["emblem"][0].get())
                data = update_max_emblem_limit(data, emblem_val)
            
            if "skill_points" in self.stats_entries:
                skill_val = int(self.stats_entries["skill_points"][0].get())
                data = update_skill_point(data, skill_val)
            
            if "souls" in self.stats_entries:
                souls_val = int(self.stats_entries["souls"][0].get())
                data = update_souls(data, souls_val)
            
            self.current_data = data
            messagebox.showinfo("Success", "Stats updated successfully")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid stat value")
    
    def reset_skill_points_func(self):
        if not self.current_data:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        if messagebox.askyesno("Confirm", "Reset all skill points?"):
            self.current_data = reset_skill_points(self.current_data)
            self.load_stats()
            messagebox.showinfo("Success", "Skill points reset")
    
    def load_inventory(self):
        if not self.current_data:
            return
        
        weapons, armors, goods, empty, all_items = get_inventory_data(self.current_data)
        goods_key,_,_=get_inventory_data_key(self.current_data)
        goods_storage, _, _ = get_storage_data(self.current_data)
        
        for item in self.weapons_tree.get_children():
            self.weapons_tree.delete(item)
        for item in self.armor_tree.get_children():
            self.armor_tree.delete(item)
        for item in self.goods_tree.get_children():
            self.goods_tree.delete(item)
        for item in self.storage_tree.get_children():
            self.storage_tree.delete(item)
        
        for gaitem, item_id, qty, idx, offset in weapons:
            name = item_lookup.get(item_id, f"Unknown ({item_id})")
            self.weapons_tree.insert("", "end", values=(name, item_id, qty))
        
        for gaitem, item_id, qty, idx, offset in armors:
            name = item_lookup.get(item_id, f"Unknown ({item_id})")
            self.armor_tree.insert("", "end", values=(name, item_id, qty))
        
        self.goods_data = {}
        for gaitem, item_id, qty, idx, offset in goods:
            name = item_lookup.get(item_id, f"Unknown ({item_id})")
            iid = self.goods_tree.insert("", "end", values=(name, item_id, qty, "✎"))
            self.goods_data[iid] = {
    "offset": offset,
    "item_id": item_id,
    "current_qty": qty,
    "name": name
}

        for gaitem, item_id, qty, idx, offset in goods_key:
            name = item_lookup.get(item_id, f"Unknown ({item_id})")
            iid = self.goods_tree.insert("", "end", values=(name, item_id, qty, "✎"))
            self.goods_data[iid] = {"offset": offset, "item_id": item_id, "current_qty": qty, "name": name}
        
        # Load storage
        self.storage_data = {}
        for gaitem, item_id, qty, idx, offset in goods_storage:
            name = item_lookup.get(item_id, f"Unknown ({item_id})")
            iid = self.storage_tree.insert("", "end", values=(name, item_id, qty))
            self.storage_data[iid] = {"offset": offset, "item_id": item_id, "current_qty": qty, "name": name}
    
    def on_goods_double_click(self, event):
        selection = self.goods_tree.selection()
        if not selection:
            return
        
        iid = selection[0]
        if iid not in self.goods_data:
            return
        
        current_qty = self.goods_data[iid]["current_qty"]
        
        new_qty = simpledialog.askinteger(
            "Edit Quantity",
            f"Enter new quantity (max 99):",
            initialvalue=current_qty,
            minvalue=0,
            maxvalue=99
        )
        
        if new_qty is not None:
            offset = self.goods_data[iid]["offset"]
            self.current_data = update_good_quantity(self.current_data, offset, new_qty)
            self.goods_data[iid]["current_qty"] = new_qty
            
            values = self.goods_tree.item(iid)["values"]
            self.goods_tree.item(iid, values=(values[0], values[1], new_qty, "✎"))
            messagebox.showinfo("Success", f"Quantity updated to {new_qty}")
    
    def spawn_weapon(self):
        if not self.current_data:
            self.spawn_status.set("Error: No file loaded")
            return
        
        weapon_name = self.weapon_combo.get()
        if not weapon_name:
            self.spawn_status.set("Error: Select a weapon")
            return
        
        result = spawn_weapon_armor(self.current_data, weapon_name, "weapon")
        if result is None:
            self.spawn_status.set("Error: Failed to spawn weapon (inventory full?)")
            return
        
        self.current_data = result
        self.load_inventory()
        self.spawn_status.set(f"Success: Spawned {weapon_name}")
    
    def spawn_armor(self):
        if not self.current_data:
            self.spawn_status.set("Error: No file loaded")
            return
        
        armor_name = self.armor_combo.get()
        if not armor_name:
            self.spawn_status.set("Error: Select armor")
            return
        
        result = spawn_weapon_armor(self.current_data, armor_name, "armor")
        if result is None:
            self.spawn_status.set("Error: Failed to spawn armor (inventory full?)")
            return
        
        self.current_data = result
        self.load_inventory()
        self.spawn_status.set(f"Success: Spawned {armor_name}")
    
    def spawn_good(self):
        if not self.current_data:
            self.spawn_status.set("Error: No file loaded")
            return
        
        good_name = self.good_combo.get()
        if not good_name:
            self.spawn_status.set("Error: Select a good")
            return
        
        try:
            qty = int(self.good_quantity.get())
            if qty < 1 or qty > 99:
                self.spawn_status.set("Error: Quantity must be 1-99")
                return
        except ValueError:
            self.spawn_status.set("Error: Invalid quantity")
            return
        
        result = spawn_goods(self.current_data, good_name, qty)
        if result is None:
            self.spawn_status.set("Error: Failed to spawn good (inventory full?)")
            return
        
        self.current_data = result
        self.load_inventory()
        self.spawn_status.set(f"Success: Spawned {qty}x {good_name}")
    
    def save_file(self):
        if not self.current_data or not self.file_path:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        try:
            if self.mode == 'PC':
                write_file(self.file_path, self.current_data)
                
                output_path = filedialog.asksaveasfilename(
                    defaultextension=".sl2",
                    filetypes=[("SL2 files", "*.sl2")],
                    initialfile="S0000.sl2"
                )
                
                if output_path:
                    merge_pc_files(output_path)
                    messagebox.showinfo("Success", f"File saved to {output_path}")
                    self.status_var.set(f"Saved: {os.path.basename(output_path)}")
            else:
                output_path = filedialog.asksaveasfilename(
                    defaultextension=".sl2",
                    filetypes=[("SL2 files", "*.sl2")]
                )
                
                if output_path:
                    write_file(output_path, self.current_data)
                    messagebox.showinfo("Success", f"File saved to {output_path}")
                    self.status_var.set(f"Saved: {os.path.basename(output_path)}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def import_slot(self):
        """Import a slot file and replace current slot data while keeping original Steam ID"""
        if not self.current_data:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        new_slot_path = filedialog.askopenfilename(
            title="Select a slot file to import",
            filetypes=[("SL2 files", "*.sl2"), ("All files", "*.*")]
        )
        
        if not new_slot_path:
            return
        
        try:
            # Read the new slot data
            with open(new_slot_path, 'rb') as f:
                new_slot_data = bytearray(f.read())
            
            # For PC saves, if the imported file is a full save (S0000.sl2), split it first
            if os.path.basename(new_slot_path) == 'S0000.sl2' and len(new_slot_data) > 0x100000:
                # This is a full PC save, we need to extract the appropriate slot
                slot_index = self.current_slot if self.mode == 'PC' else 0
                
                # Extract the slot data from the full save
                start_offset = 0x310
                for i in range(slot_index):
                    start_offset += 0x100010
                
                slot_data = new_slot_data[start_offset:start_offset+0x100000]
                new_slot_data = bytearray(slot_data)
            
            # Extract current Steam ID from existing data
            current_steam_id = struct.unpack_from('<Q', self.current_data, steam_id)[0]
            
            # Apply the current Steam ID to the new slot data
            struct.pack_into('<Q', new_slot_data, steam_id, current_steam_id)
            
            # Update current data
            self.current_data = bytes(new_slot_data)
            
            # For PC saves, also write the slot file
            if self.mode == 'PC' and self.file_path:
                write_file(self.file_path, self.current_data)
            
            # Refresh UI
            self.update_ui()
            
            messagebox.showinfo("Success", f"Slot imported successfully!\nSteam ID preserved: {current_steam_id}")
            self.status_var.set("Slot imported successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import slot: {str(e)}")

def main():
    root = tk.Tk()
    app = SekiroSaveEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()

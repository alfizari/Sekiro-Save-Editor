import os, struct, hashlib, json
from tkinter import filedialog


#globals
MODE=None
FILE_PATH=None

#offsets
steam_id=0x33E54
emblem_off=0x3459A # emblems???
attacks_off=0x3449C
skill_points_off=0x345B4 
gaurd_off=0x34488
hp_off=0x3446C
souls_off=0x344D0


# Set the working directory
working_directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(working_directory)


#Jsons
def load_and_copy_json(file_name):
    file_path = os.path.join(working_directory, file_name)
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


    
weapons_json=load_and_copy_json('weapons.json')
goods_json=load_and_copy_json('goods.json')
armor_json=load_and_copy_json('armor.json')


def write_value_at_offset(data, offset, value, byte_size=4):
    value_bytes = value.to_bytes(byte_size, 'little')
    # Replace the bytes at the given offset with the new value
    return data[:offset] + value_bytes + data[offset+byte_size:]


def read_file(file_path):
    with open(file_path,'rb') as f:
        data=f.read()

    return data


def write_file(file_path, data):

    with open(file_path,'wb') as f:
        f.write(data)


    return True


def split_pc_files(data):


    split_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'split_files')
    os.makedirs(split_dir, exist_ok=True)
    

    bnd_data=data[:0x300]
    write_file(os.path.join(split_dir, 'header' ), bnd_data)


    start_offset=0x310

    for i in range (10):
        user_data=data[start_offset:start_offset+0x100000]

        start_offset+=0x100010

        write_file(os.path.join(split_dir, f"userdata000{i}"), user_data)

    rest_of_data=data[start_offset-0x10:]
    write_file(os.path.join(split_dir, 'ud10-11' ), rest_of_data)

    return True

def merge_pc_files():

    out_path=filedialog.asksaveasfilename()

    split_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'split_files')

    pc_header = read_file(os.path.join(split_dir, 'header'))



    ud_buff = b""

    for i in range(10):
        bf_data= read_file(os.path.join(split_dir, f'userdata000{i}'))
        m = hashlib.md5(bf_data).digest()
        ud_buff+=(m+bf_data)

    ud_rem = read_file(os.path.join(split_dir, 'ud10-11'))

    out_data = pc_header + ud_buff + ud_rem

    write_file(out_path, out_data)

    return True

def show_ud_files():
    split_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "split_files")

    return [
        os.path.join(split_dir, f)
        for f in os.listdir(split_dir)
        if os.path.isfile(os.path.join(split_dir, f))
        and f.startswith("userdata")
    ]

def open_file():
    global MODE, FILE_PATH

    path=filedialog.askopenfilename()
    file_name=os.path.basename(path)

    data=read_file(path)

    if file_name=='S0000.sl2':
        MODE='PC'
        done_split=split_pc_files(data)

        if done_split:
            li=show_ud_files()
            slot_num = int(input('Choose slot: '))
            file_path = li[slot_num]
            print(file_path)
            data=read_file(file_path)
            FILE_PATH=file_path

            return data

        else:
            print('nothig')
    else:
        MODE='PS4'
        FILE_PATH=file_path
        print('MODE', MODE)


    return data


def save_file(data):
    global FILE_PATH, MODE

    write_file(FILE_PATH, data)

    if MODE is None:
        print('No MODE set')
        return

    if MODE=='PC':

        merge_pc_files()

    elif MODE=='PS4':
        return

    
    return True


def load_data(data):

    #steam id
    current_steam_id=struct.unpack_from('<Q', data, steam_id)[0]
    current_steam_id= int.to_bytes(current_steam_id, 8, 'little')
    print('steam id', current_steam_id)


    #attack
    attk_val=struct.unpack_from('<B', data, attacks_off)[0]
    print('attack val', attk_val)

    #gaurd
    gaurd_val=struct.unpack_from('<I', data, gaurd_off)[0]
    print('gaurd_val', gaurd_val)

    #emblems
    emblem_val=struct.unpack_from('<B', data, emblem_off)[0]
    print('emblem val', emblem_val)

    #skill_points_off

    skill_val=struct.unpack_from('<I', data, skill_points_off)[0]
    print('skill val', skill_val)

    #hp off
    
    hp_val=struct.unpack_from('<I', data, hp_off)[0]
    print('hp val', hp_val)

    #souls off
    
    souls_val=struct.unpack_from('<I', data, souls_off)[0]
    print('souls val', souls_val)


    return

def update_skill_point(data, value):

    max_val=0x3B9AC9FF
    data=write_value_at_offset(data, skill_points_off, value, 4)

    return data

def update_max_emblem_limit(data, value):

    max_val=0x62
    
    if value>max_val:
        value=max_val
    data=write_value_at_offset(data,emblem_off, value, 1)

    return data

def update_gaurd(data, value):

    max_val=0xFFFFFFFF

    if value>max_val:
        value=max_val

    data=write_value_at_offset(data,gaurd_off, value, 4)

    return data

def update_hp(data, value):

    max_val=0xFFFFFFFF

    if value>max_val:
        value=max_val

    data=write_value_at_offset(data,hp_off, value, 4)

    return data

def update_souls(data, value):

    max_val=0xFFFFFFFF

    if value>max_val:
        value=max_val

    data=write_value_at_offset(data,souls_off, value, 4)

    return data

def update_attk(data, value):

    max_val=0x62

    if value>max_val:
        value=max_val

    data=write_value_at_offset(data,attacks_off, value, 1)

    return data


def reset_skill_points(data):

    data=write_value_at_offset(data, 0x345A8, 0, 0x10)

    return data



ITEM_TYPE_EMPTY = 0x00000000
ITEM_TYPE_WEAPON = 0x80000000
ITEM_TYPE_ARMOR  = 0x90000000

class GA_Item:
    BASE_SIZE = 0x3C

    def __init__(self, gaitem_handle,item_id, quantity, index, offset):
        self.gaitem_handle = gaitem_handle 
        self.item_id=item_id
        self.quantity = quantity
        self.index = index
        self.offset = offset
        self.size = self.BASE_SIZE

    @classmethod
    def from_bytes(cls, data, offset=0):
        gaitem_handle, item_id= struct.unpack_from("<II", data, offset)
        return cls(gaitem_handle, item_id, offset)
    

def parse_ga(data_type, start_offset, end_offset):
    ga_items= []
    offset = start_offset
    
    while offset < end_offset:
        item = GA_Item.from_bytes(data_type, offset)
        ga_items.append(item)
        offset += item.size


    return ga_items


def gaprint(data):
    global ga_weapons, ga_armors, ga_empty, ga_items

    ga_items=[]
    ga_weapons=[]
    ga_armors=[]
    ga_empty=[]

    start_offset = 0x35614


    items = parse_ga(data, start_offset, end_offset=start_offset+0x59fc4+0x3c)

    for item in items:
        type_bits = item.gaitem_handle & 0xF0000000
        ga_items.append((item.gaitem_handle, item.item_id, item.offset))
        if type_bits == ITEM_TYPE_WEAPON:
            ga_weapons.append((item.gaitem_handle, item.item_id, item.offset))
        elif type_bits == ITEM_TYPE_ARMOR:
            ga_armors.append((item.gaitem_handle, item.item_id, item.offset))
        elif type_bits == ITEM_TYPE_EMPTY:
            ga_empty.append((item.gaitem_handle, item.item_id, item.offset))



ITEM_TYPE_GOOD = 0XB0000000

##there is a key section or somethign

class INVENTORY:
    BASE_SIZE = 16

    def __init__(self, gaitem_handle,item_id, quantity, index, offset):
        self.gaitem_handle = gaitem_handle 
        self.item_id=item_id
        self.quantity = quantity
        self.index = index
        self.offset = offset
        self.size = self.BASE_SIZE

    @classmethod
    def from_bytes(cls, data, offset=0):
        gaitem_handle, item_id, quantity, index = struct.unpack_from("<IIII", data, offset)
        return cls(gaitem_handle,item_id, quantity, index, offset)


def parse_inventory(data, start_offset, end_offset):
    inventory_item = []
    offset = start_offset

    while offset < end_offset:
        item = INVENTORY.from_bytes(data, offset)
        inventory_item.append(item)
        offset += item.size  

    return inventory_item

def inventoryprint(data):
    global weapons, armors, goods, empty, inventory_items
    
    inventory_items=[]
    weapons = []
    armors = []
    goods = []
    empty=[]

    start_offset = 0x8F70C

    end_offset = start_offset + 0x7000



    items = parse_inventory(data, start_offset, end_offset)

    for item in items:
        type_bits = item.gaitem_handle & 0xF0000000
        inventory_items.append((item.gaitem_handle, item.item_id & 0x00FFFFFF, item.quantity, item.index, item.offset))

        if type_bits == ITEM_TYPE_WEAPON:
            weapons.append((item.gaitem_handle, item.item_id, item.quantity & 0x00FFFFFF, item.index, item.offset))
        elif type_bits == ITEM_TYPE_ARMOR:
            armors.append((item.gaitem_handle, item.item_id & 0x00FFFFFF, item.quantity, item.index, item.offset))
        elif type_bits == ITEM_TYPE_GOOD:
            goods.append((item.gaitem_handle, item.item_id& 0x00FFFFFF, item.quantity, item.index, item.offset))
        elif type_bits == ITEM_TYPE_EMPTY:
            empty.append((item.gaitem_handle, item.item_id, item.quantity, item.index, item.offset))



def inventory_counters(data):



    first_counter_offset = 0x8F700


    first_val = struct.unpack_from("<H", data, first_counter_offset)[0]

    first_val += 1



    data = data[:first_counter_offset] + struct.pack("<H", first_val) + data[first_counter_offset+2:]

    return data

item_lookup = {}

for item in weapons_json + armor_json + goods_json:
    item_lookup[int(item["id"])] = item["name"]

goods_lookup = {item["name"]: item["id"] for item in goods_json}
weapons_lookup = {item["name"]: item["id"] for item in weapons_json}
armors_lookup = {item["name"]: item["id"] for item in armor_json}

def sort_list():


    highest_indices = [item[3] & 0x0FFF for item in inventory_items]
    highest_indices.sort(key=lambda x: x)

    return highest_indices


def sort_list_ga():


    highest_indices = [item[0] & 0xFFFF0000 for item in ga_items]
    highest_indices.sort(key=lambda x: x)

    return highest_indices



def show_inventory(data):

    

    inventoryprint(data)

    inv_names=[]

    for _, item_id, quantity, _, offset in inventory_items:
        name = item_lookup.get(item_id, "Unknown Item")
        inv_names.append((name, item_id, quantity))

    print(inv_names[:10])
    

    return


def spawn_goods(data, item_name, item_quantity, Stack=False, quantity_override=False):

    inventoryprint(data)
    

    
    if not data:
        return

    if item_name not in goods_lookup:
        print("Not in json")
        return

    item_id_int = int(goods_lookup[item_name])
    print(item_id_int, "id of item")

    if not quantity_override:
        if item_quantity>99:
            item_quantity=99


    if Stack==False:
        for i, (gaitem_handle, item_id, quantity, index, offset) in enumerate(inventory_items):
                if item_id_int == item_id:
                    print('true', quantity , offset)
                    quantity_offset= offset + 8
                    print('quan off', quantity_offset)

                    data = (
                        data[:quantity_offset] 
                        + item_quantity.to_bytes(4, 'little') 
                        + data[quantity_offset+4:]
                    )
                    inventory_items[i] = (gaitem_handle, item_id, item_quantity, index, offset)

                    return data


    # else we add the new item

    if not empty:
        print('no empty offset found')
        return

    empty_offset=empty[0][4]
    print('first empty offset', empty_offset)


    indexes=sort_list()

    highest_index=int(indexes[-1])
    print('highest index',  highest_index)

    highest_index+=1

    random_bytes = os.urandom(1)

    goods_slot = (
        item_id_int.to_bytes(4, 'little') +
        item_id_int.to_bytes(4, 'little') +
        item_quantity.to_bytes(4, 'little') +
        highest_index.to_bytes(4, 'little')
    )

    goods_slot=bytearray(goods_slot)

    goods_slot[3]=0xB0
    goods_slot[14]= random_bytes

    data = data[:empty_offset] + goods_slot + data[empty_offset+16:]

    data=inventory_counters(data)


    return data




def spawn_weapon_armor(data, item_name, item_type):

    gaprint(data)
    inventoryprint(data)

    if not data:
        return

    if item_type=='weapon' and item_name in weapons_lookup:
        item_id_int = int(weapons_lookup[item_name])
    

    elif item_type=='armor'and item_name in armors_lookup:
        item_id_int = int(armors_lookup[item_name])

    else:
        print('no idea')
        return


    highest_index_list=sort_list_ga()

    highest_index=int(highest_index_list[-1])

    new_index=highest_index+1
    #first we create a ga entry
    ga_slot_entry=(
        new_index.to_bytes(4, 'little') +  # gaitem_handle
        item_id_int.to_bytes(4, 'little') +  # item_id
        (0).to_bytes(34, 'little')

    )

    ga_slot_entry=bytearray(ga_slot_entry)

    ga_slot_entry[3]=0x80 if item_type=='weapon' else 0x90
    ga_slot_entry[2]=0x80

    ga_slot_entry[16]=0x01

    if item_type=='armor':
        ga_slot_entry[7]=0x10
        ga_slot_entry[8]=0xe7
        ga_slot_entry[9]=0x03

    if not ga_empty:
        print('no empty ga offset found')
        return
    
    empty_ga_offset=ga_empty[0][2]
    print('first empty ga offset', empty_ga_offset)       

    data = data[:empty_ga_offset] + ga_slot_entry + data[empty_ga_offset+0x3C:]

    #now we do the inventory entry


    if not empty:
        print('no empty offset found')
        return
    
    empty_offset=empty[0][4]
    print('first empty offset', empty_offset)
    
    
    indexes=sort_list()
    
    highest_index=int(indexes[-1])
    print('highest index',  highest_index)
    
    highest_index+=1
    
    random_bytes = os.urandom(2)

    item_quantity=1
    
    goods_slot = (
        new_index.to_bytes(4, 'little') +
        item_id_int.to_bytes(4, 'little') +
        item_quantity.to_bytes(4, 'little') +
        highest_index.to_bytes(4, 'little')
    )
    
    goods_slot=bytearray(goods_slot)
    
    goods_slot[3]=0x80 if item_type=='weapon' else 0x90
    goods_slot[2]=0x80
    goods_slot[14:14+2]= random_bytes
    
    data = data[:empty_offset] + goods_slot + data[empty_offset+16:]
    
    data=inventory_counters(data)


    return data


## testing



#file_path='C:\\Users\\omant\\AppData\\Roaming\\Sekiro\\76561197960271872\\S0000.sl2'
# data=read_file(file_path)
# split_pc_files(data)


data=open_file()
# data=update_attk(data, 95)
# data=update_hp(data, 9999)
# data=update_skill_point(data, 999999)
# data=update_max_emblem_limit(data, 95)
# data=update_souls(data, 9999999)
load_data(data)

# show_inventory(data)

spawn_goods(data, "Regenerative Power", 99, True)
save_file(data)

import os
import io
import struct
import json
from flask import Flask, jsonify, send_file, request, send_from_directory
from PIL import Image

app = Flask(__name__, template_folder='.')

# --- CONFIGURATION PATHS ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VOICE_DIR = os.path.join(BASE_DIR, "Data", "SOUND", "VOICE")
BGM_DIR = os.path.join(BASE_DIR, "Data", "SOUND", "BGM") # ADDED: BGM directory definition
SCRIPT_JSON = os.path.join(BASE_DIR, "script.json")

os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs(BGM_DIR, exist_ok=True) # Ensure BGM dir exists

# --- Character ID Mapping Table ---
CHARACTER_MAP = {
    1: {"jp": "キャロット", "en": "Carrot"}, 2: {"jp": "シャロン", "en": "Sharon"},
    3: {"jp": "パルミラ", "en": "Palmira"}, 4: {"jp": "セシリス", "en": "Cecilis"},
    5: {"jp": "ファナ", "en": "Fana"}, 6: {"jp": "アルシェ", "en": "Arshe"},
    7: {"jp": "ロザリア", "en": "Rosaria"}, 8: {"jp": "クエスト", "en": "Quest"},
    9: {"jp": "イリオン", "en": "Ilion"}, 10: {"jp": "オスキル", "en": "Oskil"},
    11: {"jp": "シリウス", "en": "Sirius"}, 12: {"jp": "ニー", "en": "Nee"},
    13: {"jp": "ユーリィ", "en": "Yury"}, 14: {"jp": "アクセル", "en": "Axel"},
    15: {"jp": "クリス", "en": "Kris"}, 16: {"jp": "グレイブ", "en": "Grave"},
    17: {"jp": "バルディ", "en": "Baldi"}, 18: {"jp": "フリッカ", "en": "Flicka"}
}

LUT_LIST = []
for pixel in range(65536):
    r = ((pixel >> 10) & 0x1F) * 255 // 31
    g = ((pixel >> 5) & 0x1F) * 255 // 31
    b = (pixel & 0x1F) * 255 // 31
    if r == 0 and g == 0 and b == 0: LUT_LIST.append(b'\x00\x00\x00\x00')
    else: LUT_LIST.append(bytes([r, g, b, 255]))

def resolve_bg_filename(bg_id):
    if bg_id <= 116:
        group_num = (bg_id - 1) // 4 + 1
        variant_idx = (bg_id - 1) % 4
        return f"BG{group_num:03d}_{['A', 'B', 'C', 'D'][variant_idx]}.BIN"
    elif 117 <= bg_id <= 122:
        return f"BG{bg_id - 117 + 30:03d}_X.BIN"
    elif 140 <= bg_id <= 147:
        return f"M{bg_id - 139:03d}.BIN"
    elif 150 <= bg_id <= 153:
        return f"MM{bg_id - 149:03d}.BIN"
    elif 154 <= bg_id <= 166:
        return f"HAN{bg_id - 153:03d}.BIN"
    elif 166 <= bg_id <= 198:
        return f"KOJIN{bg_id - 165:03d}.BIN"
    elif 200 <= bg_id <= 211:
        return f"BATTLE{bg_id - 199:03d}.BIN"
    else:
        return f"BG{bg_id:03d}_X.BIN"

def parse_arguments(data):
    args = []
    for i in range(0, len(data) - 1, 2):
        args.append(struct.unpack('<h', data[i:i+2])[0])
    return args

def ybc_to_json(filepath):
    nodes = []
    if not os.path.exists(filepath): return nodes
        
    with open(filepath, 'rb') as f:
        magic = f.read(4)
        offsets = struct.unpack('<4I', f.read(16))
        offset1, offset2, offset3 = offsets[0], offsets[1], offsets[2]
        
        f.seek(offset3)
        total_strings = struct.unpack('<I', f.read(4))[0]
        strings = {}
        for i in range(total_strings):
            entry_data = f.read(4)
            if len(entry_data) < 4: break 
            rel_offset, length_data = struct.unpack('<HH', entry_data)
            table_pos = f.tell()
            f.seek(offset3 + rel_offset)
            raw_string = f.read(length_data // 16)
            try: strings[i] = raw_string.decode('cp932').replace('\x00', '').replace('\u3000', ' ')
            except: strings[i] = ""
            f.seek(table_pos)

        f.seek(offset1)
        node_id = 0

        while f.tell() < offset2:
            cmd_off = f.tell() - offset1          # code-relative offset (jump-target space)
            header = f.read(4)
            if len(header) < 4: break

            opcode, total_length = struct.unpack('<HH', header)
            opcode_data = f.read(total_length - 4)
            parsed_args = parse_arguments(opcode_data)

            node = {"id": node_id, "opcode": f"{opcode:04X}", "name": "Unknown Command", "args": parsed_args, "meta": {}, "_off": cmd_off}
            
            if opcode == 0x0000: node["name"] = "End of Script / Halt"
            elif opcode == 0x0001:
                node["name"] = "Unconditional Jump (Goto)"
                if len(parsed_args) >= 2: node["meta"]["target_offset"] = (parsed_args[1] << 16) | (parsed_args[0] & 0xFFFF)
            elif opcode == 0x0002:
                node["name"] = "Call Subroutine (Gosub)"
                if len(parsed_args) >= 2: node["meta"]["target_offset"] = (parsed_args[1] << 16) | (parsed_args[0] & 0xFFFF)
            elif opcode == 0x0003: node["name"] = "Return from Subroutine (Ret)"
            elif opcode == 0x0004:
                node["name"] = "Conditional Jump (Branch)"
                if len(parsed_args) >= 4:
                    node["meta"]["flag_id"] = parsed_args[0]
                    node["meta"]["operator"] = {0: "==", 1: "!=", 2: ">", 3: "<"}.get(parsed_args[1], "?")
                    node["meta"]["test_val"] = parsed_args[2]
                    node["meta"]["target_offset"] = (parsed_args[4] << 16) | (parsed_args[3] & 0xFFFF) if len(parsed_args) > 4 else 0
            elif opcode == 0x0006:
                node["name"] = "Mutate Flag / Assign Variable"
                if len(parsed_args) >= 3:
                    node["meta"]["flag_id"] = parsed_args[0]
                    node["meta"]["operation"] = {0: "=", 1: "+=", 2: "-="}.get(parsed_args[1], "=?")
                    node["meta"]["value"] = parsed_args[2]
            elif opcode == 0x000C:
                node["name"] = "Screen Transition / Wait Duration"
                if parsed_args: node["meta"]["duration"] = parsed_args[0]
            elif opcode == 0x000D: node["name"] = "Draw Screen / Commit Visuals"
            
            elif opcode == 0x0011:
                node["name"] = "Display Dialogue Text"
                if parsed_args:
                    jp_text = strings.get(parsed_args[0], "")
                    node["jp_text"] = jp_text
                    node["en_text"] = jp_text 
                    node["meta"]["string_index"] = parsed_args[0]
            elif opcode == 0x000F:
                node["name"] = "Print Unit Text (Menu/UI Label)"
                if parsed_args:
                    jp_text = strings.get(parsed_args[0], "")
                    node["jp_text"] = jp_text
                    node["en_text"] = jp_text
                    node["meta"]["string_index"] = parsed_args[0]

            elif opcode == 0x0012: node["name"] = "Hard Wait / End of Paragraph Block"
            elif opcode == 0x0013: node["name"] = "Clear Dialogue Text"
            elif opcode == 0x0014: node["name"] = "Hide Text Box / UI"
            
            elif opcode == 0x001A:
                node["name"] = "Slot Transition / Link Character"
                if len(parsed_args) >= 4:
                    node["meta"]["src_slot"] = parsed_args[0]
                    node["meta"]["dest_slot"] = parsed_args[1]
                    node["meta"]["char_id"] = parsed_args[2]
                    node["meta"]["flag"] = parsed_args[3]

            elif opcode == 0x001B:
                node["name"] = "Clear Character Portrait Slot"
                if parsed_args: node["meta"]["slot_id"] = parsed_args[0]
            elif opcode == 0x001C:
                node["name"] = "Hide Window / Change Window Style Mode"
                if parsed_args: node["meta"]["style_id"] = parsed_args[0]
            
            elif opcode == 0x001E:
                node["name"] = "Render ➔ Load Portrait (Animate In)"
                if len(parsed_args) >= 3:
                    speech_box_id = parsed_args[0]  
                    char_id = parsed_args[2]        
                    expression_id = parsed_args[4] if len(parsed_args) > 4 else 0
                    speed = parsed_args[6] if len(parsed_args) > 6 else 0
                    flag = parsed_args[8] if len(parsed_args) > 8 else 0
                    
                    char_info = CHARACTER_MAP.get(char_id, {"jp": f"キャラクター {char_id}", "en": f"Character {char_id}"})
                    node["meta"]["char_id"] = char_id
                    node["meta"]["char_name_jp"] = char_info["jp"]
                    node["meta"]["char_name_en"] = char_info["en"]
                    node["meta"]["speech_box"] = speech_box_id
                    node["meta"]["expression"] = expression_id
                    node["meta"]["speed"] = speed
                    node["meta"]["flag"] = flag
                    node["meta"]["file"] = f"{'sc' if speech_box_id in [7, 8, 9, 10, 11] else 'mc'}{char_id:03d}.BIN".upper()

            elif opcode == 0x0021:
                node["name"] = "Update Portrait / Expression (Instant)"
                if len(parsed_args) >= 3:
                    speech_box_id = parsed_args[0]  
                    char_id = parsed_args[2]        
                    expression_id = parsed_args[4] if len(parsed_args) > 4 else 0
                    
                    char_info = CHARACTER_MAP.get(char_id, {"jp": f"キャラクター {char_id}", "en": f"Character {char_id}"})
                    node["meta"]["char_id"] = char_id
                    node["meta"]["char_name_jp"] = char_info["jp"]
                    node["meta"]["char_name_en"] = char_info["en"]
                    node["meta"]["speech_box"] = speech_box_id
                    node["meta"]["expression"] = expression_id
                    node["meta"]["file"] = f"{'sc' if speech_box_id in [7, 8, 9, 10, 11] else 'mc'}{char_id:03d}.BIN".upper()
            
            elif opcode == 0x001F: node["name"] = "Load Menu/Map Overlay"
            
            elif opcode == 0x0023:
                node["name"] = "Clear Character Portrait Slot (Fade)"
                if len(parsed_args) >= 2: node["meta"]["slot_id"] = parsed_args[0]; node["meta"]["fade_rule"] = parsed_args[1]
            
            elif opcode == 0x0024: node["name"] = "Wait for Portrait Update Sync"
            
            elif opcode == 0x0028:
                node["name"] = "Set Speaker Nameplate"
                if parsed_args:
                    char_id = parsed_args[0]
                    node["meta"]["char_id"] = char_id
                    char_info = CHARACTER_MAP.get(char_id, {"jp": f"Char {char_id}", "en": f"Char {char_id}"})
                    node["meta"]["char_name_jp"] = char_info["jp"]
                    node["meta"]["char_name_en"] = char_info["en"]

            elif opcode == 0x002A:
                node["name"] = "Shake Screen"
                if len(parsed_args) >= 2: node["meta"]["intensity"] = parsed_args[0]; node["meta"]["duration"] = parsed_args[1]
            
            elif opcode == 0x002B:
                node["name"] = "Set Active Text Box Slot"
                if parsed_args:
                    node["meta"]["slot_id"] = parsed_args[0]

            elif opcode == 0x002C: node["name"] = "Refresh Screen Render / Flush Buffer"

            elif opcode == 0x0032: node["name"] = "Wait for Click Input"
            elif opcode == 0x0033: node["name"] = "Stop Mouth Animations / Stop Lip-Sync"
            elif opcode == 0x0035: node["name"] = "Load UI / Menu Graphic Asset"
            elif opcode == 0x0038: node["name"] = "Wait for Menu Input / Dispatch"
            
            elif opcode == 0x003B:
                node["name"] = "Load Background Image"
                if len(parsed_args) >= 3 and parsed_args[1] == 8192:
                    bg_id = parsed_args[2]
                elif len(parsed_args) >= 2:
                    bg_id = parsed_args[1]
                else:
                    bg_id = parsed_args[0] if parsed_args else 0
                node["meta"]["bg_id"] = bg_id
                node["meta"]["file"] = resolve_bg_filename(bg_id)

            elif opcode == 0x003C:
                node["name"] = "Play Background Music (BGM)"
                if len(parsed_args) >= 3:
                    node["meta"]["bgm_id"] = parsed_args[0]
                    node["meta"]["fade_in"] = parsed_args[1]
                    node["meta"]["volume"] = parsed_args[2]

            elif opcode == 0x003D: node["name"] = "Terminate Background Music"
            elif opcode == 0x003E: node["name"] = "Execute Sound Effect (SE)"

            elif opcode == 0x003F: 
                node["name"] = "Play Audio / Stream Environment BGM"
                if len(parsed_args) >= 1: node["meta"]["track_id"] = parsed_args[0]
            
            elif opcode == 0x0041: node["name"] = "Play Voice File"
            elif opcode == 0x0042: node["name"] = "Stream Fullscreen Video Clip"

            elif opcode == 0x0043: 
                node["name"] = "Clear Render Buffers / Reset Visual Canvas"

            elif opcode == 0x0045:
                node["name"] = "Display CG / Blit Region"
                if len(parsed_args) > 16:
                    node["meta"]["source_page"] = parsed_args[0]
                    node["meta"]["dest_x"] = parsed_args[2]
                    node["meta"]["dest_y"] = parsed_args[4]
                    node["meta"]["layer_id"] = parsed_args[8]
                    node["meta"]["src_x"] = parsed_args[10]
                    node["meta"]["src_y"] = parsed_args[12]
                    node["meta"]["crop_w"] = parsed_args[14]
                    node["meta"]["crop_h"] = parsed_args[16]

            elif opcode == 0x0047:
                node["name"] = "Script Chain (Load External .ybc)"
                if parsed_args:
                    node["meta"]["target_script"] = strings.get(parsed_args[0], "UNKNOWN")
                    node["name"] += f" ➔ {os.path.basename(node['meta']['target_script'])}"
            elif opcode == 0x0034:
                node["name"] = "Define Interactive Hotspots (UI Layout)"
                if len(parsed_args) >= 6:
                    count = parsed_args[0]
                    node["meta"]["count"] = count
                    node["meta"]["layout_param"] = parsed_args[2]
                    node["meta"]["default_goto"] = parsed_args[4]
                    hotspots = []
                    for e in range(count):
                        base = 6 + e * 10
                        if base + 9 < len(parsed_args):
                            hotspots.append({
                                "goto": parsed_args[base],
                                "x": parsed_args[base + 2],
                                "y": parsed_args[base + 4],
                                "w": parsed_args[base + 6],
                                "h": parsed_args[base + 8]
                            })
                    node["meta"]["hotspots"] = hotspots
                    tail = 6 + count * 10
                    if tail < len(parsed_args):
                        node["meta"]["fallback_goto"] = parsed_args[tail]

            elif opcode == 0x004A: node["name"] = "Define Interactive Hotspot"
            elif opcode == 0x004B: node["name"] = "Clear Interactive Hotspots"
            elif opcode == 0x0050: node["name"] = "Enter Battle Mode Module"
            elif opcode == 0x0091:
                node["name"] = "End of Script File"
                nodes.append(node)
                break

            nodes.append(node)
            node_id += 1

    # Link jump targets (code-relative byte offsets) to node indices so the
    # writer can recompute them after add/remove/reorder.
    off2idx = {n["_off"]: i for i, n in enumerate(nodes) if "_off" in n}
    for n in nodes:
        op = int(n["opcode"], 16); a = n.get("args") or []
        tgt = None
        if op in (0x08, 0x09) and len(a) >= 8: tgt = (a[6] & 0xFFFF) | (a[7] << 16)
        elif op == 0x0B and len(a) >= 2:        tgt = (a[0] & 0xFFFF) | (a[1] << 16)
        if tgt is not None and tgt in off2idx:
            n["_target"] = nodes[off2idx[tgt]]["id"]   # stable node id, survives reorder/insert

    return nodes


def _read_string_table(orig, o3):
    """Return (raw_bytes_list, decoded_text_list) for the original string table."""
    total = struct.unpack_from('<I', orig, o3)[0]
    raw, txt = [], []
    for i in range(total):
        rel, ld = struct.unpack_from('<HH', orig, o3 + 4 + i * 4)
        sb = orig[o3 + rel: o3 + rel + ld // 16]
        raw.append(sb)
        txt.append(sb.decode('cp932', 'replace').replace('\x00', '').replace('　', ' '))
    return raw, txt

def _build_string_table(nodes, orig, o3, lang):
    """Rebuild the string table: keep unchanged strings byte-identical, re-encode
    edited 0x11 lines, append new ones. Mutates each 0x11 node's args[0] +
    meta.string_index so the code stream references the right entry."""
    raw, txt = _read_string_table(orig, o3)
    new = list(raw)                 # bytes per index (verbatim by default)
    cur = list(txt)
    def enc(t):
        data = (t or "").encode('cp932', 'replace') + b'\x00'
        if len(data) % 2: data += b'\x00'   # strings are even-length
        return data
    for n in nodes:
        if n.get("opcode") not in ("0011", "000F"):
            continue
        m = n.setdefault("meta", {})
        si = m.get("string_index")
        chosen = (n.get("en_text") or n.get("jp_text") or "") if lang == "en" else (n.get("jp_text") or "")
        if si is None or si < 0 or si >= len(new):   # new dialogue line → append
            si = len(new); new.append(enc(chosen)); cur.append(chosen)
        elif chosen != cur[si]:                       # edited → re-encode
            new[si] = enc(chosen); cur[si] = chosen
        m["string_index"] = si
        n["args"][0] = si                             # both 0x11 and 0x0F carry the index as first operand
    # serialize: [total][ (rel u16, len*16 u16) × total ][contiguous blob]
    total = len(new); base = 4 + total * 4
    entries = bytearray(); blob = bytearray()
    for sb in new:
        entries += struct.pack('<HH', base + len(blob), len(sb) * 16)
        blob += sb
    return struct.pack('<I', total) + bytes(entries) + bytes(blob)

def json_to_ybc(nodes, original_path, lang='jp'):
    """Rebuild a .ybc binary from edited nodes: rebuilds the code section, relinks
    jump targets, and rebuilds the string table (keeping unedited strings byte-
    identical). Preserves the middle section verbatim.
    lang='jp' writes jp_text; lang='en' writes en_text (falling back to jp)."""
    with open(original_path, 'rb') as f:
        orig = f.read()
    magic = struct.unpack_from('<I', orig, 0)[0]
    o1, o2, o3, o4 = struct.unpack_from('<4I', orig, 4)

    # 0) rebuild string table first (fixes 0x11 nodes' args before code emit)
    strings = _build_string_table(nodes, orig, o3, lang)

    # 1) compute each node's new code-relative offset
    offsets, off = [], 0
    for n in nodes:
        offsets.append(off)
        off += 4 + len(n.get("args") or []) * 2
    id2off = {n.get("id"): offsets[i] for i, n in enumerate(nodes)}

    # 2) relink jumps to their target node's new offset (by stable id)
    for i, n in enumerate(nodes):
        tgt = n.get("_target")
        if tgt is None or tgt not in id2off:
            continue
        to = id2off[tgt]
        op = int(n["opcode"], 16); a = n.setdefault("args", [])
        def setw(idx, val):
            while len(a) <= idx + 1: a.append(0)
            a[idx] = val & 0xFFFF; a[idx + 1] = (val >> 16) & 0xFFFF
        if op in (0x08, 0x09): setw(6, to)
        elif op == 0x0B:        setw(0, to)

    # 3) emit code section
    code = bytearray()
    for n in nodes:
        op = int(n["opcode"], 16); a = n.get("args") or []
        code += struct.pack('<HH', op, 4 + len(a) * 2)
        for s in a:
            code += struct.pack('<H', int(s) & 0xFFFF)

    # 4) preserve the middle (o2..o3) verbatim; strings rebuilt above
    middle = orig[o2:o3]
    new_o1 = 0x14
    new_o2 = new_o1 + len(code)
    new_o3 = new_o2 + len(middle)

    out = bytearray()
    out += struct.pack('<I', magic)
    out += struct.pack('<4I', new_o1, new_o2, new_o3, new_o3)
    while len(out) < new_o1:
        out.append(0)
    out += code + middle + strings
    return bytes(out)

@app.route('/')
def index(): return send_file('index.html')

@app.route('/opcode_schema.js')
def serve_schema(): return send_file(os.path.join(BASE_DIR, 'opcode_schema.js'), mimetype='application/javascript')

@app.route('/voice_mapping.json')
def serve_voice_mapping():
    mapping_path = os.path.join(BASE_DIR, 'voice_mapping.json')
    return send_file(mapping_path) if os.path.exists(mapping_path) else jsonify({})

@app.route('/api/voice/<path:filepath>')
def serve_voice_file(filepath): return send_from_directory(VOICE_DIR, filepath)

# ADDED: BGM routing endpoint
@app.route('/api/bgm/<path:filepath>')
def serve_bgm_file(filepath): return send_from_directory(BGM_DIR, filepath)

CURRENT_YBC = None   # resolved path of the .ybc currently loaded (for saving)

# directories searched for .ybc scripts (editor folder + the game's ADV scripts)
SCRIPT_DIRS = [BASE_DIR, os.path.join(BASE_DIR, "Data", "Adv", "DAT")]

def find_ybc(name):
    """Resolve a .ybc filename to a full path across the search dirs."""
    if not name: return None
    if os.path.isabs(name) and os.path.exists(name): return name
    for d in SCRIPT_DIRS:
        pth = os.path.join(d, name)
        if os.path.exists(pth): return pth
    return None

@app.route('/api/list_scripts')
def list_scripts():
    seen, out = set(), []
    for d in SCRIPT_DIRS:
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith('.ybc') and f not in seen:
                seen.add(f); out.append(f)
    return jsonify(out)

@app.route('/api/load_script')
def load_script():
    global CURRENT_YBC
    req = request.args.get('file')
    path = find_ybc(req) if req else None
    if not path:
        path = find_ybc('Chapter003.ybc')
        if not path:
            for d in SCRIPT_DIRS:
                if os.path.isdir(d):
                    for f in sorted(os.listdir(d)):
                        if f.lower().endswith('.ybc'): path = os.path.join(d, f); break
                if path: break
    CURRENT_YBC = os.path.abspath(path) if path else None
    # only fall back to the saved JSON when no specific file was requested
    if not req and os.path.exists(SCRIPT_JSON):
        with open(SCRIPT_JSON, 'r', encoding='utf-8') as f: return jsonify(json.load(f))
    return jsonify(ybc_to_json(path) if path else [])

@app.route('/api/save_ybc', methods=['POST'])
def save_ybc():
    """Compile the edited nodes back to a .ybc binary (backing up the original)."""
    try:
        if not CURRENT_YBC or not os.path.exists(CURRENT_YBC):
            return jsonify({"status": "error", "message": "No source .ybc loaded"}), 400
        nodes = request.get_json()
        lang = request.args.get('lang', 'jp')
        data = json_to_ybc(nodes, CURRENT_YBC, lang)
        bak = CURRENT_YBC + ".bak"
        if not os.path.exists(bak):
            with open(CURRENT_YBC, 'rb') as f, open(bak, 'wb') as g: g.write(f.read())
        with open(CURRENT_YBC, 'wb') as f:
            f.write(data)
        return jsonify({"status": "success", "message": f"Wrote {len(data)} bytes to {os.path.basename(CURRENT_YBC)} (backup: .bak)"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/image/<filename>')
def serve_image(filename):
    if filename.endswith('.png'): filename = filename[:-4]
    base_dir = os.path.join(BASE_DIR, "Data", "ADV", "BIN")
    
    candidates = [filename, filename.lower(), filename.upper(), f"{filename}.bin", f"{filename}.BIN"]
    if filename.lower().startswith('sc'):
        alt = 'mc' + filename[2:]
        candidates.extend([alt, alt.lower(), alt.upper(), f"{alt}.bin", f"{alt}.BIN"])
    elif filename.lower().startswith('mc'):
        alt = 'sc' + filename[2:]
        candidates.extend([alt, alt.lower(), alt.upper(), f"{alt}.bin", f"{alt}.BIN"])

    final_path = None
    for candidate in candidates:
        test_path = os.path.join(base_dir, candidate)
        if os.path.exists(test_path):
            final_path = test_path
            break

    if not final_path:
        for candidate in candidates:
            test_path = os.path.join(BASE_DIR, candidate)
            if os.path.exists(test_path):
                final_path = test_path
                break

    if not final_path:
        img = Image.new('RGBA', (1024, 1024), (255, 0, 0, 128))
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')

    with open(final_path, 'rb') as f:
        header = f.read(24)
        data = f.read()

    img_width = struct.unpack('<H', header[16:18])[0]
    img_height = struct.unpack('<H', header[18:20])[0]
    num_pixels = img_width * img_height
    if len(data) < num_pixels * 2: num_pixels = len(data) // 2

    words = struct.unpack(f'<{num_pixels}H', data[:num_pixels*2])
    img_data = b''.join(LUT_LIST[w] for w in words)
    img = Image.frombytes('RGBA', (img_width, img_height), img_data)

    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/api/save_script', methods=['POST'])
def save_script():
    try:
        modified_nodes = request.get_json()
        with open(SCRIPT_JSON, 'w', encoding='utf-8') as f:
            json.dump(modified_nodes, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success", "message": "Project modifications written successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)

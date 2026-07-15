// opcode_schema.js — authoritative Cross Hermit script-VM opcode schema.
// Shared by battle scripts (t####.bin) AND ADV story scripts (*.ybc): same VM
// (dispatch FUN_004ce8f0, opcode = switch_case + 5).
//
// On disk each command = [opcode u16][totalLen u16][operands...]. editor.py
// parses the operand bytes as little-endian 2-byte shorts into node.args[].
// Most operands are 4-byte TAGGED WORDS (value = word & 0x0FFFFFFF, tag =
// word>>>28: 0 local var, 1 global, 2 immediate, 3 = -1), so a word's PAYLOAD
// lands at an EVEN args index and its tag at the next odd index. A few opcodes
// pack plain 2-byte fields instead. Each param therefore declares `ai` = the
// args[] short-index it reads/writes (matching editor.py's tested mapping),
// and optionally `meta` = the node.meta key the playback reads, so the editor
// keeps both in sync.
//
// param.type drives the widget:
//   enum(options) -> dropdown   int(min/max/hint) -> number   slot -> SLOT list
//   charId -> CHARACTERS list    expr -> EXPRESSIONS list
//   text -> dialogue (binds jp_text/en_text, not args)   operand -> tagged word
// param.conf via the opcode: 'code' exe-confirmed, 'adv' playback-confirmed, 'guess'.

const SLOTS = {
  0:"Narrator (center)", 1:"Center (no name)", 2:"Left (no name)", 3:"Right (no name)",
  4:"Right (no name)", 5:"Main – Left (named)", 6:"Main – Right (named)",
  7:"Sub – Top-Left", 8:"Sub – Mid-Right", 9:"Sub – Bottom-Left", 10:"Sub – Mid-Left", 11:"Sub – Mid-Right"
};
const CHARACTERS = {
  1:"Carrott",2:"Sharron",3:"Pamela",4:"Cecilis",5:"Fana",6:"Elshe",7:"Rosaria",8:"Quest",9:"Ilian",
  10:"Ogier",11:"Sirius",12:"Niu",13:"Yuli",14:"Axo",15:"Chris",16:"Gulliver",17:"Baldr",18:"Fricka",
  19:"Cadmus",20:"Pyros",21:"Yudi",22:"Elle",23:"Sheila",24:"Feldner",25:"Iona",26:"Kifa",
  27:"Nefteka",28:"Husband",29:"Mabella",30:"Myura",31:"Lilith",32:"Yerufa",33:"Sherufa",
  34:"Jacoban",35:"Sharron",36:"Denesia",
  101:"Denesia",102:"Barbara",103:"Ogyon",104:"Rubigia",105:"Brachy",106:"Niehu",107:"Bowbes",
  108:"Bob",109:"Lepin",110:"Papeshu",111:"Fiore",112:"Schneider",113:"Nebiros",114:"Nazreg",
  115:"Cheryl",116:"Lofri",117:"Hermit",118:"Hermit",119:"Hermit",120:"Ouroboros",
  130:"Sharron (alt)"
};
const EXPRESSIONS = {0:"Face 0 (neutral)",1:"Face 1",2:"Face 2",3:"Face 3",4:"Face 4",5:"Face 5",6:"Face 6",7:"Face 7"};
const CMP_OPS   = {1:"==",2:"!=",3:">",4:">=",5:"<",6:"<="};
const ARITH_OPS = {1:"+",2:"-",3:"*",4:"/",5:"%"};

const p = (key,label,type,ai,extra={}) => Object.assign({key,label,type,ai},extra);

// Opcodes are keyed by their 4-hex string to match editor.py's node.opcode.
const OPCODES = {
  // ---- Flow / variables (operand payloads at even args indices) ----
  "0005":{name:"VAR_SET",cat:"Flow",conf:"code",desc:"dest = src.",
    params:[p("dest","Variable","operand",0),p("src","Value","operand",2)]},
  "0006":{name:"VAR_ARITH",cat:"Flow",conf:"code",desc:"dest = dest <op> b.",
    params:[p("dest","Variable","operand",0),p("op","Operator","enum",2,{options:ARITH_OPS}),p("b","Value","operand",4)]},
  "0007":{name:"VAR_RANDOM",cat:"Flow",conf:"code",desc:"dest = random(0..range).",
    params:[p("dest","Variable","operand",0),p("range","Max","operand",2)]},
  "0008":{name:"IF (jump if true)",cat:"Flow",conf:"code",desc:"if A <op> B → goto offset.",
    params:[p("a","A","operand",0),p("op","Operator","enum",2,{options:CMP_OPS}),p("b","B","operand",4),p("target","Goto offset","int",6,{min:0,hint:"byte offset"})]},
  "0009":{name:"IF NOT (jump if false)",cat:"Flow",conf:"code",desc:"if NOT(A <op> B) → goto offset.",
    params:[p("a","A","operand",0),p("op","Operator","enum",2,{options:CMP_OPS}),p("b","B","operand",4),p("target","Goto offset","int",6,{min:0})]},
  "000B":{name:"GOTO",cat:"Flow",conf:"code",desc:"Unconditional jump.",params:[p("target","Goto offset","int",0,{min:0})]},
  "0013":{name:"END_BLOCK",cat:"Flow",conf:"code",desc:"End of block/scene → engine returns to overworld.",params:[]},
  "0047":{name:"SCRIPT_CHAIN",cat:"Flow",conf:"adv",desc:"Load/chain another .ybc.",params:[p("script","Target script","text",0)]},

  // ---- Timing ----
  "000C":{name:"WAIT",cat:"Timing",conf:"code",desc:"Delay / wait for condition (60 ≈ 1s).",params:[p("frames","Frames","int",0,{min:0,hint:"60 = 1 second"})]},
  "000D":{name:"WAIT_B",cat:"Timing",conf:"code",desc:"Wait variant.",params:[p("frames","Frames","int",0,{min:0})]},
  "000E":{name:"WAIT_C",cat:"Timing",conf:"code",desc:"Wait variant + extra param.",params:[p("frames","Frames","int",0,{min:0}),p("p2","Param","int",2)]},

  // ---- Dialogue / text ----
  "0011":{name:"DISPLAY_MESSAGE",cat:"Dialogue",conf:"code",desc:"Print one dialogue line into the active text box.",text:true,params:[]},
  "000F":{name:"PRINT_UNIT_TEXT",cat:"Dialogue",conf:"code",desc:"Engine/menu text line (string table). Used for menu labels, chapter names.",text:true,params:[p("idx","Text index","int",0,{min:0})]},
  "0032":{name:"WAIT_FOR_CLICK",cat:"Dialogue",conf:"code",desc:"Wait for click; resets the dialogue line.",params:[]},
  "0033":{name:"END_PARAGRAPH",cat:"Dialogue",conf:"code",desc:"End message run / clear wait flags; stops voice.",params:[]},
  "0012":{name:"HARD_WAIT",cat:"Dialogue",conf:"adv",desc:"Hard wait / end of paragraph block.",params:[]},
  "0014":{name:"HIDE_TEXTBOX",cat:"Dialogue",conf:"code",desc:"Set display mode / hide text box & UI.",params:[p("mode","Mode","int",0,{min:0,max:255})]},
  "0028":{name:"SET_NAMEPLATE",cat:"Dialogue",conf:"adv",desc:"Set the speaker nameplate.",params:[p("char","Character","charId",0,{meta:"char_id"})]},
  "002B":{name:"SELECT_TEXTBOX_SLOT",cat:"Dialogue",conf:"code",desc:"Which speech box the next text goes to.",params:[p("slot","Active slot","slot",0,{meta:"slot_id"})]},

  // ---- Portraits ----
  "001E":{name:"PORTRAIT_LOAD (animate in)",cat:"Portrait",conf:"adv",desc:"Load a portrait into a speech box, animate in.",
    params:[p("slot","Speech box","slot",0,{meta:"speech_box"}),p("char","Character","charId",2,{meta:"char_id"}),
            p("expr","Expression","expr",4,{meta:"expression"}),p("speed","Anim speed","int",6,{min:0,max:255,meta:"speed"}),p("flag","Flag","int",8,{meta:"flag"})]},
  "0021":{name:"PORTRAIT_UPDATE (instant)",cat:"Portrait",conf:"adv",desc:"Set/swap portrait + expression instantly.",
    params:[p("slot","Speech box","slot",0,{meta:"speech_box"}),p("char","Character","charId",2,{meta:"char_id"}),p("expr","Expression","expr",4,{meta:"expression"})]},
  "001A":{name:"SLOT_LINK / transition",cat:"Portrait",conf:"adv",desc:"Connect/transition a character between slots.",
    params:[p("src","Source slot","slot",0,{meta:"src_slot"}),p("dest","Dest slot","slot",1,{meta:"dest_slot"}),p("char","Character","charId",2,{meta:"char_id"}),p("flag","Flag","int",3,{meta:"flag"})]},
  "001B":{name:"CLEAR_PORTRAIT_SLOT",cat:"Portrait",conf:"adv",desc:"Remove a portrait slot.",params:[p("slot","Slot","slot",0,{meta:"slot_id"})]},
  "0023":{name:"CLEAR_PORTRAIT (fade)",cat:"Portrait",conf:"adv",desc:"Clear a portrait slot with a fade rule.",params:[p("slot","Slot","slot",0,{meta:"slot_id"}),p("fade","Fade rule","int",1,{min:0,max:255,meta:"fade_rule"})]},
  "0024":{name:"WAIT_PORTRAIT_SYNC",cat:"Portrait",conf:"adv",desc:"Wait for portrait update to finish.",params:[]},

  // ---- Message box / window ----
  "001C":{name:"WINDOW_STYLE / hide",cat:"MsgBox",conf:"code",desc:"Hide window / change window style.",params:[p("style","Style id","int",0,{min:0,max:255,meta:"style_id"})]},
  "001F":{name:"MENU_OVERLAY",cat:"MsgBox",conf:"guess",desc:"Load a menu/map overlay (same family as 0x1E). Verify.",params:[p("slot","Slot","slot",0),p("char","Character","charId",2),p("expr","Expression","expr",4)]},
  "0020":{name:"MSGBOX_HIDE_B",cat:"MsgBox",conf:"code",desc:"Hide message box (variant).",params:[p("p0","Param","int",0)]},

  // ---- Display / visuals ----
  "0015":{name:"RESET_DISPLAY_SLOTS",cat:"Display",conf:"code",desc:"Reset all display slots.",params:[]},
  "002C":{name:"COMMIT_DISPLAY / flush",cat:"Display",conf:"code",desc:"Refresh/flush the screen.",params:[]},
  "002A":{name:"SHAKE_SCREEN",cat:"Display",conf:"adv",desc:"Screen shake.",params:[p("intensity","Intensity","int",0,{min:0,max:255,meta:"intensity"}),p("duration","Duration","int",1,{min:0,meta:"duration"})]},
  "003B":{name:"LOAD_BACKGROUND",cat:"Display",conf:"adv",desc:"Full-screen background (BGxxx). Clears chars/CG.",params:[p("bg","Background id","int",-1,{min:0,max:300,meta:"bg_id",hint:"≤116 → BG((id-1)/4+1)_(A-D)"})]},
  "0043":{name:"CLEAR_CANVAS",cat:"Display",conf:"code",desc:"Clear render buffers (BG kept).",params:[]},
  "0045":{name:"DISPLAY_CG / blit region",cat:"Effect",conf:"adv",desc:"Crop a region from a loaded BG texture and blit it to screen.",
    params:[p("page","Source page","operand",0,{meta:"source_page"}),p("destX","Dest X","operand",2,{meta:"dest_x"}),p("destY","Dest Y","operand",4,{meta:"dest_y"}),p("layer","Layer","operand",8,{meta:"layer_id"}),p("srcX","Src X","operand",10,{meta:"src_x"}),p("srcY","Src Y","operand",12,{meta:"src_y"}),p("cropW","Crop W","operand",14,{meta:"crop_w"}),p("cropH","Crop H","operand",16,{meta:"crop_h"})]},
  "004A":{name:"EFFECT_CLEAR_ALL",cat:"Effect",conf:"code",desc:"Clear all effect/scene objects.",params:[]},

  // ---- Audio ----
  "003C":{name:"PLAY_BGM",cat:"Audio",conf:"adv",desc:"Play background music.",params:[p("bgm","BGM id","int",0,{min:0,max:255,meta:"bgm_id"}),p("fadeIn","Fade in","int",1,{min:0,meta:"fade_in"}),p("volume","Volume","int",2,{min:0,max:100,meta:"volume"})]},
  "003D":{name:"STOP_BGM",cat:"Audio",conf:"adv",desc:"Stop background music.",params:[]},
  "003E":{name:"PLAY_SE",cat:"Audio",conf:"adv",desc:"Play a sound effect.",params:[p("se","SE id","int",0,{min:0,max:255})]},
  "003F":{name:"PLAY_SE_WAIT / env BGM",cat:"Audio",conf:"code",desc:"Play sound/stream and wait.",params:[p("track","Track id","int",0,{min:0,max:255,meta:"track_id"})]},
  "0041":{name:"PLAY_VOICE",cat:"Audio",conf:"code",desc:"Play a voice file (group + index).",params:[p("group","Voice group","int",0,{min:0,max:999}),p("index","Voice index","int",1,{min:0})]},
  "0042":{name:"STOP_VOICE",cat:"Audio",conf:"code",desc:"Stop voice.",params:[]},

  // ---- System / state ----
  "0034":{name:"DEFINE_HOTSPOTS",cat:"System",conf:"code",desc:"Define interactive clickable hotspot regions (menus/battles). Count + per-element (goto, x, y, w, h) + fallback goto.",
    params:[],layout:true},
  "0038":{name:"WAIT_MENU_INPUT",cat:"System",conf:"adv",desc:"Wait for menu input / dispatch.",params:[p("p0","Param","int",0)]},
  "005A":{name:"GET_SYSVAR",cat:"System",conf:"code",desc:"Read a system var into dest.",params:[p("dest","Variable","operand",0),p("which","Sysvar id","int",2,{min:0})]},
  "005B":{name:"SET_SYSVAR",cat:"System",conf:"code",desc:"Write a display/system flag (low byte).",params:[p("value","Value","int",0,{min:0})]},
  "0060":{name:"SET_WORK_W32",cat:"System",conf:"code",desc:"Write a saved 32-bit work value.",params:[p("value","Value","operand",0),p("slot","Work slot","int",2,{min:0,max:63})]},
  "0063":{name:"SET_FLAG",cat:"System",conf:"code",desc:"Set a saved 1-bit flag.",params:[p("value","0/1","int",0,{min:0,max:1}),p("flag","Flag id","int",2,{min:0,max:2047})]},
  "00A6":{name:"SET_GLOBAL_FLAG",cat:"System",conf:"code",desc:"Set a global flag.",params:[p("flag","Flag id","int",0),p("value","Value","int",2)]},

  // ---- Sprite cells ----
  "0097":{name:"SPRITE_CELL_SHOW",cat:"Sprite",conf:"code",desc:"Show a sprite cell.",params:[p("cell","Cell","int",0),p("wait","Wait?","enum",2,{options:{0:"no",1:"yes"}})]},

  // ---- Battle ----
  "0050":{name:"ENTER_BATTLE",cat:"Flow",conf:"guess",desc:"Enter battle module (battles usually launch from the overworld node — verify).",params:[p("p0","Param","int",0)]}
};
for (const k of Object.keys(OPCODES)) if (!OPCODES[k].name) delete OPCODES[k];

const CATEGORY_COLOR = {
  Flow:"#c586c0", Timing:"#569cd6", Dialogue:"#4fc1ff", Portrait:"#dcdcaa",
  MsgBox:"#9cdcfe", Display:"#4ec9b0", Effect:"#ce9178", Audio:"#b5cea8", System:"#d7ba7d", Sprite:"#d16969"
};
const CONF_BADGE = { code:["✓ exe","#2e9e2e"], adv:["● play","#0e639c"], guess:["? guess","#a06a00"] };

if (typeof window !== "undefined")
  window.OPCODE_SCHEMA = { OPCODES, SLOTS, CHARACTERS, EXPRESSIONS, CMP_OPS, ARITH_OPS, CATEGORY_COLOR, CONF_BADGE };
if (typeof module !== "undefined")
  module.exports = { OPCODES, SLOTS, CHARACTERS, EXPRESSIONS, CMP_OPS, ARITH_OPS, CATEGORY_COLOR, CONF_BADGE };

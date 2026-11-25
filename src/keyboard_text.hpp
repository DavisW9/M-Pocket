#pragma once
#include <string>
// Numeric codes are Linux input-event-codes.h values.
// The firmware emits these custom keycodes for the printed SYM layer.
// Values match M5Stack's MIT-licensed launcher keyboard_input.c.
static char typedCharacter(unsigned code,bool shift,bool caps,bool sym){
    struct Symbol{unsigned code;char text;};
    // Device keymap: /usr/share/keymaps/tca8418_keypad_m5stack_keymap.map.
    if(sym){
        static const Symbol cardputerZeroSym[]={{26,'!'},{27,'@'},{39,'#'},{40,'$'},{41,'%'},{43,'^'},
            {51,'&'},{52,'*'},{53,'('},{94,')'},{55,'~'},{69,'`'},{70,'_'},{71,'-'},{72,'+'},{73,'='},
            {74,'['},{75,']'},{76,'{'},{77,'}'},{79,';'},{80,':'},{81,'\''},{82,'"'},
            {83,'<'},{85,'>'},{86,'\\'},{89,'|'},{90,','},{91,'.'},{92,'/'},{93,'?'}};
        for(auto s:cardputerZeroSym)if(s.code==code)return s.text;
    }
    static const Symbol custom[]={{183,'!'},{184,'@'},{185,'#'},{186,'$'},{187,'%'},{188,'^'},{189,'&'},{190,'*'},{191,'('},{192,')'},
        {193,'~'},{194,'`'},{195,'_'},{196,'-'},{197,'+'},{198,'='},{199,'['},{200,']'},{201,'{'},{202,'}'},
        {231,';'},{232,':'},{209,'"'},{210,'<'},{211,'>'},{212,'\\'},{213,'|'},{214,','},{215,'.'},{216,'/'},{217,'?'}};
    for(auto s:custom)if(s.code==code)return s.text;
    char c=0;
    if(code>=16 && code<=25)c="qwertyuiop"[code-16];
    else if(code>=30 && code<=38)c="asdfghjkl"[code-30];
    else if(code>=44 && code<=50)c="zxcvbnm"[code-44];
    else if(code>=2 && code<=11)return (shift||sym?"!@#$%^&*()":"1234567890")[code-2];
    if(c){
        if(sym){
            static const char symbolKeys[]="qwertyuiopasghjklvbnm";
            static const char symbolChars[]={'~','`','_','-','+','=','[',']','{','}',';',':','"','<','>','\\','|',',','.','/','?'};
            for(size_t i=0;i<sizeof(symbolKeys)-1;i++)if(c==symbolKeys[i])return symbolChars[i];
        }
        return shift!=caps?c-32:c;
    }
    switch(code){
        case 57:return ' ';case 52:return shift?'>':'.';case 51:return shift?'<':',';
        case 12:return shift?'_':'-';case 13:return shift?'+':'=';
        case 53:return shift?'?':'/';case 43:return shift?'|':'\\';
        case 39:return shift?':':';';case 40:return shift?'"':'\'';
        case 41:return shift?'~':'`';case 26:return shift?'{':'[';case 27:return shift?'}':']';
        default:return 0;
    }
}

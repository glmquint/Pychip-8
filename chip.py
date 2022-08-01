from tui import draw_from_arr as draw
from sys import argv
from time import sleep
from byte_operations import *
from struct import unpack, pack
import traceback
from time import time

DEBUG = False
STOP_ON_EXCEPTION = False
SHOW_DISASM = True
O_HLT_ON_LOOP = False

def here(msg=''):
    print(f"REACHED HERE ({msg})")
    quit()

def usage(argv0):
    print(f"USAGE: python3 {argv0} <rom>")

def debug_bitplane(bitplane, width):
    for i in range(0, len(bitplane), width):
        log(bitplane[i:i+width])

def show_disasm(disasm):
    if DEBUG and SHOW_DISASM:
        print(f"[DISM] {disasm};")

def log(msg, end='\n'):
    if DEBUG:
        if end != '\n':
            print(f"{msg}", end=end)
        else:
            print(f"[DEBUG]: {msg}")

SCREEN_WIDTH            = 64
SCREEN_HEIGHT           = 32
STACK_BASE              = 0x0200
HEXDIGIT_SPRITES_BASE   = 0x0000
HEXDIGIT_SPRITES = bytearray([  
        0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
        0x20, 0x60, 0x20, 0x20, 0x70, # 1
        0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
        0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
        0x90, 0x90, 0xF0, 0x10, 0x10, # 4
        0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
        0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
        0xF0, 0x10, 0x20, 0x40, 0x40, # 7
        0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
        0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
        0xF0, 0x90, 0xF0, 0x90, 0x90, # A
        0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
        0xF0, 0x80, 0x80, 0x80, 0xF0, # C
        0xE0, 0x90, 0x90, 0x90, 0xE0, # D
        0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
        0xF0, 0x80, 0xF0, 0x80, 0x80  # F
    ])


class Chip:
    memory      = bytearray([0] * 4096)
    display     = '0'*(SCREEN_WIDTH * SCREEN_HEIGHT) 
    pc          = 0x0200    
    I           = 0x0000    
    sp          = 0x00    
    delay_timer = 0x00      
    sound_timer = 0x00      
    V           = [0x00]*16 
    redraw      = False

    def dump(self, show_memory=True, start=0, end=-1):
        if start == -1:
            start = self.pc 
            end += start
        elif end < 0:
            end = len(self.memory)
        log(f"\t\t===BEGIN DUMP (from {start} to {end})===")
        bytes_per_line = 8
        if show_memory:
            for y in range(start, end, bytes_per_line):
                log(f"{y:#0{5}x}\t| ", end='')
                for x in range(bytes_per_line):
                    log(f"{self.memory[y + x]:#04x} ", end='')
                log("|", end=' \n')
        log("display = ")
        debug_bitplane(self.display, SCREEN_WIDTH)

        log(f"pc = {hex(self.pc)} ({self.pc})")
        log(f"I = {hex(self.I)} ({self.I})")
        log(f"sp = {hex(self.sp)} ({self.sp})")
        log(f"delay_timer = {hex(self.delay_timer)} ({self.delay_timer})")
        log(f"sound_timer = {hex(self.sound_timer)} ({self.sound_timer})")
        for x in range(len(self.V)):
            log(f"V{x:01x} = {hex(self.V[x])} ({self.V[x]})")
        log("\t\t===END DUMP===")

    def fetch(self):
        self.pc += 2
        return self.memory[self.pc-2:self.pc]

    def decode_and_execute(self, data):
        log(f"decoding {data.hex() = }")
        high_nibble = byte_and(data, b'\xF0\x00')
        if data == b'\x00\xE0':
            self.cls()
        elif data == b'\x00\xEE':
            self.ret()
        elif high_nibble == b'\x10\x00':
            self.jp_addr(data)
        elif high_nibble == b'\x20\x00':
            self.call_addr(data)
        elif high_nibble == b'\x30\x00':
            self.se_vx_byte(data)
        elif high_nibble == b'\x40\x00':
            self.sne_vx_byte(data)
        elif high_nibble == b'\x50\x00':
            self.se_vx_vy(data)
        elif high_nibble == b'\x60\x00':
            self.ld_vx_byte(data)
        elif high_nibble == b'\x70\x00':
            self.add_vx_byte(data)
        elif high_nibble == b'\x80\x00':
            self.alu(data)
        elif high_nibble == b'\x90\x00':
            self.sne_vx_vy(data)
        elif high_nibble == b'\xa0\x00':
            self.ld_i_addr(data)
        elif high_nibble == b'\xd0\x00':
            self.drw_vx_vy_nibble(data)
        elif high_nibble == b'\xf0\x00':
            self.extra(data)
        else:
            raise Exception(f"Invalid instruction ({data.hex()} @ pc:{self.pc:#04x})")

    def render(self):
        #log(f"now rendering {len(self.display)} pixels:")
        #debug_bitplane(self.display, SCREEN_WIDTH)
        draw(SCREEN_WIDTH, SCREEN_HEIGHT, self.display, self.delay_timer)
        self.redraw = False



    def cls(self):
        self.display = '0'*(SCREEN_WIDTH * SCREEN_HEIGHT)
        self.redraw = True
        show_disasm("cls")

    def ret(self):
        offset = STACK_BASE - (self.sp*2)
        self.pc = unpack('>H', self.memory[offset:offset+2])[0]
        self.sp -= 1
        show_disasm(f"ret")

    def jp_addr(self, data):
        jmp_addr = unpack('>H', data)[0] & 0x0fff
        if O_HLT_ON_LOOP and self.pc == jmp_addr+2:
            raise Exception("Halt (infinite loop detected)")
        else:
            self.pc = jmp_addr
        show_disasm(f"jp {jmp_addr:#04x}")

    def call_addr(self, data):
        addr = unpack('>H', data)[0] & 0x0fff
        self.sp += 1
        offset = STACK_BASE - (self.sp*2)
        self.memory = self.memory[:offset] + pack('>H', self.pc) + self.memory[offset+2:]
        DEBUG = True
        self.pc = addr
        show_disasm(f"call {addr:#04x}")

    def se_vx_byte(self, data):
        x = data[0] & 0x0f
        if self.V[x] == data[1]:
            self.pc += 2
        show_disasm(f"se v{x:01x} {data[1]:#04x}")

    def sne_vx_byte(self, data):
        x = data[0] & 0x0f
        if self.V[x] != data[1]:
            self.pc += 2
        show_disasm(f"sne v{x:01x} {data[1]:#04x}")

    def se_vx_vy(self, data):
        x = data[0] & 0x0f
        y = (data[1] & 0xf0) >> 4
        if self.V[x] == self.V[y]:
            self.pc += 2
        show_disasm(f"se v{x:01x} v{y:01x}")

    def ld_vx_byte(self, data):
        x = data[0] & 0x0f
        self.V[x] = data[1]
        show_disasm(f"ld v{x:01x} {data[1]:#04x}")

    def add_vx_byte(self, data):
        x = data[0] & 0x0f
        self.V[x] += data[1]
        self.V[x] &= 0xff
        show_disasm(f"add v{x:01x} {data[1]:#04x}")

    def alu(self, data): 
        op = data[1] & 0x0f
        x = data[0] & 0x0f
        y = (data[1] & 0xf0) >> 4
        if op == 0x00: #set
            self.V[x] = self.V[y]
            show_disasm(f"ld v{x:01x} v{y:01x}")
        elif op == 0x01: #or
            self.V[x] |= self.V[y]
            show_disasm(f"or v{x:01x} v{y:01x}")
        elif op == 0x02: #and
            self.V[x] &= self.V[y]
            show_disasm(f"and v{x:01x} v{y:01x}")
        elif op == 0x03: #xor
            self.V[x] ^= self.V[y]
            show_disasm(f"xor v{x:01x} v{y:01x}")
        elif op == 0x04: #add
            self.V[x] += self.V[y]
            self.V[0xf] = 0x1 if self.V[x] > 0xff else 0x0
            self.V[x] &= 0xff
            show_disasm(f"add v{x:01x} v{y:01x}")
        elif op == 0x05: #sub
            self.V[0xf] = 0x1 if self.V[x] > self.V[y] else 0x0
            self.V[x] = (self.V[x] - self.V[y]) & 0xff
            show_disasm(f"sub v{x:01x} v{y:01x}")
        elif op == 0x06: #shr
            self.V[0xf] = self.V[x] % 2
            self.V[x] = self.V[x] >> 1
            show_disasm(f"shr v{x:01x} (, v{y:01x})")
        elif op == 0x07: #subn
            self.V[0xf] = 0x1 if self.V[y] > self.V[x] else 0x0
            self.V[x] = (self.V[y] - self.V[x]) & 0xff
            show_disasm(f"subn v{x:01x} v{y:01x}")
        elif op == 0x0e: #shl
            self.V[0xf] = 1 if self.V[x] & 0b10000000 == 0b10000000 else 0
            self.V[x] = (self.V[x] << 1) & 0xff
            show_disasm(f"shl v{x:01x} (, v{y:01x})")
        else:
            raise Exception(f"Unrecognized logic or arithmetic instruction {data}")

    def sne_vx_vy(self, data):
        x = data[0] & 0x0f
        y = (data[1] & 0xf0) >> 4
        if self.V[x] != self.V[y]: 
            self.pc += 2
        show_disasm(f"sne v{x:01x} v{y:01x}")

    def ld_i_addr(self, data):
        a = unpack('>H', data)[0] & 0x0fff
        self.I = a
        show_disasm(f"ld I 0x{a:#04x}")

    def drw_vx_vy_nibble(self, data):
        x = data[0] & 0x0f
        y = (data[1] & 0xf0) >> 4
        n = data[1] & 0x0f
        for i in range(n):
            if self.V[y] + i > SCREEN_HEIGHT:
                break
            bit_sprite_row = f"{self.memory[self.I + i]:08b}"
            for j, bit in enumerate(bit_sprite_row):
                offset = (self.V[y]+i)*SCREEN_WIDTH + self.V[x] + j
                if self.V[x] + j > SCREEN_WIDTH:
                    break
                if bit == '1':
                    if self.display[offset] == '1':
                        self.display = self.display[:offset] + '0' + self.display[offset+1:]
                        self.V[0xF] = 1
                    else:
                        self.display = self.display[:offset] + '1' + self.display[offset+1:]
                    self.redraw = True

        show_disasm(f"drw v{x:01x} v{y:01x} {n}")

    def extra(self, data):
        x = data[0] & 0x0f
        if data[1] == 0x07:
            self.V[x] = self.delay_timer
            show_disasm(f"ld v{x:01x}, dt")
        elif data[1] == 0x0a:
            raise Exception("Unimplemented keyboard interaction instruction {data.hex()}")
            show_disasm(f"ld v{x:01x} K")
        elif data[1] == 0x15:
            self.delay_timer = self.V[x]
            show_disasm(f"ld dt v{x:01x}")
        elif data[1] == 0x18:
            self.sound_timer = self.V[x]
            show_disasm(f"ld st v{x:01x}")
        elif data[1] == 0x1e:
            self.I += self.V[x]
            self.I &= 0xffff
            show_disasm(f"add i v{x:01x}")
        elif data[1] == 0x29:
            self.I = HEXDIGIT_SPRITES_BASE + (self.V[x] * 5)
            show_disasm(f"ld f v{x:01x}")
        elif data[1] == 0x33:
            raise Exception("Unimplemented BCD soring instruction {data.hex()}")
            show_disasm(f"ld b v{x:01x}")
        elif data[1] == 0x55:
            for i in range(x+1):
                self.memory = self.memory[:self.I+i] + bytes([self.V[i]]) + self.memory[self.I+i+1:]
            show_disasm(f"ld [i], v{x:01x}")
        elif data[1] == 0x65:
            for i in range(x+1):
                self.V[x] = self.memory[self.I+i]
            show_disasm(f"ld v{x:01x}, [i]")



breakpoints = []#[0x3a0]

if __name__ == '__main__':
    #argv.append('roms/test_opcode.ch8') # FIXME: temporary
    argv.append('roms/IBM Logo.ch8') # FIXME: temporary
    if len(argv) < 2:
        usage(argv[0])
        quit()

    chip = Chip()
    chip.memory = chip.memory[:HEXDIGIT_SPRITES_BASE] + HEXDIGIT_SPRITES + chip.memory[HEXDIGIT_SPRITES_BASE + len(HEXDIGIT_SPRITES):]
    with open(argv[1], 'rb') as f:
        rom = memoryview(chip.memory)
        f.readinto(rom[0x200:])

    chip.dump()
    start_time = time()
    IPF = 0 #instructions per frame
    while True:
        assert len(chip.memory) == 0x1000, f"{chip.pc:#04x}"
        if DEBUG:
            done = False
            while not done:
                cmd = input('\n(s)tep, (c)ontinue, (b)reak, (d)ump, (r)ender display > ')
                if cmd == 's':
                    done = True
                elif cmd == 'c':
                    DEBUG = False
                    done = True
                elif cmd == 'b':
                    ans = input(f"{breakpoints = } ('clear' to delete all breakpoints, non hex value to exit): ")
                    if ans == 'clear':
                        breakpoints = []
                        print("breakpoints list cleared")
                    else:
                        try:
                            breakpoints.append(int(ans, 16))
                        except:
                            pass
                        else:
                            print(f"breakpoint added @ {int(ans, 16):#04x}")
                elif cmd == 'd':
                    chip.dump()
                elif cmd == 'r':
                    chip.render()
        elapsed = time()-start_time
        if elapsed > (1/60):
            if chip.delay_timer > 0:
                chip.delay_timer -= 1
            if chip.sound_timer > 0:
                chip.sound_timer -= 1
            if chip.redraw:
                chip.render()
            start_time = time()# - (elapsed - 1/60)
            #print(f"instructions in last frame = {IPF}, time elapsed: {elapsed}, FPS = {1/elapsed}\r", end='')
            IPF = 0

        data = chip.fetch()
        #chip.dump(True, -1, 60)
        try:
            chip.decode_and_execute(data)
            IPF += 1
        except Exception as e:
            print(traceback.format_exc())
            DEBUG = STOP_ON_EXCEPTION
        if chip.pc in breakpoints:
            print(f"\nHit breakpoint! pc: {chip.pc:#04x}")
            DEBUG = True

from tui import draw_from_arr as draw
from sys import argv
from time import sleep
from byte_operations import *
from struct import unpack, pack
import traceback
from time import time

DEBUG = False

def here(msg=''):
    print(f"REACHED HERE ({msg})")
    quit()

def usage(argv0):
    print(f"USAGE: python3 {argv0} <rom>")

def debug_bitplane(bitplane, width):
    for i in range(0, len(bitplane), width):
        log(bitplane[i:i+width])

def show_disasm(disasm):
    if DEBUG:
        print(f"[DISM] {disasm};")

def log(msg, end='\n'):
    if DEBUG:
        if end != '\n':
            print(f"{msg}", end=end)
        else:
            print(f"[DEBUG]: {msg}")

SCREEN_WIDTH = 64
SCREEN_HEIGHT = 32

class Chip:
    memory      = bytearray([0] * 4096)
    display     = '0'*(SCREEN_WIDTH * SCREEN_HEIGHT) 
    pc          = 0x0200    
    I           = 0x0000    
    sp          = 0x0000    
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
                    log(f"{self.memory[y + x]:#0{4}x} ", end='')
                log("|", end=' \n')
        log("display = ")
        debug_bitplane(self.display, SCREEN_WIDTH)

        log(f"pc = {hex(self.pc)} ({self.pc})")
        log(f"I = {hex(self.I)} ({self.I})")
        log(f"sp = {hex(self.sp)} ({self.sp})")
        log(f"delay_timer = {hex(self.delay_timer)} ({self.delay_timer})")
        log(f"sound_timer = {hex(self.sound_timer)} ({self.sound_timer})")
        for x in range(len(self.V)):
            log(f"V{x} = {hex(self.V[x])} ({self.V[x]})")
        log("\t\t===END DUMP===")

    def fetch(self):
        self.pc += 2
        return self.memory[self.pc-2:self.pc]

    def decode_and_execute(self, data):
        log(f"decoding {data.hex() = }")
        high_nibble = byte_and(data, b'\xF0\x00')
        if data == b'\x00\xE0':
            self.cls()
        elif high_nibble == b'\x10\x00':
            self.jp_addr(data)
        elif high_nibble == b'\x60\x00':
            self.ld_vx_byte(data)
        elif high_nibble == b'\x70\x00':
            self.add_vx_byte(data)
        elif high_nibble == b'\xa0\x00':
            self.ld_i_addr(data)
        elif high_nibble == b'\xd0\x00':
            self.drw_vx_vy_nibble(data)
        else:
            raise Exception(f"Unimplemented instruction ({data.hex()} @ pc:{self.pc.hex()})")

    def render(self):
        #log(f"now rendering {len(self.display)} pixels:")
        #debug_bitplane(self.display, SCREEN_WIDTH)
        draw(SCREEN_WIDTH, SCREEN_HEIGHT, self.display)
        self.redraw = False



    def cls(self):
        self.display = '0'*(SCREEN_WIDTH * SCREEN_HEIGHT)
        self.redraw = True
        show_disasm("cls")

    def jp_addr(self, data):
        jmp_addr = unpack('>H', byte_and(data, b'\x0f\xff'))[0]
        if False: #self.pc == jmp_addr+2:
            raise Exception("Halt")
        else:
            self.pc = jmp_addr
        show_disasm(f"jp {jmp_addr:#04x}")

    def ld_vx_byte(self, data):
        x = unpack('<B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        self.V[x] = data[1]
        show_disasm(f"ld v{x} {data[1]:#04x}")

    def add_vx_byte(self, data):
        x = unpack('<B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        self.V[x] += data[1]
        show_disasm(f"add v{x} {data[1]:#04x}")

    def ld_i_addr(self, data):
        a = byte_and(data, b'\x0f\xff')
        self.I = unpack('>H', a)[0]
        show_disasm(f"ld I 0x{a.hex()}")

    def drw_vx_vy_nibble(self, data):
        x = unpack('>B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        y = unpack('>B', byte_and(bytes([data[1]]), b'\xf0'))[0] >> 4
        n = unpack('>B', byte_and(bytes([data[1]]), b'\x0f'))[0]
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

        show_disasm(f"drw v{x} v{y} {n}")



if __name__ == '__main__':
    argv.append('roms/IBM logo.ch8') # FIXME: temporary
    if len(argv) < 2:
        usage(argv[0])
        quit()

    chip = Chip()
    with open(argv[1], 'rb') as f:
        rom = memoryview(chip.memory)
        f.readinto(rom[0x200:])

    chip.dump()
    start_time = time()
    IPF = 0 #instructions per frame
    while True:
        data = chip.fetch()
        try:
            chip.decode_and_execute(data)
            IPF += 1
        except Exception as e:
            here(traceback.format_exc())
        #chip.dump(True, -1, 60)
        elapsed = time()-start_time
        if elapsed > (1/60):
            if chip.redraw:
                chip.render()
            start_time = time()# - (elapsed - 1/60)
            print(f"instructions in last frame = {IPF}, time elapsed: {elapsed}, FPS = {1/elapsed}\r", end='')
            IPF = 0
        #input()

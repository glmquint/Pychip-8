from tui import draw_from_arr as draw
from sys import argv
from time import sleep
from byte_operations import *
from struct import unpack, pack
import traceback
from time import time

def here(msg=''):
    print(f"REACHED HERE ({msg})")
    quit()

def usage(argv0):
    print(f"USAGE: python3 {argv0} <rom>")

def debug_bitplane(bitplane, width):
    for i in range(0, len(bitplane), width):
        print(bitplane[i:i+width])

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

    def dump(self, show_memory=True, start=0, end=-1):
        if start == -1:
            start = self.pc 
            end += start
        elif end < 0:
            end = len(self.memory)
        print(f"\t\t===BEGIN DUMP (from {start} to {end})===")
        bytes_per_line = 8
        if show_memory:
            for y in range(start, end, bytes_per_line):
                print(f"{y:#0{5}x}\t| ", end='')
                for x in range(bytes_per_line):
                    print(f"{self.memory[y + x]:#0{4}x} ", end='')
                print("|")
        print("display = ")
        debug_bitplane(self.display, SCREEN_WIDTH)

        print(f"pc = {hex(self.pc)} ({self.pc})")
        print(f"I = {hex(self.I)} ({self.I})")
        print(f"sp = {hex(self.sp)} ({self.sp})")
        print(f"delay_timer = {hex(self.delay_timer)} ({self.delay_timer})")
        print(f"sound_timer = {hex(self.sound_timer)} ({self.sound_timer})")
        for x in range(len(self.V)):
            print(f"V{x} = {hex(self.V[x])} ({self.V[x]})")
        print("\t\t===END DUMP===")

    def fetch(self):
        self.pc += 2
        return self.memory[self.pc-2:self.pc]

    def decode_and_execute(self, data):
        print(f"decoding {data.hex() = }")
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
        #print(f"now rendering {len(self.display)} pixels:")
        #debug_bitplane(self.display, SCREEN_WIDTH)
        draw(SCREEN_WIDTH, SCREEN_HEIGHT, self.display)



    def cls(self):
        self.display = '0'*(SCREEN_WIDTH * SCREEN_HEIGHT)
        print(f"[DISM] cls;")

    def jp_addr(self, data):
        jmp_addr = unpack('>H', byte_and(data, b'\x0f\xff'))[0]
        if False: #self.pc == jmp_addr+2:
            raise Exception("Halt")
        else:
            self.pc = jmp_addr
        print(f"[DISM] jp {jmp_addr};")

    def ld_vx_byte(self, data):
        x = unpack('<B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        self.V[x] = data[1]
        print(f"[DISM] ld v{x} {hex(data[1])};")

    def add_vx_byte(self, data):
        x = unpack('<B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        self.V[x] += data[1]
        print(f"[DISM] add v{x} {data[1]};")

    def ld_i_addr(self, data):
        a = byte_and(data, b'\x0f\xff')
        self.I = unpack('>H', a)[0]
        print(f"[DISM] ld I {a.hex()};")

    def drw_vx_vy_nibble(self, data):
        x = unpack('>B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        y = unpack('>B', byte_and(bytes([data[1]]), b'\xf0'))[0] >> 4
        n = unpack('>B', byte_and(bytes([data[1]]), b'\x0f'))[0]
        sprite = self.memory[self.I:self.I+n]
        #print(f"{x = } V[{x}] = {hex(self.V[x])}, {y = } V[{y}] = {hex(self.V[y])}, {n = }, {hex(self.I) = }, {sprite = }")
        
        for i in range(n):
            bit_sprite = f"{sprite[i]:08b}"
            offset = (self.V[y]+i)*SCREEN_WIDTH + self.V[x]
            new_plane = '0'*(offset) + bit_sprite + '0'*(SCREEN_WIDTH*SCREEN_HEIGHT - len(bit_sprite) - offset)
            res_plane = ''
            for a, b in zip(self.display, new_plane):
                res_plane += str(int(a) | int(b))
            self.display = res_plane

        print(f"[DISM] drw v{x} v{y} {n};")



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
    while True:
        start_time = time()
        data = chip.fetch()
        try:
            chip.decode_and_execute(data)
        except Exception as e:
            here(traceback.format_exc())
        #chip.dump(True, -1, 60)
        chip.render()
        elapsed = time()-start_time
        print(f"time elapsed: {elapsed}, FPS = {1/elapsed}")
        wait_time = max(0, 1/60 - elapsed)
        sleep(wait_time)

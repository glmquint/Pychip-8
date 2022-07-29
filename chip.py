from tui import draw_from_arr as draw
from sys import argv
from time import sleep
from byte_operations import *
from struct import unpack, pack
import traceback

def here(msg=''):
    print(f"REACHED HERE ({msg})")
    quit()

def usage(argv0):
    print(f"USAGE: python3 {argv0} <rom>")

SCREEN_WIDTH = 64
SCREEN_HEIGHT = 32

class Chip:
    memory      = bytearray([0] * 4096)
    display     = bytearray([0] * (8*4)) # 64x32 pixels monochrome
    pc          = bytearray(b'\x02\x00')
    I           = bytearray([0] * 2)
    sp          = bytearray([0] * 2)
    delay_timer = bytearray([0] * 1)
    sound_timer = bytearray([0] * 1)
    V           = [bytearray([0] * 1)]*16

    def dump(self, show_memory=True, start=0, end=-1):
        if start == -1:
            start = int.from_bytes(self.pc, 'big')
            end += start
        elif end < 0:
            end = len(self.memory)
        print(f"\t\t===BEGIN DUMP (from {start} to {end})===")
        bytes_per_line = 8
        if show_memory:
            #print(f"memory = {self.memory.hex()}")
            for y in range(start, end, bytes_per_line):
                print(f"{y:#0{5}x}\t| ", end='')
                for x in range(bytes_per_line):
                    print(f"{self.memory[y + x]:#0{4}x} ", end='')
                print("|")
        print("display = ")
        byte_width = 8
        for i in range(0, len(self.display), byte_width):
            print(f"\t{self.display[i:i+byte_width]}")
        bitarray = ''.join(format(byte, '064b') for byte in self.display)
        #bit_width = 64
        #for i in range(0, len(bitarray), bit_width):
            #print(f"\t{i:#0{5}x}: {bitarray[i:i+bit_width]}")

        print(f"pc = {self.pc.hex()} ({int.from_bytes(self.pc, 'big')})")
        print(f"I = {self.I.hex()} ({int.from_bytes(self.I, 'big')})")
        print(f"sp = {self.sp.hex()} ({int.from_bytes(self.sp, 'big')})")
        print(f"delay_timer = {self.delay_timer.hex()} ({int.from_bytes(self.delay_timer, 'big')})")
        print(f"sound_timer = {self.sound_timer.hex()} ({int.from_bytes(self.sound_timer, 'big')})")
        for x in range(len(self.V)):
            print(f"V{x} = {self.V[x].hex()} ({int.from_bytes(self.V[x], 'big')})")
        print("\t\t===END DUMP===")

    def fetch(self):
        pc_dec = unpack('>h', self.pc)[0]
        fetched = self.memory[pc_dec:pc_dec+2]
        self.pc = pack('>H', pc_dec+2)
        return fetched

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
        #bitarray = bin(int.from_bytes(self.display, 'little')).strip('0b').zfill(64*32)
        bitarray = ''.join(format(byte, '08b') for byte in self.display)
        print(f"now rendering {len(bitarray)} pixels: {bitarray = }")
        #draw(SCREEN_WIDTH, SCREEN_HEIGHT, bitarray)

    def cls(self):
        display = bytearray([0] * (8*4)) # 64x32 pixels monochrome
        print(f"[DISM] cls;")

    def jp_addr(self, data):
        jmp_addr = byte_and(data, b'\x0f\xff')
        if unpack('>H', self.pc)[0] == unpack('>H', jmp_addr)[0]+2:
            raise Exception("Halt")
        else:
            self.pc = jmp_addr
        print(f"[DISM] jp {jmp_addr};")

    def ld_vx_byte(self, data):
        x = unpack('<B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        self.V[x] = bytearray([data[1]])
        print(f"[DISM] ld v{x} {hex(data[1])};")

    def add_vx_byte(self, data):
        x = unpack('<B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        #self.V[x] = bytearray([int.from_bytes(self.V[x], 'big') + data[1]])
        self.V[x] = bytearray([unpack('<B', self.V[x])[0] + data[1]])
        print(f"[DISM] add v{x} {data[1]};")

    def ld_i_addr(self, data):
        a = byte_and(data, b'\x0f\xff')
        self.I = a
        print(f"[DISM] ld I {a.hex()};")

    def drw_vx_vy_nibble(self, data):
        x = unpack('>B', byte_and(bytes([data[0]]), b'\x0f'))[0]
        y = unpack('>B', byte_and(bytes([data[1]]), b'\xf0'))[0] >> 4
        n = unpack('>B', byte_and(bytes([data[1]]), b'\x0f'))[0]
        intI = unpack('>H', self.I)[0]
        sprite = self.memory[intI:intI+n]
        here(f"{x = } V[{x}] = {hex(unpack('>B', self.V[x])[0])}, {y = } V[{y}] = {hex(unpack('>B', self.V[y])[0])}, {n = }, {self.I.hex() = }, {intI = }, {sprite = }")
        for i in range(n):
            #self.display[((unpack('>B', self.V[y])[0]+i)//8)*SCREEN_WIDTH//8+unpack('>B', self.V[x])[0]] = sprite[i]
            d_offset = (unpack('>B', self.V[y])[0] * SCREEN_WIDTH//8 + unpack('>B', self.V[x])[0]) // 8 + i
            print(d_offset, len(self.display))
            self.display[d_offset] = sprite[i]
            #print(f"{((y//8)+i//8)*SCREEN_WIDTH//8+x} = {sprite[i]}")
        #input()
        print(f"[DISM] drw v{x} v{y} {n}")



if __name__ == '__main__':
    argv.append('roms/IBM logo.ch8') # FIXME: temporary
    if len(argv) < 2:
        usage(argv[0])
        quit()

    chip = Chip()
    with open(argv[1], 'rb') as f:
        rom = memoryview(chip.memory)
        #rom = bytearray(f.read())
        f.readinto(rom[0x200:])

    chip.dump()
    while True:
        data = chip.fetch()
        try:
            chip.decode_and_execute(data)
        except Exception as e:
            here(traceback.format_exc())
        chip.dump(True, -1, 60)
        chip.render()
        input()
        sleep(1/60)

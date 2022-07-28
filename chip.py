from tui import draw_from_arr as draw
from sys import argv
from time import sleep
from byte_operations import *
from struct import unpack

def usage(argv0):
    print(f"USAGE: python3 {argv0} <rom>")

class Chip:
    memory      = bytearray([0] * 4096)
    display     = bytearray([0] * (8*4)) # 64x32 pixels monochrome
    pc          = bytearray(b'\x02\x00')
    I           = bytearray([0] * 2)
    sp          = bytearray([0] * 2)
    delay_timer = bytearray([0] * 1)
    sound_timer = bytearray([0] * 1)
    V           = [bytearray([0] * 1)]*16

    def dump(self):
        print(f"memory = {self.memory.hex()}")
        print(f"display = {self.display.hex()}")
        print(f"pc = {self.pc.hex()}")
        print(f"I = {self.I.hex()}")
        print(f"sp = {self.sp.hex()}")
        print(f"delay_timer = {self.delay_timer.hex()}")
        print(f"sound_timer = {self.sound_timer.hex()}")
        for x in range(len(self.V)):
            print(f"V{x} = {self.V[x].hex()}")

    def fetch(self):
        pc_dec = unpack('>h', self.pc)[0]
        fetched = self.memory[pc_dec:pc_dec+2]
        #print(f"PC: {hex(self.pc[0])} => {bytes(fetched).hex()}")

        # TODO: fix pc increment with correct data type (yet to be decided)
        self.pc = bytearray([unpack('>H', self.pc)[0] + 2])
        return fetched

    def decode_and_execute(self, data):
        print(f"decoding {data.hex() = }")
        if data == b'\x00\xE0':
            self.cls()
        elif byte_and(data, b'\xF0\x00') == b'\xa0\x00':
            self.ld_i_addr(data)
        elif byte_and(data, b'\xF0\x00') == b'\x60\x00':
            self.ld_vx_byte(data)
        else:
            raise Exception(f"Unimplemented instruction ({data.hex()} @ pc:{hex(self.pc[0])})")

    def render(self):
        draw(self.display)

    def cls(self):
        display = bytearray([0] * (8*4)) # 64x32 pixels monochrome

    def ld_i_addr(self, data):
        self.I = byte_and(data, b'\x0f\xff')

    def ld_vx_byte(self, data):
        x = byte_and(bytes([data[0]]), b'\x0f')
        b = byte_and(data, b'\x00\xff')
        self.V[x] = b

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
    for _ in range(5): # TODO: change to while True:
        data = chip.fetch()
        try:
            chip.decode_and_execute(data)
        except Exception as e:
            print(e)
            quit()

        #chip.render()
        sleep(1/60)

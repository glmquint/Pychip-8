from time import sleep
from sys import stdout
def test():
    print("\033[2J") #clear screen
    print("\033[0;32mOK this is green\033[00m")
    print("\033[0;31mERROR this is red\033[00m")

def draw_from_arr(SCREEN_WIDTH, SCREEN_HEIGHT, arr):
    print("\033[2J", end='') #clear screen
    #print(f"\033[{SCREEN_HEIGHT+2}Bbegin", end='')
    #print(f"\033[{SCREEN_HEIGHT}A", end='')
    to_print = []
    to_print.append("┌")
    for _ in range(2*SCREEN_WIDTH):
        to_print.append("─")
    to_print.append("┐\n")
    to_print.append("|")
    x = 0
    y = 0
    for pixel in arr:
        if pixel == 1:
            to_print.append('▓▓')
        else:
            to_print.append('  ')
        x += 1
        if x == SCREEN_WIDTH:
            x = 0
            y +=1
            to_print.append("|\n")
            if y != SCREEN_HEIGHT:
                to_print.append("|")
    to_print.append("└")
    for _ in range(2*SCREEN_WIDTH):
        to_print.append("─")
    to_print.append("┘")

    print(''.join(to_print))
    #stdout.flush()


if __name__ == "__main__":
    arrs = [
        [
            1, 0, 0,
            0, 0, 0,
            0, 0, 0
        ],
        [
            1, 1, 0,
            0, 0, 0,
            0, 0, 0
        ],
        [
            1, 1, 1,
            0, 0, 0,
            0, 0, 0

        ],
        [
            1, 1, 1,
            0, 0, 1,
            0, 0, 0
        ],
        [
            1, 1, 1,
            0, 0, 1,
            0, 0, 1
        ],
        [
            1, 1, 1,
            0, 0, 1,
            0, 1, 1

        ],
        [
            1, 1, 1,
            0, 0, 1,
            1, 1, 1
        ],
        [
            1, 1, 1,
            1, 0, 1,
            1, 1, 1
        ],
        [
            1, 1, 1,
            1, 1, 1,
            1, 1, 1

        ]
    ]


    for i in range(100):
        for arr in arrs:
            draw_from_arr(3, 3, arr)
            #print('done')
            sleep(1/60)

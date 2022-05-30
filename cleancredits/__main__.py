#!/usr/bin/env python3
import cv2
import os
import argparse

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="the name of the video to be cleaned")
    parser.add_argument("ext", help="the extension of the file")
    parser.add_argument("mask", help="path to the mask")
    parser.add_argument("--radius", help="set interpolation radius")
    parser.add_argument("--framerate", help="set framerate")
    parser.add_argument("--novideo", help="set whether to remux frames into video", action='store_true')

    args = parser.parse_args()

    to_strip = '.' + args.ext

    stripped_name = args.name.rstrip(to_strip)

    os.mkdir(stripped_name)

    if args.framerate:
        name = 'ffmpeg -i ' + args.name + ' -r ' + args.framerate + '/1 ' + stripped_name + '/%03d' + stripped_name + '.png'
        os.system(name)
    else:
        name = 'ffmpeg -i ' + args.name + ' -r 24/1 ' + stripped_name + '/%03d' + stripped_name + '.png'
        print(name)
        os.system(name)

    mask = cv2.imread(args.mask)
    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    path = os.getcwd()

    folder = path + '/' + stripped_name

    files = os.listdir(folder)
    files.sort()

    os.chdir(folder)

    output = folder + '/output'

    os.mkdir(output)

    for f in files:

        print(f)
        orig = cv2.imread(f)

        orig = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)

        if args.radius:
            interp = cv2.inpaint(orig, mask, args.radius, cv2.INPAINT_TELEA)
        else:
            interp = cv2.inpaint(orig, mask, 3, cv2.INPAINT_TELEA)

        interp = cv2.cvtColor(interp, cv2.COLOR_BGR2RGB)

        interp = interp.astype(int)

        os.chdir(output)
        cv2.imwrite(f, interp)

        os.chdir(folder)

    if args.novideo:
        pass
    else:
        os.chdir(output)
        if args.framerate:
            name = 'ffmpeg -framerate ' + args.framerate + ' -i %03d' + stripped_name + '.png -vcodec libx264 -pix_fmt yuv420p ' + stripped_name + '.mp4'
            os.system(name)
        else:
            name = 'ffmpeg -framerate 24 -i %03d' + stripped_name + '.png -vcodec libx264 -pix_fmt yuv420p ' + stripped_name + '.mp4'
            os.system(name)

if __name__ == "__main__":
    main()

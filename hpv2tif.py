#!/usr/bin/env python
#
# hpv2tif - converts Shimadzu HPV2 native (.dat) format to 16-bit TIFF
#
# Meant to be run from command line with single parameteter: The name of the file (including extension) to convert
#
# Todd Hufnagel (hufnagel@jhu)
# 2023-07-28 Original version, based on Jupyter notebook hpv2tif.ipynb. The Shimadzu file format is described
# in the manual for the camera, but the description there is incomplete and confusing in a few respects. More
# details are in the Jupyter notebook, particularly how to extract more of the metadata. This version is 
# bare bones, only intended to do the conversion without worrying about the metadata (although the key)
# parameters are echoed back to the user.

import numpy as np
import array
import sys
from PIL import Image
import tifffile

inputFile = sys.argv[1]
outputFile = inputFile[:-3] + 'tif'
print('Converting file ' + inputFile)

# The .dat file is raw binary, so we read it in as byte string
with open(inputFile, 'rb') as fobj:
    raw_bytes = fobj.read()

# Find data tag for recording speed by searching. The .dat file format has tags that specify the beginning
# of each section. These tags are documented in the manual. We find the relevant section of the byte string
# by searching for the tags and set the offset accordingly. Then there's an additional offset (14 bytes in 
# this section) before the corresponding data begin. Finally, the variable nbytes tells us how many bytes of
# actual data there are.
offset = raw_bytes.find(b'\x30\x30\x07\x30')
offset += 14 # account for the ten bytes of metadata (see below)
nbytes = 4
byte_data=raw_bytes[offset:nbytes+offset]
print('Recording speed: ' + byte_data.decode('ascii') + ' ns')

# If you ever want to see the actual string of bytes, you can do this:
# print(''.join(['\\x%02x' % b for b in byte_data]))

# Find data tag for exposure time by searching
offset = raw_bytes.find(b'\x30\x30\x08\x30')
offset += 14 # account for the 14 bytes of metadata 
nbytes = 4
byte_data=raw_bytes[offset:nbytes+offset]
print('Exposure time: ' + byte_data.decode('ascii') + ' ns')

# Find data tag for time of recording
offset = raw_bytes.find(b'\x40\x40\x0e\x40')
offset += 14 # account for the fourteen bytes of metadata 
nbytes = 16
byte_data=raw_bytes[offset:nbytes+offset]
year = int.from_bytes(byte_data[0:2],byteorder = "little", signed=False)
month = int.from_bytes(byte_data[2:4],byteorder = "little", signed=False)
day = int.from_bytes(byte_data[6:8],byteorder = "little", signed=False)
hour = int.from_bytes( byte_data[8:10], byteorder = "little", signed=False )
minute = int.from_bytes( byte_data[10:12], byteorder = "little", signed=False )
second = int.from_bytes( byte_data[12:14], byteorder = "little", signed=False )
print('Date: ' + str(year) + '-' + str(month).zfill(2) + '-' + str(day).zfill(2) )
print('Time: ' + str(hour).zfill(2) + ':' + str(minute).zfill(2) + ':' + str(second).zfill(2) )

# Find data tag for image data
offset = raw_bytes.find(b'\xa0\xa0\x01\xa0')
offset += 14  # account for 14 bytes of metadata
# Next imageNum x 250 x 400 x 2 bytes are the actual values
imageNum = 128
nbytes = imageNum * 250 * 400 * 2
byte_data=raw_bytes[offset:nbytes+offset]

# Save data as multi-frame TIFF by looping over all of the images.
with tifffile.TiffWriter(outputFile) as tiff:
    for i in range(0,128):
        imagebytes=np.frombuffer(byte_data[i*200000:200000*(i+1)],dtype=np.int16)
        # The data format in the .dat file is 16-bit integers, but that the CMOS chip in the camera
        # is only ten bits. For some reason, rather than simply writing out the raw values when saving the data,
        # the Shimadzu software left-shifts by 6 bits (equivalent to multiplying by 64). To make sure that
        # the converted TIFFs match the true, raw data, we undo that change by right-shifting the data by
        # 6 bits on the next line:
        imagebytes=np.reshape(imagebytes,newshape=(250,400)) >> 6
        imagebytes=np.flipud(imagebytes) # flip vertically to match view in HPV viewer
     
        tiff.save(imagebytes)

print('Saved output as ' + outputFile)
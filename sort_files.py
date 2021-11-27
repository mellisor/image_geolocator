from geopy.geocoders import Nominatim
from geopy import Location
from exif import Image
import os
import argparse
import datetime
import shutil
import time

from srt_parser import SrtParser

def get_location_label(location: Location):
    address = location.raw['address']
    label = address.get('city', '')
    label = label if label else address.get('town', '')
    label = label if label else address.get('county', '')
    return label

def prompt_label(day: str):
    return input(f'Label for {day}: ')

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--label', action='store_true', help='request explicit labels')
parser.add_argument('-i', '--input', default='Files', help='input directory')
parser.add_argument('-o', '--output', default='Output', help='output directory')
parser.add_argument('-s', '--sleep', default=1, type=float, help='time between geolocation requests')
parser.add_argument('-d', '--delete', action='store_true', help='delete old files')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-n', '--num', default=float('inf'), type=float, help='number to copy')
parser.add_argument('-e', '--extensions', nargs='*', help='only process files with these extensions')
parser.add_argument('--srt', action='store_true', help='attempt to find an srt file for each mp4')
args = parser.parse_args()

img_types = ['jpg', 'dng']

# Instantiate the label map. Maps day to a specific label. NOTE: videos will use first label for a day
labels = {}

# Instantiate geolocator if necessary
if not args.label or args.srt:
    geolocator = Nominatim(user_agent="geoapiExercises")

# Instantiate srt parser if necessary
if args.srt:
    srt_parser = SrtParser()

# Tidy up extension args
if args.extensions:
    args.extensions = list(map(lambda x: x.lower().strip('.'), args.extensions))

# Get all contents of input directory and sort it. Currently sorts 
# based on extension to make sure images are processed first (no geo information on videos)
files = os.listdir(args.input)
files.sort(key=lambda x: x.split('.')[-1])

# Make output directory
if not os.path.isdir(args.output):
    os.mkdir(args.output)

num = 0
for file in files:
    # Skip srt files
    if file.lower().endswith('.srt'):
        if args.verbose:
            print(f'Skipping .srt file {file}')
        continue

    # Only process this file if the extension is currently being processed
    if args.extensions:
        extension = file.split('.')[-1]
        if extension.lower() not in args.extensions:
            print(f'Skipping {file} due to extension')
            continue

    # Make sure the specified number of images hasn't been reached
    num += 1
    if num > args.num:
        break

    # Get path of file
    old_file = os.path.join(args.input, file)

    # Print file name
    print(old_file)

    # Default folder name to blank
    folder = ''
    with open(old_file, 'rb') as f:
        # If the file is an image, get the exif timestamp, otherwise get creation date
        is_image = old_file.lower().split('.')[-1] in img_types
        if is_image:
            image = Image(f)
            date = image.get('datetime')
            parsed_date = datetime.datetime.strptime(date, '%Y:%m:%d %H:%M:%S')
            day = str(parsed_date.date())
        else:
            day = str(datetime.datetime.fromtimestamp(os.path.getctime(old_file)).date())
    
        label = ''

        # If explicit label is specified, request one for each day
        if args.label and not day in labels:
            label = prompt_label(day)
            
        # If this is a video and srt is specified
        elif not is_image and args.srt:
            srt_file = ''.join(old_file.split('.')[:-1]) + '.SRT'
            
            # Make sure the srt file exists before continuing
            if os.path.exists(srt_file):
                record = list(srt_parser.parse(srt_file))[0]
                location = geolocator.reverse(f'{record.latitude},{record.longitude}')
                label = get_location_label(location)
                label = label if label else prompt_label(day)
        
        # Attempt to geolocate image
        elif is_image:
            # Get longitude/latitude from geotag
            latitude_ref = image.get('gps_latitude_ref')
            latitude = image.get('gps_latitude')
            longitude_ref = image.get('gps_longitude_ref')
            longitude = image.get('gps_longitude')
            city = None
            
            if latitude is not None and longitude is not None:
                # Calculate longitude/latitude from deg/min/s
                actual_latitude = (latitude[0] + latitude[1] / 60 + latitude[2] / 3600) * (1 if latitude_ref == 'N' else -1)
                actual_longitude = (longitude[0] + longitude[1] / 60 + longitude[2] / 3600) * (1 if longitude_ref == 'E' else -1)

                # Geolocate
                location = geolocator.reverse(f'{actual_latitude},{actual_longitude}')

                # Print location if verbose
                if args.verbose:
                    print(location)

                # Sleep to avoid hitting api limits
                time.sleep(args.sleep)

                # Use the city/town/county as label
                city = get_location_label(location)

            # If a location could be found, set that as the label
            if city:
                label = city
            # If there is already a label for this day, use it
            elif day in labels:
                label = labels[day]
            # Otherwise, request a label
            else:
                label = input(f'Label for {day}: ')

        # If label has not been found, default to first label from this day and prompt for label if not found
        if not label:
            if day in labels:
                label = labels[day]
            
            label = prompt_label(day)
        
        # Populate label map if necessary
        if not day in labels:
            labels[day] = label

        # Join day and label to make folder name, create if needed
        folder = os.path.join(args.output, label + ' ' + day)
        if not os.path.isdir(folder):
            os.mkdir(folder)

    try:
        if args.verbose: 
            print(f'Moving {old_file} to {folder}')
        # Copy or move the file
        if args.delete:
            shutil.move(old_file, folder)
            if args.srt:
                shutil.move(srt_file, folder)
        else:
            shutil.copy(old_file, folder)
            if args.srt:
                shutil.copy(srt_file, folder)
    except Exception as e:
        print(e)

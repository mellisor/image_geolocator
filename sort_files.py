from geopy.geocoders import Nominatim
from exif import Image
import os
import argparse
import datetime
import shutil
import time

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--label', action='store_true', help='request explicit labels')
parser.add_argument('-i', '--input', default='Files', help='input directory')
parser.add_argument('-o', '--output', default='Output', help='output directory')
parser.add_argument('-s', '--sleep', default=1, type=float, help='time between geolocation requests')
parser.add_argument('-d', '--delete', action='store_true', help='delete old files')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-n', '--num', default=float('inf'), type=float, help='number to copy')
parser.add_argument('-e', '--extensions', nargs='*', help='only process files with these extensions')
args = parser.parse_args()

# Instantiate the label map. Maps day to a specific label. NOTE: videos will use first label for a day
labels = {}

# Instantiate geolocator if necessary
if not args.label:
    geolocator = Nominatim(user_agent="geoapiExercises")

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

    # Print file name if verbose
    if args.verbose:
        print(old_file)

    # Default folder name to blank
    folder = ''
    with open(old_file, 'rb') as f:
        # If the file is an image, get the exif timestamp, otherwise get creation date
        is_image = old_file.lower().endswith('.jpg')
        if is_image:
            image = Image(f)
        
            date = image.get('datetime')
            parsed_date = datetime.datetime.strptime(date, '%Y:%m:%d %H:%M:%S')
            day = str(parsed_date.date())
        else:
            day = str(datetime.datetime.fromtimestamp(os.path.getctime(old_file)).date())
    
        label = ''
        # If explicit label is specified, request one
        if (args.label or not is_image) and not day in labels:
            label = input(f'Label for {day}: ')
            labels[day] = label

        # If explicit label is not specified, attempt to geolocate image
        elif not args.label:
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
                address = location.raw['address']
                city = address.get('city', '')
                city = city if city else address.get('town', '')
                city = city if city else address.get('county', '')

            # If a location could be found, set that as the label
            if city:
                label = city
            # If there is already a label for this day, use it
            elif day in labels:
                label = labels[day]
            # Otherwise, request a label
            else:
                label = input(f'Label for {day}: ')
        
        # Populate label map if necessary
        if not day in labels:
            labels[day] = label

        # Join day and label to make folder name, create if needed
        folder = os.path.join(args.output, label + ' ' + day)
        if not os.path.isdir(folder):
            os.mkdir(folder)

    try:
        # Copy or move the file
        if args.delete:
            shutil.move(old_file, folder)
        else:
            shutil.copy(old_file, folder)
    except Exception as e:
        print(e)

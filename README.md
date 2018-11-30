# image-mover
A simple application utility for Moving Docker Images or migrating entire Registries

## Installation
Run as a Docker Container or locally with Python already installed.

## Requirements
Network access to SRC and DST Docker Registries.

## Usage

'image-mover.py -s <source-regsitry>  | -i <list of images> -m <download/sync> -d <destination-registry>'
-s source regsitry
-i list of images (comma separated)
-m mode - <download/sync> choose \'sync\' to fully synchronize Universe Docker Images to another Registry.')
-d destination registry.

Example 1 - Migrate ALL images from one Registry to another.
'image-mover.py -s harbor1.lab.domain.com  -m sync -d harbor2.prod.domain.com'

Example 2 - Migrate a list of images to the target registry to "library" project.
'image-mover.py -l nginx:latest,spotify/kafka:latest,harbor.mylab.home.com/library/hellopks:v2 -m sync -d harbor2.prod.domain.com/library'

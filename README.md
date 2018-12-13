# image-mover
A simple application utility for Moving Docker Images or migrating entire Registries

## Installation
Run as a Docker Container or locally with Python already installed.

## Requirements
If running locally as a script you will need Docker CLI installed.
Network access to SRC and DST Docker Registries.
Only tested with Python 3.6.1

## Usage


## Examples


Example 1 - Migrate ALL images from one Registry to another.
-image-mover.py -s localhost:5000 -m sync -d localhost:5001

Example 2 - Migrate a list of images to the target registry to "library" project.
-image-mover.py -l nginx:latest,kafka:latest,tomcat -m sync -d harbor2.prod.domain.com/library




## Functionality not implemented yet




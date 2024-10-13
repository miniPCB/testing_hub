# Setup Instructions

## Install Adept and Waveforms

1. Download Adept:

https://cloud.digilent.com/myproducts/Adept?pc=1&tab=2&_ga=2.200092138.538781166.1728495812-1235176072.1727884105

2. Download Waveforms:

https://cloud.digilent.com/myproducts/waveform?pc=1&tab=2&_ga=2.94045657.538781166.1728495812-1235176072.1727884105

3. Install the downloaded packages:
   
   For Linux, update your system prior to install. This may take 30 minutes:
   ```bash
   sudo apt-get update
   sudo apt-get upgrade

   Navigate to the Downloads folder:
   ```bash
   cd home/pi/downloads
   
   Install the deb packages:
   ```bash
   sudo dpkg -i digilent.adept.runtime_2.27.9-arm64.deb
   sudo dpkg -i digilent.waveforms_3.23.4_arm64.deb

## Clone Testing Hub Repository

1. Navigate to the `home/pi` directory and clone the `testing_hub` repository:
   ```bash
   git clone git@github.com:Mesa-NManteufel/testing_hub.git

## Run the Testing Hub Application

1. Run `main.py`:
   ```bash
   python3 ./testing_hub/main.py
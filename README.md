# Setup Instructions

## Install Adept and Waveforms

1. Download Adept:

https://cloud.digilent.com/myproducts/Adept?pc=1&tab=2&_ga=2.200092138.538781166.1728495812-1235176072.1727884105

2. Download Waveforms:

https://cloud.digilent.com/myproducts/waveform?pc=1&tab=2&_ga=2.94045657.538781166.1728495812-1235176072.1727884105

3. Install the downloaded packages:
   
   For Linux, update your system prior to install. This may take 30 minutes:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   cd home/pi/downloads
   sudo dpkg -i digilent.adept.runtime_2.27.9-arm64.deb
   sudo dpkg -i digilent.waveforms_3.23.4_arm64.deb

For more information:
https://digilent.com/reference/test-and-measurement/guides/getting-started-with-raspberry-pi?srsltid=AfmBOoo6cd05YITBn0m_ETnegpVOi2YgHLPCr13liVznE5YOUjJ8c1sV

## Clone Testing Hub Repository

1. Navigate to the `home/pi` directory and clone the `testing_hub` repository:
   ```bash
   git clone git@github.com:Mesa-NManteufel/testing_hub.git

## Run the Testing Hub Application

1. Run `main.py`:
   ```bash
   python3 ./testing_hub/main.py

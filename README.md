# PY-TrafficGenerator

This Python Script simulates webtraffic to stress test your own servers.


## ⚠️ Legal Disclaimer:

This stress testing tool is intended solely for use on systems and networks for which you have explicit authorization. Unauthorized stress testing of systems you do not own or have permission to test is illegal and unethical. By using this tool, you agree to comply with all applicable laws and regulations. The developers of this tool are not responsible for any misuse or damages resulting from its use.´

## Start with:
'python traffic_generator.py --video_url http://localhost:8000/ --proxy_file proxies.txt --workers 10'

Parameter Descriptions
## 1. video_url
### Description:
The URL of the video endpoint that will be targeted for the stress test. This endpoint is where the script will send simulated traffic to assess server load handling and access authenticity.

## 2. proxy_file
### Description:
A text file containing a list of proxy server addresses. Each line should include a proxy address in the format IP:PORT or http://IP:PORT. The script utilizes these proxies to mimic requests originating from various sources, thereby creating a more realistic traffic pattern.

## 3. workers
### Description:
Specifies the number of concurrent worker processes that will execute requests simultaneously. Increasing the number of workers enhances the intensity of the load simulation, allowing for a more thorough evaluation of the server's capacity to handle high traffic volumes.

